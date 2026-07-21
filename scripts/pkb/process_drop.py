from __future__ import annotations

from pathlib import Path
import hashlib
import json

from .capture import CaptureInput, create_capture


DROP_SOURCES = ("hermes", "openclaw", "workbuddy")
PROCESSED_FILE = Path("data/captures/drop-processed.json")


def process_drop(root: Path) -> tuple[int, int]:
    root = root.resolve()
    processed = load_processed(root)
    created = 0
    skipped = 0

    for source in DROP_SOURCES:
        drop_dir = root / "inbox" / "drop" / source
        drop_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(drop_dir.glob("*.json")):
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            key = f"{source}:{path.name}:{digest}"
            if key in processed:
                skipped += 1
                continue
            payload = json.loads(raw.decode("utf-8-sig"))
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                capture_input = input_from_drop(item, source)
                create_capture(root, capture_input)
                created += 1
            processed.add(key)

    save_processed(root, processed)
    return created, skipped


def input_from_drop(item: dict, source: str) -> CaptureInput:
    urls = item.get("urls") or []
    if isinstance(urls, str):
        urls = [urls]
    topics = item.get("topics") or []
    if isinstance(topics, str):
        topics = [topics]
    return CaptureInput(
        type_hint=item.get("type_hint") or item.get("type") or "note",
        text=item.get("text") or "",
        urls=urls,
        project_hint=item.get("project_hint") or item.get("project") or "",
        topics=topics,
        visibility=item.get("visibility") or "private",
        source_agent=item.get("source_agent") or source,
        source_platform=item.get("source_platform") or "windows",
        source_channel=item.get("source_channel") or source,
        source_message_id=item.get("source_message_id") or "",
        original_text=(item.get("raw") or {}).get("original_text") if isinstance(item.get("raw"), dict) else item.get("original_text", ""),
        raw_payload=item,
    )


def load_processed(root: Path) -> set[str]:
    path = root / PROCESSED_FILE
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("processed", []))


def save_processed(root: Path, processed: set[str]) -> None:
    path = root / PROCESSED_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"processed": sorted(processed)}, indent=2) + "\n", encoding="utf-8")

