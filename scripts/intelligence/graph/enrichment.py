from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from ..aliases import ArtifactAliases
from ..connectors.base import ConnectorContext
from ..discovery.budget import ExpansionBudget
from ..entity_aliases import EntityAliases
from ..providers import (
    GitHubGraphProvider, GraphProviderFailure, OpenAlexGraphProvider,
    ProviderCache, SemanticScholarGraphProvider,
)
from ..resolver import SemanticScholarResolver, materialize_semantic_scholar_result
from ..store import JsonlStore
from .builders.github import build_github_owner_edge
from .builders.scholarly import (
    build_openalex_edges, build_semantic_scholar_edges, build_semantic_scholar_recent_works_edges,
)
from .store import GraphStore


class GraphProviderStateStore:
    """Safe retry diagnostics for graph providers, separate from connector checkpoints."""

    def __init__(self, runtime_dir: Path | str):
        self.directory = Path(runtime_dir) / "graph" / "providers"

    def save_failure(self, provider_id: str, failure: GraphProviderFailure, *, now: str) -> dict[str, Any]:
        backoff_until = failure.retry_at or _retry_deadline(now, failure.retry_after_seconds)
        record = {
            "provider_id": provider_id,
            "last_attempt_at": _timestamp(now),
            "last_error_class": failure.cause_class,
            "status": failure.status,
            "backoff_until": backoff_until,
            "retry_after_seconds": failure.retry_after_seconds,
        }
        path = self.directory / f"{provider_id}.json"
        _atomic_json(path, record)
        return record

    def save_success(self, provider_id: str, *, now: str) -> None:
        path = self.directory / f"{provider_id}.json"
        _atomic_json(path, {
            "provider_id": provider_id,
            "last_attempt_at": _timestamp(now),
            "last_success_at": _timestamp(now),
            "last_error_class": None,
            "status": 200,
            "backoff_until": None,
            "retry_after_seconds": None,
        })

    def save_partial(self, provider_id: str, error: Mapping[str, Any], *, now: str) -> None:
        backoff_until = error.get("retry_at") or _retry_deadline(now, error.get("retry_after_seconds"))
        _atomic_json(self.directory / f"{provider_id}.json", {
            "provider_id": provider_id,
            "last_attempt_at": _timestamp(now),
            "last_success_at": None,
            "last_error_class": str(error.get("error_class") or "ProviderFailure"),
            "status": error.get("http_status"),
            "backoff_until": backoff_until,
            "retry_after_seconds": error.get("retry_after_seconds"),
        })


