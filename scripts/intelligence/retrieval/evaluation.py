from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ..store import JsonlStore
from .bm25 import BM25Retriever
from .corpus import build_snapshot
from .dense import DenseRetriever, SentenceTransformerBackend
from .engine import RetrievalEngine, infer_topic_ids
from .expansion import expand_query
from .graph import GraphRetriever
from .registry import RetrieverRegistry
from .request import make_request
from .topic import TopicRetriever


TOPIC_BY_CATEGORY = {
    "Search Agent": "topic-search-agent", "Agentic RL": "topic-agentic-rl", "Memory": "topic-memory",
    "RAG": "topic-rag", "Agent Harness": "topic-agent-harness", "Verifier / Reward": "topic-verifier",
    "Inference Serving": "topic-inference-serving", "Multimodal Agent": "topic-multimodal-models-and-world-models",
    "Post-training": "topic-post-training-and-alignment", "AI for Science": "topic-domain-specific-llms-and-ai-for-science",
}


def build_blind_label_pack(store_dir: str | Path, runtime_dir: str | Path, *,
                           queries_path: str | Path, output_dir: str | Path,
                           model: str = "Qwen/Qwen3-Embedding-0.6B", revision: str | None = None,
                           device: str | None = None) -> dict[str, Any]:
    store = JsonlStore(store_dir)
    snapshot = build_snapshot(store)
    registry = RetrieverRegistry()
    registry.register(BM25Retriever())
    registry.register(DenseRetriever(SentenceTransformerBackend(model, revision=revision, device=device)))
    registry.register(GraphRetriever(str(store_dir)))
    registry.register(TopicRetriever())
    engine = RetrievalEngine(snapshot, registry, store_dir=str(store_dir), runtime_dir=str(runtime_dir))
    built = engine.build(["bm25", "dense", "graph", "topic"])
    if built.get("failed_routes"):
        raise RuntimeError("label pool requires all local route indexes to build")
    query_source = json.loads(Path(queries_path).read_text(encoding="utf-8"))
    artifact_rows = {str(item["artifact_id"]): item for item in store.iter_records("artifact")}
    docs = snapshot.by_id()
    query_rows = []
    for query in query_source.get("queries", []):
        topic_ids = sorted(set(infer_topic_ids(str(query["query"]))) |
                           ({TOPIC_BY_CATEGORY[str(query["category"])]} if query.get("category") in TOPIC_BY_CATEGORY else set()))
        result = engine.search(
            make_request(
                str(query["query"]), topic_ids=topic_ids,
                filters={"corpus_profile": "research-default"}, top_k=10,
                expanded_terms=expand_query(str(query["query"])),
            ),
            routes=["bm25", "dense", "graph-expand", "topic"], route_depth=50, persist=False,
        )
        route_rows = result.get("route_candidates", {})
        candidates = blind_pool_candidates(str(query["query_id"]), route_rows, result.get("candidates", []), docs, artifact_rows)
        query_rows.append({
            "query_id": str(query["query_id"]), "category": str(query["category"]),
            "specificity": str(query["specificity"]), "query": str(query["query"]),
            "query_provenance": str(query["query_provenance"]), "label_source": None,
            "reviewed_by": None, "reviewed_at": None, "candidates": candidates,
        })
    benchmark_hash = _hash({"benchmark_id": "dev-v1", "queries": query_rows})
    pack = {
        "schema": "bubblevan/retrieval-blind-label-pack/v1", "benchmark_id": "dev-v1",
        "status": "draft", "corpus_hash": snapshot.corpus_hash, "benchmark_hash": benchmark_hash,
        "as_of": "2026-09-28T23:59:59Z", "relevance_scale": {"0": "irrelevant", "1": "relevant/useful", "2": "directly important"},
        "qrels": [], "qrels_reviewed_by": None, "qrels_reviewed_at": None, "queries": query_rows,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dev-v1-label-pack.json").write_text(json.dumps(pack, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    _write_markdown(pack, out / "dev-v1-label-pack.md")
    qrels = {"schema": "bubblevan/retrieval-human-qrels/v1", "benchmark_id": "dev-v1", "status": "draft",
             "reviewed_by": None, "reviewed_at": None, "qrels": []}
    (out / "dev-v1-qrels.json").write_text(json.dumps(qrels, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {"benchmark_id": "dev-v1", "status": "draft", "query_count": len(query_rows),
            "pool_candidates": sum(len(item["candidates"]) for item in query_rows),
            "corpus_hash": snapshot.corpus_hash, "benchmark_hash": benchmark_hash,
            "json_path": str(out / "dev-v1-label-pack.json"), "markdown_path": str(out / "dev-v1-label-pack.md"),
            "qrels_complete": False}


def evaluate_human_qrels(runs: Mapping[str, Mapping[str, list[str]]], qrels: Mapping[str, Mapping[str, int]],
                         artifact_types: Mapping[str, str], *, benchmark_corpus_hash: str | None = None,
                         current_corpus_hash: str | None = None) -> dict[str, Any]:
    from .metrics import evaluate_ranking, evaluate_routes

    if not qrels or any(grade not in (0, 1, 2) for rows in qrels.values() for grade in rows.values()):
        raise ValueError("human qrels must contain only grades 0, 1, or 2")
    if benchmark_corpus_hash and current_corpus_hash and benchmark_corpus_hash != current_corpus_hash:
        raise ValueError("benchmark corpus hash does not match the current corpus")
    route_metrics: dict[str, Any] = {}
    for route in sorted({route for rows in runs.values() for route in rows}):
        per_query = {}
        for query_id, route_rows in runs.items():
            ranking = route_rows.get(route, [])
            judged = qrels.get(query_id, {})
            metrics = evaluate_ranking(ranking, judged)
            returned = list(ranking[:10])
            per_query[query_id] = {**metrics, "EmptyResult@10": int(not returned),
                                   "UntitledResult@10": sum(not artifact_types.get(item) for item in returned)}
        route_metrics[route] = per_query
    route_contribution = {}
    for query_id, route_rows in runs.items():
        if query_id in qrels:
            route_contribution[query_id] = evaluate_routes(route_rows, qrels[query_id], k=20)
    type_slices = {}
    for route in sorted(route_metrics):
        type_slices[route] = {}
        for kind in sorted(set(artifact_types.values())):
            by_query = {}
            for query_id, route_rows in runs.items():
                judged = {aid: grade for aid, grade in qrels.get(query_id, {}).items() if artifact_types.get(aid) == kind}
                if not judged:
                    continue
                ranking = [aid for aid in route_rows.get(route, []) if artifact_types.get(aid) == kind]
                by_query[query_id] = {"N": len(judged), **evaluate_ranking(ranking, judged)}
            type_slices[route][kind] = {"judged_queries": len(by_query), "by_query": by_query}
    return {"status": "human-reviewed", "routes": route_metrics, "route_contribution": route_contribution,
            "judged_queries": len(qrels), "type_slices": type_slices}


def blind_pool_candidates(query_id: str, route_rows: Mapping[str, list[dict[str, Any]]], fused_rows: list[dict[str, Any]],
                          documents: Mapping[str, Any], artifacts: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    ids: set[str] = set()
    for route in ("bm25", "dense", "graph-expand", "topic"):
        ids.update(str(item["artifact_id"]) for item in route_rows.get(route, [])[:10] if item.get("artifact_id"))
    ids.update(str(item["artifact_id"]) for item in fused_rows[:10] if item.get("artifact_id"))
    result = []
    for artifact_id in ids:
        document = documents.get(artifact_id)
        artifact = artifacts.get(artifact_id)
        if not document or not artifact:
            continue
        result.append({"artifact_id": artifact_id, "title": document.title,
                       "artifact_type": document.artifact_type, "summary_excerpt": document.body[:600].strip(),
                       "canonical_url": str(artifact.get("canonical_url") or ""),
                       "published_at": document.published_at})
    return sorted(result, key=lambda item: hashlib.sha256(f"{query_id}:{item['artifact_id']}".encode()).hexdigest())


def require_corpus_match(benchmark: Mapping[str, Any], current_corpus_hash: str) -> None:
    if str(benchmark.get("corpus_hash") or "") != str(current_corpus_hash):
        raise ValueError("benchmark corpus hash does not match the current corpus")


def _write_markdown(pack: Mapping[str, Any], path: Path) -> None:
    lines = ["# DEV-v1 Blind Relevance Label Pack", "", f"Status: **{pack['status']}**",
             f"Corpus hash: `{pack['corpus_hash']}`", "", "Assign each candidate a grade: 0 irrelevant, 1 useful, 2 directly important.",
             "The candidate order is shuffled deterministically. Retrieval route, rank, and score are intentionally omitted.", ""]
    for query in pack["queries"]:
        lines.extend([f"## {query['category']} — {query['specificity']}", "", query["query"], "",
                      f"Query provenance: `{query['query_provenance']}`", ""])
        for candidate in query["candidates"]:
            summary = " ".join(str(candidate.get("summary_excerpt") or "No summary available").split())
            lines.extend([f"### {candidate['title'] or '(no title)'}", "",
                          f"- Artifact ID: `{candidate['artifact_id']}`",
                          f"- Type: {candidate['artifact_type']}",
                          f"- Published: {candidate['published_at'] or 'unknown'}",
                          f"- URL: {candidate['canonical_url'] or 'unavailable'}",
                          f"- Summary: {summary}",
                          "- Human grade (0/1/2):", ""])
        lines.append("---")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
