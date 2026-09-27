"""Acquire and normalize Xiaohongshu note data from explicit sources.

Parsing lives in xhs_note_parser.py. Acquisition is either static public HTML,
an offline saved file, or an explicitly requested chrome-use connection to the
already-running Chrome profile.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

try:
    from .xhs_chrome_use import acquire_note_snapshot
    from .xhs_html_acquisition import download_image, fetch_public_html
    from .xhs_note_parser import (
        extract_first_url,
        failure_result,
        parse_html,
        parse_rendered_snapshot,
        parse_runtime_json,
        redact_url,
    )
except ImportError:  # direct invocation: python scripts/tools/xhs_note_reader.py
    from xhs_chrome_use import acquire_note_snapshot
    from xhs_html_acquisition import download_image, fetch_public_html
    from xhs_note_parser import (
        extract_first_url,
        failure_result,
        parse_html,
        parse_rendered_snapshot,
        parse_runtime_json,
        redact_url,
    )


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = REPO_ROOT / ".cache" / "xhs-extracted"

StaticLoader = Callable[..., tuple[str, str]]
BrowserLoader = Callable[..., tuple[dict[str, Any], Path]]


def read_note(
    args: argparse.Namespace,
    *,
    static_loader: StaticLoader = fetch_public_html,
    browser_loader: BrowserLoader = acquire_note_snapshot,
) -> dict[str, Any]:
    source_url = extract_first_url(args.url)
    if args.state_file:
        try:
            result = parse_runtime_json(
                Path(args.state_file).read_text(encoding="utf-8"),
                url=source_url,
                mode="saved_runtime_state",
            )
        except OSError as exc:
            result = failure_result(source_url, "saved_runtime_state", f"STATE_FILE_READ_FAILED: {exc}")
        return _finish_result(result, args)

    if args.html_file:
        try:
            html_text = Path(args.html_file).read_text(encoding="utf-8")
        except OSError as exc:
            return failure_result(source_url, "saved_html", f"HTML_FILE_READ_FAILED: {exc}")
        result = parse_html(
            html_text,
            url=source_url,
            final_url=args.final_url or source_url,
            mode="saved_html",
        )
        return _finish_result(result, args)

    try:
        html_text, final_url = static_loader(source_url, timeout=args.timeout)
        result = parse_html(html_text, url=source_url, final_url=final_url, mode="static_html")
    except Exception as exc:
        result = failure_result(source_url, "static_html", f"PUBLIC_HTML_FETCH_FAILED: {exc}")

    # Do not touch Chrome after a successful static parse. Browser use is opt-in
    # and only considered when static acquisition produced no canonical note.
    errors = result.get("errors", [])
    stop_for_page_gate = any(
        str(error).startswith(("SECURITY_RESTRICTED", "CAPTCHA_CHALLENGE", "RATE_LIMITED"))
        for error in errors
    )
    if not result.get("ok") and not stop_for_page_gate and args.browser_adapter == "chrome-use":
        try:
            snapshot, snapshot_path = browser_loader(
                source_url,
                cache_dir=Path(args.snapshot_dir),
                cli=args.chrome_use_path,
                timeout=args.browser_timeout,
            )
            result = parse_rendered_snapshot(snapshot, url=source_url, mode="real_chrome")
            result.setdefault("retrieval", {}).update(
                {
                    "logged_in": {
                        "authenticated": True,
                        "anonymous": False,
                        "unknown": None,
                    }[args.browser_login_state],
                    "used_user_profile": True,
                    "browser_automation": "chrome-use",
                    "snapshot_path": str(snapshot_path),
                }
            )
            if result.get("ok"):
                result["warnings"].append("STATIC_HTML_UNAVAILABLE; note was read from the existing Chrome profile")
        except Exception as exc:
            result = failure_result(source_url, "real_chrome", f"CHROME_USE_ACQUISITION_FAILED: {exc}")
            result["retrieval"].update(
                {
                    "logged_in": {"authenticated": True, "anonymous": False, "unknown": None}[args.browser_login_state],
                    "used_user_profile": True,
                    "browser_automation": "chrome-use",
                }
            )

    return _finish_result(result, args)


def _finish_result(result: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if not result.get("ok"):
        return result
    images = result.get("images", [])
    if args.max_images > 0 and len(images) > args.max_images:
        available = len(images)
        images = images[: args.max_images]
        result["images"] = images
        result["gallery"] = {
            "image_count_available": available,
            "image_count_selected": len(images),
            "truncated": True,
        }
        result.setdefault("warnings", []).append(
            f"IMAGE_LIMIT_APPLIED: selected {len(images)} of {available} available images"
        )
    elif isinstance(result.get("gallery"), dict):
        result["gallery"].update(
            {
                "image_count_selected": len(images),
                "truncated": bool(result["gallery"].get("truncated")),
            }
        )

    if args.download_images:
        for image in images:
            try:
                local_path = download_image(
                    image["url"],
                    cache_dir=Path(args.cache_dir),
                    note_id=result.get("note_id", ""),
                    index=int(image["index"]),
                    timeout=args.image_timeout,
                    cache_key=str(image.get("image_id") or ""),
                )
                image["local_path"] = str(local_path)
            except Exception as exc:
                result.setdefault("errors", []).append(f"IMAGE_DOWNLOAD_FAILED[{image['index']}]: {exc}")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse Xiaohongshu note data from public HTML, saved files, or an explicit chrome-use read."
    )
    parser.add_argument("--url", required=True, help="Xiaohongshu share, xhslink, discovery/item, or explore URL")
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--html-file", default="", help="parse saved HTML offline; never fetch or open a browser")
    sources.add_argument("--state-file", default="", help="parse saved runtime-state JSON or sanitized snapshot offline")
    parser.add_argument("--final-url", default="", help="final URL associated with --html-file")
    parser.add_argument(
        "--browser-adapter",
        choices=("none", "chrome-use"),
        default="none",
        help="explicitly allow existing Chrome fallback only if static HTML has no note data",
    )
    parser.add_argument(
        "--browser-login-state",
        choices=("authenticated", "anonymous", "unknown"),
        default="authenticated",
        help="provenance assertion for the selected Chrome session; does not inspect cookies or storage",
    )
    parser.add_argument("--chrome-use-path", default="chrome-use", help="chrome-use executable name or path")
    parser.add_argument("--browser-timeout", type=int, default=45, help="chrome-use command timeout in seconds")
    parser.add_argument("--snapshot-dir", default=str(DEFAULT_CACHE_DIR), help="directory for sanitized runtime snapshots")
    parser.add_argument("--download-images", action="store_true", help="download all selected gallery images")
    parser.add_argument("--max-images", type=int, default=0, help="maximum images; 0 (default) keeps the full gallery")
    parser.add_argument("--out-json", default="", help="write UTF-8 JSON to this path; stdout is JSON when omitted")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR), help="image download cache directory")
    parser.add_argument("--timeout", type=int, default=20, help="static HTML request timeout in seconds")
    parser.add_argument("--image-timeout", type=int, default=30, help="per-image download timeout in seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = read_note(args)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out_json:
        output = Path(args.out_json)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized + "\n", encoding="utf-8")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        print(serialized)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
