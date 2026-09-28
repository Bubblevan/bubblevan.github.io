from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

from .bridge_capture import ingest_capture
from .bridge_xhs import ingest_xhs
from .entity_aliases import EntityAliases
from .store import JsonlStore
from .aliases import ArtifactAliases
from .connectors.base import ConnectorContext
from .connectors.registry import connector_registry
from .connectors.state import ConnectorStateStore
from .ids import artifact_id
from .connectors.http import SharedHttpClient
from .discovery.budget import ExpansionBudget
from .discovery.expand import SourceDiscovery
from .discovery.source_candidates import SourceCandidateStore
from .graph.backfill import graph_backfill, validate_graph_nodes
from .graph.enrichment import enrich_artifact, enrich_entity
from .graph.store import GraphStore
from .models import now_utc
from .resolver import SemanticScholarResolver, materialize_semantic_scholar_result
from .runner import load_source_catalog, run_all_sources, run_source


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORE = REPO_ROOT / "data" / "intelligence" / "events"
DEFAULT_RUNTIME = REPO_ROOT / "data" / "intelligence" / "runtime"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline Personal Research Intelligence data layer.")
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("ingest-xhs", "ingest-capture"):
        command = commands.add_parser(name)
        command.add_argument("json_file", type=Path)
        command.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    inspect = commands.add_parser("inspect-artifact")
    inspect.add_argument("artifact_id")
    inspect.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    stats = commands.add_parser("stats")
    stats.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    commands.add_parser("connectors", help="list available connector ids and capabilities")
    commands.add_parser("sources", help="list source ids from the seed catalog")
    local_sources = commands.add_parser("source-records", help="list locally materialized sources")
    local_sources.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    run = commands.add_parser("run-source", help="run one configured source once")
    run.add_argument("source_id")
    run.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    run.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    run_all = commands.add_parser("run-all", help="run each active source once")
    run_all.add_argument("--once", action="store_true", required=True)
    run_all.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    run_all.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    state = commands.add_parser("connector-state", help="show one local connector checkpoint")
    state.add_argument("source_id")
    state.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    smoke = commands.add_parser("smoke", help="explicitly run an optional live resolver smoke check")
    smoke.add_argument("provider", choices=["semantic-scholar"])
    smoke.add_argument("--arxiv", required=True)
    smoke.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    resolve = commands.add_parser("resolve-artifact", help="optionally reconcile an artifact with Semantic Scholar")
    resolve.add_argument("artifact_id")
    resolve.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    for name in ("graph-backfill", "graph-rebuild", "graph-stats"):
        command = commands.add_parser(name)
        command.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
        command.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    neighbors = commands.add_parser("graph-neighbors")
    neighbors.add_argument("node_id")
    neighbors.add_argument("--predicate")
    neighbors.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    path = commands.add_parser("graph-path")
    path.add_argument("from_id")
    path.add_argument("to_id")
    path.add_argument("--max-depth", type=int, default=3)
    path.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    enrich = commands.add_parser("graph-enrich")
    enrich.add_argument("--artifact", required=True)
    enrich.add_argument("--provider", choices=["openalex", "semantic-scholar", "github"], required=True)
    enrich.add_argument("--max-provider-requests", type=int, required=True)
    enrich.add_argument("--max-references", type=int, default=20)
    enrich.add_argument("--max-citations", type=int, default=20)
    enrich.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    enrich.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    pending = commands.add_parser("graph-enrich-pending")
    pending.add_argument("--provider", choices=["openalex", "semantic-scholar", "github"], required=True)
    pending.add_argument("--limit", type=int, required=True)
    pending.add_argument("--max-provider-requests", type=int, required=True)
    pending.add_argument("--max-references", type=int, default=20)
    pending.add_argument("--max-citations", type=int, default=20)
    pending.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    pending.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    enrich_author = commands.add_parser("graph-enrich-author")
    enrich_author.add_argument("--entity", required=True)
    enrich_author.add_argument("--provider", choices=["semantic-scholar"], required=True)
    enrich_author.add_argument("--limit", type=int, required=True)
    enrich_author.add_argument("--max-provider-requests", type=int, required=True)
    enrich_author.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    enrich_author.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    discover = commands.add_parser("discover-sources")
    discover.add_argument("--seed-source", required=True)
    discover.add_argument("--max-depth", type=int, default=2)
    discover.add_argument("--max-nodes", type=int, default=100)
    discover.add_argument("--max-edges", type=int, default=300)
    discover.add_argument("--max-candidates", type=int, default=50)
    discover.add_argument("--max-provider-requests", type=int, default=50)
    discover.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    candidates = commands.add_parser("source-candidates")
    candidates.add_argument("--status", choices=["pending", "approved", "rejected", "deferred"])
    candidates.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    candidate = commands.add_parser("source-candidate")
    candidate.add_argument("candidate_id")
    candidate.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    approve = commands.add_parser("approve-source-candidate")
    approve.add_argument("candidate_id")
    approve.add_argument("--reviewed-at", default=now_utc())
    approve.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    reject = commands.add_parser("reject-source-candidate")
    reject.add_argument("candidate_id")
    reject.add_argument("--reason-code", choices=["irrelevant", "low_signal", "duplicate", "too_broad", "not_a_source", "already_known", "other"], required=True)
    reject.add_argument("--reviewed-at", default=now_utc())
    reject.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    reopen = commands.add_parser("reopen-source-candidate")
    reopen.add_argument("candidate_id")
    reopen.add_argument("--reviewed-at", default=now_utc())
    reopen.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    export = commands.add_parser("export-source-template")
    export.add_argument("candidate_id")
    export.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        store = JsonlStore(getattr(args, "store_dir", DEFAULT_STORE))
        if args.command in {"ingest-xhs", "ingest-capture"}:
            payload = _read_json_object(args.json_file)
            if args.command == "ingest-xhs":
                source, observation, artifact_ids = ingest_xhs(payload, store)
                _print_json(
                    {
                        "source_id": source["source_id"],
                        "observation_id": observation["observation_id"],
                        "artifact_ids": artifact_ids,
                    }
                )
            else:
                source, observation = ingest_capture(payload, store)
                _print_json(
                    {"source_id": source["source_id"], "observation_id": observation["observation_id"]}
                )
            return 0
        if args.command == "inspect-artifact":
            artifact = store.get_by_id("artifact", args.artifact_id)
            if artifact is None:
                raise ValueError(f"artifact not found: {args.artifact_id}")
            _print_json(artifact)
            return 0
        if args.command == "stats":
            _print_json(store.stats())
            return 0
        if args.command == "connectors":
            _print_json([
                {
                    "connector_id": spec.connector_id,
                    "version": spec.version,
                    "modes": list(spec.modes),
                    "capabilities": sorted(spec.capabilities),
                    "requires_auth": spec.requires_auth,
                    "supports_incremental": spec.supports_incremental,
                }
                for spec in connector_registry().list()
            ])
            return 0
        if args.command == "sources":
            _print_json([
                {"source_id": source["source_id"], "name": source["name"],
                 "connector": source["acquisition"]["connector"], "status": source["status"]}
                for source in load_source_catalog()
            ])
            return 0
        if args.command == "source-records":
            _print_json([
                {"source_id": source["source_id"], "name": source["name"], "platform": source["platform"],
                 "status": source["status"], "canonical_url": source["canonical_url"]}
                for source in store.iter_records("source")
            ])
            return 0
        if args.command in {"run-source", "run-all"}:
            sources = load_source_catalog()
            if args.command == "run-source":
                source = next((item for item in sources if item["source_id"] == args.source_id), None)
                if source is None:
                    raise ValueError(f"source not found in catalog: {args.source_id}")
                selected = [source]
            else:
                selected = [item for item in sources if item["status"] == "active"]
            states = ConnectorStateStore(args.runtime_dir)
            registry = connector_registry()
            if args.command == "run-source":
                result = run_source(selected[0], registry, states, store, ConnectorContext(store=store))
                _print_json({"status": "succeeded", **result})
                return 0
            summary = run_all_sources(selected, registry, states, store, ConnectorContext(store=store))
            _print_json(summary)
            return 1 if summary["failed"] else 0
        if args.command == "connector-state":
            state = ConnectorStateStore(args.runtime_dir).load(args.source_id)
            if state is None:
                raise ValueError(f"connector state not found: {args.source_id}")
            from dataclasses import asdict
            _print_json(asdict(state))
            return 0
        if args.command == "smoke":
            from .canonicalize import extract_arxiv_id
            arxiv = extract_arxiv_id(args.arxiv)
            if not arxiv:
                raise ValueError("smoke requires a valid arXiv identifier")
            with tempfile.TemporaryDirectory(prefix="ri-s2-smoke-") as temp:
                result = SemanticScholarResolver().resolve(
                    {"identifiers": {"arxiv": arxiv}, "title": ""},
                    artifact_id(f"arxiv:{arxiv}"), ArtifactAliases(temp), ConnectorContext(store=store),
                )
            _print_json(result)
            return 0
        if args.command == "resolve-artifact":
            aliases = ArtifactAliases(args.store_dir)
            canonical_id = aliases.resolve_artifact_id(args.artifact_id)
            artifact = store.get_by_id("artifact", canonical_id) or store.get_by_id("artifact", args.artifact_id)
            if artifact is None:
                raise ValueError(f"artifact not found: {args.artifact_id}")
            result = SemanticScholarResolver().resolve(
                artifact, str(artifact["artifact_id"]), aliases, ConnectorContext(store=store),
            )
            resolved_artifact = materialize_semantic_scholar_result(result, artifact, store)
            if resolved_artifact:
                result["materialized_artifact"] = resolved_artifact
            _print_json(result)
            return 0
        if args.command == "graph-backfill":
            result = graph_backfill(store, args.runtime_dir, now=now_utc())
            _print_json(result)
            return 0
        if args.command == "graph-rebuild":
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            result = graph.rebuild_indexes(args.runtime_dir, entity_id_resolver=EntityAliases(args.store_dir))
            _print_json(result)
            return 0
        if args.command == "graph-neighbors":
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            aliases = EntityAliases(args.store_dir)
            _print_json({
                "node_id": args.node_id,
                "predicate": args.predicate,
                "edges": graph.neighbors(args.node_id, predicate=args.predicate, entity_id_resolver=aliases),
            })
            return 0
        if args.command == "graph-path":
            if args.max_depth < 1 or args.max_depth > 10:
                raise ValueError("graph path max-depth must be between 1 and 10")
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            result = _find_graph_path(
                args.from_id, args.to_id, graph, EntityAliases(args.store_dir), args.max_depth,
            )
            _print_json(result)
            return 0 if result["found"] else 1
        if args.command == "graph-stats":
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            edges = graph.iter_edges()
            _print_json({
                "nodes": {
                    "sources": len(list(store.iter_records("source"))),
                    "observations": len(list(store.iter_records("observation"))),
                    "artifacts": len(list(store.iter_records("artifact"))),
                    "entities": len(list(store.iter_records("entity"))),
                    "topics": len(set(
                        endpoint for edge in edges for endpoint in (edge["subject_id"], edge["object_id"])
                        if endpoint.startswith("topic-")
                    )),
                },
                "edges": len(edges),
                "predicates": _count_by(edges, "predicate"),
                "providers": _count_edge_providers(edges),
                "source_candidates": len(SourceCandidateStore(args.store_dir).iter_candidates()),
            })
            return 0
        if args.command == "graph-enrich":
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            budget = _make_budget(
                args.max_provider_requests,
                max_references=args.max_references,
                max_citations=args.max_citations,
            )
            result = enrich_artifact(
                args.artifact, args.provider, store, graph, EntityAliases(args.store_dir),
                args.runtime_dir, budget=budget,
                context=ConnectorContext(store=store, http=SharedHttpClient(), now=now_utc),
            )
            validate_graph_nodes(store, graph)
            graph.rebuild_indexes(args.runtime_dir, entity_id_resolver=EntityAliases(args.store_dir))
            _print_json(result)
            return 1 if result.get("status") == "partial" else 0
        if args.command == "graph-enrich-author":
            if args.limit < 1 or args.limit > 10:
                raise ValueError("author recent-works limit must be between 1 and 10")
            budget = _make_budget(args.max_provider_requests, recent_works=args.limit)
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            result = enrich_entity(
                args.entity, args.provider, store, graph, EntityAliases(args.store_dir),
                args.runtime_dir, budget=budget,
                context=ConnectorContext(store=store, http=SharedHttpClient(), now=now_utc),
            )
            validate_graph_nodes(store, graph)
            graph.rebuild_indexes(args.runtime_dir, entity_id_resolver=EntityAliases(args.store_dir))
            _print_json(result)
            return 1 if result.get("status") == "partial" else 0
        if args.command == "graph-enrich-pending":
            if args.limit < 1 or args.limit > 20:
                raise ValueError("graph-enrich-pending limit must be between 1 and 20")
            budget = _make_budget(
                args.max_provider_requests,
                max_references=args.max_references,
                max_citations=args.max_citations,
            )
            artifacts = _pending_artifacts(store, args.provider)[:args.limit]
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            results = []
            for artifact in artifacts:
                if budget.provider_requests >= budget.max_provider_requests:
                    budget.exhausted = True
                    break
                results.append(enrich_artifact(
                    str(artifact["artifact_id"]), args.provider, store, graph,
                    EntityAliases(args.store_dir), args.runtime_dir, budget=budget,
                    context=ConnectorContext(store=store, http=SharedHttpClient(), now=now_utc),
                ))
            validate_graph_nodes(store, graph)
            graph.rebuild_indexes(args.runtime_dir, entity_id_resolver=EntityAliases(args.store_dir))
            _print_json({
                "provider": args.provider,
                "limit": args.limit,
                "items_selected": len(artifacts),
                "provider_requests": budget.provider_requests,
                "budget_exhausted": budget.exhausted,
                "results": results,
            })
            return 1 if any(result.get("status") == "partial" for result in results) else 0
        if args.command == "discover-sources":
            budget = ExpansionBudget(
                max_depth=args.max_depth, max_nodes=args.max_nodes, max_edges=args.max_edges,
                max_candidates=args.max_candidates, max_provider_requests=args.max_provider_requests,
            )
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            result = SourceDiscovery(
                store, graph, EntityAliases(args.store_dir),
                SourceCandidateStore(args.store_dir), now=now_utc(),
            ).discover(args.seed_source, budget)
            _print_json(result)
            return 0
        if args.command == "source-candidates":
            rows = SourceCandidateStore(args.store_dir).iter_candidates()
            if args.status:
                rows = [row for row in rows if row["status"] == args.status]
            _print_json(rows)
            return 0
        if args.command == "source-candidate":
            row = next((item for item in SourceCandidateStore(args.store_dir).iter_candidates()
                        if item["candidate_id"] == args.candidate_id), None)
            if row is None:
                raise ValueError("source candidate not found")
            _print_json(row)
            return 0
        if args.command == "approve-source-candidate":
            row = SourceCandidateStore(args.store_dir).review(
                args.candidate_id, "approved", reviewed_at=args.reviewed_at,
            )
            _print_json(row)
            return 0
        if args.command == "reject-source-candidate":
            row = SourceCandidateStore(args.store_dir).review(
                args.candidate_id, "rejected", reviewed_at=args.reviewed_at, reason_code=args.reason_code,
            )
            _print_json(row)
            return 0
        if args.command == "reopen-source-candidate":
            row = SourceCandidateStore(args.store_dir).review(
                args.candidate_id, "pending", reviewed_at=args.reviewed_at,
            )
            _print_json(row)
            return 0
        if args.command == "export-source-template":
            row = next((item for item in SourceCandidateStore(args.store_dir).iter_candidates()
                        if item["candidate_id"] == args.candidate_id), None)
            if row is None:
                raise ValueError("source candidate not found")
            _print_yaml(_source_template(row))
            return 0
        raise ValueError(f"unsupported command: {args.command}")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input JSON must be one object")
    return payload


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _print_yaml(value: object) -> None:
    import yaml
    print(yaml.safe_dump(value, allow_unicode=True, sort_keys=False).rstrip())


