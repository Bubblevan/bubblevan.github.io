from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Response


COMMENT_KEYWORDS = (
    "comment",
    "comments",
    "sub_comment",
    "sub_comments",
    "reply",
)


def deep_find_comments(obj: Any) -> list[dict[str, Any]]:
    """从未知 JSON 结构里递归找像评论列表的对象。"""
    found: list[dict[str, Any]] = []

    def looks_like_comment(x: Any) -> bool:
        if not isinstance(x, dict):
            return False
        keys = set(x.keys())
        return (
            ("content" in keys or "comment" in keys or "text" in keys)
            and ("id" in keys or "comment_id" in keys)
        )

    def walk(x: Any):
        if isinstance(x, dict):
            if looks_like_comment(x):
                found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(obj)
    return found


def normalize_comment(raw: dict[str, Any]) -> dict[str, Any]:
    user = raw.get("user_info") or raw.get("user") or {}

    comment_id = (
        raw.get("id")
        or raw.get("comment_id")
        or raw.get("commentId")
        or raw.get("target_comment_id")
    )

    content = (
        raw.get("content")
        or raw.get("text")
        or raw.get("comment")
        or raw.get("desc")
        or ""
    )

    sub_comments_raw = (
        raw.get("sub_comments")
        or raw.get("subComments")
        or raw.get("replies")
        or []
    )

    return {
        "comment_id": str(comment_id) if comment_id else "",
        "content": content,
        "like_count": raw.get("like_count") or raw.get("likes") or raw.get("liked_count"),
        "create_time": raw.get("create_time") or raw.get("createTime"),
        "ip_location": raw.get("ip_location"),
        "user": {
            "user_id": user.get("user_id") or user.get("userId") or user.get("id"),
            "nickname": user.get("nickname") or user.get("nick_name") or user.get("name"),
            "avatar": user.get("image") or user.get("avatar") or user.get("avatar_url"),
        },
        "sub_comment_count": raw.get("sub_comment_count") or raw.get("subCommentCount"),
        "sub_comment_cursor": raw.get("sub_comment_cursor") or raw.get("subCommentCursor"),
        "sub_comment_has_more": raw.get("sub_comment_has_more") or raw.get("subCommentHasMore"),
        "sub_comments": [normalize_comment(x) for x in sub_comments_raw if isinstance(x, dict)],
        "_raw_keys": sorted(raw.keys()),
    }


def dedupe_comments(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for c in comments:
        cid = c.get("comment_id")
        content = c.get("content", "")
        key = cid or content[:80]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--user-data-dir", default=str(Path.home() / ".xhs-playwright-profile"))
    parser.add_argument("--max-seconds", type=int, default=120)
    parser.add_argument("--max-scrolls", type=int, default=40)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    captured_raw: list[dict[str, Any]] = []
    captured_norm: list[dict[str, Any]] = []

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=args.user_data_dir,
            headless=args.headless,
            viewport={"width": 1440, "height": 1000},
            locale="zh-CN",
        )

        page = context.pages[0] if context.pages else await context.new_page()

        async def on_response(resp: Response):
            url = resp.url.lower()
            if not any(k in url for k in COMMENT_KEYWORDS):
                return

            ctype = resp.headers.get("content-type", "")
            if "json" not in ctype and "text" not in ctype:
                return

            try:
                data = await resp.json()
            except Exception:
                return

            raw_comments = deep_find_comments(data)
            if raw_comments:
                captured_raw.extend(raw_comments)
                for rc in raw_comments:
                    captured_norm.append(normalize_comment(rc))

        page.on("response", on_response)

        await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)

        start = time.time()
        for _ in range(args.max_scrolls):
            if time.time() - start > args.max_seconds:
                break

            # 尝试点击“展开回复/查看更多回复/展开更多”
            for text in ["展开", "查看更多回复", "更多回复", "查看全部"]:
                try:
                    loc = page.get_by_text(text, exact=False)
                    count = await loc.count()
                    for i in range(min(count, 5)):
                        try:
                            await loc.nth(i).click(timeout=1000)
                            await page.wait_for_timeout(800)
                        except Exception:
                            pass
                except Exception:
                    pass

            await page.mouse.wheel(0, 1800)
            await page.wait_for_timeout(1500)

        await context.close()

    comments = dedupe_comments(captured_norm)

    result = {
        "ok": True,
        "url": args.url,
        "comment_count": len(comments),
        "comments": comments,
        "debug": {
            "raw_comment_like_objects": len(captured_raw),
        },
    }

    Path(args.out_json).write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({
        "ok": True,
        "comment_count": len(comments),
        "out_json": args.out_json,
    }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())