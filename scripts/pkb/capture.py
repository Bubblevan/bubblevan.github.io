from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib
import json
import re

from .dedupe import find_duplicate
from .normalize_url import normalize_url


ALLOWED_TYPES = {"link", "bookmark", "task", "event", "project_log", "note"}


@dataclass
class CaptureInput:
    type_hint: str
    text: str = ""
    urls: list[str] = field(default_factory=list)
    project_hint: str = ""
    topics: list[str] = field(default_factory=list)
    visibility: str = "private"
    source_agent: str = "manual"
    source_platform: str = "windows"
    source_channel: str = "cli"
    source_message_id: str = ""
    original_text: str = ""
    raw_payload: object | None = None


def create_capture(root: Path, capture_input: CaptureInput) -> dict[str, object]:
    root = root.resolve()
    now = datetime.now().astimezone()
    created_at = now.isoformat(timespec="seconds")
    type_hint = capture_input.type_hint
    if type_hint not in ALLOWED_TYPES:
        raise ValueError(f"unsupported type_hint: {type_hint}")

    urls = [normalize_url(url) for url in capture_input.urls if url.strip()]
    text = capture_input.text.strip()
    original_text = capture_input.original_text.strip() or text
    content_sha = sha256("|".join([type_hint, text, " ".join(urls), capture_input.project_hint, original_text]))
    dedupe_key = build_dedupe_key(type_hint, urls, capture_input.project_hint, content_sha)
    capture_id = "cap-" + sha256(f"{created_at}|{dedupe_key}|{content_sha}")[:20]

    duplicate_of = find_duplicate(root, dedupe_key)
    status = "duplicate" if duplicate_of else "new"

    record: dict[str, object] = {
        "capture_id": capture_id,
        "created_at": created_at,
        "source_agent": capture_input.source_agent,
        "source_platform": capture_input.source_platform,
        "source_channel": capture_input.source_channel,
        "source_message_id": capture_input.source_message_id,
        "type_hint": type_hint,
        "text": text,
        "urls": urls,
        "project_hint": capture_input.project_hint,
        "topics": sorted(set(t.strip("# ") for t in capture_input.topics if t.strip("# "))),
        "visibility": capture_input.visibility or "private",
        "dedupe_key": dedupe_key,
        "content_sha256": content_sha,
        "status": status,
        "raw": {
            "original_text": original_text,
            "payload": capture_input.raw_payload,
        },
    }
    if duplicate_of:
        record["duplicate_of"] = duplicate_of

    append_jsonl(root, now, record)
    append_raw_markdown(root, now, record)
    append_extraction_item(root, now, record)
    auto_promote_to_data(root, record)
    return record


def build_dedupe_key(type_hint: str, urls: list[str], project_hint: str, content_sha: str) -> str:
    if urls:
        return f"url:{urls[0]}"
    if type_hint == "project_log":
        return f"project:{project_hint}:{content_sha}"
    return f"text:{type_hint}:{content_sha}"


def append_jsonl(root: Path, now: datetime, record: dict[str, object]) -> None:
    path = root / "data" / "captures" / f"{now:%Y-%m}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def append_raw_markdown(root: Path, now: datetime, record: dict[str, object]) -> None:
    path = root / "inbox" / "raw" / f"{now:%Y}" / f"{now:%m}" / f"{now:%Y-%m-%d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = phase2_marker(record)
    lines = [
        "",
        f"## {now:%H:%M:%S} {record['capture_id']}",
        "",
        f"- source: {record['source_agent']} / {record['source_channel']}",
        f"- visibility: {record['visibility']}",
        f"- status: {record['status']}",
    ]
    if record.get("duplicate_of"):
        lines.append(f"- duplicate_of: {record['duplicate_of']}")
    lines.extend(["", marker, "", "```text", str(record["raw"]["original_text"]), "```", ""])
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def phase2_marker(record: dict[str, object]) -> str:
    topics = " ".join(f"#{topic}" for topic in record.get("topics", []))
    text = str(record.get("text", "")).strip()
    type_hint = record.get("type_hint")
    urls = record.get("urls", [])
    if type_hint in {"link", "bookmark"}:
        url = urls[0] if urls else ""
        return compact(f"- @link {url} {text} {topics}")
    if type_hint == "task":
        return compact(f"- @task {text} {topics}")
    if type_hint == "event":
        return compact(f"- @event {text} {topics}")
    if type_hint == "project_log":
        return compact(f"- @project {record.get('project_hint', '')} {text} {topics}")
    return compact(f"- note: {text} {topics}")


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ── Phase 2 bridge ──


_TYPE_MAP = {
    "link": "link",
    "bookmark": "link",
    "task": "task",
    "event": "event",
    "project_log": "project_log",
    "note": "note",
}


