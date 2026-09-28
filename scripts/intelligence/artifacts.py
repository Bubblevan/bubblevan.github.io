from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .aliases import ArtifactAliases
from .canonicalize import artifact_identity
from .models import new_artifact


def materialize_artifact_candidates(
    observation: Mapping[str, Any],
    store: Any,
) -> list[str]:
    """Resolve only explicit candidate identities and link them to an observation."""
    artifact_ids: list[str] = []
    observation_id = str(observation["observation_id"])
    observation_topics = [str(item) for item in observation.get("topics", [])]
    provenance = observation.get("provenance") if isinstance(observation.get("provenance"), Mapping) else {}
    metadata = observation.get("metadata") if isinstance(observation.get("metadata"), Mapping) else {}
    for candidate in observation.get("artifact_candidates", []):
        if not isinstance(candidate, Mapping):
            continue
        mention = candidate.get("mention") if isinstance(candidate.get("mention"), Mapping) else {}
        role = str(mention.get("role") or "referenced")
        if role == "incidental":
            continue
        if role not in {"primary", "referenced"}:
            role = "referenced"
        identity = artifact_identity(candidate)
        candidate_topics = [str(item) for item in candidate.get("topics", [])]
        if role == "primary":
            candidate_topics = sorted(set(observation_topics + candidate_topics))
        published_at = candidate.get("published_at")
        if role == "primary":
            published_at = published_at or observation.get("published_at")
        summary = str(candidate.get("summary") or "")
        if role == "primary":
            summary = summary[:4000]
        source_id = str(observation.get("source_id") or "")
        connector = str(metadata.get("connector") or provenance.get("collector") or "unknown")
        field_source = {
            "source": str(observation.get("platform") or "unknown"),
            "observation_id": observation_id,
            "source_id": source_id,
            "connector": connector,
            "mention_role": role,
            "mention_origin": str(mention.get("origin") or "unknown"),
        }
        artifact = new_artifact(
            identity=identity,
            artifact_type=str(candidate.get("artifact_type") or "other"),
            title=str(candidate.get("title") or ""),
            canonical_url=str(candidate.get("canonical_url") or ""),
            identifiers=dict(candidate.get("identifiers") or {}),
            authors=([str(item) for item in candidate.get("authors", [])]
                     or ([str(item) for item in observation.get("authors", [])] if role == "primary" else [])),
            organizations=[str(item) for item in candidate.get("organizations", [])],
            published_at=str(published_at) if published_at else None,
            summary=summary,
            topics=candidate_topics,
            observation_ids=[observation_id],
            status="candidate",
            field_provenance={
                "title": field_source,
                "summary": field_source,
                "authors": field_source,
                "published_at": field_source,
                "topics": {**field_source, "topic_provenance": "source_catalog_and_observation"},
                "mention": field_source,
                "identifiers": {
                    key: _provenance(observation)
                    for key, value in dict(candidate.get("identifiers") or {}).items()
                    if value not in (None, "", {})
                },
            },
        )
        stored = upsert_artifact_record(
            artifact, store, resolver="explicit-identifier", resolver_id=observation_id,
            resolved_at=str(observation.get("observed_at") or "") or None,
        )
        artifact_ids.append(str(stored["artifact_id"]))
    return sorted(set(artifact_ids))


def upsert_artifact_record(
    artifact: dict[str, Any],
    store: Any,
    *,
    resolver: str = "explicit-identifier",
    resolver_id: str = "manual",
    resolved_at: str | None = None,
) -> dict[str, Any]:
    aliases = ArtifactAliases(store.directory)
    alias_keys = _exact_alias_keys(artifact)
    linked_ids = sorted({resolved for key in alias_keys if (resolved := aliases.resolve_alias(key)) is not None})
    if len(linked_ids) > 1:
        raise ValueError(f"candidate exact identifiers resolve to conflicting artifacts: {linked_ids}")
    if linked_ids:
        canonical_id = linked_ids[0]
        if str(artifact["artifact_id"]) != canonical_id:
            aliases.add_redirect(str(artifact["artifact_id"]), canonical_id,
                                 reason="exact_identifier_alias", created_at=resolved_at)
            artifact["artifact_id"] = canonical_id
    for key in alias_keys:
        aliases.register_alias(key, str(artifact["artifact_id"]), resolver=resolver,
                               resolver_id=resolver_id, resolved_at=resolved_at)
    return store.upsert_artifact(artifact)


def _provenance(observation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source": str(observation.get("platform") or "unknown"),
        "observation_id": str(observation.get("observation_id") or "") or None,
    }


def _exact_alias_keys(candidate: Mapping[str, Any]) -> list[str]:
    identifiers = candidate.get("identifiers") if isinstance(candidate.get("identifiers"), Mapping) else {}
    values: list[str] = []
    if identifiers.get("doi"):
        values.append(f"doi:{identifiers['doi']}")
    if identifiers.get("arxiv"):
        values.append(f"arxiv:{identifiers['arxiv']}")
    if identifiers.get("github"):
        values.append(f"github:{identifiers['github']}")
    if identifiers.get("huggingface"):
        value = identifiers["huggingface"]
        if isinstance(value, Mapping):
            values.append(f"huggingface:{value.get('repo_type')}:{value.get('repo_id')}")
        else:
            artifact_type = str(candidate.get("artifact_type") or "model")
            values.append(f"huggingface:{artifact_type}:{value}")
    canonical_url = str(candidate.get("canonical_url") or "")
    if canonical_url:
        values.append(f"url:{canonical_url}")
    return sorted(set(values))
