from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...entity_aliases import EntityAliases
from ...graph.models import make_edge
from ...store import JsonlStore
from ..store import GraphStore
from .scholarly import materialize_exact_entity, _provider_evidence


def build_github_owner_edge(
    artifact: Mapping[str, Any],
    expansion: Mapping[str, Any],
    store: JsonlStore,
    graph: GraphStore,
    aliases: EntityAliases,
    *,
    now: str,
) -> dict[str, int]:
    if expansion.get("provider") != "github" or expansion.get("status") != "succeeded":
        raise ValueError("GitHub expansion is not successful")
    owner = expansion.get("owner") if isinstance(expansion.get("owner"), Mapping) else {}
    owner_id = str(owner.get("id") or "")
    owner_type = str(owner.get("type") or "").casefold()
    if not owner_id.isdigit() or owner_type not in {"user", "organization"}:
        raise ValueError("GitHub owner metadata lacks an exact numeric identity")
    repository = expansion.get("repository") if isinstance(expansion.get("repository"), Mapping) else {}
    repo_name = str(repository.get("full_name") or artifact.get("identifiers", {}).get("github") or "")
    updated_artifact = dict(artifact)
    updated_artifact["identifiers"] = {
        **dict(artifact.get("identifiers") or {}),
        "github_repository_id": repository.get("id"),
    }
    # GitHub free-form topics are provider metadata, not canonical taxonomy IDs.
    updated_artifact["summary"] = str(artifact.get("summary") or repository.get("description") or "")
    metadata = dict(artifact.get("provider_metadata") or {})
    metadata["github"] = {
        "repository": dict(repository),
        "owner": {key: owner.get(key) for key in ("id", "login", "type", "html_url")},
        "fetched_at": now,
    }
    updated_artifact["provider_metadata"] = metadata
    store.upsert_artifact(updated_artifact)
    entity, created = materialize_exact_entity(
        store, aliases,
        entity_type="person" if owner_type == "user" else "organization",
        name=str(owner.get("login") or "Unknown GitHub owner"),
        external_ids={"github_user": owner_id} if owner_type == "user" else {"github_org": owner_id},
        url=str(owner.get("html_url") or ""),
        provider="github",
        provider_record_id=repo_name or str(artifact["artifact_id"]),
        now=now,
    )
    graph.add_edge(make_edge(
        str(artifact["artifact_id"]), "owned_by", str(entity["entity_id"]),
        _provider_evidence("github", repo_name or str(artifact["artifact_id"]), now),
        observed_at=now,
    ))
    return {"entities_added": int(created), "edges_added": 1}
