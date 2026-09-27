"""Pure parsers and normalizers for saved Xiaohongshu page data.

This module has no network, filesystem, subprocess, or browser dependencies.
Acquisition layers pass HTML, JSON state, or a sanitized rendered snapshot in.
"""

from __future__ import annotations

from datetime import datetime, timezone
import html as html_lib
import json
import re
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit


SENSITIVE_QUERY_KEY = re.compile(r"token|secret|sign|auth|session|cookie|code", re.I)
NOTE_ID_PATTERNS = (
    re.compile(r"/discovery/item/([A-Za-z0-9]+)"),
    re.compile(r"/explore/([A-Za-z0-9]+)"),
    re.compile(r"[?&]note_id=([A-Za-z0-9]+)"),
    re.compile(r"[?&]noteId=([A-Za-z0-9]+)"),
)
MAX_STATE_NODES = 50_000


def redact_url(url: str, depth: int = 0) -> str:
    parsed = urlsplit(url)
    query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        query.append((key, "[redacted]" if SENSITIVE_QUERY_KEY.search(key) else value))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def extract_first_url(value: str) -> str:
    match = re.search(r'https?://[^\s<>"]+', value)
    if not match:
        return value.strip()
    return match.group(0).rstrip("，。),)]}")


def extract_note_id(url: str) -> str:
    for pattern in NOTE_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return ""


def find_js_value_after_marker(text: str, marker: str = "window.__INITIAL_STATE__") -> str:
    marker_index = text.find(marker)
    if marker_index < 0:
        raise ValueError("INITIAL_STATE_NOT_FOUND: window.__INITIAL_STATE__ is absent")
    equals_index = text.find("=", marker_index + len(marker))
    if equals_index < 0:
        raise ValueError("INITIAL_STATE_INVALID: assignment has no equals sign")
    start = equals_index + 1
    while start < len(text) and text[start].isspace():
        start += 1

    if text.startswith("JSON.parse", start):
        paren = text.find("(", start)
        if paren < 0:
            raise ValueError("INITIAL_STATE_INVALID: malformed JSON.parse call")
        value_start = paren + 1
        while value_start < len(text) and text[value_start].isspace():
            value_start += 1
        quote = text[value_start] if value_start < len(text) else ""
        if quote not in {"'", '"'}:
            raise ValueError("INITIAL_STATE_INVALID: JSON.parse argument is not a string")
        end = value_start + 1
        escaped = False
        while end < len(text):
            char = text[end]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                raw_js_string = text[value_start : end + 1]
                return json.loads("[" + sanitize_js_object(raw_js_string) + "]")[0]
            end += 1
        raise ValueError("INITIAL_STATE_INVALID: unterminated JSON.parse string")

    starts = [position for position in (text.find("{", start), text.find("[", start)) if position >= 0]
    if not starts:
        raise ValueError("INITIAL_STATE_INVALID: assignment has no object or array")
    start = min(starts)
    stack: list[str] = []
    quote = ""
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
        elif char in "{[":
            stack.append("}" if char == "{" else "]")
        elif char in "}]":
            if not stack or char != stack[-1]:
                raise ValueError("INITIAL_STATE_INVALID: unbalanced object delimiters")
            stack.pop()
            if not stack:
                return text[start : index + 1]
    raise ValueError("INITIAL_STATE_INVALID: unterminated object")


def sanitize_js_object(source: str) -> str:
    """Convert a small JSON-like JS literal to JSON without editing string data."""
    source = html_lib.unescape(source).replace("\\u002F", "/")
    out: list[str] = []
    index = 0
    quote = ""
    escaped = False
    while index < len(source):
        char = source[index]
        if quote:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            index += 1
            continue
        if char == '"':
            quote = char
            out.append(char)
            index += 1
            continue
        if char == "'":
            index += 1
            value: list[str] = []
            while index < len(source):
                current = source[index]
                if current == "'":
                    index += 1
                    break
                if current != "\\":
                    value.append(current)
                    index += 1
                    continue
                index += 1
                if index >= len(source):
                    raise ValueError("INITIAL_STATE_INVALID: unfinished escape in JS string")
                escape = source[index]
                simple = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
                if escape in simple:
                    value.append(simple[escape])
                    index += 1
                elif escape in {"'", '"', "\\", "/"}:
                    value.append(escape)
                    index += 1
                elif escape == "u" and index + 4 < len(source):
                    value.append(chr(int(source[index + 1 : index + 5], 16)))
                    index += 5
                elif escape == "x" and index + 2 < len(source):
                    value.append(chr(int(source[index + 1 : index + 3], 16)))
                    index += 3
                elif escape in "\r\n":
                    if escape == "\r" and index + 1 < len(source) and source[index + 1] == "\n":
                        index += 2
                    else:
                        index += 1
                else:
                    value.extend(("\\", escape))
                    index += 1
            else:
                raise ValueError("INITIAL_STATE_INVALID: unterminated JS string")
            out.append(json.dumps("".join(value), ensure_ascii=False))
            continue
        word_match = re.match(r"[A-Za-z_$][\w$]*", source[index:])
        if word_match:
            word = word_match.group(0)
            after_word = index + len(word)
            while after_word < len(source) and source[after_word].isspace():
                after_word += 1
            if after_word < len(source) and source[after_word] == ":":
                replacement = json.dumps(word)
            else:
                replacement = "null" if word in {"undefined", "NaN", "Infinity"} else word
            out.append(replacement)
            index += len(word)
            continue
        if char == ",":
            lookahead = index + 1
            while lookahead < len(source) and source[lookahead].isspace():
                lookahead += 1
            if lookahead < len(source) and source[lookahead] in "}]":
                index += 1
                continue
        out.append(char)
        index += 1
    return "".join(out)


