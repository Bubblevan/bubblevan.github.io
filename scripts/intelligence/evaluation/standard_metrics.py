from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


METRIC_NAMES = ("Recall@5", "Recall@10", "Recall@20", "RR@10", "nDCG@10", "P@10", "Judged@10")


def evaluate_ir_measures(ranked_ids: Sequence[str], qrels: Mapping[str, int]) -> dict[str, float]:
    """Compute the report metrics through ir-measures; grades are 0/1/2."""
    try:
        import ir_measures as irm
    except ImportError as exc:
        raise RuntimeError("install requirements-evaluation.txt to calculate ir-measures metrics") from exc
    query_id = "q"
    rel_qrels = [irm.Qrel(query_id, str(doc_id), int(grade)) for doc_id, grade in qrels.items()]
    run = [irm.ScoredDoc(query_id, str(doc_id), float(len(ranked_ids) - index))
           for index, doc_id in enumerate(ranked_ids)]
    measures = [irm.parse_measure(name) for name in METRIC_NAMES]
    if not any(int(grade) > 0 for grade in qrels.values()):
        return {name: 0.0 for name in METRIC_NAMES}
    values = irm.calc_aggregate(measures, rel_qrels, run)
    result = {}
    for measure, name in zip(measures, METRIC_NAMES):
        result[name] = float(values.get(measure, 0.0))
    return result


def evaluate_ir_per_query(rankings: Mapping[str, Sequence[str]], qrels: Mapping[str, Mapping[str, int]]) -> dict[str, dict[str, float]]:
    return {query_id: evaluate_ir_measures(ranking, qrels.get(query_id, {}))
            for query_id, ranking in rankings.items()}


def ranx_metrics(rankings: Mapping[str, Sequence[str]], qrels: Mapping[str, Mapping[str, int]]) -> dict[str, Any]:
    """Return a ranx report and per-query metrics for cross-library diagnostics."""
    try:
        from ranx import Qrels, Run, evaluate
    except ImportError as exc:
        raise RuntimeError("install requirements-evaluation.txt to calculate ranx metrics") from exc
    qrels_data = {str(query): {str(doc): int(grade) for doc, grade in docs.items()}
                  for query, docs in qrels.items()}
    run_data = {str(query): {str(doc): float(len(ids) - index) for index, doc in enumerate(ids)}
                for query, ids in rankings.items()}
    ranx_qrels = Qrels(qrels_data)
    ranx_run = Run(run_data)
    names = ["recall@5", "recall@10", "recall@20", "mrr@10", "ndcg@10", "precision@10"]
    aggregate = evaluate(ranx_qrels, ranx_run, names)
    per_measure = evaluate(ranx_qrels, ranx_run, names, return_mean=False)
    query_ids = sorted(qrels_data)
    per_query = {query: {} for query in query_ids}
    for metric, values in per_measure.items():
        for query, value in zip(query_ids, values):
            per_query[query][str(metric)] = float(value)
    return {"aggregate": {str(key): float(value) for key, value in aggregate.items()},
            "per_query": per_query}
