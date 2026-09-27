from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from .schema_validator import validate_record


_ID_FIELDS = {
    "source": "source_id",
    "observation": "observation_id",
    "artifact": "artifact_id",
    "entity": "entity_id",
    "feedback": "feedback_id",
}
_PARTITION_PREFIX = {"observation": "observations", "feedback": "feedback"}
_EVENT_KINDS = {"observation", "feedback"}
_MATERIALIZED_KINDS = {"source", "artifact", "entity"}
_SECRET_KEY = re.compile(r"(?:cookie|authorization|xsec|session|access.?token|refresh.?token|raw.?runtime)", re.IGNORECASE)
_URL_FIELDS = {"url", "canonical_url", "source_url", "preview_url"}
_SENSITIVE_QUERY = re.compile(r"(?:cookie|authorization|xsec|session|token)", re.IGNORECASE)


class JsonlStore:
    """Local JSONL event log plus atomically replaced canonical materializations."""

    def __init__(self, directory: Path | str):
        self.directory = Path(directory)

    def append_observation(self, record: dict[str, Any]) -> bool:
        return self._append_event("observation", record, "observed_at")

    def append_feedback(self, record: dict[str, Any]) -> bool:
        return self._append_event("feedback", record, "occurred_at")

    def upsert_source(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._upsert_materialized("source", record)

    def upsert_artifact(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._upsert_materialized("artifact", record)

    def upsert_entity(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._upsert_materialized("entity", record)

    def get_by_id(self, kind: str, item_id: str) -> dict[str, Any] | None:
        id_field = _ID_FIELDS.get(kind)
        if not id_field:
            raise ValueError(f"unsupported record kind: {kind}")
        for record in self.iter_records(kind):
            if record.get(id_field) == item_id:
                return record
        return None

    def iter_records(self, kind: str) -> Iterator[dict[str, Any]]:
        if kind not in _ID_FIELDS:
            raise ValueError(f"unsupported record kind: {kind}")
        files = self._files_for(kind)
        records: list[dict[str, Any]] = []
        for path in files:
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"malformed JSONL at {path}:{line_number}") from exc
                    if not isinstance(record, dict):
                        raise ValueError(f"record at {path}:{line_number} must be an object")
                    records.append(record)
        id_field = _ID_FIELDS[kind]
        if kind == "feedback":
            records.sort(key=lambda item: (str(item.get("occurred_at", "")), str(item.get(id_field, ""))))
        elif kind == "observation":
            records.sort(key=lambda item: (str(item.get("observed_at", "")), str(item.get(id_field, ""))))
        else:
            records.sort(key=lambda item: str(item.get(id_field, "")))
        yield from records

    def stats(self) -> dict[str, int]:
        return {kind: sum(1 for _ in self.iter_records(kind)) for kind in _ID_FIELDS}

    def _append_event(self, kind: str, record: dict[str, Any], timestamp_field: str) -> bool:
        if kind not in _EVENT_KINDS:
            raise ValueError(f"{kind} is not an event kind")
        self._validate_record(kind, record)
        id_field = _ID_FIELDS[kind]
        if self.get_by_id(kind, str(record[id_field])) is not None:
            return False
        timestamp = _parse_month(str(record[timestamp_field]))
        path = self.directory / f"{_PARTITION_PREFIX[kind]}-{timestamp}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = _json_line(record)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return True

    def _upsert_materialized(self, kind: str, record: dict[str, Any]) -> dict[str, Any]:
        if kind not in _MATERIALIZED_KINDS:
            raise ValueError(f"{kind} is not a materialized kind")
        self._validate_record(kind, record)
        id_field = _ID_FIELDS[kind]
        path = self.directory / f"{kind}s.jsonl"
        current = {
            str(item[id_field]): item
            for item in self.iter_records(kind)
            if item.get(id_field)
        }
        key = str(record[id_field])
        merged = _merge(current.get(key), record)
        current[key] = merged
        self._atomic_write(path, [current[item_id] for item_id in sorted(current)])
        return merged

    def _validate_record(self, kind: str, record: dict[str, Any]) -> None:
        if not isinstance(record, dict):
            raise TypeError("record must be an object")
        id_field = _ID_FIELDS[kind]
        if not str(record.get(id_field, "")).strip():
            raise ValueError(f"{kind} record requires {id_field}")
        validate_record(kind, record)
        _assert_private_fields_absent(record)

    def _files_for(self, kind: str) -> list[Path]:
        if kind in _MATERIALIZED_KINDS:
            return [self.directory / f"{kind}s.jsonl"]
        if not self.directory.exists():
            return []
        prefix = f"{_PARTITION_PREFIX[kind]}-"
        return sorted(
            (path for path in self.directory.glob(f"{prefix}*.jsonl") if path.is_file()),
            key=lambda path: path.name,
        )

    @staticmethod
    def _atomic_write(path: Path, records: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_name = ""
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="\n",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_name = handle.name
                for record in records:
                    handle.write(_json_line(record))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)


def _parse_month(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid timestamp for JSONL partition: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.strftime("%Y-%m")


def _json_line(record: Mapping[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _merge(existing: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        return dict(incoming)
    result = dict(existing)
    for key, value in incoming.items():
        old = result.get(key)
        if isinstance(value, list) and isinstance(old, list):
            by_payload = {_json_line({"value": item}): item for item in old + value}
            result[key] = [by_payload[payload] for payload in sorted(by_payload)]
        elif isinstance(value, dict) and isinstance(old, dict):
            merged_dict = dict(old)
            for nested_key, nested_value in value.items():
                if merged_dict.get(nested_key) in (None, "") and nested_value not in (None, ""):
                    merged_dict[nested_key] = nested_value
            result[key] = merged_dict
        elif key in {"created_at"} and old and value:
            result[key] = min(str(old), str(value))
        elif key in {"updated_at"} and old and value:
            result[key] = max(str(old), str(value))
        elif key == "status" and old and value:
            progression = {"candidate": 0, "saved": 1, "deep_read": 2, "verified": 3, "promoted": 4}
            if old in progression and value in progression:
                result[key] = max((old, value), key=lambda item: progression[item])
            else:
                result[key] = value
        elif key in {"title", "summary"} and isinstance(value, str) and isinstance(old, str):
            candidates = [item for item in (old, value) if item]
            if candidates:
                result[key] = min(candidates, key=lambda item: (-len(item), item.casefold(), item))
        elif old in (None, "", {}):
            result[key] = value
    return result


def _assert_private_fields_absent(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if _SECRET_KEY.search(key_text) or key_text.strip().casefold() in {"token", "tokens", "bearer"}:
                raise ValueError(f"private field is not allowed in intelligence records: {path}.{key_text}")
            _assert_private_fields_absent(item, f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_private_fields_absent(item, f"{path}[{index}]")
    elif isinstance(value, str):
        if re.search(r"(?i)(?:xsec_token|cookie|authorization|session(?:_token)?|access_token|refresh_token|token)\s*[:=]\s*(?!\[REDACTED\])[^,\s;&]+", value):
            raise ValueError(f"private credential text is not allowed in intelligence records: {path}")
        if any(key for key, _ in parse_qsl(urlsplit(value).query, keep_blank_values=True) if _SENSITIVE_QUERY.search(key)):
            raise ValueError(f"private URL query is not allowed in intelligence records: {path}")
