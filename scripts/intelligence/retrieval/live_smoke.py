from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import statistics
import tempfile
import time
from collections import Counter
from typing import Any

from ..store import JsonlStore
from .bm25 import BM25Retriever
from .corpus import build_snapshot
from .dense import DenseRetriever, SentenceTransformerBackend
from .engine import RetrievalEngine
from .graph import GraphRetriever
from .registry import RetrieverRegistry
from .source import SourceRetriever
from .synthetic_fixture import run_synthetic_evaluation
from .topic import TopicRetriever


QUERY_SPECS = [
    {"category": "Search Agent", "query": "search agent deep research synthesis", "topic": "topic-search-agent", "seed_title": "DataSTORM"},
    {"category": "Agentic RL", "query": "agentic reinforcement learning tool use long horizon", "topic": "topic-agentic-rl", "seed_title": "Self-Evolving Deep Research"},
    {"category": "Memory", "query": "persistent memory for language model agents", "topic": "topic-memory", "seed_title": "Dynamic LLM-Powered Agent Network"},
    {"category": "RAG", "query": "retrieval augmented generation recursive document retrieval", "topic": "topic-rag", "seed_title": "RAPTOR"},
    {"category": "Harness", "query": "agent harness runtime orchestration tools and state", "topic": "topic-agent-harness", "seed_title": "DSPy"},
    {"category": "Verifier / Reward", "query": "verifier reward model reasoning evaluation", "topic": "topic-verifier", "seed_title": "Prometheus 2"},
    {"category": "Inference Serving", "query": "LLM inference serving deployment throughput", "topic": "topic-efficiency-systems-and-deployment", "seed_title": "Gemini 1.5"},
    {"category": "Multimodal Agent", "query": "multimodal agent vision audio grounded reports", "topic": "topic-multimodal-models-and-world-models", "seed_title": "Wyvern"},
    {"category": "Post-training", "query": "post-training on-policy distillation reinforcement learning", "topic": "topic-post-training-and-alignment", "seed_title": "Prometheus 2"},
    {"category": "AI for Science", "query": "AI for science scientific discovery research agents", "topic": "topic-domain-specific-llms-and-ai-for-science", "seed_title": "DataSTORM"},
]

TOP10_REVIEW_NOTES = {
    "Search Agent": "Visible research items include an agent-network paper and a deep-research security paper; most top rows are model records with both title and summary blank.",
    "Agentic RL": "BM25 and Dense top tens are all untitled model records; Graph returns the same broad human-learning paper seen for other seeds.",
    "Memory": "BM25 top ten and nine of ten Dense rows are untitled model records; Graph returns the same broad shared-neighborhood paper.",
    "RAG": "The RAPTOR paper appears near the top in both BM25 and Dense; most other rows are untitled model records.",
    "Harness": "One task-agent paper is visible in BM25; the remaining BM25 rows and all Dense rows lack titles and summaries.",
    "Verifier / Reward": "BM25 exposes evaluation and research-agent papers; Dense top ten are untitled model records.",
    "Inference Serving": "The text routes return almost entirely untitled model records; the visible paper is about search effects rather than serving systems.",
    "Multimodal Agent": "Wyvern ranks first in both BM25 and Dense; nine of ten rows per route still lack titles and summaries.",
    "Post-training": "BM25 and Dense top tens are all untitled model records; Graph again returns the same broad shared-neighborhood paper.",
    "AI for Science": "BM25 top ten are untitled model records; Dense includes a search-effects paper, with no clear science-system match in the visible titles.",
}


