from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import hashlib
import json
from typing import Any

from ..repositories.artifacts import ArtifactRepository
from ..retrieval.corpus import build_snapshot
from ..store import JsonlStore
from .m32_evaluation import run_frozen_dev
from .model_judging import build_judge_input, prompt_hash
from .pool_coverage import build_evaluation_pool, judgment_coverage, pool_delta, pool_pairs


def build_model_judge_pool(*, previous_benchmark_path: str | Path, store: JsonlStore,
                           runtime_dir: str | Path, output_dir: str | Path,
                           prompt_path: str | Path, model: str = "Qwen/Qwen3-Embedding-0.6B",
                           revision: str | None = None, device: str | None = None) -> dict[str, Any]:
    """Rerun the frozen queries, save the exact B0–B4 top-20 pool, and export only new pairs."""
    previous_path = Path(previous_benchmark_path)
    previous = _read_object(previous_path)
    snapshot = build_snapshot(store)
    if previous.get("corpus_hash") != snapshot.corpus_hash:
        raise ValueError("DEV-v1 corpus hash differs from the current corpus")
    result = run_frozen_dev(previous, store, runtime_dir, model=model, revision=revision,
                           device=device, include_metrics=False)
    pool = build_evaluation_pool(result["rankings"], top_k=20)
    old_pairs = {(str(item["query_id"]), str(item["artifact_id"]))
                 for item in previous.get("qrels", [])}
    coverage = judgment_coverage(result["rankings"], old_pairs)
    delta = pool_delta(pool, previous.get("qrels", []))
    documents = snapshot.by_id()
    artifacts = {str(row["artifact_id"]): row for row in ArtifactRepository(store).iter_canonical()}
    queries = []
    for old_query in previous.get("queries", []):
        query_id = str(old_query["query_id"])
        query = {key: old_query[key] for key in ("query_id", "category", "specificity", "query")}
        if old_query.get("query_provenance") is not None:
            query["query_provenance"] = old_query["query_provenance"]
        query["candidates"] = []
        for artifact_id in pool.get(query_id, []):
            document = documents.get(artifact_id)
            artifact = artifacts.get(artifact_id)
            if document is None or artifact is None:
                raise ValueError(f"retrieval pool references unknown canonical Artifact {artifact_id}")
            query["candidates"].append({
                "artifact_id": artifact_id,
                "artifact_type": document.artifact_type,
                "title": document.title,
                "summary_excerpt": str(document.body or "").strip()[:2000],
                "canonical_url": str(artifact.get("canonical_url") or ""),
                "published_at": str(document.published_at or ""),
            })
        queries.append(query)
    benchmark_id = "dev-v1.1"
    benchmark_hash = hashlib.sha256(json.dumps(
        {"benchmark_id": benchmark_id, "queries": queries}, ensure_ascii=False,
        sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    prompt_digest = prompt_hash(Path(prompt_path).read_bytes())
    new_pairs = [(row["query_id"], row["artifact_id"]) for row in delta["new_pairs"]]
    judge_input = build_judge_input(
        benchmark_id=benchmark_id, benchmark_hash=benchmark_hash, corpus_hash=snapshot.corpus_hash,
        pairs=new_pairs, queries=queries, documents=documents, artifacts=artifacts,
        grading_prompt_hash=prompt_digest,
    )
    provenance = result["retrieval_provenance"]
    label_pack = {
        "schema": "bubblevan/retrieval-label-pack/v1", "status": "pool_built",
        "benchmark_id": benchmark_id, "benchmark_hash": benchmark_hash,
        "corpus_hash": snapshot.corpus_hash, "retrieval_provenance": provenance,
        "queries": queries,
    }
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    _write_json(target / "retrieval-pool-rankings.json", {
        key: result[key] for key in ("schema", "benchmark_hash", "corpus_hash", "query_count",
                                     "retrieval_provenance", "rankings", "topic_rankings")
    })
    _write_json(target / "dev-v1.1-label-pack.json", label_pack)
    _write_json(target / "dev-v1-1-judge-input.json", judge_input)
    _write_json(target / "pool-coverage.json", {
        "benchmark_id": "dev-v1", "corpus_hash": snapshot.corpus_hash,
        "coverage": coverage,
        "legacy_dev_v1_evaluation_judged_at_10": _legacy_judged_at_10(previous_path),
        "coverage_note": "Coverage is measured over returned candidates; empty rankings have no candidate pairs and pass vacuously.",
    })
    _write_json(target / "pool-delta.json", {
        "benchmark_id": benchmark_id, "benchmark_hash": benchmark_hash,
        "corpus_hash": snapshot.corpus_hash, **delta,
    })
    return {
        "status": "pool_built", "benchmark_id": benchmark_id,
        "benchmark_hash": benchmark_hash, "corpus_hash": snapshot.corpus_hash,
        "prompt_hash": prompt_digest, "pool_pairs": len(pool_pairs(pool)),
        "existing_judgments": delta["existing_judgments"],
        "new_judgments_required": delta["new_judgments_required"],
        "removed_from_current_pool": delta["removed_from_current_pool"],
        "coverage": {baseline: {cutoff: coverage[baseline]["cutoffs"][cutoff]["Judged"]
                                 for cutoff in ("5", "10", "20")}
                     for baseline in ("B0", "B1", "B2", "B3", "B4")},
        "paths": {
            "rankings": str(target / "retrieval-pool-rankings.json"),
            "label_pack": str(target / "dev-v1.1-label-pack.json"),
            "judge_input": str(target / "dev-v1-1-judge-input.json"),
            "coverage": str(target / "pool-coverage.json"),
            "delta": str(target / "pool-delta.json"),
        },
    }


def _legacy_judged_at_10(previous_benchmark_path: Path) -> dict[str, float]:
    evaluation_path = previous_benchmark_path.with_name("dev-v1-evaluation.json")
    try:
        evaluation = _read_object(evaluation_path)
    except (OSError, ValueError):
        return {}
    return {baseline: float(evaluation.get("baselines", {}).get(baseline, {})
                            .get("aggregate", {}).get("Judged@10", 0.0))
            for baseline in ("B0", "B1", "B2", "B3", "B4")}


def _read_object(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")
