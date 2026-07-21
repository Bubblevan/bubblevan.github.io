from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .capture import CaptureInput, create_capture
from .cleanup_raw import cleanup_raw
from .dedupe import iter_capture_records
from .draft_from_captures import draft_from_captures
from .import_wechat import import_wechat_file
from .process_drop import process_drop
from .review_captures import review_captures


REQUIRED_CAPTURE_FIELDS = {
    "capture_id",
    "created_at",
    "source_agent",
    "source_platform",
    "source_channel",
    "source_message_id",
    "type_hint",
    "text",
    "urls",
    "project_hint",
    "topics",
    "visibility",
    "dedupe_key",
    "content_sha256",
    "status",
    "raw",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scripts.pkb.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="append a capture record")
    capture.add_argument("--type", required=True, dest="type_hint", choices=["link", "bookmark", "task", "event", "project_log", "note"])
    capture.add_argument("--url", action="append", default=[], help="captured URL; can be repeated")
    capture.add_argument("--text", default="", help="capture text")
    capture.add_argument("--project", default="", help="project hint, e.g. stablepay")
    capture.add_argument("--topic", action="append", default=[], help="topic; can be repeated")
    capture.add_argument("--visibility", default="private", choices=["private", "public"])
    capture.add_argument("--source-agent", default="manual")
    capture.add_argument("--source-platform", default="windows")
    capture.add_argument("--source-channel", default="cli")
    capture.add_argument("--source-message-id", default="")
    capture.add_argument("--raw", default="", help="original raw text")
    capture.add_argument("--root", default=".")

    process = subparsers.add_parser("process-drop", help="process inbox/drop adapter files")
    process.add_argument("--root", default=".")

    validate = subparsers.add_parser("validate-captures", help="validate data/captures jsonl")
    validate.add_argument("--root", default=".")

    import_wechat = subparsers.add_parser("import-wechat", help="convert a pasted WeChat memo file into a drop JSON file")
    import_wechat.add_argument("--file", required=True, help="UTF-8 text file containing pasted/exported WeChat memo text")
    import_wechat.add_argument("--adapter", default="hermes", choices=["hermes", "openclaw", "workbuddy"])
    import_wechat.add_argument("--source-channel", default="wechat", choices=["wechat", "qq", "desktop", "manual"])
    import_wechat.add_argument("--topic", action="append", default=[], help="default topic; can be repeated")
    import_wechat.add_argument("--project", default="", help="default project hint")
    import_wechat.add_argument("--out", default="", help="optional output drop JSON path")
    import_wechat.add_argument("--root", default=".")

    review = subparsers.add_parser("review-captures", help="write a Phase 4 capture review note")
    review.add_argument("--since", default="today", help="today, all, or YYYY-MM-DD")
    review.add_argument("--include-duplicates", action="store_true")
    review.add_argument("--out", default="", help="optional markdown output path")
    review.add_argument("--root", default=".")

    draft = subparsers.add_parser("draft", help="render an inbox draft from captures")
    draft.add_argument("--from", default="today", dest="since", help="today, all, or YYYY-MM-DD")
    draft.add_argument("--topic", default="")
    draft.add_argument("--project", default="")
    draft.add_argument("--dry-run", action="store_true", help="print draft instead of writing inbox/drafts")
    draft.add_argument("--out", default="", help="optional inbox draft output path")
    draft.add_argument("--root", default=".")

    cleanup = subparsers.add_parser("cleanup-raw", help="remove inbox raw files older than N days")
    cleanup.add_argument("--max-age", type=int, default=3, help="max age in days (default 3)")
    cleanup.add_argument("--root", default=".")

    dedup = subparsers.add_parser("dedup-check", help="check data/*.yaml for duplicates against captures")
    dedup.add_argument("--root", default=".")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(getattr(args, "root", ".")).resolve()
    if args.command == "capture":
        capture_input = CaptureInput(
            type_hint=args.type_hint,
            text=args.text,
            urls=args.url,
            project_hint=args.project,
            topics=args.topic,
            visibility=args.visibility,
            source_agent=args.source_agent,
            source_platform=args.source_platform,
            source_channel=args.source_channel,
            source_message_id=args.source_message_id,
            original_text=args.raw or args.text,
        )
        record = create_capture(root, capture_input)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0
    if args.command == "process-drop":
        created, skipped = process_drop(root)
        print(f"Processed drop files: {created} captures, {skipped} files skipped")
        return 0
    if args.command == "validate-captures":
        return validate_captures(root)
    if args.command == "import-wechat":
        result = import_wechat_file(
            root=root,
            file_path=Path(args.file),
            adapter=args.adapter,
            source_channel=args.source_channel,
            topics=args.topic,
            project_hint=args.project,
            out_path=Path(args.out) if args.out else None,
        )
        print(f"Imported WeChat memo: {result.count} drop items -> {result.output_path}")
        return 0
    if args.command == "review-captures":
        result = review_captures(
            root=root,
            since=args.since,
            include_duplicates=args.include_duplicates,
            out_path=Path(args.out) if args.out else None,
        )
        print(f"Review queue: {result.count} items -> {result.markdown_path}")
        print(f"Review data: {result.queue_path}")
        return 0
    if args.command == "draft":
        result = draft_from_captures(
            root=root,
            since=args.since,
            topic=args.topic,
            project=args.project,
            dry_run=args.dry_run,
            out_path=Path(args.out) if args.out else None,
        )
        if args.dry_run:
            print(result.text)
        else:
            print(f"Draft: {result.count} captures -> {result.output_path}")
        return 0
    if args.command == "cleanup-raw":
        removed, kept = cleanup_raw(root, max_age_days=args.max_age)
        print(f"Cleaned inbox/raw: {removed} files removed, {kept} kept (>{args.max_age} days)")
        return 0
    if args.command == "dedup-check":
        return dedup_against_data(root)
    return 2