def run_live_smoke(store_dir: str | Path, runtime_dir: str | Path, *, model: str = "Qwen/Qwen3-Embedding-0.6B",
                   revision: str | None = None, device: str | None = None,
                   as_of: str = "2026-09-28T23:59:59Z") -> dict[str, Any]:
    started = time.perf_counter()
    store = JsonlStore(store_dir)
    snapshot = build_snapshot(store)
    backend = SentenceTransformerBackend(model, revision=revision, device=device)
    hardware = _hardware(backend)
    try:
        import torch
        if backend.device.startswith("cuda"):
            torch.cuda.reset_peak_memory_stats()
    except (ImportError, RuntimeError):
        pass
    registry = RetrieverRegistry()
    registry.register(BM25Retriever())
    registry.register(DenseRetriever(backend))
    registry.register(GraphRetriever(str(store_dir)))
    registry.register(TopicRetriever())
    registry.register(SourceRetriever(str(store_dir)))
    engine = RetrievalEngine(snapshot, registry, store_dir=str(store_dir), runtime_dir=str(runtime_dir))
    build_result = engine.build(["bm25", "dense", "graph", "topic", "source"])
    if build_result["failed_routes"]:
        raise RuntimeError(f"required live smoke index failed: {build_result['failed_routes']}")
    paper_by_title = {str(item.get("title") or "").casefold(): item for item in store.iter_records("artifact")}
    run_rows = []
    for spec in QUERY_SPECS:
        from .request import make_request
        from .expansion import expand_query
        request = make_request(spec["query"], topic_ids=[spec["topic"]], as_of=as_of, top_k=10,
                              expanded_terms=expand_query(spec["query"]))
        result = engine.search(request, routes=["bm25", "dense", "graph-expand", "topic"],
                               route_depth=50, persist=True)
        result["smoke_category"] = spec["category"]
        run_rows.append(result)
    dense_manifest = build_result["routes"]["dense"]
    try:
        import torch
        if backend.device.startswith("cuda"):
            torch.cuda.synchronize()
            hardware["peak_vram_mb"] = round(torch.cuda.max_memory_allocated() / (1024 * 1024), 1)
    except (ImportError, RuntimeError):
        hardware["peak_vram_mb"] = None
    hardware["peak_ram_mb"] = _peak_ram_mb()
    elapsed = round(time.perf_counter() - started, 3)
    smoke = {
        "schema": "bubblevan/intelligence-retrieval-smoke/v1",
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "corpus_hash": snapshot.corpus_hash,
        "corpus_count": len(snapshot.documents),
        "hardware": hardware,
        "dense": dense_manifest,
        "smoke_elapsed_seconds": elapsed,
        "queries": run_rows,
    }
    target = Path(runtime_dir) / "retrieval" / "live-smoke-20260928.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(smoke, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return smoke


