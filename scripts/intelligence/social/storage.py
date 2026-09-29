from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import re
from typing import Any, Mapping

from ..models import now_utc


class SocialRuntime:
    def __init__(self, runtime_dir: Path | str):
        self.root = Path(runtime_dir) / "social"

    def load(self, source_id: str, platform: str) -> dict[str, Any]:
        path = self.root / f"{source_id}.json"
        if not path.exists():
            return {
                "source_id": source_id, "platform": platform,
                "last_success_at": None, "last_seen_object_ids": [],
                "consecutive_failures": 0, "last_status": "never_synced",
            }
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(value, dict) or value.get("source_id") != source_id
                    or value.get("platform") != platform
                    or not isinstance(value.get("last_seen_object_ids"), list)):
                raise ValueError
            # Runtime checkpoints intentionally have a closed, credential-free shape.
            allowed = {"source_id", "platform", "last_success_at", "last_seen_object_ids",
                       "consecutive_failures", "last_status", "last_attempt_at", "last_run"}
            if set(value) - allowed:
                raise ValueError
            return value
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("social checkpoint is corrupt") from exc

    def save(self, value: Mapping[str, Any]) -> None:
        source_id = str(value.get("source_id") or "")
        platform = str(value.get("platform") or "")
        ids = value.get("last_seen_object_ids")
        if (not re.fullmatch(r"src-[0-9a-f]{24}", source_id)
                or platform not in {"xiaohongshu", "zhihu"}
                or not isinstance(ids, list) or len(ids) > 500
                or any(not isinstance(item, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", item) for item in ids)):
            raise ValueError("invalid social checkpoint")
        allowed_statuses = {"never_synced", "ready", "content_readable", "login_required",
                            "challenge_required", "relay_unavailable", "dom_changed", "not_found",
                            "partial", "completed", "rss_proposal_pending_approval", "unavailable"}
        if value.get("last_status", "never_synced") not in allowed_statuses:
            raise ValueError("invalid social checkpoint status")
        last_run = value.get("last_run")
        if last_run is not None:
            metric_keys = {"fetched", "new_observations", "duplicate_observations", "artifacts_touched",
                           "pages", "login_required", "challenge_required", "dom_changed"}
            if (not isinstance(last_run, dict) or set(last_run) - metric_keys
                    or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in last_run.values())):
                raise ValueError("invalid social checkpoint metrics")
        safe = {key: value[key] for key in (
            "source_id", "platform", "last_success_at", "last_seen_object_ids",
            "consecutive_failures", "last_status", "last_attempt_at", "last_run",
        ) if key in value}
        # Reject URL/body/auth-like material before it reaches runtime storage.
        serialized = json.dumps(safe, ensure_ascii=False, sort_keys=True)
        if any(marker in serialized.casefold() for marker in ("cookie", "authorization", "xsec_token", "session_storage")):
            raise ValueError("social checkpoint contains disallowed private state")
        _atomic_write(self.root / f"{source_id}.json", serialized + "\n")


class SocialInbox:
    def __init__(self, private_root: Path | str):
        self.path = Path(private_root) / "social" / "inbox.jsonl"

    def list(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            rows = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if any(not isinstance(row, dict) or set(row) != {
                "url", "platform", "source_id", "added_at", "status"
            } or row.get("platform") not in {"xiaohongshu", "zhihu"}
                   or row.get("status") not in {"pending", "completed", "deferred"}
                   or "?" in str(row.get("url") or "")
                   or any(marker in str(row.get("url") or "").casefold()
                          for marker in ("token=", "xsec_token", "cookie", "authorization"))
                   for row in rows):
                raise ValueError
            return rows
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("social inbox is corrupt") from exc

    def add(self, url: str, platform: str, source_id: str | None = None) -> dict[str, Any]:
        rows = self.list()
        existing = next((row for row in rows if row["url"] == url and row["status"] == "pending"), None)
        if existing:
            return existing
        row = {"url": url, "platform": platform, "source_id": source_id,
               "added_at": now_utc(), "status": "pending"}
        rows.append(row)
        _atomic_write(self.path, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in rows))
        return row

    def update_status(self, url: str, status: str) -> None:
        rows = self.list()
        matched = False
        for row in rows:
            if row["url"] == url and row["status"] == "pending":
                row["status"] = status
                matched = True
                break
        if matched:
            _atomic_write(self.path, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in rows))


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=".social.", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
