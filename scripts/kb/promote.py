"""Promotion logic — write extracted items into data/*.yaml and track reviewed state."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re

REVIEW_FILE = "generated/reviewed.json"

TYPE_TO_FILE = {
    "task": "data/reminders.yaml",
    "event": "data/reminders.yaml",
    "link": "data/bookmarks.yaml",
}


def load_reviewed(root: Path) -> set[str]:
    path = root / REVIEW_FILE
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("reviewed", []))


def save_reviewed(root: Path, reviewed: set[str]) -> None:
    path = root / REVIEW_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"reviewed": sorted(reviewed)}, indent=2) + "\n", encoding="utf-8")


def find_item(root: Path, capture_id: str) -> dict | None:
    extraction_dir = root / "generated" / "extraction"
    if not extraction_dir.exists():
        return None
    for fp in sorted(extraction_dir.glob("*.json")):
        payload = json.loads(fp.read_text(encoding="utf-8"))
        for item in payload.get("items", []):
            if item.get("capture_id") == capture_id:
                item["_source_path"] = payload.get("source_path", "")
                return item
    return None


def _gen_data_id(itype: str, text: str, timestamp: str) -> str:
    prefix = {"task": "reminder", "event": "event", "link": "bookmark"}.get(itype, "item")
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower().strip())[:36].strip("-")
    digest = hashlib.sha1(f"{itype}:{text}:{timestamp}".encode()).hexdigest()[:6]
    return f"{prefix}-{slug}-{digest}"


def build_data_entry(item: dict) -> dict:
    itype = item.get("type", "")
    text = item.get("text", "")
    topics = item.get("topics", [])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry: dict = {
        "id": _gen_data_id(itype, text, now),
        "title": text,
        "status": "todo" if itype in ("task", "event") else "active",
        "visibility": "public",
        "topics": topics,
    }

    if itype == "task":
        entry["due"] = item.get("due", "")
    elif itype == "event":
        entry["due"] = item.get("event_date", "")
    elif itype == "link":
        entry["url"] = item.get("url", "")
        entry["saved_at"] = now
        entry["notes"] = ""

    return entry


# ── simple YAML read/write (stdlib only, handles the known data/*.yaml shape) ──


def _is_blank(value: str) -> bool:
    return not value or value.strip() in ("", "[]")


def read_data_yaml(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if _is_blank(text):
        return []
    entries: list[dict] = []
    current: dict | None = None
    in_list: str | None = None
    for line in text.splitlines():
        raw = line.rstrip("\r")
        # new entry
        if raw.startswith("- "):
            if current is not None:
                entries.append(current)
            current = {}
            in_list = None
            rest = raw[2:]
            if ": " in rest:
                k, v = rest.split(": ", 1)
                current[k.strip()] = v.strip().strip("'\"")
        elif current is not None:
            if raw.startswith("    - ") and in_list:
                val = raw[6:].strip().strip("'\"")
                lst = current.setdefault(in_list, [])
                if isinstance(lst, list):
                    lst.append(val)
            elif ": " in raw and not raw.lstrip().startswith("- "):
                content = raw.strip()
                k, v = content.split(": ", 1)
                v = v.strip().strip("'\"")
                if v:
                    current[k.strip()] = v
                    in_list = None
                else:
                    current[k.strip()] = []
                    in_list = k.strip()
    if current is not None:
        entries.append(current)
    return entries


def _yaml_value(val: object) -> str:
    if isinstance(val, str):
        if val == "":
            return ""
        if set(val) & {" ", ":", "#"}:
            return f'"{val}"'
        return val
    return str(val)


def write_data_yaml(path: Path, entries: list[dict]) -> None:
    if not entries:
        path.write_text("[]\n", encoding="utf-8")
        return

    key_order = ["id", "title", "url", "due", "saved_at", "status", "visibility", "notes", "topics"]
    lines: list[str] = []
    for entry in entries:
        lines.append(f"- id: {entry.get('id', '')}")
        for key in key_order:
            if key == "id" or key not in entry:
                continue
            val = entry[key]
            if key == "topics":
                if isinstance(val, list) and val:
                    lines.append("  topics:")
                    for t in val:
                        lines.append(f"    - {t}")
                continue
            if val == "" or val is None:
                continue
            lines.append(f"  {key}: {_yaml_value(val)}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_promote(capture_id: str, root: str = ".", force: bool = False) -> int:
    root_path = Path(root).resolve()

    reviewed = load_reviewed(root_path)
    if capture_id in reviewed and not force:
        print(f"Item {capture_id} already promoted. Use --force to re-promote.")
        return 0

    item = find_item(root_path, capture_id)
    if not item:
        print(f"ERROR: capture_id '{capture_id}' not found in generated/extraction/*.json")
        return 1

    itype = item.get("type", "")
    target = TYPE_TO_FILE.get(itype)
    if not target:
        print(f"ERROR: type '{itype}' is not promotable (supported: task, event, link).")
        return 1

    target_path = root_path / target
    existing = read_data_yaml(target_path)

    new_entry = build_data_entry(item)

    existing_ids = {e.get("id") for e in existing}
    if new_entry["id"] in existing_ids:
        print(f"ERROR: duplicate id '{new_entry['id']}' already in {target}.")
        return 1

    existing.append(new_entry)
    write_data_yaml(target_path, existing)

    reviewed.add(capture_id)
    save_reviewed(root_path, reviewed)

    print(f"Promoted  {capture_id}")
    print(f"  → {target}  ({new_entry['id']})")
    print(f"     \"{new_entry['title']}\"")
    return 0