def enrich_artifact(
    artifact_id: str,
    provider_id: str,
    store: JsonlStore,
    graph: GraphStore,
    aliases: EntityAliases,
    runtime_dir: Path | str,
    *,
    budget: ExpansionBudget,
    context: ConnectorContext,
) -> dict[str, Any]:
    artifact_aliases = ArtifactAliases(store.directory)
    canonical_id = artifact_aliases.resolve_artifact_id(artifact_id)
    artifact = store.get_by_id("artifact", canonical_id) or store.get_by_id("artifact", artifact_id)
    if artifact is None:
        raise ValueError("artifact not found")
    cache = ProviderCache(Path(runtime_dir) / "provider-cache")
    providers = {
        "openalex": OpenAlexGraphProvider(cache),
        "semantic-scholar": SemanticScholarGraphProvider(cache),
        "github": GitHubGraphProvider(cache),
    }
    provider = providers.get(provider_id)
    if provider is None:
        raise ValueError("unsupported graph provider")

    requests_before = budget.provider_requests
    resolution_diagnostics = None
    if provider_id in {"openalex", "semantic-scholar"}:
        artifact, resolution_diagnostics = _ensure_scholarly_exact_identity(
            artifact, provider_id, store, context, budget,
        )
        identifiers = artifact.get("identifiers") if isinstance(artifact.get("identifiers"), Mapping) else {}
        exact_after_resolution = (
            bool(identifiers.get("openalex") or identifiers.get("doi"))
            if provider_id == "openalex" else bool(identifiers.get("semantic_scholar"))
        )
        if not exact_after_resolution:
            failure = _resolution_failure(provider_id, resolution_diagnostics or {})
            if failure:
                state = GraphProviderStateStore(runtime_dir).save_failure(provider_id, failure, now=context.now())
                status = "partial"
            else:
                state = None
                status = "unresolved"
            return {
                "status": status, "provider": provider_id, "artifact_id": artifact["artifact_id"],
                "provider_requests": budget.provider_requests - requests_before,
                "nodes_added": 0, "edges_added": 0,
                "retryable": bool(failure and (failure.retry_at or failure.retry_after_seconds is not None)),
                "error_class": failure.cause_class if failure else None,
                "http_status": failure.status if failure else None,
                "provider_state": state, "diagnostics": resolution_diagnostics or {},
            }
    before_entities = len(list(store.iter_records("entity")))
    before_artifacts = len(list(store.iter_records("artifact")))
    before_edges = {item["edge_id"] for item in graph.iter_edges()}
    try:
        expansion = provider.expand_artifact(artifact, context, budget)
    except GraphProviderFailure as exc:
        state = GraphProviderStateStore(runtime_dir).save_failure(provider_id, exc, now=context.now())
        return {
            "status": "partial",
            "provider": provider_id,
            "artifact_id": artifact["artifact_id"],
            "provider_requests": budget.provider_requests - requests_before,
            "nodes_added": 0,
            "edges_added": 0,
            "retryable": bool(exc.retry_at or exc.retry_after_seconds is not None),
            "provider_state": state,
            "error_class": exc.cause_class,
            "http_status": exc.status,
        }
    if expansion.get("status") not in {"succeeded", "partial"}:
        return {
            "status": str(expansion.get("status") or "partial"),
            "provider": provider_id,
            "artifact_id": artifact["artifact_id"],
            "provider_requests": budget.provider_requests - requests_before,
            "nodes_added": 0,
            "edges_added": 0,
            "diagnostics": expansion.get("diagnostics", {}),
        }
    if provider_id == "openalex":
        build = build_openalex_edges(artifact, expansion, store, graph, aliases, now=context.now())
    elif provider_id == "semantic-scholar":
        build = build_semantic_scholar_edges(
            artifact, expansion, store, graph, aliases, now=context.now(),
            max_references=budget.max_references_per_artifact,
            max_citations=budget.max_citations_per_artifact,
        )
    else:
        build = build_github_owner_edge(artifact, expansion, store, graph, aliases, now=context.now())
    provider_errors = expansion.get("provider_errors") or []
    if provider_errors:
        GraphProviderStateStore(runtime_dir).save_partial(provider_id, provider_errors[0], now=context.now())
    else:
        GraphProviderStateStore(runtime_dir).save_success(provider_id, now=context.now())
    current_edges = {item["edge_id"] for item in graph.iter_edges()}
    nodes_added = max(
        0,
        len(list(store.iter_records("entity"))) - before_entities
        + len(list(store.iter_records("artifact"))) - before_artifacts,
    )
    return {
        "status": str(expansion.get("status") or "succeeded"),
        "provider": provider_id,
        "artifact_id": artifact["artifact_id"],
        "provider_requests": budget.provider_requests - requests_before,
        "nodes_added": nodes_added,
        "edges_added": len(current_edges - before_edges),
        "diagnostics": expansion.get("diagnostics", {}),
        "provider_errors": provider_errors,
        "retryable": bool(provider_errors),
        **build,
    }


