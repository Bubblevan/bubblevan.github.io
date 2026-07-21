from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import mimetypes
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = REPO_ROOT / ".cache" / "xhs_note_reader"
DEFAULT_VISION_SCRIPT = REPO_ROOT / "scripts" / "local-vision" / "describe-image.ps1"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

IMAGE_HEADERS = {
    "User-Agent": DEFAULT_HEADERS["User-Agent"],
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Referer": "https://www.xiaohongshu.com/",
}


@dataclass
class HttpResult:
    body: bytes
    final_url: str
    content_type: str


@dataclass
class OcrResult:
    engine: str
    ocr: str
    summary: str
    confidence: float | None = None
    fallback_reason: str = ""


def extract_first_url(value: str) -> str:
    match = re.search(r"https?://[^\s<>\"]+", value)
    if not match:
        return value.strip()
    return match.group(0).rstrip("，。),)]}")


def http_get(url: str, *, timeout: int, headers: dict[str, str] | None = None) -> HttpResult:
    request = Request(url, headers=headers or DEFAULT_HEADERS, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            return HttpResult(body=body, final_url=final_url, content_type=content_type)
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while fetching {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error while fetching {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"Timeout while fetching {url}") from exc


def decode_html(body: bytes, content_type: str = "") -> str:
    charset_match = re.search(r"charset=([\w.-]+)", content_type, re.I)
    encodings = [charset_match.group(1)] if charset_match else []
    encodings.extend(["utf-8", "gb18030"])
    for encoding in encodings:
        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def extract_note_id(url: str, state: dict[str, Any] | None = None) -> str:
    patterns = [
        r"/discovery/item/([A-Za-z0-9]+)",
        r"/explore/([A-Za-z0-9]+)",
        r"[?&]note_id=([A-Za-z0-9]+)",
        r"[?&]noteId=([A-Za-z0-9]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    if state:
        for note in iter_note_dicts(state):
            for key in ("noteId", "note_id", "id"):
                value = note.get(key)
                if isinstance(value, str) and value:
                    return value
    return ""


def find_js_value_after_marker(text: str, marker: str) -> str:
    marker_index = text.find(marker)
    if marker_index < 0:
        raise ValueError(f"{marker} not found")

    equals_index = text.find("=", marker_index + len(marker))
    if equals_index < 0:
        raise ValueError(f"{marker} has no assignment")

    start = equals_index + 1
    while start < len(text) and text[start].isspace():
        start += 1

    if text.startswith("JSON.parse", start):
        paren = text.find("(", start)
        if paren < 0:
            raise ValueError("JSON.parse call is malformed")
        value_start = paren + 1
        while value_start < len(text) and text[value_start].isspace():
            value_start += 1
        quote = text[value_start]
        if quote not in {"'", '"'}:
            raise ValueError("JSON.parse argument is not a string")
        value_end = value_start + 1
        escaped = False
        while value_end < len(text):
            char = text[value_end]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                raw = text[value_start + 1 : value_end]
                return json.loads(f'"{raw}"')
            value_end += 1
        raise ValueError("JSON.parse string is unterminated")

    brace_start = text.find("{", start)
    bracket_start = text.find("[", start)
    candidates = [pos for pos in [brace_start, bracket_start] if pos >= 0]
    if not candidates:
        raise ValueError(f"{marker} assignment has no object")

    start = min(candidates)
    stack: list[str] = []
    quote: str | None = None
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in "{[":
            stack.append("}" if char == "{" else "]")
        elif char in "}]":
            if not stack or char != stack[-1]:
                raise ValueError(f"{marker} assignment has unbalanced braces")
            stack.pop()
            if not stack:
                return text[start : index + 1]

    raise ValueError(f"{marker} assignment is unterminated")


def sanitize_js_object(value: str) -> str:
    value = html_lib.unescape(value)
    value = value.replace("\\u002F", "/")
    value = re.sub(r"\bundefined\b", "null", value)
    value = re.sub(r"\bNaN\b", "null", value)
    value = re.sub(r"\bInfinity\b", "null", value)
    value = re.sub(r",(\s*[}\]])", r"\1", value)
    return value


def extract_initial_state(html_text: str) -> dict[str, Any]:
    raw = find_js_value_after_marker(html_text, "window.__INITIAL_STATE__")
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        loaded = json.loads(sanitize_js_object(raw))
    if not isinstance(loaded, dict):
        raise ValueError("window.__INITIAL_STATE__ is not a JSON object")
    return loaded


def iter_note_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if any(key in node for key in ("noteId", "note_id", "title", "desc", "interactInfo", "imageList")):
                found.append(node)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return found


def find_note(state: dict[str, Any], note_id: str) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if not isinstance(node, dict):
            if isinstance(node, list):
                for item in node:
                    visit(item)
            return

        detail_map = node.get("noteDetailMap")
        if isinstance(detail_map, dict):
            if note_id and note_id in detail_map:
                detail = detail_map[note_id]
                if isinstance(detail, dict):
                    note = detail.get("note", detail)
                    if isinstance(note, dict):
                        candidates.append(note)
            for detail in detail_map.values():
                if isinstance(detail, dict):
                    note = detail.get("note", detail)
                    if isinstance(note, dict):
                        candidates.append(note)

        for child in node.values():
            visit(child)

    visit(state)

    for note in candidates + iter_note_dicts(state):
        if note_id and note_id in {str(note.get("noteId", "")), str(note.get("note_id", "")), str(note.get("id", ""))}:
            return note
    if candidates:
        return candidates[0]
    raise ValueError(f"note data not found for note_id={note_id or '<unknown>'}")


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def first_present(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value == "":
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
            if isinstance(item, str):
                text = item
            elif isinstance(item, dict):
                text = as_text(item.get("name") or item.get("tagName") or item.get("title"))
            else:
                text = ""
            if text and text not in tags:
                tags.append(text)
    return tags


def extract_author(note: dict[str, Any]) -> dict[str, str]:
    user = note.get("user") or note.get("userInfo") or note.get("author") or {}
    if not isinstance(user, dict):
        user = {}
    return {
        "nickname": as_text(first_present(user.get("nickname"), user.get("nickName"), user.get("name"))),
        "user_id": as_text(first_present(user.get("userId"), user.get("user_id"), user.get("id"))),
    }


def extract_stats(note: dict[str, Any]) -> dict[str, str]:
    interact = note.get("interactInfo") or note.get("interact_info") or {}
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
        preferred = ["WB_DFT", "CRD_WM_WEBP", "CRD_PRV_WEBP", "DETAIL", "ORIGIN"]
        items = [item for item in info_list if isinstance(item, dict)]
        for scene in preferred:
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
        if not isinstance(values, list):
            continue
        for entry in values:
            url = image_url_from_entry(entry)
            if url and url not in urls:
                urls.append(url)
    return urls


def image_extension(url: str, content_type: str) -> str:
    parsed_suffix = Path(urlparse(url).path).suffix.lower()
    if parsed_suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}:
        return parsed_suffix
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
    if guessed:
        return ".jpg" if guessed == ".jpe" else guessed
    return ".jpg"


def download_image(url: str, *, cache_dir: Path, note_id: str, index: int, timeout: int) -> Path:
    note_cache = cache_dir / (note_id or "unknown")
    note_cache.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

    existing = sorted(note_cache.glob(f"{index:02d}-{digest}.*"))
    if existing:
        return existing[0]

    result = http_get(url, timeout=timeout, headers=IMAGE_HEADERS)
    ext = image_extension(url, result.content_type)
    path = note_cache / f"{index:02d}-{digest}{ext}"
    path.write_bytes(result.body)
    return path


def parse_vision_sections(text: str) -> tuple[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in text.splitlines():
        heading = re.match(r"^###\s+(OCR|Image Understanding|Summary)\s*$", line.strip(), re.I)
        if heading:
            if current:
                sections[current] = "\n".join(lines).strip()
            current = heading.group(1).lower()
            lines = []
        elif current:
            lines.append(line)
    if current:
        sections[current] = "\n".join(lines).strip()

    ocr = sections.get("ocr", "").strip()
    summary = sections.get("summary") or sections.get("image understanding") or text.strip()
    return ocr, summary.strip()


def run_vlm_ocr(image_path: Path, *, script_path: Path, timeout: int, max_tokens: int) -> OcrResult:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        "-ImagePath",
        str(image_path),
        "-MaxTokens",
        str(max_tokens),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    output = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0:
        raise RuntimeError(f"OCR failed for {image_path}: {stderr or output or completed.returncode}")
    ocr, summary = parse_vision_sections(output)
    return OcrResult(engine="vlm", ocr=ocr, summary=summary)


def extract_paddle_pairs(value: Any) -> list[tuple[str, float | None]]:
    pairs: list[tuple[str, float | None]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            texts = node.get("rec_texts")
            scores = node.get("rec_scores")
            if isinstance(texts, list):
                for index, text in enumerate(texts):
                    score = None
                    if isinstance(scores, list) and index < len(scores) and isinstance(scores[index], (int, float)):
                        score = float(scores[index])
                    if isinstance(text, str) and text.strip():
                        pairs.append((text.strip(), score))
            for child in node.values():
                visit(child)
            return

        if isinstance(node, (list, tuple)):
            if len(node) == 2 and isinstance(node[1], (list, tuple)) and len(node[1]) >= 2:
                text, score = node[1][0], node[1][1]
                if isinstance(text, str) and isinstance(score, (int, float)):
                    pairs.append((text.strip(), float(score)))
                    return
            for child in node:
                visit(child)

    visit(value)
    return pairs


def run_paddle_ocr(image_path: Path) -> OcrResult:
    paddlex_cache_dir = DEFAULT_CACHE_DIR / "paddlex"
    paddlex_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(paddlex_cache_dir))
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_enable_pir_api", "0")

    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"PaddleOCR unavailable: {exc}") from exc

    init_attempts = [
        {
            "lang": "ch",
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        },
        {"use_angle_cls": True, "lang": "ch", "show_log": False},
        {"use_angle_cls": True, "lang": "ch"},
        {"lang": "ch"},
        {},
    ]
    last_error: Exception | None = None
    ocr_model = None
    for kwargs in init_attempts:
        try:
            ocr_model = PaddleOCR(**kwargs)
            break
        except (TypeError, ValueError) as exc:
            last_error = exc
            continue
    if ocr_model is None:
        raise RuntimeError(f"Cannot initialize PaddleOCR: {last_error}")

    if hasattr(ocr_model, "ocr"):
        raw = ocr_model.ocr(str(image_path))
    elif hasattr(ocr_model, "predict"):
        raw = ocr_model.predict(str(image_path))
    else:
        raise RuntimeError("PaddleOCR object has neither ocr() nor predict()")

    pairs = extract_paddle_pairs(raw)
    lines = [text for text, _score in pairs if text]
    scores = [score for _text, score in pairs if score is not None]
    confidence = sum(scores) / len(scores) if scores else None
    ocr_text = "\n".join(lines).strip()
    summary = f"PaddleOCR extracted {len(lines)} text lines."
    return OcrResult(engine="paddle", ocr=ocr_text, summary=summary, confidence=confidence)


def score_ocr_quality(ocr_text: str, confidence: float | None, *, min_chars: int, min_confidence: float) -> tuple[bool, str]:
    stripped = ocr_text.strip()
    if len(stripped) < min_chars:
        return False, f"too_few_chars:{len(stripped)}<{min_chars}"
    if confidence is not None and confidence < min_confidence:
        return False, f"low_confidence:{confidence:.3f}<{min_confidence:.3f}"
    replacement_count = stripped.count("\ufffd")
    if replacement_count:
        return False, f"replacement_chars:{replacement_count}"
    useful_chars = sum(1 for char in stripped if char.isalnum() or "\u4e00" <= char <= "\u9fff")
    if useful_chars / max(len(stripped), 1) < 0.35:
        return False, "low_useful_char_ratio"
    return True, ""


def run_auto_ocr(
    image_path: Path,
    *,
    engine: str,
    script_path: Path,
    timeout: int,
    max_tokens: int,
    paddle_min_chars: int,
    paddle_min_confidence: float,
    allow_vlm_fallback: bool,
    paddle_runner: Callable[[Path], OcrResult] = run_paddle_ocr,
    vlm_runner: Callable[..., OcrResult] = run_vlm_ocr,
) -> OcrResult:
    if engine == "vlm":
        return vlm_runner(image_path, script_path=script_path, timeout=timeout, max_tokens=max_tokens)
    if engine == "paddle":
        result = paddle_runner(image_path)
        ok, reason = score_ocr_quality(
            result.ocr,
            result.confidence,
            min_chars=paddle_min_chars,
            min_confidence=paddle_min_confidence,
        )
        if not ok:
            result.fallback_reason = reason
        return result

    fallback_reason = ""
    try:
        result = paddle_runner(image_path)
        ok, fallback_reason = score_ocr_quality(
            result.ocr,
            result.confidence,
            min_chars=paddle_min_chars,
            min_confidence=paddle_min_confidence,
        )
        if ok or not allow_vlm_fallback:
            result.fallback_reason = "" if ok else fallback_reason
            return result
    except Exception as exc:
        fallback_reason = f"paddle_failed:{exc}"
        if not allow_vlm_fallback:
            raise

    vlm_result = vlm_runner(image_path, script_path=script_path, timeout=timeout, max_tokens=max_tokens)
    vlm_result.fallback_reason = fallback_reason
    return vlm_result


def build_result(
    *,
    url: str,
    final_url: str,
    note_id: str,
    note: dict[str, Any],
    image_urls: list[str],
) -> dict[str, Any]:
    title = as_text(note.get("title"))
    desc = as_text(first_present(note.get("desc"), note.get("description")))
    tags = extract_tags(note)
    result = {
        "ok": True,
        "url": url,
        "final_url": final_url,
        "note_id": note_id,
        "title": title,
        "desc": desc,
        "author": extract_author(note),
        "tags": tags,
        "stats": extract_stats(note),
        "images": [
            {
                "index": index,
                "url": image_url,
                "local_path": "",
                "ocr": "",
                "summary": "",
                "ocr_engine": "",
                "ocr_confidence": None,
                "ocr_fallback_reason": "",
            }
            for index, image_url in enumerate(image_urls, start=1)
        ],
        "combined_text": "",
        "errors": [],
    }
    result["combined_text"] = combine_text(result)
    return result


def combine_text(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "desc"):
        value = as_text(result.get(key))
        if value:
            parts.append(value)
    tags = result.get("tags")
    if isinstance(tags, list) and tags:
        parts.append("Tags: " + ", ".join(str(tag) for tag in tags))
    for image in result.get("images", []):
        if not isinstance(image, dict):
            continue
        ocr = as_text(image.get("ocr"))
        summary = as_text(image.get("summary"))
        if ocr:
            parts.append(f"Image {image.get('index')} OCR:\n{ocr}")
        if summary:
            parts.append(f"Image {image.get('index')} summary:\n{summary}")
    return "\n\n".join(parts)


def failure_result(url: str, final_url: str, note_id: str, errors: list[str]) -> dict[str, Any]:
    return {
        "ok": False,
        "url": url,
        "final_url": final_url,
        "note_id": note_id,
        "title": "",
        "desc": "",
        "author": {"nickname": "", "user_id": ""},
        "tags": [],
        "stats": {"likes": "", "collects": "", "comments": ""},
        "images": [],
        "combined_text": "",
        "errors": errors,
    }


def read_note(args: argparse.Namespace) -> dict[str, Any]:
    source_url = extract_first_url(args.url)
    final_url = source_url
    note_id = ""
    errors: list[str] = []

    try:
        if args.html_file:
            html_text = Path(args.html_file).read_text(encoding="utf-8")
            final_url = args.final_url or source_url
        else:
            fetched = http_get(source_url, timeout=args.timeout)
            final_url = fetched.final_url
            html_text = decode_html(fetched.body, fetched.content_type)
    except Exception as exc:
        return failure_result(source_url, final_url, note_id, [f"URL_FETCH_FAILED: {exc}"])

    try:
        state = extract_initial_state(html_text)
    except Exception as exc:
        return failure_result(source_url, final_url, note_id, [f"INITIAL_STATE_NOT_FOUND: {exc}"])

    note_id = extract_note_id(final_url, state)
    try:
        note = find_note(state, note_id)
    except Exception as exc:
        return failure_result(source_url, final_url, note_id, [f"NOTE_NOT_FOUND: {exc}"])

    if not note_id:
        note_id = extract_note_id(final_url, {"note": note})

    image_urls = extract_image_urls(note)[: args.max_images]
    result = build_result(url=source_url, final_url=final_url, note_id=note_id, note=note, image_urls=image_urls)
    result["errors"] = errors

    should_download = args.download_images or args.ocr_images
    if should_download:
        for image in result["images"]:
            try:
                local_path = download_image(
                    image["url"],
                    cache_dir=Path(args.cache_dir),
                    note_id=note_id,
                    index=int(image["index"]),
                    timeout=args.image_timeout,
                )
                image["local_path"] = str(local_path)
            except Exception as exc:
                result["errors"].append(f"IMAGE_DOWNLOAD_FAILED[{image['index']}]: {exc}")
                continue

            if args.ocr_images:
                try:
                    ocr_result = run_auto_ocr(
                        local_path,
                        engine=args.ocr_engine,
                        script_path=Path(args.vision_script),
                        timeout=args.ocr_timeout,
                        max_tokens=args.ocr_max_tokens,
                        paddle_min_chars=args.paddle_min_chars,
                        paddle_min_confidence=args.paddle_min_confidence,
                        allow_vlm_fallback=not args.no_vlm_fallback,
                    )
                    image["ocr"] = ocr_result.ocr
                    image["summary"] = ocr_result.summary
                    image["ocr_engine"] = ocr_result.engine
                    image["ocr_confidence"] = ocr_result.confidence
                    image["ocr_fallback_reason"] = ocr_result.fallback_reason
                    if ocr_result.fallback_reason:
                        result["errors"].append(f"OCR_FALLBACK[{image['index']}]: {ocr_result.fallback_reason}")
                except subprocess.TimeoutExpired:
                    result["errors"].append(f"OCR_TIMEOUT[{image['index']}]: exceeded {args.ocr_timeout}s")
                except Exception as exc:
                    result["errors"].append(f"OCR_FAILED[{image['index']}]: {exc}")

    result["combined_text"] = combine_text(result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read public Xiaohongshu notes from SSR HTML initial state.")
    parser.add_argument("--url", required=True, help="Xiaohongshu share, xhslink, discovery/item, or explore URL")
    parser.add_argument("--ocr-images", action="store_true", help="download images and run OCR")
    parser.add_argument("--ocr-engine", choices=["auto", "paddle", "vlm"], default="auto", help="auto uses PaddleOCR first, then VLM fallback when quality is poor")
    parser.add_argument("--download-images", action="store_true", help="download images without OCR")
    parser.add_argument("--max-images", type=int, default=20)
    parser.add_argument("--out-json", default="", help="write UTF-8 JSON to this path; stdout is always JSON when omitted")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--timeout", type=int, default=20, help="HTML fetch timeout in seconds")
    parser.add_argument("--image-timeout", type=int, default=30, help="image download timeout in seconds")
    parser.add_argument("--ocr-timeout", type=int, default=180, help="per-image OCR timeout in seconds")
    parser.add_argument("--ocr-max-tokens", type=int, default=10240)
    parser.add_argument("--paddle-min-chars", type=int, default=20, help="minimum useful PaddleOCR text length before accepting it in auto mode")
    parser.add_argument("--paddle-min-confidence", type=float, default=0.50, help="minimum average PaddleOCR confidence before accepting it in auto mode")
    parser.add_argument("--no-vlm-fallback", action="store_true", help="do not call VLM if PaddleOCR is unavailable or low quality")
    parser.add_argument("--vision-script", default=str(DEFAULT_VISION_SCRIPT))
    parser.add_argument("--html-file", default="", help="test-only: parse an already saved UTF-8 HTML file")
    parser.add_argument("--final-url", default="", help="test-only: final URL to use with --html-file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = read_note(args)
    text = json.dumps(result, ensure_ascii=False, indent=2)

    if args.out_json:
        out_path = Path(args.out_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
