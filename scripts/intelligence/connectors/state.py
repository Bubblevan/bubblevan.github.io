from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from .base import ConnectorCheckpoint


@dataclass
class ConnectorState(ConnectorCheckpoint):
    source_id: str = ""
    connector_id: str = ""
    connector_version: str = "1"
    last_attempt_at: str | None = None
    consecutive_failures: int = 0
    backoff_until: str | None = None
    last_error_class: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConnectorState":
        allowed = cls.__dataclass_fields__
        if not isinstance(value, dict) or set(value) - set(allowed):
            raise ValueError("connector checkpoint has unsupported fields")
        if not value.get("source_id") or not value.get("connector_id"):
            raise ValueError("connector checkpoint is missing source_id or connector_id")
        try:
            state = cls(**value)
        except TypeError as exc:
            raise ValueError("connector checkpoint is malformed") from exc
        for key in ("source_id", "connector_id", "connector_version"):
            if not isinstance(getattr(state, key), str) or not getattr(state, key):
                raise ValueError("connector checkpoint is malformed")
        if not isinstance(state.consecutive_failures, int) or isinstance(state.consecutive_failures, bool) or state.consecutive_failures < 0:
            raise ValueError("connector checkpoint has invalid failure count")
        for key in ("cursor", "etag", "last_modified", "high_watermark", "last_success_at",
                    "last_attempt_at", "backoff_until", "last_error_class"):
            item = getattr(state, key)
            if item is not None and not isinstance(item, str):
                raise ValueError("connector checkpoint has invalid field type")
        for key in ("last_success_at", "last_attempt_at", "backoff_until"):
            item = getattr(state, key)
            if item:
                try:
                    parsed = datetime.fromisoformat(item.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise ValueError("connector checkpoint has invalid timestamp") from exc
                if parsed.tzinfo is None:
                    raise ValueError("connector checkpoint timestamp must include a timezone")
        return state


class ConnectorStateStore:
    def __init__(self, runtime_dir: Path | str):
        self.directory = Path(runtime_dir) / "connectors"

    def path_for(self, source_id: str) -> Path:
        if not re.fullmatch(r"src-[0-9a-f]{24}", source_id):
            raise ValueError("invalid source_id for connector checkpoint")
        return self.directory / f"{source_id}.json"

    def load(self, source_id: str) -> ConnectorState | None:
        path = self.path_for(source_id)
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            state = ConnectorState.from_dict(value)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"corrupt connector checkpoint for {source_id}") from exc
        if state.source_id != source_id:
            raise ValueError(f"connector checkpoint source mismatch for {source_id}")
        return state

    def save(self, state: ConnectorState) -> None:
        if not state.source_id or not state.connector_id:
            raise ValueError("connector checkpoint requires source_id and connector_id")
        path = self.path_for(state.source_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_name = ""
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="\n", dir=path.parent,
                prefix=f".{path.name}.", suffix=".tmp", delete=False,
            ) as handle:
                temp_name = handle.name
                json.dump(asdict(state), handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
