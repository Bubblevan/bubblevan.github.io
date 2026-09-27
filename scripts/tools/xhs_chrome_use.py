"""Read-only acquisition through the existing Chrome via chrome-use.

This adapter never launches a browser or reads cookies/storage. The CLI connects
to the Chrome profile already running for the user and returns a sanitized page
snapshot only.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    from .xhs_note_parser import extract_note_id, redact_url
except ImportError:  # direct invocation
    from xhs_note_parser import extract_note_id, redact_url


XHS_HOST_SUFFIXES = ("xiaohongshu.com", "xhslink.com", "xhslink.cn")
SENSITIVE_QUERY_KEY = re.compile(r"token|secret|sign|auth|session|cookie|code", re.I)
Runner = Callable[..., subprocess.CompletedProcess[str]]


class ChromeUseError(RuntimeError):
    """The existing chrome-use connection could not provide a safe snapshot."""


def is_xhs_url(url: str) -> bool:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme.lower() in {"http", "https"} and any(
        host == suffix or host.endswith("." + suffix) for suffix in XHS_HOST_SUFFIXES
    )


def redact_page_url(url: str) -> str:
    parsed = urlsplit(url)
    kept = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not SENSITIVE_QUERY_KEY.search(key)]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(kept), ""))


def _redact_cli_message(message: str) -> str:
    message = re.sub(
        r"https?://[^\s\"'<>]+",
        lambda match: redact_url(match.group(0)),
        message,
    )
    return re.sub(
        r"([?&](?:xsec_token|token|auth|signature|sign|session|cookie)=)[^&\s]+",
        r"\1[redacted]",
        message,
        flags=re.I,
    )


def _parse_json_output(output: str) -> Any:
    text = re.sub(r"\x1b\[[0-9;]*m", "", output).strip()
    if not text:
        return None
    decoder = json.JSONDecoder()
    try:
        value, end = decoder.raw_decode(text)
        if not text[end:].strip():
            return value
    except json.JSONDecodeError:
        pass
    for index, char in enumerate(text):
        if char not in "[{\"":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
            return value
        except json.JSONDecodeError:
            continue
    return text


def _extension_relay_up(payload: Any) -> bool | None:
    for node in _walk_values(payload):
        if isinstance(node, dict) and isinstance(node.get("relayUp"), bool):
            return node["relayUp"]
    return None


def _walk_values(value: Any, max_nodes: int = 10_000):
    stack = [value]
    seen: set[int] = set()
    count = 0
    while stack and count < max_nodes:
        node = stack.pop()
        if not isinstance(node, (dict, list)):
            continue
        if id(node) in seen:
            continue
        seen.add(id(node))
        count += 1
        yield node
        if isinstance(node, dict):
            stack.extend(reversed(list(node.values())[:200]))
        else:
            stack.extend(reversed(node[:200]))


def _tab_rows(payload: Any) -> list[dict[str, Any]]:
    for node in _walk_values(payload):
        if isinstance(node, list) and node and all(isinstance(item, dict) for item in node):
            if any(any(key in item for key in ("url", "targetId", "tabId", "id")) for item in node):
                return node
    return []


def _tab_reference(tab: dict[str, Any]) -> str:
    for key in ("targetId", "target_id", "tabId", "tab_id", "id", "url"):
        value = tab.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _tab_url(tab: dict[str, Any]) -> str:
    value = tab.get("url")
    if isinstance(value, str):
        return value
    target = tab.get("target")
    return target.get("url", "") if isinstance(target, dict) and isinstance(target.get("url"), str) else ""


def find_matching_tab(payload: Any, url: str) -> dict[str, Any] | None:
    note_id = extract_note_id(url)
    canonical_path = urlsplit(url).path.rstrip("/")
    for tab in _tab_rows(payload):
        tab_url = _tab_url(tab)
        if not is_xhs_url(tab_url):
            continue
        parsed = urlsplit(tab_url)
        if note_id and extract_note_id(tab_url) == note_id:
            return tab
        if not note_id and parsed.path.rstrip("/") == canonical_path:
            return tab
    return None


def find_tab_by_id(payload: Any, tab_id: str) -> dict[str, Any] | None:
    wanted = str(tab_id)
    for tab in _tab_rows(payload):
        if str(tab.get("tabId") or tab.get("tab_id") or "") == wanted:
            return tab
    return None


def _note_route_id(url: str) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() != "https" or host not in {"xiaohongshu.com", "www.xiaohongshu.com"}:
        raise ChromeUseError("TARGET_ORIGIN_MISMATCH: expected the Xiaohongshu web origin")
    if re.match(r"^/login(?:/|$)", parsed.path, flags=re.I):
        raise ChromeUseError("LOGIN_SHELL: navigation resolved to the full login route")
    match = re.fullmatch(r"/explore/([A-Za-z0-9]+)/?", parsed.path)
    if not match:
        raise ChromeUseError("NOTE_ROUTE_MISMATCH: expected /explore/<noteId>")
    return match.group(1)


def _decode_eval_payload(output: str) -> dict[str, Any]:
    value = _parse_json_output(output)
    for _ in range(4):
        if isinstance(value, str):
            try:
                value = json.loads(value)
                continue
            except json.JSONDecodeError:
                break
        if isinstance(value, dict):
            if "snapshot" in value and isinstance(value["snapshot"], dict):
                return value["snapshot"]
            for key in ("value", "result", "data", "output"):
                if key in value and isinstance(value[key], (str, dict)):
                    value = value[key]
                    break
            else:
                return value
            continue
        break
    if isinstance(value, dict):
        return value
    raise ChromeUseError("chrome-use eval did not return a JSON snapshot")


def _safe_note_extractor_js(url: str) -> str:
    expected_id = json.dumps(extract_note_id(url), ensure_ascii=False)
    return r'''(async () => {
      const expectedId = __NOTE_ID__;
      const safeText = value => (typeof value === "string" || (typeof value === "number" && Number.isFinite(value))) ? String(value) : "";
      const safeScalar = value => (typeof value === "string" || typeof value === "boolean" || (typeof value === "number" && Number.isFinite(value))) ? value : null;
      const safeUrl = value => {
        if (typeof value !== "string") return "";
        try {
          const url = new URL(value, location.href);
          for (const key of [...url.searchParams.keys()]) if (/token|secret|sign|auth|session|cookie|code/i.test(key)) url.searchParams.delete(key);
          return /^https?:$/.test(url.protocol) ? url.href : "";
        } catch (_) { return ""; }
      };
      const read = (object, keys) => {
        for (const key of keys) { try { const value = object?.[key]; if (value !== undefined && value !== null && value !== "") return value; } catch (_) {} }
        return null;
      };
      const renderDeadline = Date.now() + 15000;
      while (Date.now() < renderDeadline) {
        let stateReady = false;
        try { stateReady = Boolean(window.__INITIAL_STATE__?.note?.noteDetailMap?.[expectedId]); } catch (_) {}
        const ready = document.readyState === "complete" && (
          stateReady
          || Boolean(document.querySelector("#noteContainer, #detail-desc, .swiper-slide img"))
          || Boolean(document.body?.innerText?.length > 300)
        );
        if (ready) break;
        await new Promise(resolve => setTimeout(resolve, 200));
      }
      const body = document.body?.innerText || "";
      const securityCode = /300011/.test(body) || /账号异常，请稍后重试/.test(body) ? "300011" : /300031/.test(body) ? "300031" : "";
      const security = securityCode === "300011";
      const challenge = /请输入验证码|请完成安全验证|拖动滑块|人机验证|captcha|robot check/i.test(body);
      const rateLimited = /操作过于频繁|请求过于频繁|访问频率|rate limit|too many requests/i.test(body);
      const pageError = security ? "SECURITY_RESTRICTED_300011" : securityCode === "300031" ? "SECURITY_RESTRICTED_300031" : challenge ? "CAPTCHA_CHALLENGE" : rateLimited ? "RATE_LIMITED" : "";
      if (pageError) return JSON.stringify({snapshot_version:1,url:location.origin+location.pathname,title:document.title.slice(0,500),note_id:expectedId||"",note:null,comments:[],comments_text:"",comment_count_label:null,comments_truncated_by_login:false,rendered_image_urls:[],login_page:/\/login(?:\/|$)/i.test(location.pathname),security_code:securityCode,page_error:pageError,page_has_note_content:false});
      const rawState = (() => { try { return window.__INITIAL_STATE__; } catch (_) { return null; } })();
      const pathId = location.pathname.match(/\/(?:explore|discovery\/item)\/([A-Za-z0-9]+)/)?.[1] || "";
      const noteId = expectedId || pathId;
      let rawNote = null;
      let mapId = "";
      if (rawState && typeof rawState === "object") {
        try {
          const direct = rawState?.note?.noteDetailMap?.[noteId];
          if (direct && typeof direct === "object") { rawNote = direct.note || direct; mapId = noteId; }
        } catch (_) {}
        if (!rawNote) {
          const stack = [rawState], seen = new WeakSet();
          let visited = 0;
          while (stack.length && visited < 30000 && !rawNote) {
            const node = stack.pop();
            if (!node || typeof node !== "object" || seen.has(node)) continue;
            seen.add(node); visited++;
            try {
              const detailMap = node.noteDetailMap;
              if (detailMap && typeof detailMap === "object") {
                const entries = Object.entries(detailMap).slice(0, 300);
                for (const [key, detail] of entries) {
                  const item = detail?.note || detail;
                  const id = safeText(read(item, ["noteId", "note_id", "id"])) || key;
                  const candidate = Boolean(read(item, ["title", "noteTitle", "displayTitle", "desc", "description", "imageList", "images"]));
                  if (candidate && ((!noteId && entries.length === 1) || (noteId && id === noteId))) { rawNote = item; mapId = key; break; }
                }
              }
              if (rawNote) break;
              const id = safeText(read(node, ["noteId", "note_id", "id"]));
              if (id === noteId && read(node, ["title", "noteTitle", "displayTitle", "desc", "description", "imageList", "images"])) { rawNote = node.note || node; break; }
              const keys = Object.keys(node).slice(0, 120);
              for (const key of keys) { const child = node[key]; if (child && typeof child === "object") stack.push(child); }
            } catch (_) {}
          }
        }
      }
      const rawUser = read(rawNote, ["user", "userInfo", "author"]) || {};
      const rawTags = read(rawNote, ["tagList", "tags", "hashTag"]);
      const rawImages = read(rawNote, ["imageList", "images", "image_list"]);
      const note = rawNote ? {
        noteId: safeText(read(rawNote, ["noteId", "note_id", "id"])) || noteId || mapId,
        title: safeText(read(rawNote, ["title", "noteTitle", "displayTitle"])),
        desc: safeText(read(rawNote, ["desc", "description", "noteDesc"])),
        time: safeScalar(read(rawNote, ["time", "createTime", "create_time"])),
        ipLocation: safeText(read(rawNote, ["ipLocation", "ip_location"])),
        type: safeText(read(rawNote, ["type", "noteType"])),
        user: {
          nickname: safeText(read(rawUser, ["nickname", "nickName", "name"])),
          userId: safeText(read(rawUser, ["userId", "user_id", "id"])),
          avatar: safeUrl(read(rawUser, ["avatar", "image", "imageb", "avatarUrl", "avatar_url"]))
        },
        interactInfo: (() => {
          const source = read(rawNote, ["interactInfo", "interact_info"]) || {};
          const out = {};
          for (const key of ["likedCount", "likeCount", "liked_count", "collectedCount", "collectCount", "collected_count", "commentCount", "commentsCount", "comment_count"]) {
            const value = read(source, [key]);
            if (["string", "number", "boolean"].includes(typeof value)) out[key] = value;
          }
          return out;
        })(),
        tagList: Array.isArray(rawTags) ? rawTags.slice(0, 500).map(tag => typeof tag === "string" ? tag : {
          name: safeText(read(tag, ["name", "tagName", "title"])),
          id: safeText(read(tag, ["id", "tagId", "tag_id"]))
        }).filter(tag => typeof tag === "string" ? tag : tag.name) : [],
        imageList: Array.isArray(rawImages) ? rawImages.slice(0, 500).map(image => {
          if (typeof image === "string") return { urlDefault: safeUrl(image) };
          const infos = read(image, ["infoList"]);
          return {
            fileId: safeText(read(image, ["fileId", "file_id"])),
            width: typeof read(image, ["width"]) === "number" ? read(image, ["width"]) : null,
            height: typeof read(image, ["height"]) === "number" ? read(image, ["height"]) : null,
            urlDefault: safeUrl(read(image, ["urlDefault", "url", "originalUrl"])),
            urlPre: safeUrl(read(image, ["urlPre", "thumbnailUrl"])),
            infoList: Array.isArray(infos) ? infos.slice(0, 50).map(info => ({ imageScene: safeText(read(info, ["imageScene"])), url: safeUrl(read(info, ["url"])) })).filter(info => info.url) : []
          };
        }).filter(image => image.urlDefault || image.urlPre || image.infoList?.length) : []
      } : null;
      const commentNode = document.querySelector(".comments-container, [class*=comments-list], [class*=comment-list]");
      const commentsText = (commentNode?.innerText || "").slice(0, 50000);
      const countMatch = commentsText.match(/共\s*(\d+)\s*条评论/) || body.match(/共\s*(\d+)\s*条评论/);
      const images = [...document.querySelectorAll(".swiper-slide img")].slice(0, 500).map(img => ({ url: safeUrl(img.currentSrc || img.src || img.getAttribute("data-src")), width: img.naturalWidth || 0, height: img.naturalHeight || 0 })).filter(image => image.url);
      const cleanUrl = location.origin + location.pathname;
      return JSON.stringify({
        snapshot_version: 1,
        url: cleanUrl,
        title: document.title.slice(0, 500),
        note_id: note?.noteId || noteId || mapId,
        note,
        comments: [],
        comments_text: commentsText,
        comment_count_label: countMatch ? Number(countMatch[1]) : null,
        comments_truncated_by_login: /登录查看全部评论内容/.test(body),
        rendered_image_urls: images,
        login_page: /\/login(?:\/|$)/i.test(location.pathname),
        security_code: security ? "300011" : "",
        page_error: pageError,
        page_has_note_content: Boolean(note?.title || note?.desc || note?.imageList?.length || images.length)
      });
    })()'''.replace("__NOTE_ID__", expected_id)


def _safe_profile_extractor_js(url: str) -> str:
    expected_user_id = re.search(r"/user/profile/([A-Za-z0-9]+)", urlsplit(url).path)
    encoded_id = json.dumps(expected_user_id.group(1) if expected_user_id else "", ensure_ascii=False)
    return r'''(async () => {
      const expectedId = __USER_ID__;
      const text = value => (typeof value === "string" || (typeof value === "number" && Number.isFinite(value))) ? String(value) : "";
      const safeScalar = value => (typeof value === "string" || typeof value === "boolean" || (typeof value === "number" && Number.isFinite(value))) ? value : null;
      const safeUrl = value => { if (typeof value !== "string") return ""; try { const u = new URL(value, location.href); for (const k of [...u.searchParams.keys()]) if (/token|secret|sign|auth|session|cookie|code/i.test(k)) u.searchParams.delete(k); return /^https?:$/.test(u.protocol) ? u.href : ""; } catch (_) { return ""; } };
      const read = (object, keys) => { for (const key of keys) { try { const value = object?.[key]; if (value !== undefined && value !== null && value !== "") return value; } catch (_) {} } return null; };
      const unwrap = value => { try { return value && typeof value === "object" && value.__v_isRef ? value.value : value; } catch (_) { return value; } };
      const renderDeadline = Date.now() + 15000;
      while (Date.now() < renderDeadline) {
        let stateReady = false;
        try {
          const root = window.__INITIAL_STATE__?.user || {};
          const page = unwrap(read(root, ["userPageData"])) || {};
          const info = read(page, ["basicInfo"]) || {};
          const groups = unwrap(read(root, ["notes"])) || [];
          stateReady = Boolean(read(info, ["nickname"]) && Array.isArray(groups) && groups.some(group => Array.isArray(unwrap(group)) && unwrap(group).length));
        } catch (_) {}
        const profileMarker = Boolean(document.querySelector("[class*=user-info],[class*=userInfo]")) || (document.body?.innerText || "").includes("小红书号");
        const domCardsReady = Boolean(document.querySelector(".note-item,[class*=note-item]"));
        const routeReady = /\/user\/profile\//.test(location.pathname);
        if (document.readyState === "complete" && routeReady && (stateReady || (profileMarker && domCardsReady))) break;
        await new Promise(resolve => setTimeout(resolve, 200));
      }
      const body = document.body?.innerText || "";
      const security = /300011.{0,20}(?:异常|安全|风险|限制)|(?:异常|安全|风险|限制).{0,20}300011/i.test(body) || /账号异常，请稍后重试/.test(body);
      const challenge = /请输入验证码|请完成安全验证|拖动滑块|人机验证|captcha|robot check/i.test(body);
      const rateLimited = /操作过于频繁|请求过于频繁|访问频率|rate limit|too many requests/i.test(body);
      const pageError = security ? "SECURITY_RESTRICTED_300011" : challenge ? "CAPTCHA_CHALLENGE" : rateLimited ? "RATE_LIMITED" : "";
      if (pageError) return JSON.stringify({snapshot_version:1,url:location.origin+location.pathname,title:document.title.slice(0,500),profile:{user_id:expectedId},notes:[],note_card_dom_count:0,pagination:{},page_has_profile_content:false,login_page:/\/login(?:\/|$)/i.test(location.pathname),security_code:security?"300011":"",page_error:pageError});
      const state = (() => { try { return window.__INITIAL_STATE__; } catch (_) { return null; } })();
      const root = read(state, ["user"]) || {};
      const page = unwrap(read(root, ["userPageData"])) || {};
      const info = read(page, ["basicInfo"]) || {};
      const userId = expectedId || text(read(info, ["userId", "user_id", "id"]));
      const interactions = unwrap(read(page, ["interactions", "stats"]));
      const stats = Array.isArray(interactions) ? interactions.slice(0, 100).map(item => ({type: text(read(item,["type","name","title","label"])),count: text(read(item,["count","value","desc"]))})) : {};
      const groups = unwrap(read(root, ["notes"])) || [];
      const notes = [], seen = new Set();
      const groupsOut = Array.isArray(groups) ? groups.slice(0, 100).map(unwrap) : [];
      let sourceIndex = 0;
      for (const group of groupsOut) {
        if (!Array.isArray(group)) continue;
        for (const entry of group.slice(0, 1000)) {
          const raw = unwrap(read(entry, ["noteCard"])) || unwrap(entry);
          if (!raw || typeof raw !== "object") { sourceIndex++; continue; }
          // Profile-feed entries may expose a row/index `id` before the nested
          // noteCard.noteId. Prefer the canonical noteCard ID and unwrap Vue
          // refs before turning the value into a string.
          const id = text(unwrap(read(raw,["noteId","note_id","id"])) || unwrap(read(entry,["noteId","note_id","id"])));
          const title = text(read(raw,["displayTitle","title","noteTitle","name"]));
          const cover = read(raw,["cover","coverImage","cover_info"]) || {};
          const coverUrl = safeUrl(read(cover,["url","urlDefault","urlPre"]) || read(raw,["coverUrl","cover_url"]));
          const images = read(raw,["imageList","images","image_list"]);
          const published = read(raw,["time","createTime","create_time","publishTime"]);
          const key = id || [title, text(published), coverUrl].join("|");
          if (key && !seen.has(key) && (title || coverUrl || Array.isArray(images))) {
            seen.add(key);
            const author = read(raw,["user","userInfo"]) || {};
            const count = read(raw,["interactInfo","interact_info","interactionInfo"]) || {};
            const safeStats = {};
            for (const k of ["likedCount","likeCount","collectedCount","collectCount","commentCount"]) { const v=read(count,[k]); if (["string","number"].includes(typeof v)) safeStats[k]=v; }
            notes.push({note_id:id,title,desc:text(read(raw,["desc","description","noteDesc"])),type:text(read(raw,["type","noteType"])),published_at_raw:typeof published === "number" ? published : null,stats:safeStats,cover_url:coverUrl,source_index:sourceIndex,detail_url:id?`https://www.xiaohongshu.com/explore/${encodeURIComponent(id)}`:"",author:{user_id:text(read(author,["userId","user_id","id"])),nickname:text(read(author,["nickname","nickName","name"]))}});
          }
          sourceIndex++;
        }
      }
      const queryRows = unwrap(read(root,["noteQueries"])) || [];
      const firstQuery = Array.isArray(queryRows) ? unwrap(queryRows[0]) || {} : {};
      const cards = [...document.querySelectorAll(".note-item,[class*=note-item]")].slice(0,1000).map(card => ({text:(card.innerText||card.textContent||"").trim().replace(/\s+/g," ").slice(0,800),cover_url:safeUrl(card.querySelector("img")?.currentSrc||card.querySelector("img")?.src||"")}));
      for (let index = 0; index < cards.length; index++) {
        const card = cards[index], post = notes[index];
        if (post) {
          if (!post.cover_url) post.cover_url = card.cover_url;
          if (!post.title) post.title = card.text;
        } else if (card.text || card.cover_url) {
          notes.push({note_id:"",title:card.text,desc:"",type:"",published_at_raw:null,stats:{},cover_url:card.cover_url,source_index:index,detail_url:"",author:{user_id:"",nickname:""}});
        }
      }
      const profileUrl = location.origin + location.pathname;
      return JSON.stringify({snapshot_version:1,url:profileUrl,title:document.title.slice(0,500),profile:{user_id:userId,red_id:text(read(info,["redId"])),nickname:text(read(info,["nickname"])),desc:text(read(info,["desc"])),avatar:safeUrl(read(info,["imageb","images","avatar"])),ip_location:text(read(info,["ipLocation"])),gender:safeScalar(read(info,["gender"])),stats,public_counts:{posts:safeScalar(read(page,["posted"])),liked:safeScalar(read(page,["liked"])),collected:safeScalar(read(page,["collected"])) }},notes,note_card_dom_count:cards.length,pagination:{requested_page_size:safeScalar(read(firstQuery,["num"])),has_more:safeScalar(read(firstQuery,["hasMore"])),note_groups_loaded:groupsOut.map(group=>Array.isArray(group)?group.length:null)},page_has_profile_content:Boolean(info.nickname||notes.length||cards.length),login_page:/\/login(?:\/|$)/i.test(location.pathname),security_code:security?"300011":"",page_error:pageError});
    })()'''.replace("__USER_ID__", encoded_id)


class ChromeUseClient:
    def __init__(
        self,
        executable: str = "chrome-use",
        timeout: int = 45,
        runner: Runner = subprocess.run,
        session: str = "",
    ):
        self.executable = executable
        self.timeout = timeout
        self.runner = runner
        self.session = session.strip()
        self._pinned_target_id = ""

    def _run(self, args: Sequence[str], *, input_text: str | None = None) -> str:
        command = [self.executable]
        if self.session:
            command.extend(["--session", self.session])
        command.extend(["--json", *args])
        try:
            result = self.runner(
                command,
                input=input_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ChromeUseError("chrome-use was not found; install and connect it to the existing Agent Chrome profile") from exc
        except subprocess.TimeoutExpired as exc:
            raise ChromeUseError(f"chrome-use command timed out: {args[0] if args else 'unknown command'}") from exc
        if result.returncode:
            # Do not surface the complete command or raw page URL: either can contain a share token.
            message = _redact_cli_message((result.stderr or result.stdout or "command failed").strip())[:600]
            raise ChromeUseError(f"chrome-use {args[0] if args else 'command'} failed ({result.returncode}): {message}")
        return result.stdout or ""

    def _target_tab(self, url: str) -> dict[str, Any] | None:
        tabs = _parse_json_output(self._run(["tab", "list"]))
        return find_matching_tab(tabs, url)

    def _require_live_relay(self) -> None:
        status = _parse_json_output(self._run(["status"]))
        if _extension_relay_up(status) is not True:
            raise ChromeUseError("RELAY_DISCONNECTED: chrome-use extension relay is down; stopping without reconnecting")

    def _tab_by_id(self, tab_id: str) -> dict[str, Any] | None:
        return find_tab_by_id(_parse_json_output(self._run(["tab", "list"])), tab_id)

    def pin_existing_tab(self, tab_id: str) -> dict[str, Any]:
        """Pin the user's already adopted XHS tab; this never navigates it."""
        self._require_live_relay()
        tab = self._tab_by_id(tab_id)
        if not tab:
            raise ChromeUseError(f"PINNED_TAB_NOT_FOUND: no existing Chrome tab matches {tab_id}")
        if tab.get("ownership") != "adopted":
            raise ChromeUseError("PINNED_TAB_NOT_ADOPTED: refusing to take ownership of a different tab")
        current_url = _tab_url(tab)
        if not is_xhs_url(current_url):
            raise ChromeUseError("PINNED_TAB_NOT_XHS: the adopted tab is not on Xiaohongshu")
        current_note_id = _note_route_id(current_url)
        target_id = str(tab.get("targetId") or tab.get("target_id") or "")
        if not target_id:
            raise ChromeUseError("PINNED_TAB_NO_TARGET: existing tab has no stable target identifier")
        self._run(["tab", "adopt", target_id])
        self._run(["tab", "select", tab_id])
        selected = self._tab_by_id(tab_id)
        if not selected or str(selected.get("targetId") or selected.get("target_id") or "") != target_id:
            raise ChromeUseError("PINNED_TAB_CHANGED: selected tab no longer refers to the original Chrome target")
        if selected.get("ownership") != "adopted" or selected.get("relayAttached") is not True:
            raise ChromeUseError("PINNED_TAB_NOT_ATTACHED: existing adopted tab is not attached to the live relay")
        probe = _decode_eval_payload(
            self._run(
                ["eval", "--stdin"],
                input_text="JSON.stringify({url: location.origin + location.pathname, title: document.title})",
            )
        )
        probe_url = str(probe.get("url") or "") if isinstance(probe, dict) else ""
        if _note_route_id(probe_url) != current_note_id:
            raise ChromeUseError("PINNED_TAB_CONTEXT_MISMATCH: read-only page probe did not match the adopted XHS tab")
        self._pinned_target_id = target_id
        return {
            "tab_id": tab_id,
            "target_id": target_id,
            "note_id": current_note_id,
            "ownership": str(selected.get("ownership") or ""),
            "relay_attached_reported": selected.get("relayAttached"),
            "relay_up": True,
        }

    def navigate_pinned_note(self, url: str, tab_id: str) -> dict[str, Any]:
        """Navigate one original share URL in the fixed adopted tab and verify it before extraction."""
        expected_id = extract_note_id(url)
        if not expected_id:
            raise ChromeUseError("NOTE_ID_MISSING: original share URL has no readable note ID")
        if not is_xhs_url(url):
            raise ChromeUseError("UNSUPPORTED_URL: expected a Xiaohongshu share URL")
        self._require_live_relay()
        tab = self._tab_by_id(tab_id)
        if not tab or tab.get("ownership") != "adopted":
            raise ChromeUseError("PINNED_TAB_LOST: the adopted Chrome tab is no longer available")
        if tab.get("relayAttached") is not True:
            raise ChromeUseError("PINNED_TAB_NOT_ATTACHED: adopted tab is no longer attached to the live relay")
        current_target_id = str(tab.get("targetId") or tab.get("target_id") or "")
        if not self._pinned_target_id or current_target_id != self._pinned_target_id:
            raise ChromeUseError("PINNED_TAB_CHANGED: refusing to navigate a replacement tab")

        # Select the same tab before each navigation. `open <url>` then reuses
        # that selected page in the already-connected Chrome session.
        self._run(["tab", "select", tab_id])
        self._run(["open", url])
        after = self._tab_by_id(tab_id)
        if not after or str(after.get("targetId") or after.get("target_id") or "") != self._pinned_target_id:
            raise ChromeUseError("PINNED_TAB_CHANGED: navigation did not remain in the adopted target")
        if after.get("ownership") != "adopted" or after.get("relayAttached") is not True:
            raise ChromeUseError("PINNED_TAB_NOT_ATTACHED: navigation lost the adopted tab relay attachment")
        current_url = _tab_url(after)
        if _note_route_id(current_url) != expected_id:
            raise ChromeUseError("NOTE_ID_MISMATCH: navigation did not land on the requested /explore/<noteId>")

        self._run(["snapshot", "-i"])
        snapshot = _decode_eval_payload(self._run(["eval", "--stdin"], input_text=_safe_note_extractor_js(url)))
        snapshot_url = str(snapshot.get("url") or "")
        if _note_route_id(snapshot_url) != expected_id:
            raise ChromeUseError("NOTE_ID_MISMATCH: sanitized page snapshot did not match the requested note")
        if str(snapshot.get("note_id") or "") != expected_id:
            raise ChromeUseError("NOTE_ID_MISMATCH: page runtime state returned a different note ID")
        if snapshot.get("login_page"):
            raise ChromeUseError("LOGIN_SHELL: page resolved to a login route")
        if snapshot.get("page_error"):
            raise ChromeUseError(str(snapshot["page_error"]))
        if not snapshot.get("page_has_note_content"):
            raise ChromeUseError("NOTE_CONTENT_MISSING: the page has no rendered note data")
        return snapshot

    def _select_page(self, url: str) -> None:
        relay_up = False
        for attempt in range(2):
            status = _parse_json_output(self._run(["status"]))
            relay_up = _extension_relay_up(status) is True
            if relay_up:
                break
            if attempt == 0:
                # The extension service worker can report a brief stale-down
                # state while it reconnects. Recheck once; never start Chrome.
                time.sleep(0.35)
        if not relay_up:
            raise ChromeUseError(
                "chrome-use extension relay is not connected; refusing to start or select another browser profile. "
                "Connect the intended existing Chrome profile, then retry."
            )
        tab = self._target_tab(url)
        if tab:
            ref = _tab_reference(tab)
            if not ref:
                raise ChromeUseError("chrome-use listed a matching tab without an adoptable reference")
            self._run(["tab", "adopt", ref])
        else:
            # `open` navigates in the already-running Chrome; it does not launch Chrome.
            self._run(["open", url])
        self._run(["snapshot", "-i"])

    def eval_json(self, url: str, expression: str) -> dict[str, Any]:
        if not is_xhs_url(url):
            raise ValueError("URL must use xiaohongshu.com or xhslink domains")
        self._select_page(url)
        output = self._run(["eval", "--stdin"], input_text=expression)
        return _decode_eval_payload(output)


