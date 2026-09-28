from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

from ..ids import stable_id
from ..schema_validator import validate_record
from ..entity_aliases import EntityAliases


SCHEMA = "bubblevan/intelligence-source-candidate/v1"


class SourceCandidateStore:
    """Single-writer, replay-safe JSONL materialization of reviewed candidates."""

    def __init__(self, directory: Path | str):
        self.directory = Path(directory)
        self.path = self.directory / "source_candidates.jsonl"

    def iter_candidates(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        result = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        raise ValueError
                    validate_record("source_candidate", item)
                    expected = candidate_id(str(item["entity_id"]))
                    if item["candidate_id"] != expected:
                        raise ValueError("candidate id does not match canonical entity id")
                    result.append(item)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
            raise ValueError("corrupt source candidate store") from exc
        ids = [item["candidate_id"] for item in result]
        if len(ids) != len(set(ids)):
            raise ValueError("source candidate store has duplicate candidate ids")
        return sorted(result, key=lambda item: item["candidate_id"])

    def upsert(
        self,
        candidate: Mapping[str, Any],
        *,
        preserve_review: bool = True,
        entity_aliases: EntityAliases | None = None,
    ) -> dict[str, Any]:
        incoming = dict(candidate)
        validate_record("source_candidate", incoming)
        if incoming["candidate_id"] != candidate_id(str(incoming["entity_id"])):
            raise ValueError("candidate id does not match canonical entity id")
        rows = {item["candidate_id"]: item for item in self.iter_candidates()}
        matching_ids = [incoming["candidate_id"]]
        if entity_aliases is not None:
            matching_ids.extend(
                candidate_id(str(item["entity_id"]))
                for item in rows.values()
                if entity_aliases.resolve_entity_id(str(item["entity_id"])) == incoming["entity_id"]
            )
        matching_ids = sorted(set(matching_ids))
        old_rows = [rows[key] for key in matching_ids if key in rows]
        old = next((item for item in old_rows if item["candidate_id"] == incoming["candidate_id"]), None)
        if old is None and old_rows:
            old = old_rows[0]
        if old:
            merged = dict(incoming)
            merged["first_discovered_at"] = min(
                *[str(item["first_discovered_at"]) for item in old_rows],
                str(incoming["first_discovered_at"]), key=_time_key,
            )
            merged["last_supported_at"] = max(
                *[str(item["last_supported_at"]) for item in old_rows],
                str(incoming["last_supported_at"]), key=_time_key,
            )
            paths = {
                _fingerprint(path): path
                for item in old_rows for path in item["evidence_paths"]
            }
            paths.update({_fingerprint(path): path for path in incoming["evidence_paths"]})
            merged["evidence_paths"] = [paths[key] for key in sorted(paths)]
            reviewed = [item for item in old_rows if item["status"] in {"rejected", "approved", "deferred"}]
            reviewed.sort(key=lambda item: (item["status"] != "rejected", item["candidate_id"]))
            if preserve_review and reviewed:
                selected = reviewed[0]
                merged["status"] = selected["status"]
                merged["reviewed_at"] = selected.get("reviewed_at")
                merged["reason_code"] = selected.get("reason_code")
        else:
            merged = incoming
        validate_record("source_candidate", merged)
        for key in matching_ids:
            rows.pop(key, None)
        rows[merged["candidate_id"]] = merged
        self._atomic_write([rows[key] for key in sorted(rows)])
        return merged

    def review(
        self,
        candidate_id_value: str,
        status: str,
        *,
        reviewed_at: str,
        reason_code: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"approved", "rejected", "deferred", "pending"}:
            raise ValueError("unsupported source candidate status")
        if status == "rejected" and reason_code not in {
            "irrelevant", "low_signal", "duplicate", "too_broad", "not_a_source", "already_known", "other",
        }:
            raise ValueError("rejected candidate requires a supported reason code")
        rows = {item["candidate_id"]: item for item in self.iter_candidates()}
        candidate = rows.get(candidate_id_value)
        if candidate is None:
            raise ValueError("source candidate not found")
        candidate["status"] = status
        candidate["reviewed_at"] = _timestamp(reviewed_at)
        candidate["reason_code"] = reason_code if status == "rejected" else None
        return self.upsert(candidate, preserve_review=False)

    def _atomic_write(self, items: Iterable[Mapping[str, Any]]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for item in items).encode("utf-8")
        temp_name = ""
        try:
            with tempfile.NamedTemporaryFile("wb", dir=self.directory, prefix=f".{self.path.name}.", suffix=".tmp", delete=False) as handle:
                temp_name = handle.name
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)


def candidate_id(entity_id: str) -> str:
    return stable_id("sc", "source-candidate", entity_id)


def make_candidate(
    *,
    entity: Mapping[str, Any],
    paths: list[dict[str, Any]],
    topics: list[str],
    signals: dict[str, Any],
    first_discovered_at: str,
    last_supported_at: str,
) -> dict[str, Any]:
    kind = str(entity.get("entity_type") or "")
    candidate_type = {"person": "person", "institution": "institution", "lab": "institution",
                      "organization": "organization", "repository": "repository"}.get(kind)
    if not candidate_type:
        raise ValueError("entity is not eligible for a source candidate")
    urls = [str(value) for value in entity.get("urls", []) if str(value).startswith(("https://", "http://"))]
    result = {
        "schema": SCHEMA,
        "candidate_id": candidate_id(str(entity["entity_id"])),
        "entity_id": str(entity["entity_id"]),
        "candidate_type": candidate_type,
        "platform": _platform(entity),
        "name": str(entity.get("name") or "Unknown entity"),
        "canonical_url": sorted(urls)[0] if urls else "",
        "external_ids": dict(entity.get("external_ids") or {}),
        "topics": sorted(set(topics)),
        "status": "pending",
        "first_discovered_at": _timestamp(first_discovered_at),
        "last_supported_at": _timestamp(last_supported_at),
        "reviewed_at": None,
        "reason_code": None,
        "signals": signals,
        "evidence_paths": paths,
    }
    validate_record("source_candidate", result)
    return result


def _platform(entity: Mapping[str, Any]) -> str:
    ids = entity.get("external_ids") if isinstance(entity.get("external_ids"), Mapping) else {}
    for key in sorted(ids):
        if key.startswith("github_"):
            return "github"
        if key.startswith("openalex_") or key == "orcid":
            return "openalex"
        if key.startswith("semantic_scholar_"):
            return "semantic-scholar"
        if key.startswith("ror"):
            return "openalex"
    return "unknown"


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _time_key(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
