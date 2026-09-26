"""Extract publicly rendered Xiaohongshu author-profile cards anonymously."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tools.xhs_cdp import extract_rendered_profile, is_xhs_url


DEFAULT_CACHE_DIR = REPO_ROOT / ".cache" / "xhs_profile_reader"
PROFILE_ID_PATTERN = re.compile(r"/user/profile/([A-Za-z0-9]+)(?:/|$)")
SENSITIVE_QUERY_KEY = re.compile(r"token|secret|sign|auth|session|cookie|share.?red.?id|share.?id", re.I)


def redact_profile_url(url: str) -> str:
    parsed = urlsplit(url)
    query = [
        (key, "[redacted]" if SENSITIVE_QUERY_KEY.search(key) else value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def profile_id_from_url(url: str) -> str:
    match = PROFILE_ID_PATTERN.search(urlsplit(url).path)
    return match.group(1) if match else ""


def to_iso_timestamp(value: object) -> str:
    if isinstance(value, (int, float)) and value > 0:
        # XHS profile card timestamps are Unix milliseconds.
        stamp = value / 1000 if value > 10_000_000_000 else value
        try:
            return datetime.fromtimestamp(stamp, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return ""
    return ""


def enrich_result(data: dict) -> dict:
    data["source_url"] = redact_profile_url(data.get("url", ""))
    data["result"] = {
        "profile_posts_total": data.get("profile", {}).get("public_counts", {}).get("posts"),
        "loaded_post_cards": len(data.get("notes", [])),
        "cards_with_note_id": sum(bool(note.get("note_id")) for note in data.get("notes", [])),
        "page_has_more": data.get("pagination", {}).get("has_more"),
    }
    for note in data.get("notes", []):
        note["published_at"] = to_iso_timestamp(note.get("published_at_raw"))

    limits = []
    if data.get("login_page"):
        limits.append("The anonymous profile URL resolved to a login page.")
    total_posts = data["result"].get("profile_posts_total")
    loaded_cards = data["result"]["loaded_post_cards"]
    if (
        isinstance(total_posts, (int, float))
        and total_posts > loaded_cards
        and data["result"]["page_has_more"] is False
    ):
        limits.append(
            f"The profile reports {int(total_posts)} posts, but only {loaded_cards} cards were rendered; "
            "the anonymous page reports no additional cards on this feed."
        )
    if data.get("notes") and not data["result"]["cards_with_note_id"]:
        limits.append(
            "The rendered profile omits note IDs. It exposes card metadata and cover images, "
            "but does not provide a safe per-note URL for opening full post text or galleries."
        )
    if data.get("pagination", {}).get("has_more"):
        limits.append("The page still reports more cards after the bounded scroll pass.")
    data["limitations"] = limits
    data.pop("url", None)
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect author and post-card data already rendered on an anonymous Xiaohongshu profile."
    )
    parser.add_argument("--url", required=True, help="Xiaohongshu author profile URL (or xhslink redirect)")
    parser.add_argument("--out-json", default="", help="write UTF-8 JSON to this path; stdout is JSON when omitted")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--browser-timeout", type=int, default=35)
    parser.add_argument("--scroll-steps", type=int, default=4, help="normal page scrolls, clamped to 0–10")
    parser.add_argument("--chrome-executable", default="", help="optional path to Google Chrome")
    parser.add_argument("--headless", action="store_true", help="run the isolated temporary Chrome headlessly")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = build_parser().parse_args(argv)
    url = args.url.strip()
    if not is_xhs_url(url):
        raise SystemExit("URL must use xiaohongshu.com or an xhslink domain")
    user_id = profile_id_from_url(url)
    if not user_id and "xhslink." not in (urlsplit(url).hostname or ""):
        raise SystemExit("URL must point to /user/profile/<user_id>")

    data = extract_rendered_profile(
        url,
        user_id,
        cache_dir=Path(args.cache_dir),
        timeout=args.browser_timeout,
        chrome_executable=args.chrome_executable,
        headless=args.headless,
        scroll_steps=args.scroll_steps,
    )
    data = enrich_result(data)
    if not data.get("page_has_profile_content"):
        raise SystemExit("The anonymous page did not expose profile content; no profile JSON was saved.")
    serialized = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out_json:
        output = Path(args.out_json)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized + "\n", encoding="utf-8")
        profile = data.get("profile", {})
        print(
            f"Saved {len(serialized.encode('utf-8')):,} bytes to {output.resolve()}\n"
            f"Author: {profile.get('nickname') or 'unknown'}; "
            f"visible cards: {data['result']['loaded_post_cards']}; "
            f"cards with note ID: {data['result']['cards_with_note_id']}"
        )
    else:
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