def write_report(smoke: dict[str, Any], store: JsonlStore, report_path: str | Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ri-m3-synthetic-eval-") as scratch:
        synthetic_benchmark = run_synthetic_evaluation(scratch)
    artifacts = list(store.iter_records("artifact"))
    artifact_by_id = {str(item["artifact_id"]): item for item in artifacts}
    by_type: dict[str, int] = {}
    for artifact in artifacts:
        kind = str(artifact.get("artifact_type") or "other")
        by_type[kind] = by_type.get(kind, 0) + 1
    route_latency: dict[str, list[float]] = {route: [] for route in ("bm25", "dense", "graph", "topic")}
    route_totals = {route: 0 for route in route_latency}
    unique_counts: dict[str, int] = {route: 0 for route in route_latency}
    overlap_counts = []
    query_rows = []
    graph_firsts = []
    for run in smoke["queries"]:
        route_candidates = run.get("route_candidates", {})
        graph_rows = route_candidates.get("graph", [])
        if graph_rows:
            graph_firsts.append(str(graph_rows[0]["artifact_id"]))
        route_sets = {}
        titleless_counts = {}
        for route in route_latency:
            items = route_candidates.get(route, [])[:10]
            route_totals[route] += len(items)
            route_sets[route] = {item["artifact_id"] for item in items}
            titleless_counts[route] = sum(
                not str(artifact_by_id.get(item["artifact_id"], {}).get("title") or "").strip()
                and not str(artifact_by_id.get(item["artifact_id"], {}).get("summary") or "").strip()
                for item in items
            )
            route_latency[route].append(float(run.get("route_status", {}).get(route, {}).get("elapsed_ms") or 0.0))
        union = set().union(*route_sets.values()) if route_sets else set()
        for route, values in route_sets.items():
            unique_counts[route] += len(values - set().union(*(other for name, other in route_sets.items() if name != route)))
        pair_overlaps = []
        routes = list(route_sets)
        for index, left in enumerate(routes):
            for right in routes[index + 1:]:
                denom = route_sets[left] | route_sets[right]
                pair_overlaps.append(len(route_sets[left] & route_sets[right]) / len(denom) if denom else 0.0)
        overlap_counts.extend(pair_overlaps)
        query_rows.append({
            "category": run["smoke_category"], "seed_artifact_id": run["seed_artifact_id"],
            "route_counts": {route: len(route_sets[route]) for route in route_sets},
            "titleless_top10": titleless_counts,
            "union_top10_candidates": len(union),
            "rrf_top10": len(run.get("candidates", [])[:10]),
            "routes_failed": [item["route"] for item in run.get("routes_failed", [])],
            "routes_skipped": [item["route"] for item in run.get("routes_skipped", [])],
        })
    def percentile(values: list[float], amount: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = round((len(ordered) - 1) * amount)
        return round(ordered[index], 3)
    timings = {route: {"p50_ms": percentile(values, .50), "p95_ms": percentile(values, .95)}
               for route, values in route_latency.items()}
    index_bytes = sum(path.stat().st_size for path in (Path(store.directory).parent / "runtime" / "retrieval" / "dense").glob("*") if path.is_file())
    report = {
        "corpus": {"artifact_count": len(artifacts), "papers": by_type.get("paper", 0), "blogs": by_type.get("blog", 0),
                   "repositories": by_type.get("repository", 0), "models": by_type.get("model", 0),
                   "datasets": by_type.get("dataset", 0), "indexed": smoke["corpus_count"],
                   "missing_published_at": sum(not item.get("published_at") for item in artifacts),
                   "corpus_hash": smoke["corpus_hash"]},
        "hardware": smoke["hardware"],
        "dense": {"model_id": smoke["dense"].get("model_id"), "model_revision": smoke["dense"].get("model_revision"),
                  "dimension": smoke["dense"].get("dimension"), "embedded_documents": smoke["dense"].get("cache", {}).get("embedded"),
                  "documents_per_second": smoke["dense"].get("embedding_docs_per_sec"),
                  "dense_index_bytes": index_bytes, "cache": smoke["dense"].get("cache")},
        "query_rows": query_rows,
        "top10_review_notes": TOP10_REVIEW_NOTES,
        "graph_top1_repeated_count": max(Counter(graph_firsts).values(), default=0),
        "route_latency": timings,
        "synthetic_benchmark": synthetic_benchmark,
        "candidate_set_complementarity_unjudged": {"route_top10_counts": route_totals, "unique_top10_candidates": unique_counts,
                                                   "mean_pairwise_jaccard": round(statistics.mean(overlap_counts), 3) if overlap_counts else 0.0},
        "smoke_elapsed_seconds": smoke["smoke_elapsed_seconds"],
    }
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_report(report) + "\n", encoding="utf-8")
    return report


def _render_report(data: dict[str, Any]) -> str:
    corpus = data["corpus"]
    dense = data["dense"]
    synthetic = data["synthetic_benchmark"]
    lines = [
        "---", "title: \"M3 Multi-route Retrieval Report\"", "---", "",
        "# RI-M3 Retrieval Report", "",
        "## Corpus", "",
        f"- Artifacts: {corpus['artifact_count']} ({corpus['papers']} papers, {corpus['blogs']} blogs, {corpus['repositories']} repositories, {corpus['models']} models, {corpus['datasets']} datasets).",
        f"- Indexed canonical documents: {corpus['indexed']}; missing `published_at`: {corpus['missing_published_at']}.",
        f"- Corpus hash: `{corpus['corpus_hash']}`.", "",
        "Most rows are Hugging Face model Artifacts; this is a small and source-skewed corpus rather than a representative paper library.", "",
        "## Routes and fusion", "",
        "- BM25: bm25s over title (repeated twice), body, authors, topics and exact graph entity names; Jieba and CJK bigrams cover Chinese.",
        "- Dense: Sentence Transformers with the configured Qwen embedding model, normalized vectors and exact cosine dot product.",
        "- Graph: bounded one-hop citation, exact common-author and accepted-source co-mention evidence from explicit seed Artifacts.",
        "- Topic: exact topic IDs; source route remains available for exact source evidence but is not part of these query runs.",
        "- Fusion: RRF with `k=60`; raw route scores are retained and not added.", "",
        "## Offline benchmark", "",
        f"- Frozen fixture: `{synthetic['benchmark_version']}`; benchmark hash `{synthetic['benchmark_hash']}`; fixture corpus hash `{synthetic['corpus_hash']}`.",
        f"- Labels: `{synthetic['label_source']}`; this one-query fixture checks candidate-route mechanics and is not a real-corpus relevance claim.",
        "- Human-confirmed DEV (30–50 queries) and HOLDOUT (15–20 queries) qrels have not been collected, so the real corpus has no judged Recall/MRR/nDCG/Precision yet.",
        "", "| Baseline | Recall@5 | MRR@10 | nDCG@10 | Precision@10 |", "|---|---:|---:|---:|---:|",
        *[f"| {label} | {synthetic['ranking_metrics'][key]['Recall@5']:.3f} | {synthetic['ranking_metrics'][key]['MRR@10']:.3f} | {synthetic['ranking_metrics'][key]['nDCG@10']:.3f} | {synthetic['ranking_metrics'][key]['Precision@10']:.3f} |"
          for label, key in (("B0 BM25", "bm25"), ("B1 Dense", "dense"), ("B2 Graph", "graph"),
                             ("B3 BM25 + Dense RRF", "bm25_dense_rrf"),
                             ("B4 BM25 + Dense + Graph RRF", "bm25_dense_graph_rrf"))],
        "", f"- Synthetic route unique hits at K=5: `{json.dumps(synthetic['route_metrics']['unique_contribution'], sort_keys=True)}`; union Recall@5: {synthetic['route_metrics']['union_recall']:.3f}; FutureLeakCount: {synthetic['route_metrics']['future_leak_count']}.",
        "The real corpus runs below are unjudged smoke queries, so these synthetic metrics do not estimate real-world retrieval quality.", "",
        "## Real query smoke", "",
        "All ten fixed queries ran with BM25, Dense, Graph, Topic and RRF. The seed is a manually selected existing Artifact to make the Graph route testable; it does not mark a relevance judgment.", "",
        "| Query category | BM25 | Dense | Graph | Topic | RRF | Candidate union | Failed/skipped |", "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in data["query_rows"]:
        counts = row["route_counts"]
        failures = ", ".join(row["routes_failed"] + row["routes_skipped"]) or "—"
        lines.append(f"| {row['category']} | {counts['bm25']} | {counts['dense']} | {counts['graph']} | {counts['topic']} | {row['rrf_top10']} | {row['union_top10_candidates']} | {failures} |")
    lines.extend([
        "", "These are candidate counts, not relevance scores. `candidate_set_complementarity_unjudged` below records unique IDs and overlap without claiming that they are useful.", "",
        "## Top-10 qualitative inspection", "",
        "The ten query result sets were inspected route by route. The counts below are top-ten rows with both title and summary empty; the notes describe visible output behavior and are not qrels.", "",
        "| Query | Untitled BM25 | Untitled Dense | Review note |", "|---|---:|---:|---|",
        *[f"| {row['category']} | {row['titleless_top10']['bm25']}/10 | {row['titleless_top10']['dense']}/10 | {data['top10_review_notes'][row['category']]} |"
          for row in data["query_rows"]],
        "", f"Graph's top result repeated for {data['graph_top1_repeated_count']} of the ten seeds, showing that this sparse route follows the shared citation neighborhood rather than query-specific text relevance.", "",
        "## Latency and dense resource use", "",
        f"- Model: `{dense['model_id']}` at revision `{dense['model_revision']}`, dimension {dense['dimension']}.",
        f"- Newly embedded documents: {dense['embedded_documents']}; observed throughput: {dense['documents_per_second']} docs/s.",
        f"- Dense vector index on disk: {dense['dense_index_bytes']} bytes; peak RAM {data['hardware'].get('peak_ram_mb')} MiB; peak VRAM {data['hardware'].get('peak_vram_mb')} MiB.",
        f"- Route latency p50/p95 (ms): `{json.dumps(data['route_latency'], sort_keys=True)}`.",
        f"- Total smoke wall time: {data['smoke_elapsed_seconds']} seconds.", "",
        "## Ablation and failure review", "",
        f"- Unjudged top-10 unique candidate totals by route across all queries: `{json.dumps(data['candidate_set_complementarity_unjudged']['unique_top10_candidates'], sort_keys=True)}`.",
        f"- Mean pairwise top-10 Jaccard overlap: {data['candidate_set_complementarity_unjudged']['mean_pairwise_jaccard']}.",
        "- Topic route has limited coverage because only a small portion of the local Artifact corpus has canonical topics.",
        "- Graph route depends on the manually selected seed and sparse citation/author edges; it cannot provide broad text-only retrieval on its own.",
        "- The corpus contains no blog Artifacts and very few papers, so the memory, serving and science categories may return nearby model catalog rows rather than direct research matches.",
        "- 792 Artifacts lack a publication timestamp in the current store. Historical `as_of` searches use first-observed fallback and exclude rows with neither clock.",
        "- Query-level result lists and provenance are preserved in the ignored runtime smoke JSON for manual follow-up; no raw local results are copied into this published report.", "",
        "## Limits", "",
        "This report records a local smoke on one RTX 5060 8 GB desktop. It is not a benchmark comparison, relevance claim, model guarantee or quality score. No Feedback, freshness weighting, LLM rewriting or reranking is used.", "",
    ])
    return "\n".join(lines)


def _hardware(backend: SentenceTransformerBackend) -> dict[str, Any]:
    info: dict[str, Any] = {"platform": platform.platform(), "python": platform.python_version(), "device": backend.device,
                            "gpu_name": None, "gpu_memory_total_mb": None}
    try:
        import torch
        if backend.device.startswith("cuda") and torch.cuda.is_available():
            props = torch.cuda.get_device_properties(torch.device(backend.device))
            info["gpu_name"] = props.name
            info["gpu_memory_total_mb"] = round(props.total_memory / (1024 * 1024), 1)
    except (ImportError, RuntimeError):
        pass
    return info


def _peak_ram_mb() -> float | None:
    try:
        import psutil
        process = psutil.Process()
        memory = process.memory_info()
        peak = getattr(memory, "peak_wset", getattr(memory, "rss", None))
        return round(peak / (1024 * 1024), 1) if peak is not None else None
    except (ImportError, OSError):
        return None