def _make_budget(
    max_provider_requests: int,
    *,
    max_references: int = 20,
    max_citations: int = 20,
    recent_works: int = 10,
) -> ExpansionBudget:
    if max_provider_requests < 1 or max_provider_requests > 50:
        raise ValueError("max-provider-requests must be between 1 and 50")
    if max_references < 0 or max_references > 20 or max_citations < 0 or max_citations > 20:
        raise ValueError("reference and citation limits must be between 0 and 20")
    if recent_works < 0 or recent_works > 10:
        raise ValueError("recent-work limit must be between 0 and 10")
    return ExpansionBudget(
        max_provider_requests=max_provider_requests,
        max_references_per_artifact=max_references,
        max_citations_per_artifact=max_citations,
        max_recent_works_per_author=recent_works,
    )


def _pending_artifacts(store: JsonlStore, provider: str) -> list[dict[str, Any]]:
    selected = []
    for artifact in store.iter_records("artifact"):
        identifiers = artifact.get("identifiers") if isinstance(artifact.get("identifiers"), dict) else {}
        if provider == "github":
            eligible = artifact.get("artifact_type") == "repository" and bool(identifiers.get("github"))
        elif provider == "openalex":
            eligible = artifact.get("artifact_type") == "paper" and bool(
                identifiers.get("openalex") or identifiers.get("doi") or identifiers.get("arxiv")
            )
        else:
            eligible = artifact.get("artifact_type") == "paper" and bool(
                identifiers.get("semantic_scholar") or identifiers.get("doi") or identifiers.get("arxiv")
            )
        if eligible and artifact.get("status") == "candidate":
            selected.append(artifact)
    return sorted(selected, key=lambda item: str(item["artifact_id"]))


