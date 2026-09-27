"""Static public HTML and image acquisition for Xiaohongshu URLs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import mimetypes
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

try:
    from .xhs_note_parser import redact_url
except ImportError:  # direct invocation
    from xhs_note_parser import redact_url


ALLOWED_RESOURCE_HOSTS = ("xiaohongshu.com", "xhslink.com", "xhslink.cn", "xhscdn.com")
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


def is_allowed_resource_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme.lower() in {"http", "https"} and any(
        host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_RESOURCE_HOSTS
    )


@dataclass(frozen=True)
class HttpResult:
    body: bytes
    final_url: str
    content_type: str


class SafeXhsRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_allowed_resource_url(newurl):
            raise HTTPError(req.full_url, 310, "Redirect outside Xiaohongshu/CDN domains blocked", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def http_get(url: str, *, timeout: int, headers: dict[str, str] | None = None) -> HttpResult:
    if not is_allowed_resource_url(url):
        raise ValueError("URL must use Xiaohongshu, xhslink, or xhscdn domains")
    request = Request(url, headers=headers or DEFAULT_HEADERS, method="GET")
    try:
        opener = build_opener(SafeXhsRedirectHandler())
        with opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
            if not is_allowed_resource_url(final_url):
                raise ValueError("Final URL left Xiaohongshu/CDN domains")
            return HttpResult(
                body=response.read(),
                final_url=final_url,
                content_type=response.headers.get("Content-Type", ""),
            )
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while fetching {redact_url(url)}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error while fetching {redact_url(url)}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"Timeout while fetching {redact_url(url)}") from exc


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


def fetch_public_html(url: str, *, timeout: int = 20) -> tuple[str, str]:
    response = http_get(url, timeout=timeout)
    return decode_html(response.body, response.content_type), response.final_url


def image_extension(url: str, content_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}:
        return suffix
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
    if guessed:
        return ".jpg" if guessed == ".jpe" else guessed
    return ".jpg"


def download_image(
    url: str,
    *,
    cache_dir: Path,
    note_id: str,
    index: int,
    timeout: int = 30,
    cache_key: str = "",
) -> Path:
    if not is_allowed_resource_url(url):
        raise ValueError("Image URL is outside Xiaohongshu/CDN domains")
    safe_note_id = re.sub(r"[^A-Za-z0-9_-]", "_", note_id)[:100] or "unknown"
    note_cache = cache_dir / safe_note_id
    note_cache.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((cache_key or url).encode("utf-8")).hexdigest()[:16]
    existing = sorted(note_cache.glob(f"{index:02d}-{digest}.*"))
    if existing:
        return existing[0]
    response = http_get(url, timeout=timeout, headers=IMAGE_HEADERS)
    path = note_cache / f"{index:02d}-{digest}{image_extension(url, response.content_type)}"
    path.write_bytes(response.body)
    return path
