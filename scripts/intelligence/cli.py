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
from .retrieval.bm25 import BM25Retriever
from .retrieval.corpus import build_snapshot
from .retrieval.dense import DenseRetriever, SentenceTransformerBackend
from .retrieval.engine import RetrievalEngine, explain_candidate, infer_topic_ids, read_run
from .retrieval.graph import GraphRetriever
from .retrieval.manifest import make_manifest
from .retrieval.registry import RetrieverRegistry
from .retrieval.request import make_request
from .retrieval.source import SourceRetriever
from .retrieval.topic import TopicRetriever
from .retrieval.expansion import expand_query


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

    retrieval_build = commands.add_parser("retrieval-build", help="build reproducible local retrieval indexes")
    retrieval_build.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    retrieval_build.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    retrieval_build.add_argument("--dense", action="store_true", help="build the live embedding index")
    retrieval_build.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    retrieval_build.add_argument("--revision")
    retrieval_build.add_argument("--device")
    retrieval_manifest = commands.add_parser("retrieval-manifest", help="show deterministic corpus/index manifests")
    retrieval_manifest.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    retrieval_manifest.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    retrieval_smoke = commands.add_parser("retrieval-smoke", help="run ten fixed local multi-route smoke queries")
    retrieval_smoke.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    retrieval_smoke.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    retrieval_smoke.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    retrieval_smoke.add_argument("--revision")
    retrieval_smoke.add_argument("--device")

    search = commands.add_parser("search", help="run explainable multi-route retrieval")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--top-k", type=int, default=20)
    search.add_argument("--topic", action="append", default=[])
    search.add_argument("--seed-artifact", action="append", default=[])
    search.add_argument("--negative-seed-artifact", action="append", default=[])
    search.add_argument("--source", action="append", default=[])
    search.add_argument("--as-of")
    search.add_argument("--artifact-type", action="append", default=[])
    search.add_argument("--language", action="append", default=[])
    search.add_argument("--routes", help="comma-separated route IDs")
    search.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    search.add_argument("--revision")
    search.add_argument("--device")
    search.add_argument("--no-dense", action="store_true")
    search.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    search.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    explain = commands.add_parser("explain-retrieval", help="explain one candidate from a stored retrieval run")
    explain.add_argument("request_id")
    explain.add_argument("artifact_id")
    explain.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        store = JsonlStore(getattr(args, "store_dir", DEFAULT_STORE))
        if args.command in {"retrieval-build", "retrieval-manifest", "retrieval-smoke", "search", "explain-retrieval"}:
            if args.command == "explain-retrieval":
                run_path = args.runtime_dir / "retrieval" / "runs" / f"{args.request_id}.json"
                run_result = read_run(run_path)
                _print_json(explain_candidate(run_result, args.artifact_id))
                return 0
            snapshot = build_snapshot(store)
            if args.command == "retrieval-smoke":
                from .retrieval.live_smoke import run_live_smoke, write_report
                smoke_result = run_live_smoke(
                    args.store_dir, args.runtime_dir, model=args.model,
                    revision=args.revision, device=args.device,
                )
                report = write_report(
                    smoke_result, store,
                    REPO_ROOT / "content" / "docs" / "agent" / "search" / "research-intelligence" / "m3-retrieval-report.md",
                )
                _print_json({"corpus_hash": smoke_result["corpus_hash"],
                             "queries": [{"category": item["smoke_category"], "request_id": item["request"]["request_id"]}
                                         for item in smoke_result["queries"]],
                             "hardware": smoke_result["hardware"], "dense": report["dense"],
                             "report_path": str(REPO_ROOT / "content" / "docs" / "agent" / "search" / "research-intelligence" / "m3-retrieval-report.md"),
                             "runtime_smoke_path": str(args.runtime_dir / "retrieval" / "live-smoke-20260928.json")})
                return 0
            if args.command == "retrieval-manifest":
                manifests = {}
                for route in ("bm25", "dense"):
                    manifest_path = args.runtime_dir / "retrieval" / route / "manifest.json"
                    if manifest_path.exists():
                        value = json.loads(manifest_path.read_text(encoding="utf-8"))
                        manifests[route] = {key: item for key, item in value.items()
                                            if key not in {"document_hashes", "document_order_hash", "index_file_hashes"}}
                _print_json({"corpus": make_manifest(snapshot, retriever_versions={"normalization": snapshot.normalization_version}),
                             "indexes": manifests})
                return 0
            registry = _retriever_registry(store, args.store_dir, args.runtime_dir, dense=False)
            if args.command == "retrieval-build":
                if args.dense:
                    registry.register(DenseRetriever(SentenceTransformerBackend(
                        args.model, revision=args.revision, device=args.device,
                    )))
                engine = RetrievalEngine(snapshot, registry, store_dir=str(args.store_dir), runtime_dir=str(args.runtime_dir))
                result = engine.build()
                result = {"corpus_hash": result["corpus_hash"],
                          "corpus": _corpus_counts(store, snapshot),
                          "indexes": {route: {key: value for key, value in manifest.items()
                                              if key not in {"document_hashes", "index_file_hashes"}}
                                      for route, manifest in result["routes"].items()},
                          "failed_routes": result["failed_routes"]}
                _write_json(args.runtime_dir / "retrieval" / "corpus_manifest.json",
                            make_manifest(snapshot, retriever_versions=registry.versions()))
                _print_json(result)
                return 1 if result.get("failed_routes") else 0
            if args.command == "search":
                if args.top_k < 1 or args.top_k > 500:
                    raise ValueError("--top-k must be between 1 and 500")
                topic_map = _topic_ids(args.topic)
                topic_ids = sorted(set(topic_map).union(infer_topic_ids(args.query)))
                expanded = expand_query(args.query, entity_names=[
                    str(item.get("name") or "") for item in store.iter_records("entity")
                ])
                request = make_request(
                    args.query, seed_artifact_ids=args.seed_artifact,
                    negative_seed_artifact_ids=args.negative_seed_artifact, topic_ids=topic_ids,
                    source_ids=args.source, as_of=args.as_of,
                    filters={"artifact_types": args.artifact_type, "published_after": None,
                             "published_before": None, "languages": args.language},
                    top_k=args.top_k, expanded_terms=expanded,
                )
                if not args.no_dense:
                    registry.register(DenseRetriever(SentenceTransformerBackend(
                        args.model, revision=args.revision, device=args.device,
                    )))
                engine = RetrievalEngine(snapshot, registry, store_dir=str(args.store_dir), runtime_dir=str(args.runtime_dir))
                selected_routes = [item.strip() for item in args.routes.split(",") if item.strip()] if args.routes else None
                result = engine.search(request, routes=selected_routes)
                result["corpus"] = _corpus_counts(store, snapshot)
                result["items"] = [
                    {"artifact_id": item["artifact_id"], "title": (snapshot.by_id().get(item["artifact_id"]).title if snapshot.by_id().get(item["artifact_id"]) else ""),
                     "artifact_type": (snapshot.by_id().get(item["artifact_id"]).artifact_type if snapshot.by_id().get(item["artifact_id"]) else ""),
                     "score": item["fusion"]["score"], "routes": [route["route"] for route in item["routes"]]}
                    for item in result["candidates"]
                ]
                _print_json(result)
                return 0
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