def _find_graph_path(from_id: str, to_id: str, graph: GraphStore, aliases: EntityAliases, max_depth: int) -> dict[str, Any]:
    from collections import deque

    def canonical(value: str) -> str:
        return aliases.resolve_entity_id(value) if value.startswith("ent-") else value

    start, target = canonical(from_id), canonical(to_id)
    outgoing: dict[str, list[dict[str, Any]]] = {}
    for edge in graph.iter_edges():
        subject, obj = canonical(str(edge["subject_id"])), canonical(str(edge["object_id"]))
        outgoing.setdefault(subject, []).append(dict(edge, _object=obj))
    for values in outgoing.values():
        values.sort(key=lambda item: (item["predicate"], item["_object"], item["edge_id"]))
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        node, path = queue.popleft()
        if node == target:
            return {"found": True, "from_id": from_id, "to_id": to_id, "depth": len(path), "steps": path}
        if len(path) >= max_depth:
            continue
        for edge in outgoing.get(node, []):
            next_node = str(edge["_object"])
            if next_node in visited:
                continue
            step = {
                "edge_id": edge["edge_id"],
                "subject_id": edge["subject_id"],
                "predicate": edge["predicate"],
                "object_id": edge["object_id"],
                "evidence": edge["evidence"],
            }
            visited.add(next_node)
            queue.append((next_node, path + [step]))
    return {"found": False, "from_id": from_id, "to_id": to_id, "max_depth": max_depth, "steps": []}


def _count_by(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for record in records:
        key = str(record.get(field) or "")
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def _count_edge_providers(edges: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for edge in edges:
        for provider in {str(item.get("provider")) for item in edge.get("evidence", []) if item.get("provider")}:
            result[provider] = result.get(provider, 0) + 1
    return dict(sorted(result.items()))


def _source_template(candidate: dict[str, Any]) -> dict[str, Any]:
    source_type = {
        "person": "author",
        "institution": "lab",
        "organization": "community",
        "repository": "repository",
    }[candidate["candidate_type"]]
    return {
        "identity": f"candidate|{candidate['candidate_id']}",
        "source_type": source_type,
        "platform": candidate["platform"],
        "name": candidate["name"],
        "canonical_url": candidate["canonical_url"],
        "external_ids": candidate["external_ids"],
        "topics": candidate["topics"],
        "acquisition": {"connector": "manual", "mode": "manual"},
        "status": "paused",
        "review_note": "Generated suggestion only; review the evidence path and choose a supported connector before activation.",
    }


if __name__ == "__main__":
    raise SystemExit(main())
