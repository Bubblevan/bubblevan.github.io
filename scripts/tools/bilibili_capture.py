from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from playwright.async_api import (
    BrowserContext,
    Page,
    Response,
    async_playwright,
)


PLAYER_API_PATH = "/x/player/wbi/v2"

COMMENT_API_PATHS = (
    "/x/v2/reply/wbi/main",
    "/x/v2/reply/reply",
)

BILIBILI_API_BASE = "https://api.bilibili.com"


def normalize_bilibili_comment(
    raw: dict[str, Any],
    *,
    is_pinned: bool = False,
    source: str = "",
) -> dict[str, Any]:
    """将 B站评论结构转换为相对稳定的内部结构。"""
    content_obj = raw.get("content") or {}
    member = raw.get("member") or {}
    replies = raw.get("replies") or []
    reply_control = raw.get("reply_control") or {}

    if isinstance(content_obj, dict):
        content = content_obj.get("message") or ""
    else:
        content = str(content_obj)

    return {
        "comment_id": str(raw.get("rpid") or raw.get("id") or ""),
        "root_id": str(raw.get("root") or ""),
        "parent_id": str(raw.get("parent") or ""),
        "content": content,
        "like_count": raw.get("like"),
        "reply_count": raw.get("rcount", raw.get("count")),
        "create_time": raw.get("ctime"),
        "is_pinned": bool(is_pinned or reply_control.get("is_up_top")),
        "source": source,
        "user": {
            "user_id": str(member.get("mid") or ""),
            "nickname": member.get("uname") or "",
            "avatar": member.get("avatar") or "",
        },
        "replies": [
            normalize_bilibili_comment(reply)
            for reply in replies
            if isinstance(reply, dict)
        ],
    }


