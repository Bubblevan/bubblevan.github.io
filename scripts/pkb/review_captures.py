from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import json

from .dedupe import iter_capture_records


@dataclass
class ReviewResult:
    markdown_path: Path
    queue_path: Path
    count: int


def review_captures(
    root: Path,
    since: str = "today",
    include_duplicates: bool = False,
    out_path: Path | None = None,
) -> ReviewResult:
    root = root.resolve()
    records = list(iter_capture_records(root) or [])
    filtered = [
        record for record in records
        if should_include(record, since, include_duplicates)
    ]
    queue = [to_queue_item(record) for record in filtered]

    today = date.today().isoformat()
    markdown_path = out_path or (root / "inbox" / "review" / f"{today}.md")
    if not markdown_path.is_absolute():
        markdown_path = root / markdown_path
    queue_path = root / "data" / "review" / "queue.json"

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(queue, since), encoding="utf-8")
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ReviewResult(markdown_path=markdown_path, queue_path=queue_path, count=len(queue))


def should_include(record: dict, since: str, include_duplicates: bool) -> bool:
    if not include_duplicates and record.get("status") == "duplicate":
        return False
    if since == "all":
        return True
    created = parse_date(str(record.get("created_at", "")))
    if created is None:
        return False
    if since == "today":
        return created == date.today()
    try:
        return created >= date.fromisoformat(since)
    except ValueError:
        return True


def to_queue_item(record: dict) -> dict[str, object]:
    return {
        "capture_id": record.get("capture_id", ""),
        "created_at": record.get("created_at", ""),
        "type_hint": record.get("type_hint", ""),
        "text": record.get("text", ""),
        "urls": record.get("urls", []),
        "topics": record.get("topics", []),
        "project_hint": record.get("project_hint", ""),
        "status": record.get("status", ""),
        "source_agent": record.get("source_agent", ""),
        "source_channel": record.get("source_channel", ""),
        "candidate_action": candidate_action(record),
    }


def candidate_action(record: dict) -> str:
    if record.get("status") == "duplicate":
        return "inspect_duplicate"
    type_hint = record.get("type_hint")
    if type_hint in {"link", "bookmark"}:
        return "bookmark_or_source_candidate"
    if type_hint == "task":
        return "dashboard_reminder_candidate"
    if type_hint == "event":
        return "schedule_candidate"
    if type_hint == "project_log":
        return "project_retrospective_candidate"
    return "draft_or_keep_raw"


def render_markdown(queue: list[dict[str, object]], since: str) -> str:
    lines = [
        "---",
        "schema: bubblevan/review/v1",
        f"date: {date.today().isoformat()}",
        f"since: {since}",
        "status: private",
        "---",
        "",
        f"# Capture Review - {date.today().isoformat()}",
        "",
        f"Total pending items: {len(queue)}",
        "",
    ]
    by_action: dict[str, list[dict[str, object]]] = {}
    for item in queue:
        by_action.setdefault(str(item["candidate_action"]), []).append(item)

    for action, items in sorted(by_action.items()):
        lines.extend([f"## {action}", ""])
        for item in items:
            text = str(item.get("text", "")).replace("\n", " ")[:180]
            urls = item.get("urls", [])
            url_text = f" {urls[0]}" if isinstance(urls, list) and urls else ""
            lines.append(f"- [{item.get('type_hint')}] {text}{url_text}")
            lines.append(f"  - id: {item.get('capture_id')}")
            lines.append(f"  - source: {item.get('source_agent')} / {item.get('source_channel')}")
            topics = item.get("topics", [])
            if topics:
                lines.append(f"  - topics: {', '.join(str(t) for t in topics)}")
        lines.append("")
    return "\n".join(lines)


def parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None

