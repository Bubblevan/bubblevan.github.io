from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


BASELINES = ("B0", "B1", "B2", "B3", "B4")
CUTOFFS = (5, 10, 20)


def build_evaluation_pool(rankings: Mapping[str, Mapping[str, Sequence[str]]], *,
                         top_k: int = 20) -> dict[str, list[str]]:
    """Build the exact per-query union of B0–B4 top-k results."""
    missing = set(BASELINES) - set(rankings)
    if missing:
        raise ValueError(f"retrieval rankings are missing baselines: {', '.join(sorted(missing))}")
    query_ids = set().union(*(set(rankings[baseline]) for baseline in BASELINES))
    pool: dict[str, list[str]] = {}
    for query_id in sorted(query_ids):
        candidates: set[str] = set()
        for baseline in BASELINES:
            for artifact_id in rankings[baseline].get(query_id, ())[:top_k]:
                value = str(artifact_id).strip()
                if value:
                    candidates.add(value)
        pool[query_id] = sorted(candidates)
    return pool


def pool_pairs(pool: Mapping[str, Sequence[str]]) -> set[tuple[str, str]]:
    return {(str(query_id), str(artifact_id)) for query_id, ids in pool.items() for artifact_id in ids}


def pool_delta(pool: Mapping[str, Sequence[str]], qrels: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    current = pool_pairs(pool)
    previous = {(str(item["query_id"]), str(item["artifact_id"])) for item in qrels}
    return {
        "existing_judgments": len(current & previous),
        "new_judgments_required": len(current - previous),
        "removed_from_current_pool": len(previous - current),
        "total_v1_1_pool": len(current),
        "new_pairs": [
            {"query_id": query_id, "artifact_id": artifact_id}
            for query_id, artifact_id in sorted(current - previous)
        ],
        "removed_pairs": [
            {"query_id": query_id, "artifact_id": artifact_id}
            for query_id, artifact_id in sorted(previous - current)
        ],
    }


def judgment_coverage(rankings: Mapping[str, Mapping[str, Sequence[str]]],
                      judged_pairs: set[tuple[str, str]], *,
                      cutoffs: Sequence[int] = CUTOFFS) -> dict[str, Any]:
    """Report per-baseline judged proportions and every unjudged ranked pair."""
    report: dict[str, Any] = {}
    for baseline in BASELINES:
        if baseline not in rankings:
            raise ValueError(f"retrieval rankings are missing baseline {baseline}")
        query_rankings = rankings[baseline]
        result: dict[str, Any] = {"queries": len(query_rankings), "cutoffs": {}, "unjudged": {}}
        for cutoff in cutoffs:
            slots = [(str(query_id), str(artifact_id), rank)
                     for query_id, ids in sorted(query_rankings.items())
                     for rank, artifact_id in enumerate(ids[:cutoff], 1)]
            unjudged = [
                {"query_id": query_id, "artifact_id": artifact_id,
                 "baseline": baseline, "rank": rank}
                for query_id, artifact_id, rank in slots
                if (query_id, artifact_id) not in judged_pairs
            ]
            total = len(slots)
            judged = total - len(unjudged)
            result["cutoffs"][str(cutoff)] = {
                "judged": judged,
                "total": total,
                "Judged": judged / total if total else 1.0,
                "unjudged_count": len(unjudged),
            }
            result["unjudged"][str(cutoff)] = unjudged
        report[baseline] = result
    report["official_gate"] = official_coverage_gate({
        baseline: {f"Judged@{cutoff}": report[baseline]["cutoffs"][str(cutoff)]["Judged"]
                   for cutoff in (10, 20)}
        for baseline in BASELINES
    })
    return report


def official_coverage_gate(baselines: Mapping[str, Mapping[str, float]]) -> dict[str, Any]:
    missing = [f"{baseline}.{metric}" for baseline in BASELINES
               for metric in ("Judged@10", "Judged@20")
               if float(baselines.get(baseline, {}).get(metric, 0.0)) != 1.0]
    return {
        "requirements": {"Judged@10": 1.0, "Judged@20": 1.0},
        "passed": not missing,
        "incomplete": missing,
        "status": "completed" if not missing else "incomplete_judgment_pool",
    }
