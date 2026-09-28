from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from ..entity_aliases import EntityAliases
from ..graph.store import GraphStore
from ..store import JsonlStore
from .budget import ExpansionBudget
from .paths import evidence_paths_to_entity
from .source_candidates import SourceCandidateStore, make_candidate


class SourceDiscovery:
    def __init__(
        self,
        store: JsonlStore,
        graph: GraphStore,
        aliases: EntityAliases,
        candidates: SourceCandidateStore,
        *,
        now: str,
    ):
        self.store = store
        self.graph = graph
        self.aliases = aliases
        self.candidates = candidates
        self.now = _timestamp(now)

    def discover(self, seed_source_id: str, budget: ExpansionBudget) -> dict[str, Any]:
        sources = {item["source_id"]: item for item in self.store.iter_records("source")}
        if seed_source_id not in sources:
            raise ValueError("seed source does not exist in the local store")
        entities = {
            self.aliases.resolve_entity_id(str(item["entity_id"])): item
            for item in self.store.iter_records("entity")
        }
        artifacts = {item["artifact_id"]: item for item in self.store.iter_records("artifact")}
        edges = self.graph.iter_edges()
        outgoing: dict[str, list[dict[str, Any]]] = {}
        incoming: dict[str, list[dict[str, Any]]] = {}
        for edge in edges:
            subject = self._resolve(str(edge["subject_id"]))
            obj = self._resolve(str(edge["object_id"]))
            normalized = dict(edge, _subject=subject, _object=obj)
            outgoing.setdefault(subject, []).append(normalized)
            incoming.setdefault(obj, []).append(normalized)
        for mapping in (outgoing, incoming):
            for node_id in mapping:
                mapping[node_id].sort(key=lambda item: (item["predicate"], item["_object"], item["edge_id"]))

        seed_paths = self._walk(seed_source_id, outgoing, budget)
        reached = sorted({
            node for node in seed_paths
            if node in entities and _eligible_entity(entities[node])
        })
        new_count = 0
        deduplicated = 0
        for entity_id in reached:
            paths = evidence_paths_to_entity(seed_source_id, entity_id, self.graph, _path_budget(budget), self.aliases)
            if not paths:
                continue
            support_artifacts = self._supporting_artifacts(entity_id, entities, artifacts, incoming, outgoing)
            source_ids = sorted({
                str(edge["_subject"])
                for artifact_id in support_artifacts
                for edge in incoming.get(artifact_id, [])
                if edge["predicate"] in {"mentions", "recommends"} and str(edge["_subject"]).startswith("src-")
            })
            topic_support: dict[str, dict[str, Any]] = {}
            for artifact_id in support_artifacts:
                artifact = artifacts.get(artifact_id, {})
                linked_sources = {
                    str(edge["_subject"])
                    for edge in incoming.get(artifact_id, [])
                    if edge["predicate"] in {"mentions", "recommends"} and str(edge["_subject"]).startswith("src-")
                }
                for topic in artifact.get("topics", []):
                    entry = topic_support.setdefault(str(topic), {"artifact_count": 0, "source_ids": set()})
                    entry["artifact_count"] += 1
                    entry["source_ids"].update(linked_sources)
            topic_support = {
                topic: {
                    "artifact_count": entry["artifact_count"],
                    "source_count": len(entry["source_ids"]),
                }
                for topic, entry in sorted(topic_support.items())
            }
            depth = min(int(path["depth"]) for path in paths)
            support_edge_ids = {
                edge["edge_id"] for edge in edges
                if edge["subject_id"] in support_artifacts or edge["object_id"] in support_artifacts
            }
            providers = {
                str(evidence["provider"])
                for edge in edges
                if edge["edge_id"] in support_edge_ids
                for evidence in edge["evidence"]
                if evidence.get("provider") and evidence.get("provider") != "curated-topic-catalog"
            }
            recent_cutoff = datetime.fromisoformat(self.now.replace("Z", "+00:00")) - timedelta(days=365)
            recent_support = sum(
                1 for path in paths
                if _path_last_observed(path, edges) >= recent_cutoff
            )
            entity = entities[entity_id]
            signals = {
                "supporting_artifact_count": len(support_artifacts),
                "independent_source_count": len(source_ids),
                "provider_count": len(providers),
                "min_path_depth": depth,
                "recent_support": recent_support,
                "exact_identity": bool(entity.get("external_ids")) and entity.get("resolution_state", "resolved") == "resolved",
                "supporting_source_ids": source_ids,
                "supporting_artifact_ids": support_artifacts,
                "topic_support": topic_support,
            }
            candidate = make_candidate(
                entity=entity, paths=paths, topics=sorted(topic_support), signals=signals,
                first_discovered_at=self.now, last_supported_at=self.now,
            )
            if not budget.candidate():
                break
            existing = {item["candidate_id"] for item in self.candidates.iter_candidates()}
            self.candidates.upsert(candidate, entity_aliases=self.aliases)
            if candidate["candidate_id"] in existing:
                deduplicated += 1
            else:
                new_count += 1
        return {
            "seed_sources": [seed_source_id],
            "nodes_visited": budget.nodes_visited,
            "edges_traversed": budget.edges_traversed,
            "provider_requests": budget.provider_requests,
            "candidates_generated": new_count,
            "candidates_deduplicated": deduplicated,
            "budget_exhausted": budget.exhausted,
            "candidate_ids": [
                item["candidate_id"] for item in self.candidates.iter_candidates()
                if item["entity_id"] in reached
            ],
        }

    def _walk(
        self,
        seed: str,
        outgoing: Mapping[str, list[dict[str, Any]]],
        budget: ExpansionBudget,
    ) -> dict[str, list[dict[str, Any]]]:
        if not budget.visit_node():
            return {}
        queue = deque([(seed, 0, [])])
        best: dict[str, int] = {seed: 0}
        paths: dict[str, list[dict[str, Any]]] = {seed: []}
        while queue:
            node, depth, steps = queue.popleft()
            if depth >= budget.max_depth:
                continue
            for edge in outgoing.get(node, []):
                if not budget.traverse_edge():
                    return paths
                next_node = str(edge["_object"])
                if next_node in best and best[next_node] <= depth + 1:
                    continue
                if not budget.visit_node():
                    return paths
                primary = min(
                    edge.get("evidence", []),
                    key=lambda value: (
                        str(value.get("observation_id") or ""),
                        str(value.get("provider") or ""),
                        str(value.get("provider_record_id") or ""),
                    ),
                ) if edge.get("evidence") else {}
                step = {
                    "subject_id": str(edge["subject_id"]),
                    "predicate": str(edge["predicate"]),
                    "object_id": str(edge["object_id"]),
                    "edge_id": str(edge["edge_id"]),
                    "evidence_id": str(primary.get("observation_id") or edge["edge_id"]),
                    "provider": str(primary.get("provider") or "") or None,
                }
                best[next_node] = depth + 1
                next_steps = steps + [step]
                paths[next_node] = next_steps
                queue.append((next_node, depth + 1, next_steps))
        return paths

    def _supporting_artifacts(
        self,
        entity_id: str,
        entities: Mapping[str, dict[str, Any]],
        artifacts: Mapping[str, dict[str, Any]],
        incoming: Mapping[str, list[dict[str, Any]]],
        outgoing: Mapping[str, list[dict[str, Any]]],
    ) -> list[str]:
        entity = entities[entity_id]
        entity_type = str(entity.get("entity_type"))
        artifacts_found: set[str] = set()
        if entity_type == "person":
            artifacts_found.update(
                str(edge["_subject"]) for edge in incoming.get(entity_id, [])
                if edge["predicate"] == "authored_by" and str(edge["_subject"]).startswith("art-")
            )
        elif entity_type in {"institution", "organization", "lab"}:
            people = {
                str(edge["_subject"]) for edge in incoming.get(entity_id, [])
                if edge["predicate"] == "affiliated_with" and str(edge["_subject"]).startswith("ent-")
            }
            for person_id in people:
                artifacts_found.update(
                    str(edge["_subject"]) for edge in incoming.get(person_id, [])
                    if edge["predicate"] == "authored_by" and str(edge["_subject"]).startswith("art-")
                )
            artifacts_found.update(
                str(edge["_subject"]) for edge in incoming.get(entity_id, [])
                if edge["predicate"] in {"owned_by", "maintained_by"} and str(edge["_subject"]).startswith("art-")
            )
        elif entity_type == "repository":
            artifacts_found.update(
                str(edge["_subject"]) for edge in incoming.get(entity_id, [])
                if edge["predicate"] in {"implemented_by", "related_to"}
            )
        return sorted(item for item in artifacts_found if item in artifacts)

    def _resolve(self, value: str) -> str:
        return self.aliases.resolve_entity_id(value) if value.startswith("ent-") else value