def _cache_path(cache_dir: Path, url: str) -> Path:
    note_id = extract_note_id(url)
    safe_name = note_id or hashlib.sha256(redact_url(url).encode("utf-8")).hexdigest()[:16]
    return cache_dir / f"{safe_name}-runtime-snapshot.json"


def acquire_note_snapshot(
    url: str,
    *,
    cache_dir: Path,
    cli: str = "chrome-use",
    timeout: int = 45,
    client: ChromeUseClient | None = None,
) -> tuple[dict[str, Any], Path]:
    if not is_xhs_url(url):
        raise ValueError("URL must use xiaohongshu.com or xhslink domains")
    cache_dir.mkdir(parents=True, exist_ok=True)
    browser = client or ChromeUseClient(cli, timeout)
    snapshot = browser.eval_json(url, _safe_note_extractor_js(url))
    if snapshot.get("snapshot_version") != 1:
        raise ChromeUseError("chrome-use returned an unsupported sanitized note snapshot")
    snapshot["url"] = redact_page_url(str(snapshot.get("url") or url))
    path = _cache_path(cache_dir, url)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snapshot, path


def pin_existing_tab(
    tab_id: str,
    *,
    cli: str = "chrome-use",
    timeout: int = 45,
    session: str = "",
    client: ChromeUseClient | None = None,
) -> dict[str, Any]:
    browser = client or ChromeUseClient(cli, timeout, session=session)
    return browser.pin_existing_tab(tab_id)