def enrich_entity(
    entity_id: str,
    provider_id: str,
    store: JsonlStore,
    graph: GraphStore,
    aliases: EntityAliases,
    runtime_dir: Path | str,
    *,
    budget: ExpansionBudget,
    context: ConnectorContext,
) -> dict[str, Any]:
    if provider_id != "semantic-scholar":
        raise ValueError("only Semantic Scholar author expansion is supported")
    canonical_id = aliases.resolve_entity_id(entity_id)
    entity = store.get_by_id("entity", canonical_id)
    if entity is None:
        raise ValueError("entity not found")
    provider = SemanticScholarGraphProvider(ProviderCache(Path(runtime_dir) / "provider-cache"))
    before_edges = {item["edge_id"] for item in graph.iter_edges()}
    before_entities = len(list(store.iter_records("entity")))
    before_artifacts = len(list(store.iter_records("artifact")))
    requests_before = budget.provider_requests
    try:
        expansion = provider.expand_entity(entity, context, budget)
    except GraphProviderFailure as exc:
        state = GraphProviderStateStore(runtime_dir).save_failure(provider_id, exc, now=context.now())
        return {
            "status": "partial", "provider": provider_id, "entity_id": canonical_id,
            "provider_requests": budget.provider_requests - requests_before, "nodes_added": 0, "edges_added": 0,
            "retryable": bool(exc.retry_at or exc.retry_after_seconds is not None),
            "provider_state": state, "error_class": exc.cause_class, "http_status": exc.status,
        }
    if expansion.get("status") != "succeeded":
        return {
            "status": str(expansion.get("status") or "partial"), "provider": provider_id,
            "entity_id": canonical_id, "provider_requests": budget.provider_requests - requests_before,
            "nodes_added": 0, "edges_added": 0,
        }
    build = build_semantic_scholar_recent_works_edges(
        entity, expansion, store, graph, aliases, now=context.now(),
        max_recent_works=budget.max_recent_works_per_author,
    )
    GraphProviderStateStore(runtime_dir).save_success(provider_id, now=context.now())
    edge_ids = {item["edge_id"] for item in graph.iter_edges()}
    nodes_added = max(
        0,
        len(list(store.iter_records("entity"))) - before_entities
        + len(list(store.iter_records("artifact"))) - before_artifacts,
    )
    return {
        "status": "succeeded", "provider": provider_id, "entity_id": canonical_id,
        "provider_requests": budget.provider_requests - requests_before,
        "nodes_added": nodes_added, "edges_added": len(edge_ids - before_edges),
        "diagnostics": expansion.get("diagnostics", {}), **build,
    }


def _ensure_scholarly_exact_identity(
    artifact: Mapping[str, Any],
    provider_id: str,
    store: JsonlStore,
    context: ConnectorContext,
    budget: ExpansionBudget,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    identifiers = artifact.get("identifiers") if isinstance(artifact.get("identifiers"), Mapping) else {}
    exact = (
        bool(identifiers.get("openalex") or identifiers.get("doi"))
        if provider_id == "openalex"
        else bool(identifiers.get("semantic_scholar"))
    )
    if exact:
        return dict(artifact), None
    # The M1 resolver uses only explicit DOI/arXiv identifiers and never title search.
    if not (identifiers.get("doi") or identifiers.get("arxiv")):
        return dict(artifact), None
    aliases = ArtifactAliases(store.directory)
    local_aliases = []
    if identifiers.get("doi"):
        local_aliases.append(f"doi:{identifiers['doi']}")
    if identifiers.get("arxiv"):
        local_aliases.append(f"arxiv:{identifiers['arxiv']}")
    if not budget.request():
        return dict(artifact), {"error": "provider_request_budget_exhausted"}
    result = SemanticScholarResolver().resolve(
        artifact, str(artifact["artifact_id"]), aliases, context, force_provider_lookup=True,
    )
    materialized = materialize_semantic_scholar_result(result, artifact, store)
    if materialized:
        diagnostics = result.get("diagnostics") if isinstance(result.get("diagnostics"), dict) else None
        return materialized, diagnostics
    diagnostics = result.get("diagnostics") if isinstance(result.get("diagnostics"), dict) else None
    return dict(artifact), diagnostics


def _resolution_failure(provider_id: str, diagnostics: Mapping[str, Any]) -> GraphProviderFailure | None:
    if diagnostics.get("error") == "provider_request_failed":
        return GraphProviderFailure(
            provider_id, cause_class=str(diagnostics.get("error_class") or "ProviderFailure"),
        )
    status = diagnostics.get("status")
    if not isinstance(status, int) or status in {200, 404}:
        return None
    retry_after = None
    try:
        raw = diagnostics.get("retry-after")
        retry_after = max(0.0, float(raw)) if raw is not None else None
    except (TypeError, ValueError):
        retry_after = None
    return GraphProviderFailure(
        provider_id, status=status, retry_after_seconds=retry_after, cause_class="HTTPStatus",
    )


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _retry_deadline(now: str, seconds: Any) -> str | None:
    if seconds is None:
        return None
    try:
        delay = max(0.0, float(seconds))
        parsed = datetime.fromisoformat(now.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(parsed.timestamp() + delay, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
