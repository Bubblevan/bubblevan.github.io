from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import math
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from ..aliases import ArtifactAliases
from ..canonicalize import artifact_identity
from ..connectors.state import ConnectorStateStore
from ..ids import artifact_id as make_artifact_id
from ..models import now_utc
from ..ops.storage import DailyRunStore
from ..repositories.artifacts import ArtifactRepository
from ..store import JsonlStore


def source_coverage(store: JsonlStore, runtime_dir: Path | str, sources: list[dict[str, Any]], *,
                    days: int = 7, today: str | None = None) -> dict[str, Any]:
    if isinstance(days, bool) or days < 1 or days > 365:
        raise ValueError("coverage days must be between 1 and 365")
    end_day = date.fromisoformat((today or now_utc())[:10])
    start_day = end_day - timedelta(days=days - 1)
    cutoff = datetime.combine(start_day, datetime.min.time(), timezone.utc)
    observations = [row for row in store.iter_records("observation")
                    if _datetime(row.get("observed_at")) and _datetime(row.get("observed_at")) >= cutoff]
    repo = ArtifactRepository(store)
    alias = ArtifactAliases(store.directory)
    artifacts = {str(row["artifact_id"]): row for row in repo.iter_canonical()}
    by_source: dict[str, dict[str, list[tuple[datetime, dict[str, Any]]]]] = {}
    for observation in observations:
        source_id = str(observation.get("source_id") or "")
        observed = _datetime(observation.get("observed_at"))
        if not source_id or observed is None:
            continue
        for candidate in observation.get("artifact_candidates", []):
            if not isinstance(candidate, Mapping):
                continue
            if str((candidate.get("mention") or {}).get("role") or "referenced") == "incidental":
                continue
            try:
                raw_id = make_artifact_id(artifact_identity(candidate))
            except ValueError:
                continue
            canonical_id = repo.resolve_id(raw_id)
            if canonical_id not in artifacts:
                canonical_id = _resolve_candidate(candidate, alias, repo, canonical_id)
            if canonical_id not in artifacts:
                continue
            by_source.setdefault(source_id, {}).setdefault(canonical_id, []).append((observed, observation))

    artifact_sources: dict[str, dict[str, datetime]] = {}
    for source_id, rows in by_source.items():
        for artifact_id, hits in rows.items():
            artifact_sources.setdefault(artifact_id, {})[source_id] = min(item[0] for item in hits)
    first_sources: dict[str, set[str]] = {}
    for artifact_id, source_dates in artifact_sources.items():
        first = min(source_dates.values())
        first_sources[artifact_id] = {source for source, seen_at in source_dates.items() if seen_at == first}

    run_cutoff = start_day.isoformat()
    run_rows = [row for row in DailyRunStore(runtime_dir).all() if row.get("run_date", "") >= run_cutoff]
    connector_states = ConnectorStateStore(runtime_dir)
    poll_counts: dict[str, list[int]] = {}
    for run in run_rows:
        summary = run.get("source_summary") if isinstance(run.get("source_summary"), Mapping) else {}
        for item in summary.get("results", []) if isinstance(summary.get("results"), list) else []:
            source_id = str(item.get("source_id") or "")
            if not source_id:
                continue
            counts = poll_counts.setdefault(source_id, [0, 0])
            counts[0] += 1
            if item.get("status") in {"succeeded", "succeeded_after_retry"}:
                counts[1] += 1

    source_rows = []
    for source in sorted(sources, key=lambda row: str(row.get("source_id") or "")):
        source_id = str(source["source_id"])
        artifact_ids = set(by_source.get(source_id, {}))
        unique_ids = {artifact_id for artifact_id in artifact_ids if first_sources.get(artifact_id) == {source_id}}
        first_seen_ids = {artifact_id for artifact_id in artifact_ids if source_id in first_sources.get(artifact_id, set())}
        duplicates = {artifact_id for artifact_id in artifact_ids
                      if len(artifact_sources.get(artifact_id, {})) > 1 and source_id not in first_sources.get(artifact_id, set())}
        observed_count = sum(len(hits) for hits in by_source.get(source_id, {}).values())
        primary_artifacts = [artifacts[item] for item in artifact_ids
                             if _is_primary_artifact(artifacts[item], by_source[source_id].get(item, []))]
        completeness = []
        lags = []
        topics = set()
        for artifact in primary_artifacts:
            fields = [bool(str(artifact.get("title") or "").strip()),
                      bool(artifact.get("authors")), bool(str(artifact.get("summary") or "").strip()),
                      bool(artifact.get("published_at"))]
            completeness.append(sum(fields) / len(fields))
            topics.update(str(value) for value in artifact.get("topics", []))
            source_dates = artifact_sources.get(str(artifact["artifact_id"]), {})
            first_observed = min(source_dates.values()) if source_dates else None
            published = _datetime(artifact.get("published_at"))
            if first_observed and published and first_observed >= published:
                lags.append((first_observed - published).total_seconds() / 3600)
        polls = poll_counts.get(source_id, [0, 0])
        checkpoint = connector_states.load(source_id)
        checkpoint_status = _checkpoint_health(checkpoint)
        source_rows.append({
            "source_id": source_id, "name": str(source.get("name") or source_id),
            "polls": polls[0], "successful_polls": polls[1],
            "observations": observed_count, "canonical_artifacts": len(artifact_ids),
            "new_canonical_artifacts": len(first_seen_ids), "unique_contribution": len(unique_ids),
            "duplicate_canonical_artifacts": len(duplicates),
            "duplicate_rate": round(len(duplicates) / max(1, len(artifact_ids)), 4),
            "median_discovery_lag_hours": _quantile(lags, 0.5),
            "p90_discovery_lag_hours": _quantile(lags, 0.9),
            "primary_metadata_completeness": round(median(completeness), 4) if completeness else None,
            "topic_coverage": sorted(topics),
            "checkpoint_last_attempt_at": checkpoint.last_attempt_at if checkpoint else None,
            "checkpoint_last_success_at": checkpoint.last_success_at if checkpoint else None,
            "health": (checkpoint_status if checkpoint and checkpoint.last_attempt_at
                       else _health(source_id, run_rows, polls)),
        })

    overlaps = []
    for index, left in enumerate(source_rows):
        left_id = left["source_id"]
        left_artifacts = set(by_source.get(left_id, {}))
        for right in source_rows[index + 1:]:
            right_id = right["source_id"]
            right_artifacts = set(by_source.get(right_id, {}))
            common = left_artifacts & right_artifacts
            if common:
                overlaps.append({"source_a": left_id, "source_b": right_id,
                                 "shared_canonical_artifacts": len(common),
                                 "jaccard": round(len(common) / len(left_artifacts | right_artifacts), 4)})
    return {"window_days": days, "from": start_day.isoformat(), "to": end_day.isoformat(),
            "sources": source_rows, "pairwise_overlap": overlaps,
            "definitions": {"unique_contribution": "only source in the earliest observed_at tie set",
                            "new_canonical_artifacts": "artifact first observed by this source, including exact-time ties",
                            "duplicate_rate": "overlapping artifact count divided by this source's distinct artifacts",
                            "polls": "attempts recorded by DailyRun within the window; latest direct run-source time is exposed as checkpoint_last_attempt_at"}}


