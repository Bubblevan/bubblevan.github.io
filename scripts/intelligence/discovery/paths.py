from __future__ import annotations

from collections import deque
from typing import Any, Mapping

from ..entity_aliases import EntityAliases
from ..graph.store import GraphStore
from .budget import ExpansionBudget


def evidence_paths_to_entity(
    seed_source_id: str,
    entity_id: str,
    graph: GraphStore,
    budget: ExpansionBudget,
    aliases: EntityAliases,
) -> list[dict[str, Any]]:
    """Return deterministic, evidence-carrying shortest paths from one Source."""
    target = aliases.resolve_entity_id(entity_id)
    edges = graph.iter_edges()
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        subject, obj = str(edge["subject_id"]), str(edge["object_id"])
        if subject.startswith("ent-"):
            subject = aliases.resolve_entity_id(subject)
        if obj.startswith("ent-"):
            obj = aliases.resolve_entity_id(obj)
        projected = dict(edge, _resolved_subject=subject, _resolved_object=obj)
        adjacency.setdefault(subject, []).append(projected)
    for node in adjacency:
        adjacency[node].sort(key=lambda item: (item["predicate"], item["_resolved_object"], item["edge_id"]))

    queue = deque([(seed_source_id, 0, [])])
    best_depth: dict[str, int] = {seed_source_id: 0}
    found: list[dict[str, Any]] = []
    while queue:
        node, depth, steps = queue.popleft()
        if depth >= budget.max_depth:
            continue
        for edge in adjacency.get(node, []):
            if not budget.traverse_edge():
                return sorted(found, key=_path_key)
            next_node = str(edge["_resolved_object"])
            next_depth = depth + 1
            evidence = edge.get("evidence", [])
            primary = min(
                evidence,
                key=lambda item: (
                    str(item.get("observation_id") or ""),
                    str(item.get("provider") or ""),
                    str(item.get("provider_record_id") or ""),
                ),
            ) if evidence else {}
            step = {
                "subject_id": str(edge["subject_id"]),
                "predicate": str(edge["predicate"]),
                "object_id": str(edge["object_id"]),
                "edge_id": str(edge["edge_id"]),
                "evidence_id": str(primary.get("observation_id") or edge["edge_id"]),
                "provider": str(primary.get("provider") or "") or None,
            }
            path = steps + [step]
            if next_node == target:
                found.append({"seed_source_id": seed_source_id, "steps": path, "depth": next_depth})
                continue
            if next_depth < best_depth.get(next_node, 10**9):
                best_depth[next_node] = next_depth
                queue.append((next_node, next_depth, path))
    return sorted(found, key=_path_key)


def _path_key(path: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        int(path["depth"]),
        tuple((step["predicate"], step["subject_id"], step["object_id"], step["evidence_id"]) for step in path["steps"]),
    )
