from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


def reciprocal_rank_fusion(route_results: Mapping[str, Sequence[Mapping[str, Any]]], *, request_id: str,
                           top_k: int, k: int = 60,
                           canonicalize: Callable[[str], str] | None = None) -> list[dict[str, Any]]:
    if k < 1:
        raise ValueError("RRF k must be positive")
    accumulated: dict[str, dict[str, Any]] = {}
    for route in sorted(route_results):
        seen: set[str] = set()
        rows = route_results[route]
        for position, candidate in enumerate(rows, 1):
            original_id = str(candidate.get("artifact_id") or "")
            artifact_id = canonicalize(original_id) if canonicalize else original_id
            if not artifact_id or artifact_id in seen:
                continue
            seen.add(artifact_id)
            route_rank = int(candidate.get("rank") or position)
            if route_rank < 1:
                continue
            item = accumulated.setdefault(artifact_id, {"request_id": request_id, "artifact_id": artifact_id,
                                                        "routes": [], "fusion": {"method": "rrf", "score": 0.0,
                                                                                  "contributions": {}},
                                                        "explanation": {"routes": {}}})
            contribution = 1.0 / (k + route_rank)
            item["fusion"]["score"] += contribution
            item["fusion"]["contributions"][route] = contribution
            item["routes"].append({"route": route, "rank": route_rank,
                                   "raw_score": _number(candidate.get("raw_score")),
                                   "explanation": dict(candidate.get("explanation") or {})})
            item["explanation"]["routes"][route] = dict(candidate.get("explanation") or {})
    ordered = sorted(accumulated.values(), key=lambda item: (-item["fusion"]["score"], item["artifact_id"]))[:top_k]
    for rank, item in enumerate(ordered, 1):
        item["fusion"]["rank"] = rank
        item["routes"].sort(key=lambda route: route["route"])
    return ordered


def _number(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
