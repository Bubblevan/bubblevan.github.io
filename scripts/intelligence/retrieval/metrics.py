from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


def evaluate_ranking(ranked_ids: Sequence[str], qrels: Mapping[str, int]) -> dict[str, float | int]:
    relevant = {str(item) for item, grade in qrels.items() if int(grade) > 0}
    result: dict[str, float | int] = {}
    for k in (5, 10, 20):
        top = [str(item) for item in ranked_ids[:k]]
        result[f"Recall@{k}"] = len(set(top).intersection(relevant)) / len(relevant) if relevant else 0.0
    top10 = [str(item) for item in ranked_ids[:10]]
    reciprocal_rank = next((1.0 / rank for rank, artifact_id in enumerate(top10, 1) if artifact_id in relevant), 0.0)
    result["MRR@10"] = reciprocal_rank
    result["Precision@10"] = len(set(top10).intersection(relevant)) / 10.0
    # ir-measures nDCG uses linear gains by default; keep this diagnostic in parity.
    gains = [int(qrels.get(artifact_id, 0)) / math.log2(index + 2) for index, artifact_id in enumerate(top10)]
    ideal = sorted((int(grade) for grade in qrels.values()), reverse=True)[:10]
    ideal_dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(ideal))
    result["nDCG@10"] = sum(gains) / ideal_dcg if ideal_dcg else 0.0
    return result


def evaluate_routes(route_ids: Mapping[str, Sequence[str]], qrels: Mapping[str, int], *, k: int = 20) -> dict[str, Any]:
    relevant = {str(item) for item, grade in qrels.items() if int(grade) > 0}
    hits_by_route = {route: set(map(str, ids[:k])).intersection(relevant) for route, ids in sorted(route_ids.items())}
    union = set().union(*hits_by_route.values()) if hits_by_route else set()
    unique = {}
    for route, hits in hits_by_route.items():
        other_hits = set().union(*(values for name, values in hits_by_route.items() if name != route)) if len(hits_by_route) > 1 else set()
        unique[route] = sorted(hits - other_hits)
    overlap = {}
    routes = sorted(hits_by_route)
    for left_index, left in enumerate(routes):
        for right in routes[left_index + 1:]:
            intersection = hits_by_route[left] & hits_by_route[right]
            denominator = hits_by_route[left] | hits_by_route[right]
            overlap[f"{left}|{right}"] = len(intersection) / len(denominator) if denominator else 0.0
    return {
        "k": k,
        "route_recall": {route: len(hits) / len(relevant) if relevant else 0.0 for route, hits in hits_by_route.items()},
        "union_recall": len(union) / len(relevant) if relevant else 0.0,
        "union_relevant_hits": sorted(union),
        "unique_contribution": unique,
        "overlap_jaccard": overlap,
    }


def future_leak_count(ranked_ids: Sequence[str], documents: Mapping[str, Any], as_of: str | None) -> int:
    if not as_of:
        return 0
    cutoff = _time(as_of)
    leaked = 0
    for artifact_id in ranked_ids:
        document = documents.get(str(artifact_id))
        if document is None:
            continue
        published = _time(_value(document, "published_at"))
        fallback = _time(_value(document, "first_observed_at"))
        value = published or fallback
        if value and value > cutoff:
            leaked += 1
    return leaked


def discovery_lag_days(published_at: str | None, observed_at: str | None) -> float | None:
    if not published_at or not observed_at:
        return None
    return (_time(observed_at) - _time(published_at)).total_seconds() / 86400.0


def _time(value: Any):
    from datetime import datetime, timezone
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc)


def _value(document: Any, field: str) -> Any:
    if isinstance(document, Mapping):
        return document.get(field)
    return getattr(document, field, None)