def _eligible_entity(entity: Mapping[str, Any]) -> bool:
    return (
        str(entity.get("entity_type")) in {"person", "institution", "lab", "organization", "repository"}
        and entity.get("resolution_state", "resolved") != "unresolved"
        and bool(entity.get("external_ids"))
    )


def _path_budget(source: ExpansionBudget) -> ExpansionBudget:
    # Evidence path extraction should observe the same depth limit without consuming traversal limits again.
    return ExpansionBudget(
        max_depth=source.max_depth,
        max_nodes=max(1, source.max_nodes),
        max_edges=max(1, source.max_edges),
        max_candidates=max(1, source.max_candidates),
        max_references_per_artifact=source.max_references_per_artifact,
        max_citations_per_artifact=source.max_citations_per_artifact,
        max_recent_works_per_author=source.max_recent_works_per_author,
        max_provider_requests=max(1, source.max_provider_requests),
    )


def _path_last_observed(path: Mapping[str, Any], edges: list[dict[str, Any]]) -> datetime:
    by_id = {edge["edge_id"]: edge for edge in edges}
    timestamps = [
        datetime.fromisoformat(by_id[step["edge_id"]]["last_observed_at"].replace("Z", "+00:00"))
        for step in path["steps"] if step["edge_id"] in by_id
    ]
    return max(timestamps) if timestamps else datetime.min.replace(tzinfo=timezone.utc)


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
