from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable

from ..schema_validator import validate_record
from ..store import JsonlStore
from .models import default_profile


class FeedRepository:
    """Private profile and immutable FeedRun storage rooted below private/feed."""

    def __init__(self, private_dir: Path | str):
        self.root = Path(private_dir)
        self.profile_path = self.root / "profile.json"
        self.runs_dir = self.root / "runs"
        self.feedback_store = JsonlStore(self.root / "events")

    def load_profile(self) -> dict[str, Any]:
        if not self.profile_path.exists():
            return default_profile()
        value = _read_object(self.profile_path)
        validate_record("feed_profile", value)
        return value

    def save_profile(self, profile: dict[str, Any]) -> None:
        validate_record("feed_profile", profile)
        _atomic_json(self.profile_path, profile)

    def runs(self, feed_date: str | None = None) -> list[dict[str, Any]]:
        if not self.runs_dir.exists():
            return []
        rows = []
        for path in sorted(self.runs_dir.glob("*.json")):
            if feed_date and not path.name.startswith(feed_date + "-"):
                continue
            run = _read_object(path)
            validate_record("feed_run", run)
            rows.append(run)
        return sorted(rows, key=lambda row: (row["feed_date"], int(row["revision"])))

    def current_run(self, feed_date: str) -> dict[str, Any] | None:
        rows = self.runs(feed_date)
        return rows[-1] if rows else None

    def get_run(self, feed_run_id: str) -> dict[str, Any] | None:
        for run in self.runs():
            if run["feed_run_id"] == feed_run_id:
                return run
        return None

    def save_run(self, run: dict[str, Any]) -> None:
        validate_record("feed_run", run)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        path = self.runs_dir / f"{run['feed_date']}-r{int(run['revision']):04d}.json"
        if path.exists():
            existing = _read_object(path)
            if existing != run:
                raise ValueError("immutable FeedRun revision already exists with different contents")
            return
        _atomic_json(path, run)

    def all_feedback(self, legacy_store: JsonlStore | None = None) -> list[dict[str, Any]]:
        # M4's feed feedback is private to this repository/environment. Legacy
        # M0 Feedback records in the canonical event store are never unioned in.
        rows = list(self.feedback_store.iter_records("feedback"))
        unique = {str(row.get("feedback_id")): row for row in rows if row.get("feedback_id")}
        return sorted(unique.values(), key=lambda row: (str(row.get("occurred_at") or ""), str(row.get("feedback_id") or "")))

    def append_feedback(self, event: dict[str, Any]) -> bool:
        return self.feedback_store.append_feedback(event)


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid private feed JSON at {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"private feed JSON must be an object: {path}")
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
