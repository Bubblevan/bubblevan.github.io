"""Sequential XHS batch reader that pins every navigation to one adopted Chrome tab."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import parse_qsl, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tools.xhs_chrome_use import (  # noqa: E402
    ChromeUseClient,
    ChromeUseError,
    acquire_pinned_note_snapshot,
    is_xhs_url,
    pin_existing_tab,
)
from scripts.tools.xhs_note_parser import (  # noqa: E402
    extract_note_id,
    failure_result,
    parse_rendered_snapshot,
    redact_url,
)


URL_PATTERN = re.compile(r"https?://[^\s<>\]\)\"']+")
DEFAULT_CACHE_DIR = REPO_ROOT / ".cache" / "xhs-extracted"
SENSITIVE_QUERY_KEY = re.compile(r"token|secret|sign|auth|session|cookie|code", re.I)


def source_urls_from_text(text: str) -> tuple[list[tuple[str, str]], int]:
    """Return first source URL per note ID; callers must not persist these raw URLs."""
    rows: list[tuple[str, str]] = []
    raw_note_url_count = 0
    seen: set[str] = set()
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;，。；、】》")
        url = url.replace("\\&", "&").replace("\\_", "_").replace("&amp;", "&")
        if not is_xhs_url(url):
            continue
        note_id = extract_note_id(url)
        if not note_id:
            continue
        raw_note_url_count += 1
        if note_id in seen:
            continue
        seen.add(note_id)
        rows.append((url, note_id))
    return rows, raw_note_url_count


def _load_success_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    succeeded: set[str] = set()
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("ok") and isinstance(row.get("note_id"), str):
                succeeded.add(row["note_id"])
    return succeeded


def _write_checkpoint(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        output.flush()
        os.fsync(output.fileno())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _contains_unredacted_sensitive_url(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_unredacted_sensitive_url(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_unredacted_sensitive_url(child) for child in value)
    if not isinstance(value, str) or not value.startswith(("http://", "https://")):
        return False
    return any(
        SENSITIVE_QUERY_KEY.search(key) and item not in {"", "[redacted]"}
        for key, item in parse_qsl(urlsplit(value).query, keep_blank_values=True)
    )


def write_report_artifacts(
    *,
    source_rows: list[tuple[str, str]],
    raw_url_count: int,
    jsonl_path: Path,
    checkpoint_path: Path,
    summary_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Refresh human-readable and machine summaries from sanitized JSONL only."""
    results = _read_jsonl(jsonl_path)
    successes_by_id: dict[str, dict[str, Any]] = {}
    failures_by_id: dict[str, dict[str, Any]] = {}
    for row in results:
        note_id = str(row.get("note_id") or "")
        if not note_id:
            continue
        if row.get("ok"):
            successes_by_id[note_id] = row
        else:
            failures_by_id[note_id] = row
    ordered_ids = [note_id for _url, note_id in source_rows]
    success_ids = set(successes_by_id)
    failure_ids = set(failures_by_id)
    attempted_ids = success_ids | failure_ids
    pending_ids = [note_id for note_id in ordered_ids if note_id not in attempted_ids]
    successful_rows = [successes_by_id[note_id] for note_id in ordered_ids if note_id in successes_by_id]
    visible_comment_rows = [row for row in successful_rows if str(row.get("comments_text") or "").strip()]
    image_count = sum(len(row.get("images") or []) for row in successful_rows)
    visible_comment_characters = sum(len(str(row.get("comments_text") or "")) for row in successful_rows)
    comments_login_limited = sum(bool(row.get("comments_truncated_by_login")) for row in successful_rows)
    checkpoint: dict[str, Any] = {}
    if checkpoint_path.exists():
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            checkpoint = {}
    unredacted_urls = any(_contains_unredacted_sensitive_url(row) for row in results)
    summary = {
        "source_attachment": "user-provided attachment",
        "raw_url_count": raw_url_count,
        "unique_note_count": len(ordered_ids),
        "attempted_unique_notes": len(attempted_ids),
        "successful_unique_notes": len(success_ids),
        "failed_unique_notes": len(failure_ids),
        "not_attempted_unique_notes": len(pending_ids),
        "extracted_gallery_images": image_count,
        "notes_with_visible_comment_text": len(visible_comment_rows),
        "visible_comment_text_characters": visible_comment_characters,
        "notes_where_comments_were_login_limited": comments_login_limited,
        "failure_note_ids": [note_id for note_id in ordered_ids if note_id in failure_ids],
        "not_attempted_note_ids": pending_ids,
        "current_blocker": (
            f"{checkpoint.get('stop_reason')} at note index {checkpoint.get('next_index')} "
            f"({checkpoint.get('stop_note_id')}); checkpoint saved."
            if checkpoint.get("stop_reason") not in {"", "complete"}
            else ""
        ),
        "checkpoint": {
            "next_index": checkpoint.get("next_index", 0),
            "stop_note_id": checkpoint.get("stop_note_id", ""),
            "stop_reason": checkpoint.get("stop_reason", ""),
            "pinned_tab_id": checkpoint.get("pinned_tab_id", ""),
        },
        "retrieval": {
            "mode": "real_chrome",
            "logged_in": False,
            "used_user_profile": True,
            "browser_automation": "chrome-use",
        },
        "secrets_persisted": unredacted_urls,
        "offline_cache_additional_notes": 0,
        "readable_report": report_path.name,
        "jsonl": jsonl_path.name,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Xiaohongshu batch extraction",
        "",
        f"- Raw note links: {raw_url_count}",
        f"- Unique notes: {len(ordered_ids)}",
        f"- Attempted: {len(attempted_ids)}; successful: {len(success_ids)}; failed: {len(failure_ids)}; pending: {len(pending_ids)}",
        f"- Gallery images: {image_count}",
        f"- Notes with visible comment text: {len(visible_comment_rows)} ({visible_comment_characters} characters)",
        f"- Comments login-limited: {comments_login_limited}",
        f"- Pinned Chrome tab: {summary['checkpoint']['pinned_tab_id']}",
        f"- Next index: {summary['checkpoint']['next_index']}",
        f"- Stop reason: {summary['checkpoint']['stop_reason'] or 'none'}",
        "",
        "Source URLs are omitted; the JSONL stores only redacted result URLs.",
        "",
        "## Successfully extracted notes",
        "",
    ]
    for note_id in ordered_ids:
        row = successes_by_id.get(note_id)
        if not row:
            continue
        title = str(row.get("title") or "(no title)").replace("\r", " ").replace("\n", " ")
        author = str((row.get("author") or {}).get("nickname") or "")
        lines.extend([
            f"### {title}",
            "",
            f"- Note ID: `{note_id}`",
            f"- Author: {author or '(unknown)'}",
            f"- Gallery images: {len(row.get('images') or [])}",
            f"- Tags: {', '.join(str(tag) for tag in row.get('tags') or []) or '(none)'}",
            f"- Engagement: {json.dumps(row.get('stats') or {}, ensure_ascii=False)}",
            "",
        ])
        desc = str(row.get("desc") or "").strip()
        if desc:
            lines.extend(["**正文**", "", desc, ""])
        comment_text = str(row.get("comments_text") or "").strip()
        if comment_text:
            lines.extend(["**当前可见评论**", "", comment_text, ""])
        if row.get("comments_truncated_by_login"):
            lines.extend(["评论区还标记为登录后可查看完整内容。", ""])
        images = row.get("images") or []
        if images:
            lines.extend(["**图集 URL**", ""])
            for image in images:
                image_url = redact_url(str(image.get("url") or ""))
                if image_url:
                    lines.append(f"- [{image.get('index', '?')}]({image_url})")
            lines.append("")
    if failure_ids:
        lines.extend(["## Failed attempts", ""])
        for note_id in ordered_ids:
            row = failures_by_id.get(note_id)
            if row:
                reason = "; ".join(str(item) for item in row.get("errors") or []) or "BATCH_STOPPED"
                lines.append(f"- Index {row.get('source_index', '?')}: `{note_id}` — {reason}")
        lines.append("")
    if pending_ids:
        lines.extend(["## Not attempted", "", ", ".join(f"`{note_id}`" for note_id in pending_ids), ""])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return summary


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _checkpoint_seed(
    *, source_fingerprint: str, next_index: int, total: int, tab_id: str, succeeded: set[str]
) -> dict[str, Any]:
    return {
        "source_fingerprint": source_fingerprint,
        "next_index": next_index,
        "total_unique_notes": total,
        "pinned_tab_id": tab_id,
        "successful_note_ids": sorted(succeeded),
        "last_success_note_id": "",
        "stop_reason": "",
        "updated_at": _now(),
    }