def extract_initial_state(html_text: str) -> dict[str, Any]:
    raw = find_js_value_after_marker(html_text)
    try:
        loaded = json.loads(raw, parse_constant=lambda _value: None)
    except json.JSONDecodeError:
        loaded = json.loads(sanitize_js_object(raw), parse_constant=lambda _value: None)
    if not isinstance(loaded, dict):
        raise ValueError("INITIAL_STATE_INVALID: state is not an object")
    return loaded


def _walk_dicts(root: Any, limit: int = MAX_STATE_NODES) -> Iterator[dict[str, Any]]:
    stack = [root]
    seen: set[int] = set()
    visited = 0
    while stack and visited < limit:
        node = stack.pop()
        if not isinstance(node, (dict, list)):
            continue
        identity = id(node)
        if identity in seen:
            continue
        seen.add(identity)
        visited += 1
        if isinstance(node, dict):
            yield node
            stack.extend(reversed(list(node.values())[:500]))
        else:
            stack.extend(reversed(node[:500]))


def _note_from_detail(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    note = value.get("note", value)
    if not isinstance(note, dict):
        return None
    if not any(key in note for key in ("title", "noteTitle", "displayTitle", "desc", "description", "imageList", "images")):
        return None
    return note


def find_note_with_id(state: dict[str, Any], note_id: str) -> tuple[dict[str, Any], str]:
    candidates: list[tuple[dict[str, Any], str]] = []
    seen_notes: set[int] = set()
    for node in _walk_dicts(state):
        detail_map = node.get("noteDetailMap")
        if isinstance(detail_map, dict):
            for key, detail in detail_map.items():
                note = _note_from_detail(detail)
                if note is not None and id(note) not in seen_notes:
                    candidates.append((note, str(key)))
                    seen_notes.add(id(note))
        if _note_from_detail(node) is not None and id(node) not in seen_notes:
            candidates.append((node, ""))
            seen_notes.add(id(node))

    if note_id:
        for note, map_id in candidates:
            ids = {str(note.get(key, "")) for key in ("noteId", "note_id", "id")}
            if note_id == map_id or note_id in ids:
                return note, note_id
        raise ValueError(f"NOTE_NOT_FOUND: note data missing for {note_id}")

    if len(candidates) == 1:
        note, map_id = candidates[0]
        discovered_id = map_id or next(
            (str(note.get(key)) for key in ("noteId", "note_id", "id") if note.get(key)), ""
        )
        return note, discovered_id
    if not candidates:
        raise ValueError("NOTE_NOT_FOUND: state contains no note-shaped object")
    raise ValueError("NOTE_ID_MISSING: state contains multiple note candidates")


def find_note(state: dict[str, Any], note_id: str) -> dict[str, Any]:
    """Compatibility helper returning the raw note dict from a runtime state."""
    return find_note_with_id(state, note_id)[0]


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return ""


def first_present(*values: Any) -> Any:
    for value in values:
        if value is None or value == "":
            continue
        return value
    return ""


def extract_tags(note: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for key in ("tagList", "tags", "hashTag"):
        values = note.get(key)
        if not isinstance(values, list):
            continue
        for item in values:
            value = item if isinstance(item, str) else (
                first_present(item.get("name"), item.get("tagName"), item.get("title"))
                if isinstance(item, dict) else ""
            )
            text = as_text(value)
            if text and text not in tags:
                tags.append(text)
    return tags


def extract_author(note: dict[str, Any]) -> dict[str, str]:
    user = first_present(note.get("user"), note.get("userInfo"), note.get("author"))
    if not isinstance(user, dict):
        user = {}
    return {
        "nickname": as_text(first_present(user.get("nickname"), user.get("nickName"), user.get("name"))),
        "user_id": as_text(first_present(user.get("userId"), user.get("user_id"), user.get("id"))),
        "avatar": as_text(first_present(user.get("avatar"), user.get("image"), user.get("imageb"), user.get("avatarUrl"), user.get("avatar_url"))),
    }


def extract_stats(note: dict[str, Any]) -> dict[str, str]:
    interact = first_present(note.get("interactInfo"), note.get("interact_info"))
    if not isinstance(interact, dict):
        interact = {}
    return {
        "likes": as_text(first_present(interact.get("likedCount"), interact.get("likeCount"), interact.get("liked_count"))),
        "collects": as_text(first_present(interact.get("collectedCount"), interact.get("collectCount"), interact.get("collected_count"))),
        "comments": as_text(first_present(interact.get("commentCount"), interact.get("commentsCount"), interact.get("comment_count"))),
    }


def normalize_image_url(url: str) -> str:
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http://") and ".xhscdn.com/" in url:
        return "https://" + url[len("http://"):]
    return url


def image_url_from_entry(entry: Any) -> str:
    if isinstance(entry, str):
        return normalize_image_url(entry)
    if not isinstance(entry, dict):
        return ""
    for key in ("urlDefault", "urlPre", "url", "originalUrl", "thumbnailUrl"):
        value = entry.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://", "//")):
            return normalize_image_url(value)
    info_list = entry.get("infoList")
    if isinstance(info_list, list):
        items = [item for item in info_list if isinstance(item, dict)]
        for scene in ("WB_DFT", "CRD_WM_WEBP", "CRD_PRV_WEBP", "DETAIL", "ORIGIN"):
            for item in items:
                if item.get("imageScene") == scene and isinstance(item.get("url"), str):
                    return normalize_image_url(item["url"])
        for item in items:
            if isinstance(item.get("url"), str):
                return normalize_image_url(item["url"])
    return ""


def extract_image_urls(note: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("imageList", "images", "image_list"):
        values = note.get(key)
        if isinstance(values, list):
            for entry in values:
                url = image_url_from_entry(entry)
                if url and url not in urls:
                    urls.append(url)
    return urls


def _image_metadata(note: dict[str, Any], url: str, index: int) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    for key in ("imageList", "images", "image_list"):
        values = note.get(key)
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict) and image_url_from_entry(item) == url:
                raw = item
                break
        if raw:
            break
    info_list = raw.get("infoList") if isinstance(raw.get("infoList"), list) else []
    preview = first_present(raw.get("urlPre"), raw.get("thumbnailUrl"))
    if not preview:
        preview = next((item.get("url") for item in info_list if isinstance(item, dict) and item.get("imageScene") in {"WB_PRV", "CRD_PRV_WEBP"} and isinstance(item.get("url"), str)), "")
    return {
        "index": index,
        "image_id": as_text(first_present(raw.get("fileId"), raw.get("file_id"))).rsplit("/", 1)[-1],
        "width": raw.get("width") if isinstance(raw.get("width"), (int, float)) else None,
        "height": raw.get("height") if isinstance(raw.get("height"), (int, float)) else None,
        "url": url,
        "preview_url": normalize_image_url(as_text(preview)),
        "variants": [
            {"scene": as_text(item.get("imageScene")), "url": normalize_image_url(item["url"])}
            for item in info_list if isinstance(item, dict) and isinstance(item.get("url"), str)
        ],
        "local_path": "",
    }


def combine_text(result: dict[str, Any]) -> str:
    parts = [as_text(result.get(key)) for key in ("title", "desc")]
    parts = [part for part in parts if part]
    tags = result.get("tags")
    if isinstance(tags, list) and tags:
        parts.append("Tags: " + ", ".join(str(tag) for tag in tags))
    comments_text = as_text(result.get("comments_text"))
    if comments_text:
        parts.append("Publicly rendered comments:\n" + comments_text)
    return "\n\n".join(parts)


def provenance(mode: str) -> dict[str, Any]:
    real_chrome = mode == "real_chrome"
    return {
        "mode": mode,
        "logged_in": True if real_chrome else False if mode == "static_html" else None,
        "used_user_profile": real_chrome,
        "browser_automation": "chrome-use" if real_chrome else None,
    }


def failure_result(url: str, mode: str, error: str, final_url: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "url": redact_url(url),
        "final_url": redact_url(final_url or url),
        "note_id": extract_note_id(url),
        "title": "",
        "desc": "",
        "author": {"nickname": "", "user_id": "", "avatar": ""},
        "tags": [],
        "stats": {"likes": "", "collects": "", "comments": ""},
        "images": [],
        "comments": [],
        "comments_text": "",
        "comment_count_label": None,
        "comments_truncated_by_login": False,
        "retrieval": provenance(mode),
        "combined_text": "",
        "errors": [error],
        "warnings": [],
    }


def _page_error(html_text: str, final_url: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", html_lib.unescape(html_text)).lower()
    path = urlparse(final_url).path.lower()
    if re.search(r"300011.{0,20}(?:异常|安全|风险|限制)|(?:异常|安全|风险|限制).{0,20}300011", plain) or "账号异常，请稍后重试" in plain:
        return "SECURITY_RESTRICTED_300011: page returned a Xiaohongshu security restriction"
    if "300031" in plain:
        return "SECURITY_RESTRICTED_300031: page rejected the note request"
    if re.search(r"验证码|安全验证|人机验证|captcha|robot check", plain):
        return "CAPTCHA_CHALLENGE: page requires a security challenge"
    if re.search(r"操作过于频繁|请求过于频繁|访问频率|rate limit|too many requests", plain):
        return "RATE_LIMITED: page reports a request or action limit"
    if path.startswith("/login") or re.search(r"登录\s*/\s*注册|请先登录|登录后查看", plain):
        return "LOGIN_SHELL: page exposed a login shell instead of note data"
    return ""


def normalize_note(
    note: dict[str, Any],
    *,
    url: str,
    note_id: str = "",
    mode: str = "saved_runtime_state",
    final_url: str = "",
    comments: list[dict[str, Any]] | None = None,
    comments_text: str = "",
    comment_count_label: int | None = None,
    comments_truncated_by_login: bool = False,
) -> dict[str, Any]:
    image_urls = extract_image_urls(note)
    note_id = note_id or next((as_text(note.get(key)) for key in ("noteId", "note_id", "id") if note.get(key)), "")
    timestamp = first_present(note.get("time"), note.get("createTime"), note.get("create_time"))
    published_at = ""
    if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
        seconds = float(timestamp) / 1000 if timestamp > 10_000_000_000 else float(timestamp)
        try:
            published_at = datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        except (OverflowError, OSError, ValueError):
            pass
    interact = first_present(note.get("interactInfo"), note.get("interact_info"))
    raw_stats = {str(key): value for key, value in interact.items() if isinstance(value, (str, int, float, bool)) or value is None} if isinstance(interact, dict) else {}
    result = {
        "ok": True,
        "url": redact_url(url),
        "final_url": redact_url(final_url or url),
        "note_id": note_id,
        "title": as_text(first_present(note.get("title"), note.get("noteTitle"), note.get("displayTitle"))),
        "desc": as_text(first_present(note.get("desc"), note.get("description"), note.get("noteDesc"))),
        "author": extract_author(note),
        "tags": extract_tags(note),
        "stats": extract_stats(note),
        "stats_raw": raw_stats,
        "published_at": published_at,
        "published_at_raw": timestamp,
        "ip_location": as_text(first_present(note.get("ipLocation"), note.get("ip_location"))),
        "note_type": as_text(first_present(note.get("type"), note.get("noteType"))),
        "images": [_image_metadata(note, image_url, index) for index, image_url in enumerate(image_urls, 1)],
        "gallery": {"image_count_available": len(image_urls), "image_count_selected": len(image_urls), "truncated": False},
        "comments": comments if isinstance(comments, list) else [],
        "comments_text": comments_text,
        "comment_count_label": comment_count_label,
        "comments_truncated_by_login": comments_truncated_by_login,
        "retrieval": provenance(mode),
        "combined_text": "",
        "errors": [],
        "warnings": [],
    }
    if comments_truncated_by_login:
        result["warnings"].append("COMMENTS_LIMITED_TO_ANONYMOUSLY_RENDERED_PUBLIC_SECTION")
    result["combined_text"] = combine_text(result)
    return result


def _unwrap_runtime_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        for key in ("__INITIAL_STATE__", "initialState", "state"):
            candidate = payload.get(key)
            if isinstance(candidate, dict):
                return candidate
    return payload


def parse_runtime_state(
    state: dict[str, Any], *, url: str, mode: str = "saved_runtime_state", final_url: str = ""
) -> dict[str, Any]:
    state = _unwrap_runtime_payload(state)
    if not isinstance(state, dict):
        return failure_result(url, mode, "RUNTIME_STATE_INVALID: expected a JSON object", final_url)
    try:
        note_id = extract_note_id(url)
        note, found_id = find_note_with_id(state, note_id)
        return normalize_note(note, url=url, note_id=note_id or found_id, mode=mode, final_url=final_url)
    except ValueError as exc:
        return failure_result(url, mode, str(exc), final_url)


def parse_runtime_json(
    json_text: str, *, url: str, mode: str = "saved_runtime_state", final_url: str = ""
) -> dict[str, Any]:
    try:
        payload = json.loads(json_text, parse_constant=lambda _value: None)
    except json.JSONDecodeError as exc:
        return failure_result(url, mode, f"RUNTIME_STATE_INVALID: {exc.msg}", final_url)
    if not isinstance(payload, dict):
        return failure_result(url, mode, "RUNTIME_STATE_INVALID: expected a JSON object", final_url)
    if isinstance(payload.get("note"), dict) and ("note_id" in payload or "snapshot_version" in payload):
        return parse_rendered_snapshot(payload, url=url, mode=mode)
    return parse_runtime_state(payload, url=url, mode=mode, final_url=final_url)


def parse_rendered_snapshot(
    snapshot: dict[str, Any], *, url: str, mode: str = "saved_runtime_state"
) -> dict[str, Any]:
    page_url = as_text(snapshot.get("url")) or url
    final_url = redact_url(page_url)
    page_error = as_text(snapshot.get("page_error"))
    if not page_error:
        security_code = str(snapshot.get("security_code") or "")
        page_error = (
            "SECURITY_RESTRICTED_300011: page returned a Xiaohongshu security restriction"
            if security_code == "300011"
            else "SECURITY_RESTRICTED_300031: page rejected the note request"
            if security_code == "300031"
            else ""
        )
    if not page_error and snapshot.get("login_page"):
        page_error = "LOGIN_SHELL: rendered page is a login shell"
    if page_error.startswith(("SECURITY_RESTRICTED", "CAPTCHA_CHALLENGE", "RATE_LIMITED", "LOGIN_SHELL")):
        return failure_result(url, mode, page_error, final_url)
    note = snapshot.get("note")
    if not isinstance(note, dict) or not any(note.get(key) for key in ("title", "desc", "imageList", "images")):
        return failure_result(url, mode, page_error or "NOTE_NOT_FOUND: sanitized snapshot has no note data", final_url)
    normalized = normalize_note(
        note,
        url=url,
        note_id=as_text(snapshot.get("note_id")) or extract_note_id(page_url),
        mode=mode,
        final_url=final_url,
        comments=snapshot.get("comments") if isinstance(snapshot.get("comments"), list) else [],
        comments_text=as_text(snapshot.get("comments_text")),
        comment_count_label=snapshot.get("comment_count_label") if isinstance(snapshot.get("comment_count_label"), int) else None,
        comments_truncated_by_login=bool(snapshot.get("comments_truncated_by_login")),
    )
    rendered_urls = snapshot.get("rendered_image_urls")
    if isinstance(rendered_urls, list):
        merged = list(normalized["images"])
        known = {item["url"] for item in merged}
        for raw in rendered_urls:
            candidate = raw.get("url") if isinstance(raw, dict) else raw
            candidate = normalize_image_url(candidate) if isinstance(candidate, str) else ""
            if candidate.startswith(("http://", "https://")) and candidate not in known:
                known.add(candidate)
                merged.append(_image_metadata({"imageList": [candidate]}, candidate, len(merged) + 1))
        normalized["images"] = merged
        normalized["gallery"] = {"image_count_available": len(merged), "image_count_selected": len(merged), "truncated": False}
    normalized["page_has_note_content"] = bool(snapshot.get("page_has_note_content", True))
    normalized["combined_text"] = combine_text(normalized)
    return normalized


def parse_html(
    html_text: str, *, url: str, final_url: str = "", mode: str = "saved_html"
) -> dict[str, Any]:
    final_url = final_url or url
    try:
        state = extract_initial_state(html_text)
    except (ValueError, json.JSONDecodeError) as exc:
        return failure_result(url, mode, _page_error(html_text, final_url) or str(exc), final_url)
    try:
        note_id = extract_note_id(url) or extract_note_id(final_url)
        note, found_id = find_note_with_id(state, note_id)
        return normalize_note(note, url=url, note_id=note_id or found_id, mode=mode, final_url=final_url)
    except ValueError as exc:
        return failure_result(url, mode, _page_error(html_text, final_url) or str(exc), final_url)
