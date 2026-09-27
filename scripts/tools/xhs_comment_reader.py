#!/usr/bin/env python3
"""Compatibility command for comments already rendered in existing Chrome."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from .xhs_chrome_use import acquire_note_snapshot
    from .xhs_note_parser import parse_rendered_snapshot
except ImportError:  # direct invocation
    from xhs_chrome_use import acquire_note_snapshot
    from xhs_note_parser import parse_rendered_snapshot


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = REPO_ROOT / ".cache" / "xhs-extracted"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read comments already rendered in the user's existing Chrome profile via chrome-use."
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--chrome-use-path", default="chrome-use")
    parser.add_argument("--browser-timeout", type=int, default=45)
    parser.add_argument("--snapshot-dir", default=str(DEFAULT_CACHE_DIR))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        snapshot, snapshot_path = acquire_note_snapshot(
            args.url,
            cache_dir=Path(args.snapshot_dir),
            cli=args.chrome_use_path,
            timeout=args.browser_timeout,
        )
        result = parse_rendered_snapshot(snapshot, url=args.url, mode="real_chrome")
        result["retrieval"].update(
            {
                "logged_in": True,
                "used_user_profile": True,
                "browser_automation": "chrome-use",
                "snapshot_path": str(snapshot_path),
            }
        )
    except Exception as exc:
        result = {
            "ok": False,
            "url": "",
            "note_id": "",
            "comments": [],
            "comments_text": "",
            "comment_count_label": None,
            "retrieval": {
                "mode": "real_chrome",
                "logged_in": True,
                "used_user_profile": True,
                "browser_automation": "chrome-use",
            },
            "errors": [f"CHROME_USE_ACQUISITION_FAILED: {exc}"],
        }
    output = {
        "ok": result.get("ok", False),
        "url": result.get("url", ""),
        "note_id": result.get("note_id", ""),
        "comment_count": len(result.get("comments", [])),
        "comment_count_label": result.get("comment_count_label"),
        "comments_truncated_by_login": result.get("comments_truncated_by_login", False),
        "comments_text": result.get("comments_text", ""),
        "comments": result.get("comments", []),
        "retrieval": result.get("retrieval", {}),
        "warnings": result.get("warnings", []),
        "errors": result.get("errors", []),
    }
    path = Path(args.out_json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    print(json.dumps({"ok": output["ok"], "comment_count": output["comment_count"], "out_json": str(path)}, ensure_ascii=False))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