def extract_reply_objects(data: Any) -> list[dict[str, Any]]:
    """从已知及可能变化的响应结构中提取评论对象。"""
    results: list[dict[str, Any]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if "rpid" in obj and "content" in obj:
                results.append(obj)

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return results


def dedupe_comments(
    comments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []

    for comment in comments:
        comment_id = comment.get("comment_id", "")
        content = comment.get("content", "")
        key = comment_id or content[:100]

        if not key or key in seen:
            continue

        seen.add(key)
        result.append(comment)

    return result


def count_comment_tree(comments: list[dict[str, Any]]) -> int:
    total = 0
    for comment in comments:
        total += 1
        replies = comment.get("replies") or []
        if isinstance(replies, list):
            total += count_comment_tree([
                reply
                for reply in replies
                if isinstance(reply, dict)
            ])
    return total


def extract_oid_from_urls(urls: list[str]) -> str:
    for url in urls:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        for key in ("aid", "oid"):
            value = params.get(key)
            if value and value[0]:
                return value[0]
    return ""


async def extract_oid_from_page(page: Page) -> str:
    scripts = (
        "() => String(window.__INITIAL_STATE__?.aid || '')",
        "() => String(window.__INITIAL_STATE__?.videoData?.aid || '')",
    )

    for script in scripts:
        try:
            value = await page.evaluate(script)
        except Exception:
            continue

        if isinstance(value, str) and value and value != "undefined":
            return value

    return ""


async def fetch_bilibili_json(
    context: BrowserContext,
    path: str,
    params: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    url = f"{BILIBILI_API_BASE}{path}?{urlencode(params)}"
    response = await context.request.get(
        url,
        headers={
            "Referer": "https://www.bilibili.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        },
        timeout=30_000,
    )

    if not response.ok:
        return None, url

    try:
        data = await response.json()
    except Exception:
        return None, url

    return data if isinstance(data, dict) else None, url


async def fetch_sub_replies(
    context: BrowserContext,
    *,
    oid: str,
    root_id: str,
    page_size: int,
    max_pages: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    replies: list[dict[str, Any]] = []
    urls: list[str] = []

    for page_number in range(1, max_pages + 1):
        data, url = await fetch_bilibili_json(
            context,
            "/x/v2/reply/reply",
            {
                "type": 1,
                "oid": oid,
                "root": root_id,
                "pn": page_number,
                "ps": page_size,
            },
        )
        urls.append(url)

        if not data or data.get("code") != 0:
            break

        payload = data.get("data") or {}
        page_replies = payload.get("replies") or []
        if not isinstance(page_replies, list) or not page_replies:
            break

        replies.extend(
            reply
            for reply in page_replies
            if isinstance(reply, dict)
        )

        page_info = payload.get("page") or {}
        total = page_info.get("count")
        if isinstance(total, int) and total > 0:
            total_pages = math.ceil(total / page_size)
            if page_number >= total_pages:
                break

    return replies, urls


async def fetch_legacy_comment_tree(
    context: BrowserContext,
    *,
    oid: str,
    page_size: int,
    max_pages: int,
    max_sub_reply_pages: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    roots_by_id: dict[str, dict[str, Any]] = {}
    pinned_ids: set[str] = set()
    fetched_urls: list[str] = []
    api_errors: list[dict[str, Any]] = []
    page_stats: list[dict[str, Any]] = []
    total_count: int | None = None

    for page_number in range(1, max_pages + 1):
        data, url = await fetch_bilibili_json(
            context,
            "/x/v2/reply",
            {
                "type": 1,
                "oid": oid,
                "pn": page_number,
                "ps": page_size,
                "sort": 2,
            },
        )
        fetched_urls.append(url)

        if not data or data.get("code") != 0:
            api_errors.append({
                "url": url,
                "code": data.get("code") if isinstance(data, dict) else None,
                "message": data.get("message") if isinstance(data, dict) else "no json",
            })
            break

        payload = data.get("data") or {}
        page_info = payload.get("page") or {}
        if isinstance(page_info.get("count"), int) and page_info["count"] > 0:
            total_count = page_info["count"]

        upper = payload.get("upper") or {}
        top = upper.get("top") if isinstance(upper, dict) else None
        if isinstance(top, dict) and top.get("rpid"):
            pinned_ids.add(str(top["rpid"]))
            roots_by_id.setdefault(str(top["rpid"]), top)

        top_replies = payload.get("top_replies") or []
        top_reply_count = 0
        if isinstance(top_replies, list):
            top_reply_count = len(top_replies)
            for raw in top_replies:
                if isinstance(raw, dict) and raw.get("rpid"):
                    pinned_ids.add(str(raw["rpid"]))
                    roots_by_id.setdefault(str(raw["rpid"]), raw)

        page_replies = payload.get("replies") or []
        page_reply_count = 0
        if isinstance(page_replies, list):
            page_reply_count = len(page_replies)
            for raw in page_replies:
                if isinstance(raw, dict) and raw.get("rpid"):
                    roots_by_id.setdefault(str(raw["rpid"]), raw)

        page_stats.append({
            "page": page_number,
            "page_count": page_info.get("count"),
            "reply_roots": page_reply_count,
            "top_replies": top_reply_count,
        })

        if page_number > 1 and page_reply_count == 0 and top_reply_count == 0:
            break

        if isinstance(total_count, int) and total_count > 0:
            total_pages = math.ceil(total_count / page_size)
            if page_number >= total_pages:
                break

    normalized_roots: list[dict[str, Any]] = []

    for root_id, raw in roots_by_id.items():
        existing_replies = raw.get("replies") or []
        reply_count = raw.get("rcount", raw.get("count", 0))

        if (
            isinstance(reply_count, int)
            and reply_count > len(existing_replies)
            and max_sub_reply_pages > 0
        ):
            sub_replies, sub_urls = await fetch_sub_replies(
                context,
                oid=oid,
                root_id=root_id,
                page_size=page_size,
                max_pages=max_sub_reply_pages,
            )
            fetched_urls.extend(sub_urls)
            if sub_replies:
                raw = {**raw, "replies": sub_replies}

        normalized_roots.append(
            normalize_bilibili_comment(
                raw,
                is_pinned=root_id in pinned_ids,
                source="legacy_api",
            )
        )

    normalized_roots.sort(
        key=lambda item: (
            not item.get("is_pinned", False),
            -(item.get("like_count") or 0),
            -(item.get("create_time") or 0),
        )
    )

    return normalized_roots, {
        "oid": oid,
        "total_count": total_count,
        "pinned_ids": sorted(pinned_ids),
        "page_stats": page_stats,
        "legacy_api_urls": fetched_urls,
        "legacy_api_errors": api_errors,
    }


def extract_subtitle_tracks(
    player_data: dict[str, Any],
) -> list[dict[str, Any]]:
    data = player_data.get("data") or {}
    subtitle = data.get("subtitle") or {}
    tracks = subtitle.get("subtitles") or []

    result: list[dict[str, Any]] = []

    for track in tracks:
        if not isinstance(track, dict):
            continue

        subtitle_url = (
            track.get("subtitle_url")
            or track.get("subtitleUrl")
            or ""
        )

        if subtitle_url.startswith("//"):
            subtitle_url = f"https:{subtitle_url}"

        result.append({
            "id": track.get("id"),
            "language": track.get("lan"),
            "language_doc": track.get("lan_doc"),
            "is_ai": bool(track.get("ai_type")),
            "subtitle_url": subtitle_url,
        })

    return result


async def fetch_subtitle_body(
    context: BrowserContext,
    subtitle_url: str,
) -> dict[str, Any] | None:
    if not subtitle_url:
        return None

    response = await context.request.get(
        subtitle_url,
        headers={
            "Referer": "https://www.bilibili.com/",
        },
        timeout=30_000,
    )

    if not response.ok:
        print(
            f"字幕请求失败: HTTP {response.status}",
            flush=True,
        )
        return None

    try:
        return await response.json()
    except Exception as exc:
        print(f"字幕 JSON 解析失败: {exc}", flush=True)
        return None


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument(
        "--user-data-dir",
        default=str(
            Path.home() / ".bilibili-playwright-profile"
        ),
    )
    parser.add_argument("--max-seconds", type=int, default=120)
    parser.add_argument("--max-scrolls", type=int, default=30)
    parser.add_argument("--comment-page-size", type=int, default=20)
    parser.add_argument("--max-comment-pages", type=int, default=10)
    parser.add_argument("--max-sub-reply-pages", type=int, default=10)
    parser.add_argument("--skip-direct-comments", action="store_true")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    captured_comments: list[dict[str, Any]] = []
    player_responses: list[dict[str, Any]] = []
    captured_urls: list[str] = []

    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=args.user_data_dir,
            headless=args.headless,
            viewport={"width": 1440, "height": 1000},
            locale="zh-CN",
            service_workers="block",
        )

        page: Page = (
            context.pages[0]
            if context.pages
            else await context.new_page()
        )

        async def on_response(response: Response) -> None:
            url = response.url
            lower_url = url.lower()

            is_player_api = PLAYER_API_PATH in lower_url
            is_comment_api = any(
                path in lower_url
                for path in COMMENT_API_PATHS
            )

            if not is_player_api and not is_comment_api:
                return

            captured_urls.append(url)

            try:
                data = await response.json()
            except Exception:
                return

            if is_player_api and isinstance(data, dict):
                player_responses.append(data)

            if is_comment_api:
                for raw in extract_reply_objects(data):
                    captured_comments.append(
                        normalize_bilibili_comment(raw)
                    )

        page.on("response", on_response)

        await page.goto(
            args.url,
            wait_until="domcontentloaded",
            timeout=60_000,
        )

        # 给播放器脚本和字幕请求一些启动时间。
        await page.wait_for_timeout(5_000)

        start = time.monotonic()

        for _ in range(args.max_scrolls):
            if time.monotonic() - start > args.max_seconds:
                break

            # 尝试加载评论回复。
            candidate_texts = (
                "查看回复",
                "展开回复",
                "查看更多回复",
                "查看全部",
            )

            for text in candidate_texts:
                locator = page.get_by_text(text, exact=False)

                try:
                    count = await locator.count()
                except Exception:
                    continue

                for index in range(min(count, 8)):
                    try:
                        await locator.nth(index).click(
                            timeout=1_000
                        )
                        await page.wait_for_timeout(500)
                    except Exception:
                        continue

            await page.mouse.wheel(0, 1_800)
            await page.wait_for_timeout(1_200)

        subtitle_tracks: list[dict[str, Any]] = []

        for player_response in player_responses:
            subtitle_tracks.extend(
                extract_subtitle_tracks(player_response)
            )

        # 按字幕 URL 去重。
        unique_tracks: list[dict[str, Any]] = []
        seen_subtitle_urls: set[str] = set()

        for track in subtitle_tracks:
            subtitle_url = track.get("subtitle_url", "")

            if not subtitle_url:
                continue

            if subtitle_url in seen_subtitle_urls:
                continue

            seen_subtitle_urls.add(subtitle_url)
            unique_tracks.append(track)

        subtitles: list[dict[str, Any]] = []

        for track in unique_tracks:
            subtitle_body = await fetch_subtitle_body(
                context,
                track["subtitle_url"],
            )

            subtitles.append({
                **track,
                "body": subtitle_body,
            })

        oid = extract_oid_from_urls(captured_urls)
        if not oid:
            oid = await extract_oid_from_page(page)

        legacy_debug: dict[str, Any] = {
            "oid": oid,
            "total_count": None,
            "pinned_ids": [],
            "legacy_api_urls": [],
            "legacy_api_errors": [],
        }
        comments: list[dict[str, Any]] = []

        if oid and not args.skip_direct_comments:
            comments, legacy_debug = await fetch_legacy_comment_tree(
                context,
                oid=oid,
                page_size=args.comment_page_size,
                max_pages=args.max_comment_pages,
                max_sub_reply_pages=args.max_sub_reply_pages,
            )

        if not comments:
            comments = dedupe_comments(captured_comments)

        comment_count = count_comment_tree(comments)

        result = {
            "ok": True,
            "url": args.url,
            "comment_count": comment_count,
            "root_comment_count": len(comments),
            "comments": comments,
            "subtitle_track_count": len(subtitles),
            "subtitles": subtitles,
            "debug": {
                "player_response_count": len(player_responses),
                "captured_api_urls": captured_urls,
                "direct_comment_api": legacy_debug,
                "fallback_captured_comment_count": len(captured_comments),
            },
        }

        Path(args.out_json).write_text(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        await context.close()

    print(json.dumps(
        {
            "ok": True,
            "comment_count": comment_count,
            "root_comment_count": len(comments),
            "subtitle_track_count": len(subtitles),
            "out_json": args.out_json,
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    asyncio.run(main())
