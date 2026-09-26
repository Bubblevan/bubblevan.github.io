"""Anonymous, isolated Chrome DevTools Protocol reader for public XHS pages.

This module starts the user's installed Chrome with a fresh temporary profile.
It does not use Playwright, cookies, extensions, or direct XHS API requests. It
reads note, comment, profile, and post-card data rendered by the public page.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any


XHS_HOSTS = ("xiaohongshu.com", "xhslink.com", "xhslink.cn")


def find_chrome(executable: str = "") -> str:
    candidates = [executable] if executable else []
    for name in ("chrome.exe", "chrome"):
        found = shutil.which(name)
        if found:
            candidates.append(found)

    for root in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", "")):
        if root:
            candidates.append(str(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe"))
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidates.append(str(Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe"))

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise FileNotFoundError("Google Chrome was not found; pass --chrome-executable with its path")


def is_xhs_url(url: str) -> bool:
    from urllib.parse import urlsplit

    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme.lower() in {"http", "https"} and any(
        host == suffix or host.endswith("." + suffix) for suffix in XHS_HOSTS
    )


def _extract_expression(note_id: str) -> str:
    encoded_id = json.dumps(note_id, ensure_ascii=False)
    return r'''(async () => {
      const expectedId = __NOTE_ID__;
      const safeText = value => (typeof value === "string" || typeof value === "number") ? String(value) : "";
      const pageUrl = location.href;
      const pathMatch = location.pathname.match(/\/(?:explore|discovery\/item)\/([A-Za-z0-9]+)/);
      const noteId = expectedId || (pathMatch ? pathMatch[1] : "");
      const state = window.__INITIAL_STATE__;
      const stateNote = (() => {
        try {
          const direct = state?.note?.noteDetailMap?.[noteId];
          if (direct && typeof direct === "object") return direct.note || direct;
        } catch (_) {}
        if (!state || typeof state !== "object") return null;
        const stack = [state];
        const seen = new WeakSet();
        let visited = 0;
        while (stack.length && visited < 40000) {
          const node = stack.pop();
          if (!node || typeof node !== "object" || seen.has(node)) continue;
          seen.add(node); visited++;
          try {
            const nodeId = safeText(node.noteId || node.note_id || node.id);
            if (nodeId === noteId && (Array.isArray(node.imageList) || node.title || node.desc)) return node.note || node;
            for (const key of Object.keys(node).slice(0, 120)) {
              const child = node[key];
              if (child && typeof child === "object") stack.push(child);
            }
          } catch (_) {}
        }
        return null;
      })();

      const user = stateNote?.user || stateNote?.userInfo || stateNote?.author || {};
      const tagValues = stateNote?.tagList || stateNote?.tags || [];
      const imageValues = stateNote?.imageList || stateNote?.images || [];
      const note = stateNote ? {
        noteId: safeText(stateNote.noteId || stateNote.note_id || stateNote.id || noteId),
        title: safeText(stateNote.title || stateNote.noteTitle || stateNote.displayTitle),
        desc: safeText(stateNote.desc || stateNote.description || stateNote.noteDesc),
        time: stateNote.time ?? stateNote.createTime ?? stateNote.create_time ?? null,
        lastUpdateTime: stateNote.lastUpdateTime ?? null,
        ipLocation: safeText(stateNote.ipLocation || stateNote.ip_location),
        type: safeText(stateNote.type),
        user: {
          nickname: safeText(user.nickname || user.nickName || user.name),
          userId: safeText(user.userId || user.user_id || user.id),
          avatar: safeText(user.avatar || user.image || user.imageb || user.avatarUrl || user.avatar_url)
        },
        interactInfo: stateNote.interactInfo || stateNote.interact_info || {},
        tagList: Array.isArray(tagValues) ? tagValues.map(tag => typeof tag === "string" ? tag : {
          name: safeText(tag?.name || tag?.tagName || tag?.title),
          id: safeText(tag?.id || tag?.tagId || tag?.tag_id)
        }).filter(tag => typeof tag === "string" ? tag : tag.name) : [],
        imageList: Array.isArray(imageValues) ? imageValues.map(image => {
          if (typeof image === "string") return { urlDefault: image };
          const infoList = Array.isArray(image?.infoList) ? image.infoList.map(info => ({
            imageScene: safeText(info?.imageScene), url: safeText(info?.url)
          })) : [];
          return {
            fileId: safeText(image?.fileId || image?.file_id),
            width: image?.width ?? null,
            height: image?.height ?? null,
            urlDefault: safeText(image?.urlDefault || image?.url || image?.originalUrl),
            urlPre: safeText(image?.urlPre || image?.thumbnailUrl),
            infoList
          };
        }) : []
      } : null;

      const bodyText = document.body?.innerText || "";
      const commentRoot = document.querySelector(".comments-container")
        || document.querySelector("[class*=comments-list]")
        || document.querySelector("[class*=comment-list]");
      let commentsText = commentRoot?.innerText || "";
      if (!commentsText) {
        const start = bodyText.search(/共\s*\d+\s*条评论/);
        const end = bodyText.indexOf("登录查看全部评论内容", start < 0 ? 0 : start);
        if (start >= 0) commentsText = bodyText.slice(start, end > start ? end : undefined);
      }
      const comments = [];
      const commentIds = new Set();
      if (state && typeof state === "object" && noteId) {
        const stack = [state];
        const seen = new WeakSet();
        let visited = 0;
        while (stack.length && visited < 40000) {
          const node = stack.pop();
          if (!node || typeof node !== "object" || seen.has(node)) continue;
          seen.add(node); visited++;
          try {
            const refId = safeText(node.noteId || node.note_id);
            const id = safeText(node.id || node.commentId || node.comment_id);
            const content = safeText(node.content || node.text || node.comment);
            if (refId === noteId && id && content && !commentIds.has(id)) {
              const author = node.userInfo || node.user_info || node.user || {};
              const visible = !commentsText || commentsText.includes(content.slice(0, Math.min(24, content.length)));
              if (visible) {
                commentIds.add(id);
                comments.push({
                  comment_id: id,
                  parent_comment_id: safeText(node.targetComment?.id || node.parentCommentId || node.parent_comment_id),
                  content,
                  like_count: node.likeCount ?? node.like_count ?? null,
                  create_time: node.createTime ?? node.create_time ?? null,
                  ip_location: safeText(node.ipLocation || node.ip_location),
                  user: {
                    user_id: safeText(author.userId || author.user_id || author.id),
                    nickname: safeText(author.nickname || author.nickName || author.name),
                    avatar: safeText(author.image || author.avatar || author.avatarUrl || author.avatar_url)
                  },
                  sub_comment_count: node.subCommentCount ?? node.sub_comment_count ?? null,
                  sub_comment_has_more: node.subCommentHasMore ?? node.sub_comment_has_more ?? null
                });
              }
            }
            for (const key of Object.keys(node).slice(0, 120)) {
              const child = node[key];
              if (child && typeof child === "object") stack.push(child);
            }
          } catch (_) {}
        }
      }

      const slideImages = [...document.querySelectorAll(".swiper-slide img")].map(img => ({
        url: img.currentSrc || img.src || img.getAttribute("data-src") || "",
        slide: img.closest(".swiper-slide")?.getAttribute("data-swiper-slide-index") || "",
        width: img.naturalWidth || 0,
        height: img.naturalHeight || 0
      })).filter(img => /^https?:\/\//i.test(img.url));
      const visibleCountMatch = commentsText.match(/共\s*(\d+)\s*条评论/);
      const noteText = document.querySelector("#noteContainer")?.innerText
        || document.querySelector("#detail-desc")?.innerText
        || "";
      const loginWall = /登录查看全部评论内容/.test(bodyText);
      const loginPage = /\/login(?:\/|$)/i.test(location.pathname);
      return JSON.stringify({
        url: pageUrl,
        title: document.title,
        note_id: note?.noteId || noteId,
        note,
        note_text: noteText,
        comments_text: commentsText,
        comments,
        comment_count_label: visibleCountMatch ? Number(visibleCountMatch[1]) : null,
        comments_truncated_by_login: loginWall,
        login_page: loginPage,
        rendered_image_urls: slideImages,
        page_has_note_content: Boolean(note?.title || note?.desc || slideImages.length)
      });
    })()'''.replace("__NOTE_ID__", encoded_id)


def _send_command(ws: Any, command_id: int, method: str, params: dict[str, Any] | None = None, timeout: float = 25) -> dict[str, Any]:
    ws.send(json.dumps({"id": command_id, "method": method, "params": params or {}}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = json.loads(ws.recv())
        if message.get("id") == command_id:
            if "error" in message:
                raise RuntimeError(f"Chrome DevTools {method} failed: {message['error']}")
            return message.get("result", {})
    raise TimeoutError(f"Chrome DevTools timed out during {method}")


def _wait_for_page_target(port: int, process: subprocess.Popen[bytes], timeout: float = 8) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Chrome exited early with status {process.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as response:
                targets = json.load(response)
            page = next((item for item in targets if item.get("type") == "page"), None)
            if page:
                return page
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)
    raise TimeoutError(f"Chrome DevTools page target did not become ready: {last_error or 'no page target'}")


def _connect_page_socket(websocket: Any, port: int, process: subprocess.Popen[bytes], timeout: int) -> Any:
    last_error: Exception | None = None
    for _ in range(4):
        page = _wait_for_page_target(port, process, timeout=3)
        time.sleep(0.5)
        try:
            return websocket.create_connection(
                page["webSocketDebuggerUrl"],
                timeout=timeout,
                suppress_origin=True,
                enable_multithread=True,
            )
        except Exception as exc:
            last_error = exc
            time.sleep(0.35)
    raise RuntimeError(f"Could not attach to the isolated Chrome page: {last_error}")


def _connect_page_session(websocket: Any, port: int, process: subprocess.Popen[bytes], timeout: int) -> Any:
    last_error: Exception | None = None
    for _ in range(3):
        ws = _connect_page_socket(websocket, port, process, timeout)
        try:
            _send_command(ws, 1, "Page.enable", timeout=min(timeout, 8))
            return ws
        except Exception as exc:
            last_error = exc
            try:
                ws.close()
            except Exception:
                pass
            time.sleep(0.5)
    raise RuntimeError(f"Chrome DevTools closed while enabling page access: {last_error}")


def extract_rendered_note(
    url: str,
    note_id: str,
    *,
    cache_dir: Path,
    timeout: int = 35,
    chrome_executable: str = "",
    headless: bool = False,
) -> dict[str, Any]:
    """Read data already rendered by an anonymous XHS note page using CDP."""
    if not is_xhs_url(url):
        raise ValueError("URL must stay on xiaohongshu.com or an xhslink domain")
    try:
        import websocket  # type: ignore[import-not-found]
    except Exception as exc:
        raise RuntimeError("Rendered-page fallback requires the existing websocket-client Python package") from exc

    chrome = find_chrome(chrome_executable)
    profile_parent = cache_dir / "temporary-browser-profiles"
    profile_parent.mkdir(parents=True, exist_ok=True)
    profile_path = Path(tempfile.mkdtemp(prefix="anonymous-", dir=profile_parent))
    process: subprocess.Popen[bytes] | None = None
    ws = None
    try:
        command = [
            chrome,
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-sync",
            "--remote-debugging-port=0",
            "--remote-allow-origins=*",
            "--window-size=1440,1000",
            f"--user-data-dir={profile_path.resolve()}",
        ]
        if headless:
            command.append("--headless=new")
        command.append("about:blank")
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        port_file = profile_path / "DevToolsActivePort"
        deadline = time.monotonic() + min(timeout, 20)
        while time.monotonic() < deadline and not port_file.exists():
            if process.poll() is not None:
                raise RuntimeError(f"Chrome exited early with status {process.returncode}")
            time.sleep(0.2)
        if not port_file.exists():
            raise TimeoutError("Chrome DevTools did not start")

        port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
        ws = _connect_page_session(websocket, port, process, timeout)
        _send_command(ws, 2, "Runtime.enable")
        _send_command(ws, 3, "Page.navigate", {"url": url})
        wait_expression = r'''new Promise(resolve => {
          const start = Date.now();
          const timer = setInterval(() => {
            const text = document.body?.innerText || "";
            const idInPath = /\/(?:explore|discovery\/item)\/[A-Za-z0-9]+/.test(location.pathname);
            const rendered = Boolean(window.__INITIAL_STATE__ || document.querySelector(".swiper-slide img") || text.length > 300);
            if ((document.readyState === "complete" && idInPath && rendered) || Date.now() - start > __TIMEOUT__) {
              clearInterval(timer); resolve(true);
            }
          }, 250);
        })'''.replace("__TIMEOUT__", str(max(5000, timeout * 1000 - 1000)))
        _send_command(
            ws,
            4,
            "Runtime.evaluate",
            {"expression": wait_expression, "awaitPromise": True, "returnByValue": True},
            timeout=timeout + 2,
        )
        evaluated = _send_command(
            ws,
            5,
            "Runtime.evaluate",
            {
                "expression": _extract_expression(note_id),
                "awaitPromise": True,
                "returnByValue": True,
                "userGesture": False,
            },
            timeout=timeout,
        )
        value = evaluated.get("result", {}).get("value")
        if not isinstance(value, str):
            raise RuntimeError("Rendered page returned no serializable note data")
        data = json.loads(value)
        if not is_xhs_url(data.get("url", "")):
            raise RuntimeError("The note link navigated outside Xiaohongshu; extraction stopped")
        if not data.get("page_has_note_content"):
            if data.get("login_page"):
                raise RuntimeError("Anonymous page redirected to a login page; no public note DOM was exposed")
            raise RuntimeError("Anonymous page did not expose note content in its rendered DOM")
        data["retrieval"] = "isolated_anonymous_chrome_cdp"
        data["logged_in"] = False
        data["used_user_profile"] = False
        return data
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        shutil.rmtree(profile_path, ignore_errors=True)


def _extract_profile_expression(expected_user_id: str) -> str:
    encoded_id = json.dumps(expected_user_id, ensure_ascii=False)
    return r'''(() => {
      const pathUserId = location.pathname.match(/\/user\/profile\/([A-Za-z0-9]+)/)?.[1] || "";
      const expectedUserId = __USER_ID__ || pathUserId;
      const text = value => typeof value === "string" || typeof value === "number" ? String(value) : "";
      const unwrap = value => value && typeof value === "object" && value.__v_isRef ? value.value : value;
      const scalarMap = value => {
        if (!value || typeof value !== "object") return {};
        const output = {};
        for (const [key, item] of Object.entries(value)) {
          if (["string", "number", "boolean"].includes(typeof item) || item === null) output[key] = item;
        }
        return output;
      };
      const state = window.__INITIAL_STATE__;
      const userState = state?.user || {};
      const userPageData = unwrap(userState.userPageData) || {};
      const basicInfo = userPageData.basicInfo || {};
      const bodyText = document.body?.innerText || "";
      const interactions = unwrap(userPageData.interactions || userPageData.stats);
      const normalizedStats = Array.isArray(interactions)
        ? interactions.map(item => ({
            type: text(item?.type || item?.name || item?.title || item?.label),
            count: text(item?.count || item?.value || item?.desc)
          })).filter(item => item.type || item.count)
        : scalarMap(interactions);
      const profile = {
        user_id: expectedUserId,
        red_id: text(basicInfo.redId),
        nickname: text(basicInfo.nickname),
        desc: text(basicInfo.desc),
        avatar: text(basicInfo.imageb || basicInfo.images || basicInfo.avatar),
        ip_location: text(basicInfo.ipLocation),
        gender: basicInfo.gender ?? null,
        stats: normalizedStats,
        public_counts: {
          posts: userPageData.posted ?? null,
          liked: userPageData.liked ?? null,
          collected: userPageData.collected ?? null
        }
      };
      const notes = [];
      const noteKeys = new Set();
      const simplifyImages = values => Array.isArray(values) ? values.map(image => {
        if (typeof image === "string") return { url: image };
        const infoList = Array.isArray(image?.infoList) ? image.infoList.map(info => ({
          scene: text(info?.imageScene), url: text(info?.url)
        })).filter(info => info.url) : [];
        return {
          image_id: text(image?.fileId || image?.file_id),
          width: image?.width ?? null, height: image?.height ?? null,
          url: text(image?.urlDefault || image?.url || image?.originalUrl || image?.cover?.url || image?.info?.url),
          variants: infoList
        };
      }) : [];
      const addNote = (entry, sourceIndex) => {
        const raw = unwrap(entry?.noteCard) || unwrap(entry);
        if (!raw || typeof raw !== "object") return;
        const id = text(entry?.noteId || entry?.note_id || entry?.id || raw.noteId || raw.note_id || raw.id);
        if (id === expectedUserId) return;
        const title = text(raw.displayTitle || raw.title || raw.noteTitle || raw.name);
        const cover = raw.cover || raw.coverImage || raw.cover_info || {};
        const coverImage = simplifyImages([cover])[0] || {};
        const images = simplifyImages(raw.imageList || raw.images || raw.image_list);
        const coverUrl = text(cover.url || cover.urlDefault || cover.urlPre || coverImage.url || raw.coverUrl || raw.cover_url);
        if (!(title || images.length || coverUrl)) return;
        const published = raw.time ?? raw.createTime ?? raw.create_time ?? raw.publishTime ?? null;
        const key = id || [title, text(published), coverUrl].join("|");
        if (!key || noteKeys.has(key)) return;
        noteKeys.add(key);
        const stats = scalarMap(raw.interactInfo || raw.interact_info || raw.interactionInfo);
        const user = raw.user || raw.userInfo || {};
        notes.push({
          note_id: id,
          title,
          desc: text(raw.desc || raw.description || raw.noteDesc),
          type: text(raw.type || raw.noteType),
          published_at_raw: published,
          is_pinned: Boolean(raw.isSticky || raw.isTop || raw.sticky || raw.isPinned
            || raw.interactInfo?.sticky || raw.interact_info?.sticky),
          stats,
          images,
          cover: coverImage,
          cover_url: coverUrl,
          author: {
            user_id: text(user.userId || user.user_id || user.id),
            nickname: text(user.nickname || user.nickName || user.name)
          },
          source_index: sourceIndex,
          detail_url: id ? `https://www.xiaohongshu.com/explore/${encodeURIComponent(id)}` : "",
          detail_available_from_profile: Boolean(id)
        });
      };
      const groupedNotes = unwrap(userState.notes);
      const noteGroupCounts = Array.isArray(groupedNotes)
        ? groupedNotes.map(group => {
            const entries = unwrap(group);
            return Array.isArray(entries) ? entries.length : null;
          }) : [];
      let sourceIndex = 0;
      if (Array.isArray(groupedNotes)) {
        for (const group of groupedNotes) {
          const entries = unwrap(group);
          if (!Array.isArray(entries)) continue;
          for (const entry of entries) addNote(entry, sourceIndex++);
        }
      }
      const noteQueries = unwrap(userState.noteQueries);
      const queryRows = Array.isArray(noteQueries) ? noteQueries.map(unwrap) : [];
      const firstQuery = queryRows[0] || {};
      const domCards = [...document.querySelectorAll(".note-item, [class*=note-item]")].map((card, index) => {
        const image = card.querySelector("img");
        return {
          index,
          text: (card.innerText || card.textContent || "").trim().replace(/\s+/g, " ").slice(0, 800),
          cover_url: image?.currentSrc || image?.src || ""
        };
      }).filter(card => card.text || card.cover_url);
      for (const card of domCards) {
        const post = notes[card.index];
        if (post) {
          if (!post.cover_url) post.cover_url = card.cover_url;
          if (!post.title) post.title = card.text;
        }
      }
      const profileNode = document.querySelector('[class*="user-info"], [class*="userInfo"]');
      const avatar = profile.avatar || profileNode?.querySelector("img")?.currentSrc || "";
      const safeUrl = new URL(location.href);
      for (const key of [...safeUrl.searchParams.keys()]) {
        if (/token|secret|sign|auth|session|shareid|share_id|redid/i.test(key)) safeUrl.searchParams.delete(key);
      }
      return JSON.stringify({
        url: safeUrl.href,
        title: document.title,
        login_page: /\/login(?:\/|$)/i.test(location.pathname),
        login_gate_visible: /登录(?:即可|后|查看)/.test(bodyText),
        profile: { ...profile, avatar },
        notes,
        note_card_dom_count: domCards.length,
        pagination: {
          requested_page_size: firstQuery.num ?? null,
          has_more: firstQuery.hasMore ?? null,
          note_groups_loaded: noteGroupCounts
        },
        page_has_profile_content: Boolean(profile.nickname || profile.desc || notes.length || domCards.length),
        extraction_limits: {
          loaded_note_cards: notes.length,
          cards_with_note_id: notes.filter(note => note.note_id).length,
          page_says_more_available: firstQuery.hasMore ?? null
        }
      });
    })()'''.replace("__USER_ID__", encoded_id)


def extract_rendered_profile(
    url: str,
    user_id: str = "",
    *,
    cache_dir: Path,
    timeout: int = 35,
    chrome_executable: str = "",
    headless: bool = False,
    scroll_steps: int = 4,
) -> dict[str, Any]:
    """Inspect a public profile and its already-rendered note cards anonymously."""
    if not is_xhs_url(url):
        raise ValueError("URL must stay on xiaohongshu.com or an xhslink domain")
    try:
        import websocket  # type: ignore[import-not-found]
    except Exception as exc:
        raise RuntimeError("Rendered-page fallback requires the existing websocket-client Python package") from exc

    chrome = find_chrome(chrome_executable)
    profile_parent = cache_dir
    profile_parent.mkdir(parents=True, exist_ok=True)
    profile_path = Path(tempfile.mkdtemp(prefix="anonymous-profile-", dir=profile_parent))
    process: subprocess.Popen[bytes] | None = None
    ws = None
    try:
        command = [
            chrome,
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-sync",
            "--remote-debugging-port=0",
            "--remote-allow-origins=*",
            "--window-size=1440,1000",
            f"--user-data-dir={profile_path.resolve()}",
        ]
        if headless:
            command.append("--headless=new")
        command.append("about:blank")
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        port_file = profile_path / "DevToolsActivePort"
        deadline = time.monotonic() + min(timeout, 20)
        while time.monotonic() < deadline and not port_file.exists():
            if process.poll() is not None:
                raise RuntimeError(f"Chrome exited early with status {process.returncode}")
            time.sleep(0.2)
        if not port_file.exists():
            raise TimeoutError("Chrome DevTools did not start")

        port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
        page = _wait_for_page_target(port, process, timeout=min(timeout, 10))
        time.sleep(0.5)
        ws = websocket.create_connection(
            page["webSocketDebuggerUrl"], timeout=timeout,
            suppress_origin=True, enable_multithread=True,
        )
        _send_command(ws, 1, "Page.enable", timeout=min(timeout, 8))
        _send_command(ws, 2, "Runtime.enable")
        _send_command(ws, 3, "Page.navigate", {"url": url})
        wait_expression = r'''new Promise(resolve => {
          const start = Date.now();
          let readySince = 0;
          const unwrap = value => value && typeof value === "object" && value.__v_isRef ? value.value : value;
          const timer = setInterval(() => {
            const text = document.body?.innerText || "";
            const state = window.__INITIAL_STATE__;
            const user = state?.user || {};
            const pageData = unwrap(user.userPageData) || {};
            const basic = pageData.basicInfo || {};
            const groups = unwrap(user.notes);
            const cards = Array.isArray(groups) ? groups.reduce((sum, group) => {
              const values = unwrap(group);
              return sum + (Array.isArray(values) ? values.length : 0);
            }, 0) : 0;
            const hasProfile = Boolean(basic.nickname || text.includes("小红书号："));
            const hasPosts = cards > 0 || Boolean(document.querySelector(".note-item, [class*=note-item]"));
            const settled = document.readyState === "complete" && /\/user\/profile\//.test(location.pathname)
              && hasProfile && hasPosts;
            if (settled) {
              if (!readySince) readySince = Date.now();
              if (Date.now() - readySince >= 700) { clearInterval(timer); resolve(true); }
            } else readySince = 0;
            if (Date.now() - start > __TIMEOUT__) { clearInterval(timer); resolve(false); }
          }, 250);
        })'''.replace("__TIMEOUT__", str(max(5000, timeout * 1000 - 1000)))
        _send_command(
            ws,
            4,
            "Runtime.evaluate",
            {"expression": wait_expression, "awaitPromise": True, "returnByValue": True},
            timeout=timeout + 2,
        )
        close_modal_expression = r'''(() => {
          const modal = document.querySelector(".login-modal");
          const close = modal?.querySelector(".close-button");
          if (!modal || !close || !/登录即可查看/.test(modal.innerText || "")) return false;
          close.click();
          return true;
        })()'''
        close_result = _send_command(
            ws, 5, "Runtime.evaluate",
            {"expression": close_modal_expression, "returnByValue": True}, timeout=8,
        )
        modal_closed = bool(close_result.get("result", {}).get("value"))
        for index in range(max(0, min(int(scroll_steps), 10))):
            _send_command(
                ws, 6 + index, "Runtime.evaluate",
                {
                    "expression": r'''new Promise(resolve => {
                      const scroller = document.scrollingElement || document.documentElement;
                      scroller.scrollTo({ top: scroller.scrollHeight, behavior: "instant" });
                      setTimeout(() => resolve(true), 850);
                    })''',
                    "awaitPromise": True,
                    "returnByValue": True,
                },
                timeout=4,
            )
        evaluated = _send_command(
            ws,
            20,
            "Runtime.evaluate",
            {"expression": _extract_profile_expression(user_id), "returnByValue": True},
            timeout=timeout,
        )
        value = evaluated.get("result", {}).get("value")
        if not isinstance(value, str):
            raise RuntimeError("Rendered page returned no serializable profile data")
        data = json.loads(value)
        if not is_xhs_url(data.get("url", "")):
            raise RuntimeError("The profile link navigated outside Xiaohongshu; extraction stopped")
        data["retrieval"] = {
            "mode": "isolated_anonymous_chrome_cdp",
            "logged_in": False,
            "used_user_profile": False,
            "login_modal_dismissed": modal_closed,
            "normal_page_scroll_steps": max(0, min(int(scroll_steps), 10)),
        }
        return data
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        shutil.rmtree(profile_path, ignore_errors=True)
