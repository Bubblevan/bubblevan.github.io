from __future__ import annotations

from datetime import date, timedelta
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from ..schema_validator import validate_record


class DailyRunStore:
    """Immutable daily run manifests stored below runtime/ops/daily."""

    def __init__(self, runtime_dir: Path | str):
        self.directory = Path(runtime_dir) / "ops" / "daily"

    def path_for(self, run_date: str, attempt: int) -> Path:
        normalized = date.fromisoformat(run_date).isoformat()
        if attempt < 1:
            raise ValueError("attempt must be positive")
        return self.directory / f"{normalized}-r{attempt:04d}.json"

    def save(self, run: dict[str, Any]) -> None:
        validate_record("daily_pipeline_run", run)
        path = self.path_for(str(run["run_date"]), int(run["attempt"]))
        if path.exists():
            existing = self._read(path)
            if existing != run:
                raise ValueError("DailyPipelineRun attempt is immutable and already exists")
            return
        _atomic_json(path, run)

    def for_date(self, run_date: str, *, mode: str | None = None) -> list[dict[str, Any]]:
        normalized = date.fromisoformat(run_date).isoformat()
        if not self.directory.exists():
            return []
        rows = [self._read(path) for path in sorted(self.directory.glob(f"{normalized}-r*.json"))]
        if mode:
            rows = [row for row in rows if row["mode"] == mode]
        return sorted(rows, key=lambda row: int(row["attempt"]))

    def all(self, *, mode: str | None = None) -> list[dict[str, Any]]:
        if not self.directory.exists():
            return []
        rows = [self._read(path) for path in sorted(self.directory.glob("*-r*.json"))]
        if mode:
            rows = [row for row in rows if row["mode"] == mode]
        return sorted(rows, key=lambda row: (row["run_date"], int(row["attempt"])))

    def latest(self, *, mode: str | None = None) -> dict[str, Any] | None:
        rows = self.all(mode=mode)
        return rows[-1] if rows else None

    def prune(self, *, today: str | None = None, retain_days: int = 90) -> int:
        if retain_days < 1:
            raise ValueError("retention must be positive")
        cutoff = date.fromisoformat(today or date.today().isoformat()) - timedelta(days=retain_days - 1)
        deleted = 0
        if not self.directory.exists():
            return deleted
        for path in self.directory.glob("*-r*.json"):
            try:
                run_day = date.fromisoformat(path.name[:10])
            except ValueError:
                continue
            if run_day < cutoff:
                path.unlink()
                deleted += 1
        return deleted

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("daily pipeline run manifest is corrupt") from exc
        if not isinstance(row, dict):
            raise ValueError("daily pipeline run manifest must be an object")
        validate_record("daily_pipeline_run", row)
        return row


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
