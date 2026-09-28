from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

from .models import stable_hash


def project_feedback(events: Iterable[Mapping[str, Any]], *, max_useful: int = 20) -> dict[str, Any]:
    rows = sorted((dict(row) for row in events), key=lambda row: (str(row.get("occurred_at") or ""), str(row.get("feedback_id") or "")))
    retracted = {str(row.get("supersedes_feedback_id")) for row in rows
                 if _action(row) == "retract" and row.get("supersedes_feedback_id")}
    active = [row for row in rows if str(row.get("feedback_id") or "") not in retracted and _action(row) != "retract"]
    saved: set[str] = set()
    hidden: set[str] = set()
    useful: dict[str, tuple[str, str]] = {}
    not_relevant: set[str] = set()
    blocked_sources: set[str] = set()
    blocked_topics: set[str] = set()
    impressions: Counter[str] = Counter()
    impression_keys: set[tuple[str, str]] = set()
    by_action: Counter[str] = Counter()
    for row in active:
        action = _action(row)
        artifact = str(row.get("artifact_id") or "")
        target = row.get("target") if isinstance(row.get("target"), Mapping) else {}
        target_type, target_id = str(target.get("type") or ""), str(target.get("id") or "")
        by_action[action] += 1
        if action == "save": saved.add(artifact)
        elif action == "unsave": saved.discard(artifact)
        elif action == "hide": hidden.add(artifact)
        elif action == "unhide": hidden.discard(artifact)
        elif action == "useful": useful[artifact] = (str(row.get("occurred_at") or ""), str(row.get("feedback_id") or ""))
        elif action == "not_relevant": not_relevant.add(artifact)
        elif action == "show_less_from_source" and target_type == "source": blocked_sources.add(target_id)
        elif action == "restore_source" and target_type == "source": blocked_sources.discard(target_id)
        elif action == "show_less_of_topic" and target_type == "topic": blocked_topics.add(target_id)
        elif action == "restore_topic" and target_type == "topic": blocked_topics.discard(target_id)
        if action == "impression":
            run_id = str((row.get("context") or {}).get("feed_run_id") or "")
            key = (run_id, artifact)
            if key not in impression_keys:
                impression_keys.add(key)
                impressions[artifact] += 1
    ordered_useful = sorted(useful, key=lambda item: (useful[item][0], item), reverse=True)[:max_useful]
    payload = {
        "hidden_artifact_ids": sorted(hidden), "saved_artifact_ids": sorted(saved),
        "useful_artifact_ids": ordered_useful, "blocked_source_ids": sorted(blocked_sources),
        "blocked_topic_ids": sorted(blocked_topics), "impression_counts": dict(sorted(impressions.items())),
        "not_relevant_artifact_ids": sorted(not_relevant),
        "actions": dict(sorted(by_action.items())),
        "active_event_count": len(active),
    }
    payload["projection_hash"] = stable_hash(payload)
    return payload


def _action(row: Mapping[str, Any]) -> str:
    return str(row.get("action") or row.get("event") or "")
