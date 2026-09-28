from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import hashlib
import json
from typing import Any, Callable, Mapping

from ..repositories.artifacts import ArtifactRepository
from ..store import JsonlStore
from ..retrieval.corpus import build_snapshot
from ..retrieval.bm25 import BM25Retriever
from ..retrieval.dense import DenseRetriever, SentenceTransformerBackend
from ..retrieval.engine import RetrievalEngine, infer_topic_ids
from ..retrieval.expansion import expand_query
from ..retrieval.graph import GraphRetriever
from ..retrieval.registry import RetrieverRegistry
from ..retrieval.topic import TopicRetriever
from ..retrieval.request import make_request
from ..retrieval.fusion import reciprocal_rank_fusion
from ..retrieval.evaluation import TOPIC_BY_CATEGORY
from .standard_metrics import evaluate_ir_measures, ranx_metrics


def run_frozen_dev(pack: Mapping[str, Any], store: JsonlStore, runtime_dir: str | Path, *,
                   model: str = "Qwen/Qwen3-Embedding-0.6B", revision: str | None = None,
                   device: str | None = None) -> dict[str, Any]:
    snapshot = build_snapshot(store)
    _require_frozen_pack(pack, snapshot.corpus_hash)
    artifact_repository = ArtifactRepository(store)
    registry = RetrieverRegistry()
    registry.register(BM25Retriever())
    registry.register(DenseRetriever(SentenceTransformerBackend(model, revision=revision, device=device)))
    registry.register(GraphRetriever(str(store.directory)))
    registry.register(TopicRetriever())
    engine = RetrievalEngine(snapshot, registry, store_dir=str(store.directory), runtime_dir=str(runtime_dir))
    build = engine.build(["bm25", "dense", "graph", "topic"])
    if build.get("failed_routes"):
        raise RuntimeError("DEV evaluation requires successful BM25, Dense, Graph, and Topic indexes")
    topic_rows: dict[str, list[str]] = {}
    rankings: dict[str, dict[str, list[str]]] = {key: {} for key in ("B0", "B1", "B2", "B3", "B4")}
    qrels_by_query: dict[str, dict[str, int]] = defaultdict(dict)
    query_metadata: dict[str, dict[str, str]] = {}
    for item in pack["qrels"]:
        qrels_by_query[str(item["query_id"])][str(item["artifact_id"])] = int(item["grade"])
    for query in pack["queries"]:
        query_id = str(query["query_id"])
        query_metadata[query_id] = {"category": str(query["category"]), "specificity": str(query["specificity"])}
        topic_ids = sorted(set(infer_topic_ids(str(query["query"]))) |
                           ({TOPIC_BY_CATEGORY[str(query["category"])]} if query.get("category") in TOPIC_BY_CATEGORY else set()))
        request = make_request(str(query["query"]), topic_ids=topic_ids,
                               filters={"corpus_profile": "research-default"}, top_k=20,
                               expanded_terms=expand_query(str(query["query"])))
        route_result = engine.search(request, routes=["bm25", "dense", "graph-expand"],
                                     route_depth=50, persist=False)
        for baseline, route in (("B0", "bm25"), ("B1", "dense")):
            rankings[baseline][query_id] = _ids(route_result.get("route_candidates", {}).get(route, []))[:20]
        rankings["B2"][query_id] = _ids(route_result.get("route_candidates", {}).get("graph-expand", []))[:20]
        route_rows = route_result.get("route_candidates", {})
        rankings["B3"][query_id] = _fused_ids(
            {"bm25": route_rows.get("bm25", []), "dense": route_rows.get("dense", [])},
            query_id, artifact_repository.resolve_id)
        rankings["B4"][query_id] = _fused_ids(
            {"bm25": route_rows.get("bm25", []), "dense": route_rows.get("dense", []),
             "graph-expand": route_rows.get("graph-expand", [])}, query_id, artifact_repository.resolve_id)
        if topic_ids:
            topic_result = engine.search(request, routes=["topic"], route_depth=50, persist=False)
            topic_rows[query_id] = _ids(topic_result.get("route_candidates", {}).get("topic", []))[:20]
    artifact_types = {str(row["artifact_id"]): str(row.get("artifact_type") or "other")
                      for row in artifact_repository.iter_canonical()}
    baselines = {}
    for baseline, queries in rankings.items():
        per_query = {query_id: evaluate_ir_measures(queries.get(query_id, []), qrels_by_query[query_id])
                     for query_id in sorted(qrels_by_query)}
        baselines[baseline] = {"aggregate": _mean_metrics(per_query), "per_query": per_query,
                               "slices": _slices(per_query, query_metadata),
                               "artifact_type_slices": _type_slices(queries, qrels_by_query, artifact_types)}
    topic_metrics = {query_id: evaluate_ir_measures(ranking, qrels_by_query[query_id])
                     for query_id, ranking in topic_rows.items()}
    ranx_reports = {baseline: ranx_metrics(rankings[baseline], qrels_by_query) for baseline in rankings}
    return {
        "schema": "bubblevan/retrieval-m3-2-evaluation/v1", "status": "completed",
        "benchmark_hash": pack["benchmark_hash"], "corpus_hash": snapshot.corpus_hash,
        "query_count": len(pack["queries"]), "judged_pairs": sum(map(len, qrels_by_query.values())),
        "baselines": baselines,
        "topic_route": {"eligible_queries": len(topic_metrics), "per_query": topic_metrics,
                        "aggregate": _mean_metrics(topic_metrics)},
        "ranx": ranx_reports,
        "rankings": rankings,
        "topic_rankings": topic_rows,
    }