def _error_code(message: str) -> str:
    for code in (
        "LOGIN_SHELL",
        "CAPTCHA_CHALLENGE",
        "SECURITY_RESTRICTED_300011",
        "SECURITY_RESTRICTED_300031",
        "RATE_LIMITED",
        "RELAY_DISCONNECTED",
        "PINNED_TAB_LOST",
        "PINNED_TAB_CHANGED",
        "PINNED_TAB_NOT_ATTACHED",
        "NOTE_ID_MISMATCH",
        "NOTE_ROUTE_MISMATCH",
        "TARGET_ORIGIN_MISMATCH",
        "NOTE_CONTENT_MISSING",
    ):
        if code in message:
            return code
    if "relay" in message.lower():
        return "RELAY_DISCONNECTED"
    return "BATCH_STOPPED"


def run_batch(args: argparse.Namespace) -> int:
    input_path = Path(args.input_file)
    try:
        source_text = input_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"INPUT_READ_FAILED: {exc}", file=sys.stderr)
        return 2
    rows, raw_count = source_urls_from_text(source_text)
    del source_text  # Raw share URLs stay in memory only for live navigation.
    if not rows:
        print("NO_XHS_NOTE_URLS: input file contained no supported note links", file=sys.stderr)
        return 2

    note_ids = [note_id for _url, note_id in rows]
    fingerprint = hashlib.sha256("\n".join(note_ids).encode("utf-8")).hexdigest()
    output_path = Path(args.out_jsonl)
    checkpoint_path = Path(args.checkpoint)
    summary_path = Path(args.summary_json)
    report_path = Path(args.report_md)
    succeeded = _load_success_ids(output_path)

    def refresh_reports() -> None:
        try:
            write_report_artifacts(
                source_rows=rows,
                raw_url_count=raw_count,
                jsonl_path=output_path,
                checkpoint_path=checkpoint_path,
                summary_path=summary_path,
                report_path=report_path,
            )
        except OSError as exc:
            print(f"REPORT_UPDATE_FAILED: {exc}", file=sys.stderr)

    if checkpoint_path.exists():
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"CHECKPOINT_INVALID: {exc}", file=sys.stderr)
            return 2
        if checkpoint.get("source_fingerprint") != fingerprint:
            print("CHECKPOINT_SOURCE_MISMATCH: refusing to resume a different URL set", file=sys.stderr)
            return 2
        if str(checkpoint.get("pinned_tab_id") or "") != args.tab_id:
            print("CHECKPOINT_TAB_MISMATCH: resume with the same pinned tab ID", file=sys.stderr)
            return 2
        start_index = int(checkpoint.get("next_index", 0))
    else:
        start_index = args.start_index if args.start_index is not None else 0
        checkpoint = _checkpoint_seed(
            source_fingerprint=fingerprint,
            next_index=start_index,
            total=len(rows),
            tab_id=args.tab_id,
            succeeded=succeeded,
        )
        _write_checkpoint(checkpoint_path, checkpoint)

    if not 0 <= start_index <= len(rows):
        print("CHECKPOINT_INDEX_INVALID: next_index is outside the source list", file=sys.stderr)
        return 2
    if args.dry_run:
        pending = sum(1 for _url, note_id in rows[start_index:] if note_id not in succeeded)
        print(json.dumps({
            "raw_note_url_count": raw_count,
            "unique_note_count": len(rows),
            "start_index": start_index,
            "remaining_not_successful": pending,
            "pinned_tab_id": args.tab_id,
            "checkpoint": str(checkpoint_path),
            "out_jsonl": str(output_path),
        }, ensure_ascii=False, indent=2))
        return 0

    browser = ChromeUseClient(
        executable=args.chrome_use_path,
        timeout=args.timeout,
        session=args.session,
    )
    try:
        pinned = pin_existing_tab(args.tab_id, client=browser)
    except Exception as exc:
        checkpoint.update({
            "next_index": start_index,
            "stop_reason": _error_code(str(exc)),
            "updated_at": _now(),
        })
        _write_checkpoint(checkpoint_path, checkpoint)
        print(f"STOPPED_BEFORE_NAVIGATION: {_error_code(str(exc))}", file=sys.stderr)
        refresh_reports()
        return 2

    print(json.dumps({
        "event": "pinned_tab_ready",
        "tab_id": pinned["tab_id"],
        "note_id_at_start": pinned["note_id"],
        "ownership": pinned["ownership"],
        "relay_up": pinned["relay_up"],
        "relay_attached_reported": pinned["relay_attached_reported"],
        "first_batch_index": start_index,
        "total_unique_notes": len(rows),
    }, ensure_ascii=False))

    newly_succeeded = 0
    index = start_index
    while index < len(rows):
        source_url, note_id = rows[index]
        if note_id in succeeded:
            index += 1
            checkpoint.update({"next_index": index, "stop_reason": "", "updated_at": _now()})
            _write_checkpoint(checkpoint_path, checkpoint)
            continue

        try:
            snapshot, snapshot_path = acquire_pinned_note_snapshot(
                source_url,
                tab_id=args.tab_id,
                cache_dir=Path(args.snapshot_dir),
                cli=args.chrome_use_path,
                timeout=args.timeout,
                session=args.session,
                client=browser,
            )
            result = parse_rendered_snapshot(snapshot, url=source_url, mode="real_chrome")
            if not result.get("ok"):
                error_message = "; ".join(str(item) for item in result.get("errors", [])) or "NOTE_CONTENT_MISSING"
                raise ChromeUseError(error_message)
            if result.get("note_id") != note_id:
                raise ChromeUseError("NOTE_ID_MISMATCH: normalized note ID differed from requested ID")
            result["retrieval"].update({
                "logged_in": False,
                "used_user_profile": True,
                "browser_automation": "chrome-use",
                "pinned_tab_id": args.tab_id,
                "snapshot_path": str(snapshot_path),
            })
            result["source_index"] = index
            _append_jsonl(output_path, result)
            succeeded.add(note_id)
            newly_succeeded += 1
            index += 1
            checkpoint.update({
                "next_index": index,
                "successful_note_ids": sorted(succeeded),
                "last_success_note_id": note_id,
                "stop_reason": "",
                "updated_at": _now(),
            })
            _write_checkpoint(checkpoint_path, checkpoint)
            refresh_reports()
            print(json.dumps({
                "event": "note_saved",
                "source_index": index - 1,
                "note_id": note_id,
                "image_count": len(result.get("images", [])),
                "visible_comment_text_characters": len(result.get("comments_text") or ""),
                "next_index": index,
                "saved_total": newly_succeeded,
            }, ensure_ascii=False))
        except KeyboardInterrupt:
            checkpoint.update({"next_index": index, "stop_reason": "INTERRUPTED", "updated_at": _now()})
            _write_checkpoint(checkpoint_path, checkpoint)
            print(f"CHECKPOINT_SAVED: next_index={index}", file=sys.stderr)
            return 130
        except Exception as exc:
            error = str(exc)
            code = _error_code(error)
            failure = failure_result(source_url, "real_chrome", code)
            failure["source_index"] = index
            failure["retrieval"].update({
                "logged_in": False,
                "used_user_profile": True,
                "browser_automation": "chrome-use",
                "pinned_tab_id": args.tab_id,
            })
            _append_jsonl(output_path, failure)
            checkpoint.update({
                "next_index": index,
                "successful_note_ids": sorted(succeeded),
                "stop_note_id": note_id,
                "stop_reason": code,
                "updated_at": _now(),
            })
            _write_checkpoint(checkpoint_path, checkpoint)
            refresh_reports()
            print(json.dumps({
                "event": "batch_stopped",
                "source_index": index,
                "note_id": note_id,
                "reason": code,
                "next_index": index,
                "checkpoint": str(checkpoint_path),
            }, ensure_ascii=False), file=sys.stderr)
            return 2

    checkpoint.update({
        "next_index": len(rows),
        "successful_note_ids": sorted(succeeded),
        "stop_reason": "complete",
        "updated_at": _now(),
    })
    _write_checkpoint(checkpoint_path, checkpoint)
    refresh_reports()
    print(json.dumps({
        "event": "batch_complete",
        "new_successes": newly_succeeded,
        "success_total": len(succeeded),
        "unique_note_count": len(rows),
        "next_index": len(rows),
        "out_jsonl": str(output_path),
        "checkpoint": str(checkpoint_path),
    }, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read XHS notes sequentially through one existing adopted Chrome tab and checkpoint each result."
    )
    parser.add_argument("--input-file", required=True, help="user-provided text/Markdown containing original XHS share URLs")
    parser.add_argument("--out-jsonl", default=str(DEFAULT_CACHE_DIR / "batch-from-attachment.jsonl"))
    parser.add_argument("--checkpoint", default=str(DEFAULT_CACHE_DIR / "batch-from-attachment.checkpoint.json"))
    parser.add_argument("--summary-json", default=str(DEFAULT_CACHE_DIR / "batch-from-attachment.summary.json"))
    parser.add_argument("--report-md", default=str(DEFAULT_CACHE_DIR / "batch-from-attachment.md"))
    parser.add_argument("--start-index", type=int, default=None, help="starting unique-link index for a new checkpoint")
    parser.add_argument("--tab-id", required=True, help="existing adopted Chrome tab ID, such as t2")
    parser.add_argument("--session", default="default", help="existing chrome-use session name")
    parser.add_argument("--chrome-use-path", default="chrome-use")
    parser.add_argument("--snapshot-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true", help="validate input/checkpoint counts without opening or navigating a page")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_batch(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