def validate_captures(root: Path) -> int:
    errors: list[str] = []
    count = 0
    for record in iter_capture_records(root) or []:
        count += 1
        missing = sorted(field for field in REQUIRED_CAPTURE_FIELDS if field not in record)
        if missing:
            errors.append(f"{record.get('capture_id', '<unknown>')}: missing {', '.join(missing)}")
        if not isinstance(record.get("urls"), list):
            errors.append(f"{record.get('capture_id', '<unknown>')}: urls must be a list")
        if not isinstance(record.get("topics"), list):
            errors.append(f"{record.get('capture_id', '<unknown>')}: topics must be a list")
        if record.get("visibility") not in {"private", "public"}:
            errors.append(f"{record.get('capture_id', '<unknown>')}: invalid visibility")
        if record.get("status") not in {"new", "duplicate", "processed", "rejected"}:
            errors.append(f"{record.get('capture_id', '<unknown>')}: invalid status")
        raw = record.get("raw")
        if not isinstance(raw, dict) or "original_text" not in raw:
            errors.append(f"{record.get('capture_id', '<unknown>')}: raw.original_text is required")

    for error in errors:
        print(f"ERROR: {error}")
    print(f"Validated {count} captures: {len(errors)} errors")
    return 1 if errors else 0


def dedup_against_data(root: Path) -> int:
    """Cross-check capture JSONL against existing data/*.yaml for duplicates."""
    try:
        from scripts.kb.promote import read_data_yaml
    except ImportError:
        print("ERROR: cannot import scripts.kb.promote; run from repo root")
        return 1

    data_urls: set[str] = set()
    data_titles: set[str] = set()
    for yaml_path in [Path("data/reminders.yaml"), Path("data/bookmarks.yaml")]:
        entries = read_data_yaml(root / yaml_path)
        for entry in entries:
            if entry.get("url"):
                data_urls.add(entry["url"].lower().rstrip("/"))
            if entry.get("title"):
                data_titles.add(entry["title"].strip().lower())

    dupes = 0
    for record in iter_capture_records(root) or []:
        if record.get("status") == "duplicate":
            continue
        urls = record.get("urls", [])
        for url in urls:
            if url.lower().rstrip("/") in data_urls:
                print(f"DUPLICATE URL:  {record.get('capture_id','?')}  →  {url}")
                dupes += 1
                break
        text = (record.get("text", "") or "").strip().lower()
        if text and text in data_titles:
            print(f"DUPLICATE TEXT: {record.get('capture_id','?')}  →  \"{record.get('text','')}\"")
            dupes += 1

    print(f"Dedup check: {dupes} potential duplicates found")
    return 0 if dupes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