def _retriever_registry(store: JsonlStore, store_dir: Path, runtime_dir: Path, *, dense: bool) -> RetrieverRegistry:
    from .retrieval.semantic_scholar_recommendations import SemanticScholarRecommendationsRetriever
    registry = RetrieverRegistry()
    registry.register(BM25Retriever())
    registry.register(GraphRetriever(str(store_dir)))
    registry.register(TopicRetriever())
    registry.register(SourceRetriever(str(store_dir)))
    registry.register(SemanticScholarRecommendationsRetriever(store, runtime_dir))
    if dense:
        registry.register(DenseRetriever(SentenceTransformerBackend()))
    return registry


def _topic_ids(values: list[str]) -> list[str]:
    from .topics import topic_aliases
    aliases = topic_aliases()
    result = []
    for value in values:
        if value.startswith("topic-"):
            if value not in set(aliases.values()):
                raise ValueError(f"unknown topic id: {value}")
            result.append(value)
            continue
        key = " ".join("".join(char if char.isalnum() else " " for char in value.casefold()).split())
        topic = aliases.get(key)
        if not topic:
            raise ValueError(f"unknown topic alias: {value}")
        result.append(topic)
    return sorted(set(result))


def _corpus_counts(store: JsonlStore, snapshot: Any) -> dict[str, Any]:
    artifacts = list(store.iter_records("artifact"))
    by_type: dict[str, int] = {}
    for artifact in artifacts:
        artifact_type = str(artifact.get("artifact_type") or "other")
        by_type[artifact_type] = by_type.get(artifact_type, 0) + 1
    missing_published = sum(not artifact.get("published_at") for artifact in artifacts)
    return {
        "artifacts_total": len(artifacts),
        "papers": by_type.get("paper", 0),
        "blogs": by_type.get("blog", 0),
        "repositories": by_type.get("repository", 0),
        "models": by_type.get("model", 0),
        "datasets": by_type.get("dataset", 0),
        "models_and_datasets": by_type.get("model", 0) + by_type.get("dataset", 0),
        "documents_indexed": len(snapshot.documents),
        "documents_skipped_or_canonicalized": max(0, len(artifacts) - len(snapshot.documents)),
        "missing_published_at": missing_published,
        "corpus_hash": snapshot.corpus_hash,
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


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
