from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re

from .dedupe import iter_capture_records


@dataclass
class DraftResult:
    text: str
    output_path: Path | None
    count: int


def draft_from_captures(
    root: Path,
    since: str = "today",
    topic: str = "",
    project: str = "",
    dry_run: bool = True,
    out_path: Path | None = None,
) -> DraftResult:
    root = root.resolve()
    records = [
        record for record in (iter_capture_records(root) or [])
        if record.get("status") != "duplicate"
        and matches_since(record, since)
        and matches_topic(record, topic)
        and matches_project(record, project)
    ]
    text = render_draft(records, topic=topic, project=project, since=since)
    output: Path | None = None
    if not dry_run:
        slug = slugify(topic or project or "capture-draft")
        output = out_path or (root / "inbox" / "drafts" / f"{date.today().isoformat()}-{slug}.md")
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    return DraftResult(text=text, output_path=output, count=len(records))


def render_draft(records: list[dict], topic: str, project: str, since: str) -> str:
    title_hint = topic or project or "capture draft"
    lines = [
        "---",
        "schema: bubblevan/draft/v1",
        f"date: {date.today().isoformat()}",
        "status: draft",
        "visibility: private",
        f"source: captures since {since}",
        "---",
        "",
        f"# {title_hint}",
        "",
        "## Why this matters",
        "",
        "- TODO: Confirm the actual angle before publishing.",
        "",
        "## Source captures",
        "",
    ]
    for record in records:
        text = str(record.get("text", "")).replace("\n", " ")[:220]
        urls = record.get("urls", [])
        url_text = f" {urls[0]}" if isinstance(urls, list) and urls else ""
        lines.append(f"- [{record.get('type_hint')}] {text}{url_text}")
    lines.extend([
        "",
        "## Draft outline",
        "",
        "1. Context",
        "2. Key observations",
        "3. What I should do next",
        "4. Links and references",
        "",
        "## Publish checklist",
        "",
        "- Confirm visibility.",
        "- Confirm no private raw text leaks.",
        "- Confirm Hugo build passes.",
    ])
    return "\n".join(lines)


def matches_since(record: dict, since: str) -> bool:
    if since == "all":
        return True
    value = str(record.get("created_at", ""))
    try:
        created = datetime.fromisoformat(value).date()
    except ValueError:
        return False
    if since == "today":
        return created == date.today()
    try:
        return created >= date.fromisoformat(since)
    except ValueError:
        return True


def matches_topic(record: dict, topic: str) -> bool:
    if not topic:
        return True
    wanted = topic.strip("# ").lower()
    topics = [str(t).lower() for t in record.get("topics", [])]
    text = str(record.get("text", "")).lower()
    return wanted in topics or wanted in text


def matches_project(record: dict, project: str) -> bool:
    if not project:
        return True
    return str(record.get("project_hint", "")).lower() == project.lower()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.strip().lower()).strip("-")
    return slug or "capture-draft"

