from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from ..models import now_utc
from ..retrieval.corpus import build_snapshot
from ..store import JsonlStore
from .feedback_projection import project_feedback
from .generation import build_feed
from .models import new_feedback, update_profile
from .storage import FeedRepository
from ..ops.locks import feed_writer_lock


FEEDBACK_ACTIONS = {
    "impression", "open", "useful", "not_relevant", "save", "unsave", "hide", "unhide",
    "deep_read", "show_less_from_source", "restore_source", "show_less_of_topic", "restore_topic", "retract",
}


def apply_feedback(repository: FeedRepository, legacy_store: JsonlStore, *, feed_run_id: str,
                   artifact_id: str, action: str, target_id: str | None = None,
                   reason_code: str | None = None, supersedes_feedback_id: str | None = None) -> dict[str, Any]:
    with feed_writer_lock(repository.root, timeout_seconds=5.0):
        return _apply_feedback_unlocked(repository, legacy_store, feed_run_id=feed_run_id,
                                        artifact_id=artifact_id, action=action, target_id=target_id,
                                        reason_code=reason_code,
                                        supersedes_feedback_id=supersedes_feedback_id)


def _apply_feedback_unlocked(repository: FeedRepository, legacy_store: JsonlStore, *, feed_run_id: str,
                             artifact_id: str, action: str, target_id: str | None = None,
                             reason_code: str | None = None,
                             supersedes_feedback_id: str | None = None) -> dict[str, Any]:
    if action not in FEEDBACK_ACTIONS:
        raise ValueError(f"unsupported feed feedback action: {action}")
    run = repository.get_run(feed_run_id)
    if run is None:
        raise ValueError(f"unknown feed_run_id: {feed_run_id}")
    item = next((row for row in run["items"] if row.get("artifact_id") == artifact_id), None)
    if item is None:
        raise ValueError("artifact_id is not part of the specified FeedRun")
    target = None
    if action in {"show_less_from_source", "restore_source"}:
        selected = target_id or next(iter(item.get("source_ids", [])), None)
        if not selected or selected not in item.get("source_ids", []):
            raise ValueError("source feedback target must be a source linked to this feed item")
        target = {"type": "source", "id": selected}
    elif action in {"show_less_of_topic", "restore_topic"}:
        selected = target_id or next(iter(item.get("topics", [])), None)
        if not selected or selected not in item.get("topics", []):
            raise ValueError("topic feedback target must be a topic linked to this feed item")
        target = {"type": "topic", "id": selected}
    elif target_id is not None:
        raise ValueError(f"action {action} does not accept target_id")
    if action == "retract":
        if not supersedes_feedback_id:
            raise ValueError("retract requires supersedes_feedback_id")
        prior = next((row for row in repository.all_feedback(legacy_store)
                      if row.get("feedback_id") == supersedes_feedback_id), None)
        if prior is None:
            raise ValueError("cannot retract an unknown feedback event")
        prior_action = str(prior.get("action") or prior.get("event") or "")
        if prior_action == "retract":
            raise ValueError("retracting a retract is not supported")
        if str(prior.get("artifact_id") or "") != artifact_id:
            raise ValueError("retract can only supersede feedback for the same Artifact")
    elif supersedes_feedback_id:
        raise ValueError("supersedes_feedback_id is only valid for retract")
    events = repository.all_feedback(legacy_store)
    if action == "impression" and any(
        (row.get("action") or row.get("event")) == "impression"
        and row.get("artifact_id") == artifact_id
        and (row.get("context") or {}).get("feed_run_id") == feed_run_id
        for row in events
    ):
        return {"status": "already_recorded", "action": action, "feed_run_id": feed_run_id, "artifact_id": artifact_id}
    identity = f"impression|{feed_run_id}|{artifact_id}" if action == "impression" else None
    event = new_feedback(artifact_id=artifact_id, action=action, feed_run_id=feed_run_id,
                         rank=int(item.get("rank") or 1), target=target, reason_code=reason_code,
                         supersedes_feedback_id=supersedes_feedback_id, identity=identity)
    appended = repository.append_feedback(event)
    return {"status": "recorded" if appended else "already_recorded", "feedback_id": event["feedback_id"],
            "action": action, "feed_run_id": feed_run_id, "artifact_id": artifact_id}


