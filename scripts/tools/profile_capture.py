"""XHS author profile scraper — extracts all note_ids + titles + xsec_tokens + individual content.

Three-phase pipeline:
  Phase 1: Intercept user_posted API → note_ids + metadata
  Phase 2: Extract xsec_tokens from SSR HTML <a> tags  
  Phase 3: Navigate to each note → extract __INITIAL_STATE__ → full content

Usage:
  cd D:/MyLab/Hugo/bubblevan.github.io
  PYTHONPATH="" D:/MyLab/venv-workbench/Scripts/python.exe scripts/tools/profile_capture.py
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

# --- Config -----------------------------------------------------------
PROFILE_URL = "https://www.xiaohongshu.com/user/profile/6a127fbb0000000002002405"
USER_DATA_DIR = os.path.expandvars(r"%USERPROFILE%\.xhs-playwright-profile")
OUTPUT_DIR = Path("xhs_debug")
OUTPUT_DIR.mkdir(exist_ok=True)

# Add repo root to path so we can import xhs_note_reader parsing functions
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "tools"))

from xhs_note_reader import (
    extract_initial_state,
    find_note,
    extract_image_urls,
    extract_tags,
    extract_author,
    extract_stats,
    as_text,
    first_present,
)


# --- Phase 2: Extract xsec_tokens from SSR HTML -----------------------
XSEC_PATTERN = re.compile(
    r'/user/profile/\w+/([a-f0-9]{24})\?xsec_token=([A-Za-z0-9_+/=-]+)'
)


def extract_xsec_tokens(html: str) -> dict[str, str]:
    """Return {note_id: xsec_token} mapping from SSR HTML."""
    pairs: dict[str, str] = {}
    for nid, token in XSEC_PATTERN.findall(html):
        if nid not in pairs:
            pairs[nid] = token
    return pairs


def build_note_url(note_id: str, xsec_token: str) -> str:
    return (
        f"https://www.xiaohongshu.com/explore/{note_id}"
        f"?xsec_token={xsec_token}&xsec_source=pc_profile"
    )


# --- Phase 3: Extract individual note content -------------------------
async def extract_note_content(page, note_id: str, xsec_token: str) -> dict:
    """Navigate to a note page and extract __INITIAL_STATE__ content."""
    url = build_note_url(note_id, xsec_token)
    result = {
        "note_id": note_id,
        "xsec_token": xsec_token,
        "url": url,
        "accessible": False,
        "title": "",
        "desc": "",
        "images": [],
        "tags": [],
        "stats": {},
        "author": {},
        "error": "",
    }

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)

        # Check for 404 / not found
        page_url = page.url
        if "404" in page_url or "error" in page_url.lower():
            result["error"] = "404 or error page"
            return result

        # Extract __INITIAL_STATE__ from page HTML (avoid circular refs in evaluate)
        html = await page.content()
        try:
            state = extract_initial_state(html)
        except Exception as exc:
            result["error"] = f"extract_initial_state failed: {exc}"
            return result

        if not state:
            result["error"] = "no __INITIAL_STATE__"
            return result

        note = find_note(state, note_id)

        result["accessible"] = True
        result["title"] = as_text(note.get("title"))
        result["desc"] = as_text(
            first_present(note.get("desc"), note.get("description"))
        )
        result["images"] = extract_image_urls(note)
        result["tags"] = extract_tags(note)
        result["stats"] = extract_stats(note)
        result["author"] = extract_author(note)

    except Exception as exc:
        result["error"] = str(exc)[:200]

    return result


# --- Main -------------------------------------------------------------
async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True,
            locale="zh-CN",
        )
        page = await context.new_page()

        # ================================================================
        # Phase 1: API interception + DOM fallback → note_ids + titles
        # ================================================================
        collected: dict[str, dict] = {}
        api_count = 0

        async def on_response(resp):
            nonlocal api_count
            if "user_posted" not in resp.url or resp.status != 200:
                return
            api_count += 1
            data = await resp.json()
            notes = data.get("data", {}).get("notes", [])
            print(f"\n[API {api_count}] {len(notes)} notes")

            with open(
                OUTPUT_DIR / f"user_posted_{api_count}.json", "w", encoding="utf8"
            ) as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            for n in notes:
                nid = n.get("note_id", "")
                if not nid or nid in collected:
                    continue
                collected[nid] = {
                    "note_id": nid,
                    "title": n.get("display_title", n.get("title", "")),
                    "type": n.get("type"),
                    "liked_count": n.get("interact_info", {}).get("liked_count"),
                    "author": n.get("user", {}).get("nickname"),
                }
                print(f"  + {collected[nid]['title']}")

        page.on("response", on_response)

        # Load profile
        print("[OPEN]", PROFILE_URL)
        await page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=60000)

        # If login needed
        if "login" in page.url.lower():
            print("\n请在浏览器完成登录")
            input("登录完成按 Enter...")

        # Reload to trigger API
        print("[RELOAD]")
        await page.reload(wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        # Click 笔记 tab
        try:
            tab = page.locator("text=笔记").first
            if await tab.count() > 0:
                await tab.click()
                await page.wait_for_timeout(3000)
        except Exception:
            pass

        # Scroll to trigger API pagination
        for i in range(10):
            print(f"[SCROLL] {i}")
            await page.evaluate("window.scrollBy(0, 3000)")
            await page.wait_for_timeout(1500)

        # DOM fallback if no API data
        if not collected:
            print("\nNo API calls — extracting from DOM...")
            dom_notes = await page.evaluate("""
                () => {
                    var results = [];
                    document.querySelectorAll('[data-note-id]').forEach(function(el) {
                        var nid = el.getAttribute('data-note-id');
                        var text = el.textContent.trim().replace(/\\s+/g, ' ');
                        results.push({id: nid, title: text});
                    });
                    return results;
                }
            """)
            for dn in dom_notes:
                # Strip trailing username
                title = re.sub(r"\s*momo\.v\d+$", "", dn["title"]).strip()
                collected[dn["id"]] = {
                    "note_id": dn["id"],
                    "title": title,
                }
            print(f"DOM: {len(collected)} notes")

        print(f"\nPhase 1 done: {len(collected)} notes collected")

        # ================================================================
        # Phase 2: Extract xsec_tokens from SSR HTML
        # ================================================================
        html = await page.content()
        xsec_map = extract_xsec_tokens(html)
        print(f"Phase 2: {len(xsec_map)} xsec_tokens extracted from HTML")

        # Merge xsec_tokens into collected notes
        for nid, note in collected.items():
            note["xsec_token"] = xsec_map.get(nid, "")
        missing = [nid for nid in collected if nid not in xsec_map]
        if missing:
            print(f"  WARNING: {len(missing)} notes missing xsec_token")

        # ================================================================
        # Phase 3: Extract individual note content
        # ================================================================
        print(f"\nPhase 3: extracting content for {len(collected)} notes...")
        note_list = list(collected.values())

        for i, note in enumerate(note_list):
            nid = note["note_id"]
            token = note.get("xsec_token", "")
            title = note.get("title", "")

            if not token:
                print(f"  [{i+1}/{len(note_list)}] SKIP {title[:40]} (no token)")
                note["accessible"] = False
                note["error"] = "no xsec_token"
                continue

            print(f"  [{i+1}/{len(note_list)}] {title[:50]}...", end=" ", flush=True)
            content = await extract_note_content(page, nid, token)

            # Merge content into note
            note.update(
                {
                    "accessible": content["accessible"],
                    "url": content["url"],
                    "desc": content.get("desc", ""),
                    "images": content.get("images", []),
                    "tags": content.get("tags", []),
                    "stats": content.get("stats", {}),
                    "author": content.get("author", {}),
                    "error": content.get("error", ""),
                }
            )

            if content["accessible"]:
                img_count = len(content.get("images", []))
                print(f"✅ ({img_count} images)")
            else:
                print(f"❌ {content.get('error', 'unknown')}")

            # Rate limit
            await page.wait_for_timeout(1500)

        # ================================================================
        # Output
        # ================================================================
        print(f"\n{'='*40}")
        accessible = sum(1 for n in note_list if n.get("accessible"))
        print(f"TOTAL: {len(note_list)} notes, {accessible} accessible")

        output = {
            "profile": PROFILE_URL,
            "count": len(note_list),
            "accessible": accessible,
            "notes": note_list,
        }
        out_file = OUTPUT_DIR / "profile_posts.json"
        with open(out_file, "w", encoding="utf8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Saved: {out_file}")

        # Summary table
        for n in note_list:
            status = "✅" if n.get("accessible") else "❌"
            print(f"  {status} [{n['note_id'][:12]}] {n.get('title', '')[:60]}")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
