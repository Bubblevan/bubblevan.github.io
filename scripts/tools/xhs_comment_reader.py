#!/usr/bin/env python3
"""Compatibility entry point for the old XHS comment-reader command.

Comment extraction now lives in xhs_note_reader.py and reads only comments
already rendered by the anonymous note page. This wrapper preserves the old
output shape without importing or launching Playwright.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .xhs_note_reader import build_parser as build_note_parser, read_note
except ImportError:  # direct invocation from scripts/tools
    from xhs_note_reader import build_parser as build_note_parser, read_note


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read the comments already exposed by an anonymous Xiaohongshu note page."
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--browser-timeout", type=int, default=None)
    parser.add_argument("--chrome-executable", default="")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--user-data-dir", default="", help="deprecated and ignored; this command never reuses a profile")
    parser.add_argument("--max-seconds", type=int, default=None, help="deprecated alias for --browser-timeout")
    parser.add_argument("--max-scrolls", type=int, default=40, help="deprecated; anonymous comments are not expanded or bypassed")
    args = parser.parse_args(argv)

    if args.user_data_dir:
        print("Ignoring --user-data-dir: a fresh temporary anonymous Chrome profile is always used.", file=sys.stderr)

    reader_argv = [
        "--url", args.url,
        "--browser-timeout", str(args.browser_timeout or min(args.max_seconds or 35, 120)),
        "--chrome-executable", args.chrome_executable,
    ]
    if args.headless:
        reader_argv.append("--headless")
    result = read_note(build_note_parser().parse_args(reader_argv))
    comments = result.get("comments", [])
    output = {
        "ok": result.get("ok", False),
        "url": result.get("url", ""),
        "note_id": result.get("note_id", ""),
        "comment_count": len(comments),
        "comment_count_label": result.get("comment_count_label"),
        "comments_truncated_by_login": result.get("comments_truncated_by_login", False),
        "comments_text": result.get("comments_text", ""),
        "comments": comments,
        "retrieval": result.get("retrieval", {}),
        "warnings": result.get("warnings", []),
        "errors": result.get("errors", []),
    }
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": output["ok"], "comment_count": output["comment_count"], "out_json": str(out_path)}, ensure_ascii=False))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
