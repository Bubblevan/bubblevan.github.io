from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re

from .markdown import read_markdown, read_markdown_text


MARKER_RE = re.compile(r"^(?:[-*]\s+(?:\[[ xX]\]\s+)?)?@(?P<kind>task|link|event|project)\s+(?P<body>.+?)\s*$")
TOPIC_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_-]+)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_RE = re.compile(r"^https?://\S+$")
MARKDOWN_LINK_RE = re.compile(r"^\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)\s]+)\)(?:\s+(?P<text>.*))?$")


def run_extract(paths: list[str], out: str, root: str = ".") -> int:
    root_path = Path(root).resolve()
    out_dir = (root_path / out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = 0
    for raw_path in paths:
        path = (root_path / raw_path).resolve()
        if not path.exists():
            print(f"ERROR: {raw_path}: file does not exist")
            exit_code = 1
            continue
        items = extract_file(path, root_path)
        payload = {
            "schema": "bubblevan/extraction/v1",
            "source_path": to_posix(path, root_path),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "items": items,
        }
        output_path = out_dir / f"{path.stem}.json"
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(items)} items to {to_posix(output_path, root_path)}")
    return exit_code


def extract_file(path: Path, root: Path) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    md = read_markdown(path)
    default_date = frontmatter_date(md.frontmatter)
    for line_number, line in enumerate(read_markdown_text(path).splitlines(), start=1):
        parsed = parse_marker(line, default_date=default_date)
        if not parsed:
            continue
        parsed.update(
            {
                "capture_id": capture_id(path, root, line_number, line),
                "source_path": to_posix(path, root),
                "line": line_number,
                "raw": line.strip(),
                "confidence": 1.0,
            }
        )
        items.append(parsed)
    return items


def parse_marker(line: str, default_date: str | None = None) -> dict[str, object] | None:
    match = MARKER_RE.match(line.strip())
    if not match:
        return None

    item_type = match.group("kind")
    body = match.group("body").strip()
    topics = TOPIC_RE.findall(body)
    body = TOPIC_RE.sub("", body).strip()

    if item_type == "task":
        return parse_task(body, topics)
    if item_type == "link":
        return parse_link(body, topics)
    if item_type == "event":
        return parse_event(body, topics, default_date)
    if item_type == "project":
        return parse_project(body, topics)
    return None


def parse_task(body: str, topics: list[str]) -> dict[str, object]:
    parts = body.split(maxsplit=1)
    due = parts[0] if parts and DATE_RE.match(parts[0]) else None
    text = parts[1] if due and len(parts) > 1 else body
    item: dict[str, object] = {"type": "task", "text": text.strip(), "topics": topics}
    if due:
        item["due"] = due
    return item


def parse_link(body: str, topics: list[str]) -> dict[str, object]:
    markdown_link = MARKDOWN_LINK_RE.match(body)
    if markdown_link:
        label = markdown_link.group("label").strip()
        url = markdown_link.group("url").strip()
        note = (markdown_link.group("text") or "").strip()
        item: dict[str, object] = {"type": "link", "url": url, "text": label, "topics": topics}
        if note:
            item["note"] = note
        return item

    parts = body.split(maxsplit=1)
    url = parts[0] if parts and URL_RE.match(parts[0]) else ""
    text = parts[1] if url and len(parts) > 1 else body
    item: dict[str, object] = {"type": "link", "text": text.strip(), "topics": topics}
    if url:
        item["url"] = url
    return item


def parse_event(body: str, topics: list[str], default_date: str | None = None) -> dict[str, object]:
    parts = body.split(maxsplit=1)
    has_explicit_date = bool(parts and DATE_RE.match(parts[0]))
    event_date = parts[0] if has_explicit_date else default_date
    text = parts[1] if has_explicit_date and len(parts) > 1 else body
    item: dict[str, object] = {"type": "event", "text": text.strip(), "topics": topics}
    if event_date:
        item["event_date"] = event_date
    return item


def parse_project(body: str, topics: list[str]) -> dict[str, object]:
    parts = body.split(maxsplit=1)
    project_id = parts[0] if parts else ""
    text = parts[1] if len(parts) > 1 else ""
    return {"type": "project_log", "project_id": project_id, "text": text.strip(), "topics": topics}


def frontmatter_date(frontmatter: dict[str, object]) -> str | None:
    raw_date = frontmatter.get("date")
    if not isinstance(raw_date, str):
        return None
    date = raw_date.strip()[:10]
    return date if DATE_RE.match(date) else None


def capture_id(path: Path, root: Path, line_number: int, raw: str) -> str:
    source = f"{to_posix(path, root)}:{line_number}:{raw}".encode("utf-8")
    return "cap-" + hashlib.sha1(source).hexdigest()[:16]


def to_posix(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