def mutate_profile(repository: FeedRepository, *, add: Mapping[str, list[str]] | None = None,
                   remove: Mapping[str, list[str]] | None = None) -> dict[str, Any]:
    with feed_writer_lock(repository.root, timeout_seconds=5.0):
        profile = repository.load_profile()
        updated = update_profile(profile, add=add, remove=remove, updated_at=now_utc())
        if updated != profile:
            repository.save_profile(updated)
        return updated


def daily_feed(store_dir: Path | str, runtime_dir: Path | str, private_dir: Path | str, *, date: str,
               refresh: bool = False, lookback_days: int = 7, model: str = "Qwen/Qwen3-Embedding-0.6B",
               revision: str | None = None, device: str | None = None,
               experimental_graph: bool = False, dense_resource_factory: Any = None,
               snapshot: Any = None, dense_enabled: bool = True,
               lock_timeout_seconds: float = 5.0) -> dict[str, Any]:
    repository = FeedRepository(private_dir)
    with feed_writer_lock(private_dir, timeout_seconds=lock_timeout_seconds):
        return build_feed(store_dir, runtime_dir, repository, feed_date=date, refresh=refresh,
                          lookback_days=lookback_days, model=model, revision=revision, device=device,
                          experimental_graph=experimental_graph, dense_resource_factory=dense_resource_factory,
                          snapshot=snapshot, dense_enabled=dense_enabled)


def feedback_stats(store: JsonlStore, repository: FeedRepository) -> dict[str, Any]:
    runs = repository.runs()
    events = repository.all_feedback()
    retracted = {str(row.get("supersedes_feedback_id")) for row in events
                 if (row.get("action") or row.get("event")) == "retract" and row.get("supersedes_feedback_id")}
    active = [row for row in events if str(row.get("feedback_id") or "") not in retracted
              and (row.get("action") or row.get("event")) != "retract"]
    counts = Counter(str(row.get("action") or row.get("event") or "unknown") for row in active)
    total_impressions = counts["impression"]
    useful = counts["useful"]
    negative = counts["not_relevant"]
    hides = counts["hide"]
    snapshot = build_snapshot(store)
    docs = snapshot.by_id()
    by_slice: dict[str, dict[str, Counter[str]]] = {
        "source": defaultdict(Counter), "topic": defaultdict(Counter), "artifact_type": defaultdict(Counter),
    }
    for row in active:
        action = str(row.get("action") or row.get("event") or "unknown")
        doc = docs.get(str(row.get("artifact_id") or ""))
        if doc is None:
            continue
        for source in doc.source_ids:
            by_slice["source"][source][action] += 1
        for topic in doc.topics:
            by_slice["topic"][topic][action] += 1
        by_slice["artifact_type"][doc.artifact_type][action] += 1
    return {
        "environment": repository.root.name.removeprefix("feed-") or "custom",
        "feed_runs": len(runs), "feedback_events": len(active),
        "impressions": total_impressions, "useful": useful, "not_relevant": negative,
        "save": counts["save"], "hide": hides, "deep_read": counts["deep_read"],
        "useful_rate": round(useful / total_impressions, 4) if total_impressions else None,
        "negative_rate": round(negative / total_impressions, 4) if total_impressions else None,
        "hide_rate": round(hides / total_impressions, 4) if total_impressions else None,
        "actions": dict(sorted(counts.items())),
        "by_source": _counter_payload(by_slice["source"]),
        "by_topic": _counter_payload(by_slice["topic"]),
        "by_artifact_type": _counter_payload(by_slice["artifact_type"]),
    }


def _counter_payload(values: Mapping[str, Counter[str]]) -> list[dict[str, Any]]:
    return [{"key": key, "actions": dict(sorted(counter.items()))}
            for key, counter in sorted(values.items())]
