from __future__ import annotations

from collections import defaultdict
from collections import Counter
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
from .pool_coverage import BASELINES, official_coverage_gate


def run_frozen_dev(pack: Mapping[str, Any], store: JsonlStore, runtime_dir: str | Path, *,
                   model: str = "Qwen/Qwen3-Embedding-0.6B", revision: str | None = None,
                   device: str | None = None, include_metrics: bool = True) -> dict[str, Any]:
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
    active_provenance = retrieval_provenance(runtime_dir)
    expected_provenance = pack.get("retrieval_provenance")
    if expected_provenance is not None and expected_provenance != active_provenance:
        raise ValueError("frozen DEV retrieval provenance does not match current indexes and route configuration")
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
    if not include_metrics:
        return {
            "schema": "bubblevan/retrieval-pool-rankings/v1", "status": "pool_built",
            "benchmark_hash": pack["benchmark_hash"], "corpus_hash": snapshot.corpus_hash,
            "query_count": len(pack["queries"]), "retrieval_provenance": active_provenance,
            "rankings": rankings, "topic_rankings": topic_rows,
        }
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
    coverage_gate = official_coverage_gate({baseline: baselines[baseline]["aggregate"]
                                            for baseline in BASELINES})
    official_complete = bool(coverage_gate["passed"])
    quality_issues = {(str(item.get("query_id") or ""), str(item.get("artifact_id") or "")):
                      str(item.get("quality_issue") or "none")
                      for item in pack.get("quality_issues", [])}
    issue_counts = Counter(quality_issues.values())
    grade_by_pair = {(str(item["query_id"]), str(item["artifact_id"])): int(item["grade"])
                     for item in pack.get("qrels", [])}
    insufficient_distribution = Counter(
        grade_by_pair[identity] for identity, issue in quality_issues.items()
        if issue == "insufficient_metadata" and identity in grade_by_pair
    )
    return {
        "schema": "bubblevan/retrieval-m3-2-1-evaluation/v1",
        "status": "completed" if official_complete else "incomplete_judgment_pool",
        "comparison_eligibility": "official" if official_complete else "exploratory_only",
        "official_coverage_gate": coverage_gate,
        "warnings": [] if official_complete else [
            "Judged@10 and Judged@20 must equal 1.0 for B0–B4 before official comparison."
        ],
        "retrieval_provenance": active_provenance,
        "benchmark_hash": pack["benchmark_hash"], "corpus_hash": snapshot.corpus_hash,
        "query_count": len(pack["queries"]), "judged_pairs": sum(map(len, qrels_by_query.values())),
        "judge": pack.get("judge"),
        "judge_consistency_audit": {"status": "not_run", "reason": "optional second-judge audit not performed"},
        "quality_review": {
            "quality_issue_count": sum(count for issue, count in issue_counts.items() if issue != "none"),
            "quality_issue_counts": dict(sorted(issue_counts.items())),
            "insufficient_metadata_count": issue_counts.get("insufficient_metadata", 0),
            "grade_distribution_among_insufficient_metadata": {
                str(grade): insufficient_distribution.get(grade, 0) for grade in (0, 1, 2)
            },
        },
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
    lines = [f"# GPT-6 Luna-judged DEV {pack.get('benchmark_id', 'benchmark')} Error Analysis", "",
             "This is a model-judged development relevance analysis, not human ground truth.",
             f"Comparison eligibility: `{result.get('comparison_eligibility', 'exploratory_only')}`", "",
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
        raise ValueError("DEV evaluation requires a frozen development benchmark JSON")
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


def retrieval_provenance(runtime_dir: str | Path) -> dict[str, Any]:
    """Return the frozen route, index, and model identities used by M3.2 evaluation."""
    runtime = Path(runtime_dir) / "retrieval"
    dense = _read_manifest(runtime / "dense" / "manifest.json")
    bm25 = _read_manifest(runtime / "bm25" / "manifest.json")
    repo_root = Path(__file__).resolve().parents[3]
    retrieval_sources = (
        "bm25.py", "dense.py", "engine.py", "expansion.py", "fusion.py",
        "graph.py", "request.py", "topic.py",
    )
    code_digest = hashlib.sha256()
    for name in retrieval_sources:
        path = repo_root / "scripts" / "intelligence" / "retrieval" / name
        code_digest.update(name.encode("utf-8"))
        code_digest.update(path.read_bytes())
    return {
        "corpus_hash": dense.get("corpus_hash"),
        "baselines": {
            "B0": {"routes": ["bm25"]},
            "B1": {"routes": ["dense"]},
            "B2": {"routes": ["graph-expand"]},
            "B3": {"routes": ["bm25", "dense"], "fusion": "rrf"},
            "B4": {"routes": ["bm25", "dense", "graph-expand"], "fusion": "rrf"},
        },
        "route_depth": 50,
        "top_k": 20,
        "filters": {"corpus_profile": "research-default"},
        "rrf_k": 60,
        "dense": {key: dense.get(key) for key in (
            "model_id", "model_revision", "version", "dimension", "normalize_embeddings",
            "query_prompt", "similarity",
        )},
        "bm25": {key: bm25.get(key) for key in ("version", "library_version", "config")},
        "retrieval_source_sha256": code_digest.hexdigest(),
    }


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"retrieval manifest is unavailable or malformed: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"retrieval manifest is not an object: {path}")
    return value


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
