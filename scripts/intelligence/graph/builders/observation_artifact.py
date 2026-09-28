from __future__ import annotations

from collections.abc import Mapping

from ...aliases import ArtifactAliases
from ...canonicalize import artifact_identity
from ...entity_aliases import EntityAliases
from ...graph.models import make_edge
from ...ids import artifact_id
from ...store import JsonlStore
from ..store import GraphStore
from ...repositories.artifacts import ArtifactRepository


def build_observation_artifact_edges(
    store: JsonlStore,
    graph: GraphStore,
    artifact_aliases: ArtifactAliases,
    entity_aliases: EntityAliases,
    *,
    now: str | None = None,
) -> dict[str, int]:
    sources = {item["source_id"]: item for item in store.iter_records("source")}
    artifact_repository = ArtifactRepository(store)
    artifacts = {item["artifact_id"]: item for item in artifact_repository.iter_canonical()}
    observations = list(store.iter_records("observation"))
    edges_added = 0
    skipped_unlinked = 0
    prior_ids = {item["edge_id"] for item in graph.iter_edges()}
    edges = []
    for observation in observations:
        source_id = str(observation["source_id"])
        if source_id not in sources:
            raise ValueError("observation refers to a missing source")
        for candidate in observation.get("artifact_candidates", []):
            if not isinstance(candidate, Mapping):
                continue
            mention = candidate.get("mention") if isinstance(candidate.get("mention"), Mapping) else {}
            role = str(mention.get("role") or "referenced")
            if role == "incidental":
                continue
            if not _is_explicit_link(candidate):
                skipped_unlinked += 1
                continue
            candidate_artifact_id = artifact_id(artifact_identity(candidate))
            canonical_id = artifact_repository.resolve_id(candidate_artifact_id)
            if canonical_id not in artifacts:
                alias_id = _resolve_candidate_alias(candidate, artifact_aliases)
                canonical_id = alias_id or canonical_id
            if canonical_id not in artifacts:
                raise ValueError("explicit observation link does not resolve to a materialized artifact")
            materialized_mention = ((artifacts[canonical_id].get("field_provenance") or {}).get("mention") or {})
            if (materialized_mention.get("mention_role") == "primary"
                    and materialized_mention.get("observation_id") == str(observation["observation_id"])):
                role = "primary"
            predicate = "recommends" if observation.get("kind") == "recommendation" else "mentions"
            provider_repository = (
                mention.get("evidence_level") == "api_metadata"
                and str(mention.get("origin") or "").casefold() == "repository"
                and bool((candidate.get("identifiers") or {}).get("github"))
            )
            evidence = {
                "evidence_type": "exact_provider_metadata" if provider_repository else "explicit_source_link",
                "source_id": source_id,
                "observation_id": str(observation["observation_id"]),
                "confidence": float(mention.get("confidence", 1.0)),
                "observed_at": str(observation.get("observed_at") or now or ""),
            }
            if provider_repository:
                evidence.update({
                    "provider": "github",
                    "provider_record_id": str((candidate.get("identifiers") or {}).get("github") or ""),
                })
            edge = make_edge(
                source_id, predicate, canonical_id,
                evidence,
                observed_at=str(observation.get("observed_at") or now or ""),
            )
            edges.append(edge)
        primary_ids = []
        referenced_ids = []
        for artifact in artifacts.values():
            mention = ((artifact.get("field_provenance") or {}).get("mention") or {})
            if mention.get("mention_role") == "primary" and mention.get("observation_id") == str(observation["observation_id"]):
                primary_ids.append(str(artifact["artifact_id"]))
        for candidate in observation.get("artifact_candidates", []):
            if not isinstance(candidate, Mapping):
                continue
            mention = candidate.get("mention") if isinstance(candidate.get("mention"), Mapping) else {}
            role = str(mention.get("role") or "referenced")
            if role == "incidental":
                continue
            identity = artifact_identity(candidate)
            candidate_id = artifact_id(identity)
            canonical_id = artifact_aliases.resolve_artifact_id(candidate_id)
            if canonical_id not in artifacts:
                canonical_id = _resolve_candidate_alias(candidate, artifact_aliases) or canonical_id
            if canonical_id not in artifacts:
                continue
            materialized_mention = ((artifacts[canonical_id].get("field_provenance") or {}).get("mention") or {})
            if (materialized_mention.get("mention_role") == "primary"
                    and materialized_mention.get("observation_id") == str(observation["observation_id"])):
                role = "primary"
            (primary_ids if role == "primary" else referenced_ids).append(canonical_id)
        for primary_id in sorted(set(primary_ids)):
            for referenced_id in sorted(set(referenced_ids) - set(primary_ids)):
                if primary_id == referenced_id:
                    continue
                evidence = {
                    "evidence_type": "explicit_source_link",
                    "source_id": source_id,
                    "observation_id": str(observation["observation_id"]),
                    "confidence": 1.0,
                    "observed_at": str(observation.get("observed_at") or now or ""),
                }
                edges.append(make_edge(primary_id, "references", referenced_id, evidence,
                                       observed_at=str(observation.get("observed_at") or now or "")))
    graph.add_edges(edges)
    edges_added = len({edge["edge_id"] for edge in edges} - prior_ids)
    return {
        "observations": len(observations),
        "edges_added": edges_added,
        "unlinked_candidates_skipped": skipped_unlinked,
    }


def _is_explicit_link(candidate: Mapping[str, object]) -> bool:
    mention = candidate.get("mention") if isinstance(candidate.get("mention"), Mapping) else {}
    if mention.get("evidence_level") == "rendered_link":
        return True
    origin = str(mention.get("origin") or "").casefold().replace("-", "_")
    if origin in {"link", "url", "explicit_link", "markdown_link", "source_link"}:
        return True
    identifiers = candidate.get("identifiers") if isinstance(candidate.get("identifiers"), Mapping) else {}
    return (
        mention.get("evidence_level") == "api_metadata"
        and origin == "repository"
        and bool(identifiers.get("github"))
    )


def _resolve_candidate_alias(candidate: Mapping[str, object], aliases: ArtifactAliases) -> str | None:
    identifiers = candidate.get("identifiers") if isinstance(candidate.get("identifiers"), Mapping) else {}
    values = []
    for key in ("doi", "arxiv", "github", "semantic_scholar", "openalex"):
        if identifiers.get(key):
            values.append(f"{key}:{identifiers[key]}")
    if candidate.get("canonical_url"):
        values.append(f"url:{candidate['canonical_url']}")
    for value in values:
        resolved = aliases.resolve_alias(value)
        if resolved:
            return resolved
    return None
