"""Read author fields and post cards through the user's existing Chrome."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from .xhs_chrome_use import acquire_profile_snapshot, is_xhs_url
    from .xhs_note_parser import redact_url
except ImportError:  # direct invocation
    from xhs_chrome_use import acquire_profile_snapshot, is_xhs_url
    from xhs_note_parser import redact_url


DEFAULT_CACHE_DIR = REPO_ROOT / ".cache" / "xhs-extracted"
PROFILE_ID_PATTERN = re.compile(r"/user/profile/([A-Za-z0-9]+)(?:/|$)")


def profile_id_from_url(url: str) -> str:
    match = PROFILE_ID_PATTERN.search(urlsplit(url).path)
    return match.group(1) if match else ""


def to_iso_timestamp(value: object) -> str:
    if isinstance(value, (int, float)) and value > 0:
        timestamp = value / 1000 if value > 10_000_000_000 else value
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return ""
    return ""


def enrich_result(data: dict) -> dict:
    data["source_url"] = redact_url(data.get("url", ""))
    data["retrieval"] = {
        "mode": "real_chrome",
        "logged_in": True,
        "used_user_profile": True,
        "browser_automation": "chrome-use",
        "snapshot_path": data.pop("snapshot_path", ""),
    }
    data["result"] = {
        "profile_posts_total": data.get("profile", {}).get("public_counts", {}).get("posts"),
        "loaded_post_cards": len(data.get("notes", [])),
        "cards_with_note_id": sum(bool(note.get("note_id")) for note in data.get("notes", [])),
        "page_has_more": data.get("pagination", {}).get("has_more"),
    }
    for note in data.get("notes", []):
        note["published_at"] = to_iso_timestamp(note.get("published_at_raw"))

    limits = []
    page_error = str(data.get("page_error") or "")
    errors = []
    if page_error.startswith(("SECURITY_RESTRICTED", "CAPTCHA_CHALLENGE", "RATE_LIMITED")):
        errors.append(page_error)
    data["errors"] = errors
    if data.get("login_page"):
        limits.append("The selected Chrome tab resolved to a login page.")
    if page_error:
        limits.append("The page displayed a security, verification, or rate-limit gate; no profile data was collected.")
    total_posts = data["result"].get("profile_posts_total")
    loaded_cards = data["result"]["loaded_post_cards"]
    if isinstance(total_posts, (int, float)) and total_posts > loaded_cards and data["result"]["page_has_more"] is False:
        limits.append(
            f"The profile reports {int(total_posts)} posts, but only {loaded_cards} cards were rendered; "
            "the current profile feed reports no additional cards."
        )
    if data.get("notes") and not data["result"]["cards_with_note_id"]:
        limits.append("The rendered profile omits note IDs; cards expose metadata and covers only.")
    if data.get("pagination", {}).get("has_more"):
        limits.append("The page still reports more cards after the bounded scroll pass.")
    data["limitations"] = limits
    data.pop("url", None)
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect profile data already rendered in an existing Chrome profile via chrome-use."
    )
    parser.add_argument("--url", required=True, help="Xiaohongshu author profile URL")
    parser.add_argument("--out-json", default="", help="write UTF-8 JSON; stdout is JSON when omitted")
    parser.add_argument("--snapshot-dir", default=str(DEFAULT_CACHE_DIR), help="directory for sanitized snapshots")
    parser.add_argument("--chrome-use-path", default="chrome-use", help="chrome-use executable name or path")
    parser.add_argument("--browser-timeout", type=int, default=45)
    parser.add_argument("--scroll-steps", type=int, default=4, help="ordinary page scrolls, clamped to 0–10")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = build_parser().parse_args(argv)
    url = args.url.strip()
    if not is_xhs_url(url):
        raise SystemExit("URL must use xiaohongshu.com or an xhslink domain")
    if not profile_id_from_url(url) and "xhslink." not in (urlsplit(url).hostname or ""):
        raise SystemExit("URL must point to /user/profile/<user_id>")

    snapshot, snapshot_path = acquire_profile_snapshot(
        url,
        cache_dir=Path(args.snapshot_dir),
        cli=args.chrome_use_path,
        timeout=args.browser_timeout,
        scroll_steps=args.scroll_steps,
    )
    snapshot["snapshot_path"] = str(snapshot_path)
    data = enrich_result(snapshot)
    if not data.get("page_has_profile_content") or data.get("errors"):
        serialized = json.dumps(data, ensure_ascii=False, indent=2)
        if args.out_json:
            output = Path(args.out_json)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(serialized + "\n", encoding="utf-8")
        else:
            print(serialized)
        return 1

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
