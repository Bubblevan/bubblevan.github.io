from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from .base import BrowserStatus, SocialItem
from .chrome_use_driver import ChromeUseDriver, ChromeUseError


_ANSWER_PATH = re.compile(r"^/question/(\d+)/answer/(\d+)/?$")
_EXTRACT_ANSWER = r'''JSON.stringify((() => {
  const cleanUrl = value => { try {
    const u = new URL(value, location.href);
    if (!/^https?:$/.test(u.protocol)) return "";
    u.search = ""; u.hash = ""; return u.origin + u.pathname;
  } catch (_) { return ""; } };
  const one = selectors => { for (const selector of selectors) {
    const node = document.querySelector(selector); const value = node?.innerText?.trim(); if (value) return node;
  } return null; };
  const text = node => (node?.innerText || "").trim().slice(0, 100000);
  const path = location.pathname;
  const ids = path.match(/^\/question\/(\d+)\/answer\/(\d+)/);
  const bodyText = (document.body?.innerText || "").slice(0, 8000);
  const answer = one([".RichContent-inner", ".AnswerItem .RichText", "[data-zop-question] .RichText"]);
  const container = answer?.closest(".AnswerItem") || answer?.parentElement || null;
  const titleNode = one([".QuestionHeader-title", "h1.QuestionHeader-title", "main h1"]);
  const author = one([".AuthorInfo-name", ".AnswerItem .AuthorInfo-name"]);
  const authorAnchor = (container || document).querySelector('a[href*="/people/"]');
  const times = [...(container || document).querySelectorAll("time[datetime]")].slice(0, 2);
  const links = [...(container || document).querySelectorAll("a[href]")].slice(0, 300)
    .map(a => cleanUrl(a.href)).filter(Boolean);
  return {
    url: ids ? location.origin + "/question/" + ids[1] + "/answer/" + ids[2] : cleanUrl(location.href),
    question_id: ids?.[1] || "", answer_id: ids?.[2] || "",
    question_title: text(titleNode), body: text(answer), author_name: text(author),
    author_url: cleanUrl(authorAnchor?.href || ""),
    created_at: times[0]?.dateTime || "", updated_at: times[1]?.dateTime || "",
    links: [...new Set(links)],
    login_page: /\/login(?:\/|$)/i.test(path),
    challenge: /验证码|安全验证|人机验证|captcha|security verification/i.test(bodyText),
    not_found: /问题不存在|回答不存在|内容已被删除/.test(bodyText)
  };
})())'''


class ZhihuAcquirer:
    platform = "zhihu"

    def __init__(self, driver: ChromeUseDriver):
        self.driver = driver

    def probe(self, url: str) -> dict[str, Any]:
        try:
            relay = self.driver.status()["relay_up"]
            return {"status": BrowserStatus.READY if relay else BrowserStatus.RELAY_UNAVAILABLE}
        except Exception as exc:
            return {"status": getattr(exc, "status", BrowserStatus.RELAY_UNAVAILABLE)}

    def discover(self, url: str, *, limit: int = 20) -> dict[str, Any]:
        limit = max(0, min(int(limit), 20))
        self.driver.navigate_selected_tab(url)
        snapshot = self.driver.snapshot()
        answers = []
        for link in _snapshot_urls(snapshot):
            canonical = canonical_zhihu_url(link)
            if canonical and canonical not in answers:
                answers.append(canonical)
            if len(answers) >= limit:
                break
        return {"status": BrowserStatus.READY if answers else BrowserStatus.DOM_CHANGED,
                "urls": answers[:limit]}

    def acquire(self, url: str) -> SocialItem:
        canonical = canonical_zhihu_url(url)
        match = _ANSWER_PATH.fullmatch(urlsplit(canonical).path) if canonical else None
        if not match:
            return SocialItem(self.platform, "", "", {}, BrowserStatus.NOT_FOUND)
        self.driver.navigate_selected_tab(canonical)
        snapshot = self.driver.snapshot()
        refs = snapshot.get("data", {}).get("refs", {}) if isinstance(snapshot, dict) else {}
        login_overlay = any(
            item.get("role") == "button" and
            item.get("name", "").strip() in {"验证码登录", "密码登录"}
            for item in refs.values() if isinstance(item, dict)
        )
        if login_overlay:
            try:
                self.driver.click_role("button", "关闭")
            except ChromeUseError:
                pass
            self.driver.snapshot()
        value = self.driver.eval_json(_EXTRACT_ANSWER)
        if not isinstance(value, dict):
            return SocialItem(self.platform, match.group(2), canonical, {}, BrowserStatus.DOM_CHANGED)
        status = _status(value)
        if status != BrowserStatus.CONTENT_READABLE:
            return SocialItem(self.platform, match.group(2), canonical, {}, status)
        if (value.get("question_id") != match.group(1) or value.get("answer_id") != match.group(2)
                or not value.get("question_title") or not value.get("body")):
            return SocialItem(self.platform, match.group(2), canonical, {}, BrowserStatus.DOM_CHANGED)
        value["canonical_url"] = canonical
        value["retrieval"] = {"mode": "browser_assisted"}
        return SocialItem(self.platform, match.group(2), canonical, value, status)


def canonical_zhihu_url(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        if (parsed.scheme not in {"http", "https"} or
                (parsed.hostname or "").casefold() not in {"www.zhihu.com", "zhihu.com"}):
            return ""
        match = _ANSWER_PATH.fullmatch(parsed.path)
        return f"https://www.zhihu.com/question/{match.group(1)}/answer/{match.group(2)}" if match else ""
    except ValueError:
        return ""


def _status(value: dict[str, Any]) -> str:
    if value.get("login_page"):
        return BrowserStatus.LOGIN_REQUIRED
    if value.get("challenge"):
        return BrowserStatus.CHALLENGE_REQUIRED
    if value.get("not_found"):
        return BrowserStatus.NOT_FOUND
    if value.get("question_title") and value.get("body"):
        return BrowserStatus.CONTENT_READABLE
    return BrowserStatus.DOM_CHANGED


def _snapshot_urls(value: Any) -> list[str]:
    if isinstance(value, str):
        raw = re.findall(r"https?://[^\s<>\"'`()]+", value)
        return [item.rstrip(".,;:!?]}") for item in raw]
    if isinstance(value, dict):
        return [url for item in value.values() for url in _snapshot_urls(item)]
    if isinstance(value, list):
        return [url for item in value for url in _snapshot_urls(item)]
    return []