def write_error_analysis(result: Mapping[str, Any], pack: Mapping[str, Any], output: str | Path) -> None:
    query_by_id = {str(query["query_id"]): query for query in pack["queries"]}
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    for item in pack["qrels"]:
        qrels[str(item["query_id"])][str(item["artifact_id"])] = int(item["grade"])
    lines = ["# M3.2 DEV-v1 Error Analysis", "",
             f"Corpus hash: `{result['corpus_hash']}`", f"Benchmark hash: `{result['benchmark_hash']}`", ""]
    for query_id in sorted(query_by_id):
        query = query_by_id[query_id]
        lines.extend([f"## {query['category']} / {query['specificity']} — {query_id}", "", str(query["query"]), ""])
        for baseline in ("B0", "B1", "B2", "B3", "B4"):
            ranking = result["rankings"][baseline].get(query_id, [])
            judged = qrels[query_id]
            top = [f"`{artifact_id}` grade={judged.get(artifact_id, 'unjudged')}"
                   for artifact_id in ranking[:10]]
            missed = sorted(artifact_id for artifact_id, grade in judged.items()
                            if grade > 0 and artifact_id not in ranking[:20])
            lines.extend([f"### {baseline}", "", "Top 10: " + (", ".join(top) if top else "(empty)"),
                          "Missed relevant items outside top 20: " + (", ".join(f"`{item}`" for item in missed) if missed else "none"), ""])
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _require_frozen_pack(pack: Mapping[str, Any], current_hash: str) -> None:
    if pack.get("status") != "frozen" or pack.get("schema") != "bubblevan/retrieval-frozen-benchmark/v1":
        raise ValueError("DEV evaluation requires a frozen dev-v1.json")
    if pack.get("corpus_hash") != current_hash:
        raise ValueError("frozen DEV corpus hash does not match current corpus")
    if len(pack.get("queries", [])) != 20:
        raise ValueError("frozen DEV benchmark must contain 20 queries")
    expected_hash = hashlib.sha256(json.dumps(
        {"benchmark_id": pack.get("benchmark_id"), "queries": pack.get("queries")},
        ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if expected_hash != pack.get("benchmark_hash"):
        raise ValueError("frozen DEV benchmark hash is invalid")
    expected_pairs = {(str(query["query_id"]), str(item["artifact_id"]))
                      for query in pack["queries"] for item in query.get("candidates", [])}
    actual_pairs = {(str(item["query_id"]), str(item["artifact_id"])) for item in pack.get("qrels", [])}
    if expected_pairs and actual_pairs != expected_pairs:
        raise ValueError("frozen DEV qrels do not cover the candidate inventory")
    if any(item.get("grade") not in (0, 1, 2) for item in pack.get("qrels", [])):
        raise ValueError("frozen DEV qrels have an invalid grade")


def _ids(rows: list[Mapping[str, Any]]) -> list[str]:
    return [str(row["artifact_id"]) for row in rows if row.get("artifact_id")]


def _fused_ids(routes: Mapping[str, list[Mapping[str, Any]]], request_id: str,
               canonicalize: Callable[[str], str]) -> list[str]:
    return [str(item["artifact_id"]) for item in reciprocal_rank_fusion(
        routes, request_id=request_id, top_k=20, canonicalize=canonicalize)]


def _mean_metrics(per_query: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    if not per_query:
        return {}
    keys = sorted({key for row in per_query.values() for key in row})
    return {key: sum(float(row.get(key, 0.0)) for row in per_query.values()) / len(per_query) for key in keys}


def _slices(per_query: Mapping[str, Mapping[str, float]], metadata: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    groups: dict[str, dict[str, Mapping[str, float]]] = {"category": {}, "specificity": {}}
    for query_id, metrics in per_query.items():
        for field in groups:
            key = str(metadata.get(query_id, {}).get(field) or "unknown")
            groups[field].setdefault(key, {})[query_id] = metrics
    return {field: {key: {"N": len(rows), "metrics": _mean_metrics(rows)} for key, rows in sorted(values.items())}
            for field, values in groups.items()}


def _type_slices(rankings: Mapping[str, list[str]], qrels: Mapping[str, Mapping[str, int]],
                 artifact_types: Mapping[str, str]) -> dict[str, Any]:
    types = sorted({artifact_types.get(artifact_id, "unknown")
                    for rows in qrels.values() for artifact_id in rows})
    result = {}
    for kind in types:
        per_query = {}
        for query_id, judgments in qrels.items():
            subset_qrels = {artifact_id: grade for artifact_id, grade in judgments.items()
                            if artifact_types.get(artifact_id, "unknown") == kind}
            if not subset_qrels:
                continue
            ranking = [artifact_id for artifact_id in rankings.get(query_id, [])
                       if artifact_types.get(artifact_id, "unknown") == kind]
            per_query[query_id] = evaluate_ir_measures(ranking, subset_qrels)
        result[kind] = {"N": sum(artifact_types.get(artifact_id, "unknown") == kind
                                  for rows in qrels.values() for artifact_id in rows),
                        "judged_queries": len(per_query), "aggregate": _mean_metrics(per_query),
                        "per_query": per_query}
    return result