def acquire_pinned_note_snapshot(
    url: str,
    *,
    tab_id: str,
    cache_dir: Path,
    cli: str = "chrome-use",
    timeout: int = 45,
    session: str = "",
    client: ChromeUseClient | None = None,
) -> tuple[dict[str, Any], Path]:
    if not is_xhs_url(url):
        raise ValueError("URL must use xiaohongshu.com or an xhslink domain")
    cache_dir.mkdir(parents=True, exist_ok=True)
    browser = client or ChromeUseClient(cli, timeout, session=session)
    snapshot = browser.navigate_pinned_note(url, tab_id)
    snapshot["url"] = redact_page_url(str(snapshot.get("url") or url))
    path = _cache_path(cache_dir, url)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snapshot, path


def _run_profile_scrolls(client: ChromeUseClient, scroll_steps: int) -> None:
    for _ in range(max(0, min(int(scroll_steps), 10))):
        client._run(["scroll", "down", "800"])
        client._run(["wait", "700"])


def acquire_profile_snapshot(
    url: str,
    *,
    cache_dir: Path,
    cli: str = "chrome-use",
    timeout: int = 45,
    scroll_steps: int = 4,
    client: ChromeUseClient | None = None,
) -> tuple[dict[str, Any], Path]:
    if not is_xhs_url(url):
        raise ValueError("URL must use xiaohongshu.com or xhslink domains")
    cache_dir.mkdir(parents=True, exist_ok=True)
    browser = client or ChromeUseClient(cli, timeout)
    browser._select_page(url)
    _run_profile_scrolls(browser, scroll_steps)
    snapshot = _decode_eval_payload(browser._run(["eval", "--stdin"], input_text=_safe_profile_extractor_js(url)))
    if snapshot.get("snapshot_version") != 1:
        raise ChromeUseError("chrome-use returned an unsupported sanitized profile snapshot")
    snapshot["url"] = redact_page_url(str(snapshot.get("url") or url))
    profile_id = str((snapshot.get("profile") or {}).get("user_id") or "")
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", profile_id)[:80]
    safe_name = safe_name or hashlib.sha256(redact_url(url).encode("utf-8")).hexdigest()[:16]
    path = cache_dir / f"{safe_name}-profile-snapshot.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snapshot, path
