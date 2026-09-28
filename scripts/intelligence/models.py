from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SCHEMA_PREFIX = "bubblevan/intelligence"

SOURCE_TYPES = {
    "curator", "author", "lab", "publication", "feed", "community", "platform", "repository"
}
ARTIFACT_TYPES = {
    "paper", "blog", "repository", "model", "dataset", "technical_report",
    "discussion", "social_post", "course", "tool", "space", "other",
}
FEEDBACK_EVENTS = {
    "impression", "open", "save", "dismiss", "deep_read", "verify", "cite",
    "implement", "promote_to_hugo",
}

Record = dict[str, Any]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_datetime(value: object, *, default_now: bool = False) -> str | None:
    text = str(value or "").strip()
    if not text:
        return now_utc() if default_now else None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid ISO-8601 datetime: {text}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    normalized = parsed.astimezone(timezone.utc)
    timespec = "microseconds" if normalized.microsecond else "seconds"
    return normalized.isoformat(timespec=timespec).replace("+00:00", "Z")


def new_source(
    *,
    identity: str,
    source_type: str,
    platform: str,
    name: str,
    canonical_url: str = "",
    external_ids: dict[str, Any] | None = None,
    topics: list[str] | None = None,
    connector: str,
    mode: str,
    artifact_policy: dict[str, Any] | None = None,
    status: str = "active",
    created_at: str | None = None,
) -> Record:
    from .ids import source_id

    created = parse_datetime(created_at, default_now=True)
    acquisition = {"connector": connector, "mode": mode}
    if artifact_policy:
        acquisition["artifact_policy"] = dict(artifact_policy)
    return {
        "schema": f"{SCHEMA_PREFIX}-source/v1",
        "source_id": source_id(identity),
        "source_type": source_type,
        "platform": platform,
        "name": name.strip(),
        "canonical_url": canonical_url,
        "external_ids": external_ids or {},
        "topics": sorted(set(topics or [])),
        "acquisition": acquisition,
        "status": status,
        "created_at": created,
        "updated_at": created,
    }


def new_observation(
    *,
    identity: str,
    source_id: str,
    platform: str,
    platform_object_id: str,
    kind: str,
    title: str,
    text: str,
    urls: list[str],
    media: list[Record],
    published_at: str | None,
    observed_at: str | None,
    topics: list[str],
    provenance: Record,
    artifact_candidates: list[Record],
    native_tags: list[str] | None = None,
    authors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Record:
    from .ids import observation_id

    return {
        "schema": f"{SCHEMA_PREFIX}-observation/v1",
        "observation_id": observation_id(identity),
        "source_id": source_id,
        "platform": platform,
        "platform_object_id": platform_object_id,
        "kind": kind,
        "title": title,
        "text": text,
        "urls": sorted(set(urls)),
        "media": media,
        "published_at": parse_datetime(published_at),
        "observed_at": parse_datetime(observed_at, default_now=True),
        "topics": sorted(set(topics)),
        "native_tags": sorted(set(native_tags or [])),
        "authors": sorted(set(authors or [])),
        "metadata": metadata or {},
        "provenance": provenance,
        "artifact_candidates": artifact_candidates,
    }


def new_artifact(
    *,
    identity: str,
    artifact_type: str,
    title: str = "",
    canonical_url: str = "",
    identifiers: dict[str, Any] | None = None,
    authors: list[str] | None = None,
    organizations: list[str] | None = None,
    published_at: str | None = None,
    summary: str = "",
    topics: list[str] | None = None,
    observation_ids: list[str] | None = None,
    entity_ids: list[str] | None = None,
    status: str = "candidate",
    field_provenance: dict[str, Any] | None = None,
    field_conflicts: list[Record] | None = None,
) -> Record:
    from .ids import artifact_id

    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"unsupported artifact_type: {artifact_type}")
    return {
        "schema": f"{SCHEMA_PREFIX}-artifact/v1",
        "artifact_id": artifact_id(identity),
        "artifact_type": artifact_type,
        "title": title.strip(),
        "canonical_url": canonical_url,
        "identifiers": identifiers or {"doi": None, "arxiv": None, "github": None, "huggingface": None},
        "authors": sorted(set(authors or [])),
        "organizations": sorted(set(organizations or [])),
        "published_at": parse_datetime(published_at),
        "summary": summary.strip(),
        "topics": sorted(set(topics or [])),
        "observation_ids": sorted(set(observation_ids or [])),
        "entity_ids": sorted(set(entity_ids or [])),
        "status": status,
        "field_provenance": field_provenance or {},
        "field_conflicts": field_conflicts or [],
    }


def new_feedback(
    *,
    artifact_id: str,
    event: str,
    occurred_at: str,
    surface: str = "manual",
    rank: int | None = None,
    query: str | None = None,
) -> Record:
    from .ids import feedback_id

    if event not in FEEDBACK_EVENTS:
        raise ValueError(f"unsupported feedback event: {event}")
    timestamp = parse_datetime(occurred_at)
    if not timestamp:
        raise ValueError("feedback occurred_at is required")
    identity = "|".join([artifact_id, event, timestamp, surface, str(rank), query or ""])
    return {
        "schema": f"{SCHEMA_PREFIX}-feedback/v1",
        "feedback_id": feedback_id(identity),
        "artifact_id": artifact_id,
        "event": event,
        "occurred_at": timestamp,
        "context": {"surface": surface, "rank": rank, "query": query},
    }


def new_entity(
    *,
    identity: str,
    entity_type: str,
    name: str,
    aliases: list[str] | None = None,
    urls: list[str] | None = None,
    external_ids: dict[str, Any] | None = None,
    topics: list[str] | None = None,
    relations: list[Record] | None = None,
    resolution_state: str = "resolved",
) -> Record:
    from .ids import entity_id

    return {
        "schema": f"{SCHEMA_PREFIX}-entity/v1",
        "entity_id": entity_id(identity),
        "entity_type": entity_type,
        "name": name.strip(),
        "aliases": sorted(set(aliases or [])),
        "urls": sorted(set(urls or [])),
        "external_ids": external_ids or {},
        "topics": sorted(set(topics or [])),
        "resolution_state": resolution_state,
        "relations": sorted(relations or [], key=lambda item: (item["predicate"], item["target_id"])),
    }
