from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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
    for candidate in observation.get("artifact_candidates", []):
        if not isinstance(candidate, Mapping):
            continue
        identity = artifact_identity(candidate)
        artifact = new_artifact(
            identity=identity,
            artifact_type=str(candidate.get("artifact_type") or "other"),
            title=str(candidate.get("title") or ""),
            canonical_url=str(candidate.get("canonical_url") or ""),
            identifiers=dict(candidate.get("identifiers") or {}),
            authors=[str(item) for item in candidate.get("authors", [])],
            organizations=[str(item) for item in candidate.get("organizations", [])],
            summary=str(candidate.get("summary") or ""),
            topics=sorted(set(observation_topics + [str(item) for item in candidate.get("topics", [])])),
            observation_ids=[observation_id],
            status="candidate",
        )
        stored = store.upsert_artifact(artifact)
        artifact_ids.append(str(stored["artifact_id"]))
    return sorted(set(artifact_ids))
