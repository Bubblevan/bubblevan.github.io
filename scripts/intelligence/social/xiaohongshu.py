from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .base import BrowserStatus, SocialItem
from .chrome_use_driver import ChromeUseDriver


class XiaohongshuAcquirer:
    platform = "xiaohongshu"

    def __init__(self, driver: ChromeUseDriver):
        self.driver = driver
        self._profile_url = ""

    def probe(self, url: str) -> dict[str, Any]:
        try:
            relay = self.driver.status()["relay_up"]
            return {"status": BrowserStatus.READY if relay else BrowserStatus.RELAY_UNAVAILABLE}
        except Exception as exc:
            return {"status": getattr(exc, "status", BrowserStatus.RELAY_UNAVAILABLE)}

    def discover(self, url: str, *, limit: int = 20) -> dict[str, Any]:
        limit = max(0, min(int(limit), 20))
        if not limit:
            return {"status": BrowserStatus.PARTIAL, "urls": []}
        parts = urlsplit(url.strip())
        self._profile_url = ""
        if ((parts.hostname or "").casefold() in {"xiaohongshu.com", "www.xiaohongshu.com"}
                and re.fullmatch(r"/user/profile/[A-Za-z0-9]+/?", parts.path)):
            self._profile_url = urlunsplit(("https", "www.xiaohongshu.com", parts.path.rstrip("/"), "", ""))
        self.driver.navigate_selected_tab(self._profile_url or url)
        self.driver.snapshot()
        payload = self.driver.eval_json(_PROFILE_LINKS_EXTRACTOR)
        values = payload if isinstance(payload, list) else []
        candidates = []
        for value in values:
            cleaned = canonical_xhs_url(str(value))
            if cleaned and note_id(cleaned) and cleaned not in candidates:
                candidates.append(cleaned)
            if len(candidates) >= limit:
                break
        if candidates:
            return {"status": BrowserStatus.READY, "urls": candidates[:limit]}
        return {"status": BrowserStatus.DOM_CHANGED, "urls": []}

    def acquire(self, url: str) -> SocialItem:
        canonical = canonical_xhs_url(url)
        identifier = note_id(canonical)
        if not canonical or not identifier:
            return SocialItem(self.platform, "", "", {}, BrowserStatus.NOT_FOUND)
        # If the authorized tab is already on this note, keep its in-memory
        # signed access context. The canonical URL stored in the inbox omits
        # xsec parameters, so re-navigating here can turn a readable note into
        # a 404. The extractor and persistence layer still receive only the
        # sanitized canonical URL.
        current_url = self.driver.selected_tab_url()
        current = canonical_xhs_url(current_url)
        if current != canonical and self._profile_url:
            if urlsplit(current_url).path != urlsplit(self._profile_url).path:
                self.driver.navigate_selected_tab(self._profile_url)
                self.driver.snapshot()
            self.driver.click_selector(f'a[href*="/explore/{identifier}"]')
        elif current != canonical:
            self.driver.navigate_selected_tab(canonical)
        if urlsplit(canonical).hostname == "xhslink.com":
            canonical = canonical_xhs_url(self.driver.selected_tab_url())
            identifier = note_id(canonical)
            if not canonical or not identifier:
                return SocialItem(self.platform, "", "", {}, BrowserStatus.NOT_FOUND)
        # The raw snapshot stays in process memory; no debug snapshot is written.
        self.driver.snapshot()
        from scripts.tools.xhs_chrome_use import _safe_note_extractor_js
        from scripts.tools.xhs_note_parser import parse_rendered_snapshot
        payload = self.driver.eval_json(_safe_note_extractor_js(canonical))
        if not isinstance(payload, dict):
            return SocialItem(self.platform, identifier, canonical, {}, BrowserStatus.DOM_CHANGED)
        parsed = parse_rendered_snapshot(payload, url=canonical, mode="real_chrome")
        status = _xhs_status(parsed, payload)
        if status not in {BrowserStatus.CONTENT_READABLE, BrowserStatus.COMPLETED}:
            return SocialItem(self.platform, identifier, canonical, {}, status)
        parsed["retrieval"] = {"mode": "browser_assisted"}
        parsed["canonical_url"] = canonical
        return SocialItem(self.platform, identifier, canonical, parsed, BrowserStatus.CONTENT_READABLE)


def canonical_xhs_url(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").casefold()
        if host == "xhslink.com":
            # The redirect is resolved only by navigating the already adopted tab.
            return urlunsplit(("https", "xhslink.com", parsed.path, "", ""))
        if host not in {"xiaohongshu.com", "www.xiaohongshu.com"}:
            return ""
        match = re.fullmatch(r"/(?:explore|discovery/item)/([A-Za-z0-9]+)(?:/)?", parsed.path)
        return f"https://www.xiaohongshu.com/explore/{match.group(1)}" if match else ""
    except ValueError:
        return ""


def note_id(value: str) -> str:
    match = re.search(r"/(?:explore|discovery/item)/([A-Za-z0-9]+)(?:/|$)", urlsplit(value).path)
    return match.group(1) if match else ""


_PROFILE_LINKS_EXTRACTOR = r'''JSON.stringify([...new Set(
  [...document.querySelectorAll('a[href]')].map(anchor => {
    try {
      const url = new URL(anchor.href, location.href);
      const match = url.pathname.match(/^\/(?:explore|discovery\/item)\/([A-Za-z0-9]+)\/?$/);
      return match ? url.origin + "/explore/" + match[1] : "";
    } catch (_) { return ""; }
  }).filter(Boolean)
)].slice(0, 20))'''


def _xhs_status(parsed: dict[str, Any], payload: dict[str, Any]) -> str:
    error = str(parsed.get("error_code") or payload.get("page_error") or "").casefold()
    if payload.get("login_page") or "login" in error:
        return BrowserStatus.LOGIN_REQUIRED
    if any(marker in error for marker in ("captcha", "challenge", "security", "rate_limited")):
        return BrowserStatus.CHALLENGE_REQUIRED
    if parsed.get("ok") is not True:
        return BrowserStatus.DOM_CHANGED if not error else BrowserStatus.NOT_FOUND
    canonical = canonical_xhs_url(str(parsed.get("canonical_url") or parsed.get("url") or ""))
    if not parsed.get("note_id") or not canonical or not (
        parsed.get("title") or parsed.get("desc")
    ):
        return BrowserStatus.DOM_CHANGED
    return BrowserStatus.CONTENT_READABLE
