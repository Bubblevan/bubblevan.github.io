from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .corpus import CorpusSnapshot, RetrievalDocument


ARTIFACT_A = "art-" + "1" * 24
ARTIFACT_D = "art-" + "2" * 24
ARTIFACT_E = "art-" + "3" * 24
ARTIFACT_SEED = "art-" + "4" * 24


def build_synthetic_snapshot() -> CorpusSnapshot:
    """Stable five-document fixture for candidate-route and fusion sanity checks."""
    rows = (
        _document(ARTIFACT_A, "Search Agent reinforcement learning", "retrievalsignal distractor distractor distractor"),
        _document(ARTIFACT_D, "semantic twin", "semantic twin"),
        _document(ARTIFACT_E, "Citation neighbor", "structural-only candidate"),
        _document("art-" + "5" * 24, "Agent memory", "memory for assistants"),
        _document(ARTIFACT_SEED, "Graph seed", "seed document"),
    )
    documents = tuple(sorted(rows, key=lambda item: item.artifact_id))
    semantic = [item.to_dict() for item in documents]
    corpus_hash = hashlib.sha256(_canonical(semantic)).hexdigest()
    source_tree_hash = hashlib.sha256(b"ri-m3-synthetic-source-tree-v1").hexdigest()
    return CorpusSnapshot(documents, corpus_hash, source_tree_hash)


def run_synthetic_evaluation(runtime_dir: str | Path) -> dict[str, Any]:
    """Run the frozen fixture end to end without loading a live model or network client."""
    from .benchmark import load_benchmark
    from .bm25 import BM25Retriever
    from .dense import DenseRetriever, DeterministicFakeEmbedding
    from .fusion import reciprocal_rank_fusion
    from .graph import GraphRetriever
    from .metrics import evaluate_ranking, evaluate_routes, future_leak_count
    from .request import make_request
    from ..graph.models import make_edge
    from ..graph.store import GraphStore

    root = Path(runtime_dir)
    store_dir = root / "synthetic-store"
    snapshot = build_synthetic_snapshot()
    GraphStore(store_dir).add_edge(make_edge(
        ARTIFACT_SEED, "cites", ARTIFACT_E,
        {"evidence_type": "exact_provider_metadata", "provider": "fixture",
         "provider_record_id": "seed-cites-e", "observed_at": "2026-09-28T00:00:00Z"},
    ))
    dense = DenseRetriever(DeterministicFakeEmbedding(2, token_vectors={
        "retrievalsignal": [1, 0], "semantictwin": [1, 0], "twin": [1, 0],
        **{token: [0, 1] for token in (
            "distractor", "search", "agent", "reinforcement", "learning", "citation", "neighbor",
            "structural", "only", "candidate", "memory", "for", "assistants", "unrelated", "computer",
            "vision", "dataset", "graph", "seed", "document",
        )},
    }))
    routes = {"bm25": BM25Retriever(), "dense": dense, "graph": GraphRetriever(str(store_dir))}
    for route in routes.values():
        route.build(snapshot, str(root / "indexes"))
    request = make_request("retrievalsignal", seed_artifact_ids=[ARTIFACT_SEED], as_of="2026-09-28T00:00:00Z", top_k=1)
    rows = {
        name: route.retrieve(request, documents=snapshot.documents, top_k=request.top_k).candidates
        for name, route in routes.items()
    }
    bm25_dense = reciprocal_rank_fusion({name: rows[name] for name in ("bm25", "dense")},
                                        request_id=request.request_id, top_k=5)
    fused = reciprocal_rank_fusion(rows, request_id=request.request_id, top_k=5)
    benchmark_path = Path(__file__).resolve().parents[3] / "data" / "intelligence" / "eval" / "retrieval" / "synthetic-v1.json"
    benchmark = load_benchmark(benchmark_path, snapshot.by_id())
    query = benchmark["queries"][0]
    ranking_metrics = {route: evaluate_ranking([item["artifact_id"] for item in values], query["qrels"])
                       for route, values in rows.items()}
    ranking_metrics.update({
        "bm25_dense_rrf": evaluate_ranking([item["artifact_id"] for item in bm25_dense], query["qrels"]),
        "bm25_dense_graph_rrf": evaluate_ranking([item["artifact_id"] for item in fused], query["qrels"]),
    })
    route_metrics = evaluate_routes({route: [item["artifact_id"] for item in values] for route, values in rows.items()},
                                    query["qrels"], k=5)
    route_metrics["future_leak_count"] = future_leak_count(
        [item["artifact_id"] for values in [*rows.values(), fused] for item in values], snapshot.by_id(), query["as_of"],
    )
    return {
        "benchmark_version": benchmark["version"], "benchmark_hash": benchmark["benchmark_hash"],
        "corpus_hash": snapshot.corpus_hash, "query_id": query["query_id"],
        "label_source": query["provenance"]["label_source"],
        "route_top1": {route: values[0]["artifact_id"] if values else None for route, values in rows.items()},
        "fused_ids": [item["artifact_id"] for item in fused],
        "bm25_dense_fused_ids": [item["artifact_id"] for item in bm25_dense],
        "ranking_metrics": ranking_metrics, "route_metrics": route_metrics,
    }


def _document(artifact_id: str, title: str, body: str) -> RetrievalDocument:
    return RetrievalDocument(
        artifact_id=artifact_id,
        artifact_type="paper",
        title=title,
        body=body,
        authors=(),
        organizations=(),
        topics=(),
        published_at="2026-09-01T00:00:00Z",
        first_observed_at="2026-09-02T00:00:00Z",
        source_ids=(),
        graph_entities=(),
        observation_excerpts=(),
        language="en",
        freshness_basis="published_at",
    )


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
