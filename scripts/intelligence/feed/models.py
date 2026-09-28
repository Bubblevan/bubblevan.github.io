from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping
import uuid

from ..ids import feedback_id
from ..models import now_utc, parse_datetime
from ..schema_validator import validate_record


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def profile_hash(profile: Mapping[str, Any]) -> str:
    return stable_hash({key: value for key, value in profile.items() if key not in {"created_at", "updated_at"}})


def default_profile(*, created_at: str | None = None) -> dict[str, Any]:
    stamp = parse_datetime(created_at, default_now=True)
    profile = {
        "schema": "bubblevan/feed-profile/v1",
        "profile_id": "profile-default",
        "selected_topic_ids": [],
        "followed_source_ids": [],
        "blocked_topic_ids": [],
        "blocked_source_ids": [],
        "created_at": stamp,
        "updated_at": stamp,
        "version": 1,
    }
    validate_record("feed_profile", profile)
    return profile


def update_profile(profile: Mapping[str, Any], *, add: Mapping[str, list[str]] | None = None,
                   remove: Mapping[str, list[str]] | None = None, updated_at: str | None = None) -> dict[str, Any]:
    result = deepcopy(dict(profile))
    changed = False
    for field, values in (add or {}).items():
        if field not in {"selected_topic_ids", "followed_source_ids", "blocked_topic_ids", "blocked_source_ids"}:
            raise ValueError(f"unsupported feed profile field: {field}")
        current = set(map(str, result[field]))
        before = set(current)
        current.update(map(str, values))
        result[field] = sorted(current)
        changed |= current != before
    for field, values in (remove or {}).items():
        if field not in {"selected_topic_ids", "followed_source_ids", "blocked_topic_ids", "blocked_source_ids"}:
            raise ValueError(f"unsupported feed profile field: {field}")
        current = set(map(str, result[field]))
        before = set(current)
        current.difference_update(map(str, values))
        result[field] = sorted(current)
        changed |= current != before
    if changed:
        result["version"] = int(result["version"]) + 1
        result["updated_at"] = parse_datetime(updated_at, default_now=True)
    validate_record("feed_profile", result)
    return result


def new_feedback(*, artifact_id: str, action: str, feed_run_id: str, rank: int | None,
                 target: Mapping[str, str] | None = None, reason_code: str | None = None,
                 supersedes_feedback_id: str | None = None, occurred_at: str | None = None,
                 identity: str | None = None) -> dict[str, Any]:
    stamp = parse_datetime(occurred_at, default_now=True)
    event_identity = identity or f"{artifact_id}|{action}|{feed_run_id}|{stamp}|{uuid.uuid4().hex}"
    record = {
        "schema": "bubblevan/intelligence-feedback/v2",
        "feedback_id": feedback_id(event_identity),
        "artifact_id": artifact_id,
        "action": action,
        "occurred_at": stamp,
        "context": {"surface": "daily_feed", "feed_run_id": feed_run_id, "rank": rank},
        "target": dict(target) if target else None,
        "reason_code": reason_code,
        "supersedes_feedback_id": supersedes_feedback_id,
    }
    validate_record("feedback", record)
    return record


def utc_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