def _resolve_candidate(candidate: Mapping[str, Any], aliases: ArtifactAliases,
                       repo: ArtifactRepository, fallback: str) -> str:
    identifiers = candidate.get("identifiers") if isinstance(candidate.get("identifiers"), Mapping) else {}
    alias_keys = []
    for key in ("doi", "arxiv", "openalex", "openreview", "hf_paper"):
        if identifiers.get(key):
            prefix = "hf-paper" if key == "hf_paper" else key
            alias_keys.append(f"{prefix}:{identifiers[key]}")
    if candidate.get("canonical_url"):
        alias_keys.append("url:" + str(candidate["canonical_url"]))
    for key in alias_keys:
        resolved = aliases.resolve_alias(key)
        if resolved:
            return repo.resolve_id(resolved)
    return fallback


def _is_primary_artifact(artifact: Mapping[str, Any], hits: list[tuple[datetime, dict[str, Any]]]) -> bool:
    mention = ((artifact.get("field_provenance") or {}).get("mention") or {})
    if mention.get("mention_role") == "primary":
        return True
    return any(any(str((candidate.get("mention") or {}).get("role")) == "primary"
                   for candidate in observation.get("artifact_candidates", []) if isinstance(candidate, Mapping))
               for _, observation in hits)


def _datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _quantile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower = math.floor(index); upper = math.ceil(index)
    value = ordered[lower] if lower == upper else ordered[lower] * (upper - index) + ordered[upper] * (index - lower)
    return round(value, 2)


def _health(source_id: str, runs: list[dict[str, Any]], polls: list[int]) -> str:
    if polls[0] and polls[1] == polls[0]:
        return "healthy"
    for run in reversed(runs):
        for item in (run.get("source_summary") or {}).get("results", []):
            if item.get("source_id") == source_id:
                return "healthy" if item.get("status") in {"succeeded", "succeeded_after_retry"} else "failing"
    return "unknown"


def _checkpoint_health(state: Any) -> str:
    if state is None:
        return "unknown"
    if state.backoff_until and _datetime(state.backoff_until) and _datetime(state.backoff_until) > _datetime(now_utc()):
        return "deferred"
    if state.last_error_class:
        return "failing"
    if state.last_success_at:
        return "healthy"
    return "unknown"
