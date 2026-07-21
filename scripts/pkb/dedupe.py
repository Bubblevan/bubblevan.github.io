from __future__ import annotations

from pathlib import Path
import json


def iter_capture_records(root: Path):
    captures_dir = root / "data" / "captures"
    if not captures_dir.exists():
        return
    for path in sorted(captures_dir.glob("*.jsonl")):
        if path.name == "drop-processed.json":
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def find_duplicate(root: Path, dedupe_key: str) -> str | None:
    for record in iter_capture_records(root) or []:
        if record.get("dedupe_key") == dedupe_key and record.get("status") != "duplicate":
            return record.get("capture_id")
    return None