def _record_to_extraction(record: dict[str, object], source_path: str, line: int) -> dict[str, object]:
    itype = _TYPE_MAP.get(str(record.get("type_hint", "")), "note")
    text = str(record.get("text", ""))
    topics = list(record.get("topics", [])) if isinstance(record.get("topics"), list) else []
    urls = list(record.get("urls", [])) if isinstance(record.get("urls"), list) else []
    raw_text = str((record.get("raw") or {}).get("original_text", text)) if isinstance(record.get("raw"), dict) else text
    raw_marker = _build_marker_str(record)
    item: dict[str, object] = {
        "capture_id": record.get("capture_id", ""),
        "type": itype,
        "source_path": source_path,
        "line": line,
        "raw": raw_marker,
        "text": text,
        "topics": topics,
        "confidence": 1.0,
    }
    if itype == "link" and urls:
        item["url"] = urls[0]
    if itype == "task":
        item["due"] = ""
    if itype == "event":
        item["event_date"] = ""
    if itype == "project_log":
        item["project_id"] = str(record.get("project_hint", ""))
    return item


def _build_marker_str(record: dict[str, object]) -> str:
    topics = " ".join(f"#{t}" for t in (record.get("topics") or []))
    text = str(record.get("text", ""))
    urls = record.get("urls", [])
    th = record.get("type_hint")
    if th in ("link", "bookmark"):
        url = urls[0] if isinstance(urls, list) and urls else ""
        return compact(f"@link {url} {text} {topics}")
    if th == "task":
        return compact(f"@task {text} {topics}")
    if th == "event":
        return compact(f"@event {text} {topics}")
    if th == "project_log":
        return compact(f"@project {record.get('project_hint', '')} {text} {topics}")
    return compact(f"@note {text} {topics}")


def append_extraction_item(root: Path, now: datetime, record: dict[str, object]) -> None:
    extraction_dir = root / "generated" / "extraction"
    extraction_dir.mkdir(parents=True, exist_ok=True)

    source_path = f"inbox/raw/{now:%Y}/{now:%m}/{now:%Y-%m-%d}.md"
    json_path = extraction_dir / f"{now:%Y-%m-%d}.json"

    existing_items: list[dict[str, object]] = []
    if json_path.exists():
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            existing_items = payload.get("items", []) if isinstance(payload, list) else payload.get("items", [])
        except (json.JSONDecodeError, KeyError):
            existing_items = []

    # count lines in raw file to determine new item's line number
    raw_path = root / "inbox" / "raw" / f"{now:%Y}" / f"{now:%m}" / f"{now:%Y-%m-%d}.md"
    line_count = len(raw_path.read_text(encoding="utf-8").splitlines()) if raw_path.exists() else 0

    new_item = _record_to_extraction(record, source_path, line_count)
    existing_items.append(new_item)

    # deduplicate by capture_id (keep last occurrence)
    seen: set[str] = set()
    deduped: list[dict[str, object]] = []
    for item in reversed(existing_items):
        cid = str(item.get("capture_id", ""))
        if cid not in seen:
            seen.add(cid)
            deduped.append(item)
    deduped.reverse()

    payload = {
        "schema": "bubblevan/extraction/v1",
        "source_path": source_path,
        "generated_at": now.isoformat(),
        "items": deduped,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


_AUTO_TARGET = {"task": "data/reminders.yaml", "event": "data/reminders.yaml", "link": "data/bookmarks.yaml", "bookmark": "data/bookmarks.yaml"}


def auto_promote_to_data(root: Path, record: dict[str, object]) -> None:
    th = str(record.get("type_hint", ""))
    target = _AUTO_TARGET.get(th)
    if not target:
        return

    # use shared YAML reader from scripts.kb
    from scripts.kb.promote import read_data_yaml, write_data_yaml

    target_path = root / target
    existing = read_data_yaml(target_path)

    # build entry matching existing data format
    text = str(record.get("text", ""))
    topics = list(record.get("topics", [])) if isinstance(record.get("topics"), list) else []
    urls = list(record.get("urls", [])) if isinstance(record.get("urls"), list) else []
    entry_id = f"{th}-about-{record.get('capture_id','')[:12]}"
    entry_id = re.sub(r"[^a-z0-9_-]", "-", entry_id.lower())

    entry: dict = {
        "id": entry_id,
        "title": text,
        "status": "todo" if th in ("task", "event") else "active",
        "visibility": "public",
        "topics": topics,
    }
    if th in ("task", "event"):
        entry["due"] = ""
    if th in ("link", "bookmark"):
        entry["url"] = urls[0] if urls else ""
        entry["saved_at"] = datetime.now().astimezone().strftime("%Y-%m-%d")
        entry["notes"] = ""

    # avoid duplicate id
    existing_ids = {e.get("id") for e in existing}
    if entry["id"] in existing_ids:
        return

    existing.append(entry)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    write_data_yaml(target_path, existing)
