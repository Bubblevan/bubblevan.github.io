from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from typing import Any, Sequence

from ..aliases import ArtifactAliases
from ..entity_aliases import EntityAliases
from ..graph.store import GraphStore
from .base import RetrievalResult, RetrieverSpec
from .corpus import CorpusSnapshot, RetrievalDocument
from .request import RetrievalRequest


class GraphRetriever:
    spec = RetrieverSpec("graph", "bounded-graph-v1", independent_local=True)

    def __init__(self, store_dir: str):
        self.graph = GraphStore(store_dir)
        self.artifact_aliases = ArtifactAliases(store_dir)
        self.entity_aliases = EntityAliases(store_dir)
        self.edges: list[dict[str, Any]] = []
        self.artifact_ids: set[str] = set()
        self.artifact_redirects: dict[str, str] = {}
        self.entity_redirects: dict[str, str] = {}

    def build(self, snapshot: CorpusSnapshot, runtime_dir: str) -> dict[str, Any]:
        self.edges = self.graph.iter_edges()
        self.artifact_ids = set(snapshot.by_id())
        # Graph expansion resolves every edge repeatedly for each DEV query. Load and
        # flatten the small redirect stores once per graph build instead of reopening
        # their JSONL files for every endpoint of every edge.
        self.artifact_redirects = _flatten_redirects(
            self.artifact_aliases._redirect_rows(), "from_artifact_id", "to_artifact_id")
        self.entity_redirects = _flatten_redirects(
            self.entity_aliases._read_redirects(), "from_entity_id", "to_entity_id")
        return {"route": "graph", "version": self.spec.version, "corpus_hash": snapshot.corpus_hash,
                "edge_count": len(self.edges),
                "edge_hash": hashlib.sha256(json.dumps(self.edges, ensure_ascii=False, sort_keys=True,
                                                         separators=(",", ":")).encode("utf-8")).hexdigest(),
                "max_depth": 2}

    def retrieve(self, request: RetrievalRequest, *, documents: Sequence[RetrievalDocument], top_k: int) -> RetrievalResult:
        if not request.seed_artifact_ids:
            return RetrievalResult("graph", status="skipped", reason="no seed Artifact IDs")
        seeds = sorted({_resolve_redirect(item, self.artifact_redirects) for item in request.seed_artifact_ids})[:10]
        eligible = {item.artifact_id for item in documents}
        outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
        incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in self.edges:
            subject = _canonical(str(edge["subject_id"]), self.artifact_redirects, self.entity_redirects)
            obj = _canonical(str(edge["object_id"]), self.artifact_redirects, self.entity_redirects)
            outgoing[subject].append(dict(edge, _subject=subject, _object=obj))
            incoming[obj].append(dict(edge, _subject=subject, _object=obj))
        for values in (*outgoing.values(), *incoming.values()):
            values.sort(key=lambda row: (str(row["predicate"]), str(row["_subject"]), str(row["_object"]), str(row["edge_id"])))

        signals: dict[str, dict[str, Any]] = {}
        per_seed_neighbors: dict[str, set[str]] = defaultdict(set)
        for seed in seeds:
            if seed not in self.artifact_ids:
                continue
            seed_candidates: dict[str, list[tuple[str, dict[str, Any], list[str], list[str]]]] = defaultdict(list)
            cited = []
            referenced = []
            for edge in (outgoing.get(seed, []) + incoming.get(seed, []))[:100]:
                if edge["predicate"] == "cites":
                    other = edge["_object"] if edge["_subject"] == seed else edge["_subject"]
                    if other.startswith("art-"):
                        cited.append((other, edge))
                elif edge["predicate"] == "references":
                    other = edge["_object"] if edge["_subject"] == seed else edge["_subject"]
                    if other.startswith("art-"):
                        referenced.append((other, edge))
            authors = {edge["_object"] for edge in outgoing.get(seed, [])[:100] if edge["predicate"] == "authored_by"}
            authors.update(edge["_subject"] for edge in incoming.get(seed, [])[:100] if edge["predicate"] == "authored" )
            authored_neighbors: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for person in sorted(authors)[:100]:
                for edge in (outgoing.get(person, []) + incoming.get(person, []))[:100]:
                    if edge["predicate"] == "authored_by":
                        other = edge["_subject"] if edge["_object"] == person else edge["_object"]
                        if other.startswith("art-") and other != seed:
                            authored_neighbors[other].append(edge)
            sources = {edge["_subject"] for edge in incoming.get(seed, [])[:100] if edge["predicate"] in {"mentions", "recommends"}}
            sourced_neighbors: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for source in sorted(sources)[:100]:
                for edge in outgoing.get(source, [])[:100]:
                    if edge["predicate"] in {"mentions", "recommends"} and edge["_object"].startswith("art-") and edge["_object"] != seed:
                        sourced_neighbors[edge["_object"]].append(edge)
            for other, edge in cited:
                seed_candidates[other].append(("citation", edge, [], []))
            for other, edge in referenced:
                seed_candidates[other].append(("reference", edge, [], []))
            for other, matched_edges in authored_neighbors.items():
                for edge in matched_edges:
                    person = edge["_object"] if edge["_subject"] == other else edge["_subject"]
                    seed_candidates[other].append(("author", edge, [person], []))
            for other, matched_edges in sourced_neighbors.items():
                for edge in matched_edges:
                    source_id = edge["_subject"]
                    seed_candidates[other].append(("source", edge, [], [source_id]))
            for candidate_id in sorted(seed_candidates)[:100]:
                if candidate_id not in signals and len(signals) >= 500:
                    continue
                per_seed_neighbors[seed].add(candidate_id)
                for signal, edge, entity_ids, source_ids in seed_candidates[candidate_id]:
                    self._record(signals, candidate_id, signal, seed, edge, entity_ids=entity_ids, source_ids=source_ids)
        ordered_ids = sorted(
            (item for item in signals if item in eligible and item not in seeds),
            key=lambda item: (
                -len(signals[item]["seed_ids"]),
                -signals[item]["citation_distance"],
                -len(signals[item]["references"]),
                -len(signals[item]["authors"]),
                -len(signals[item]["sources"]),
                item,
            ),
        )[:500]
        degrees: dict[str, int] = defaultdict(int)
        for edge in self.edges:
            left = _canonical(str(edge["subject_id"]), self.artifact_redirects, self.entity_redirects)
            right = _canonical(str(edge["object_id"]), self.artifact_redirects, self.entity_redirects)
            if left.startswith("art-"):
                degrees[left] += 1
            if right.startswith("art-"):
                degrees[right] += 1
        candidates = []
        for artifact_id in ordered_ids[:top_k]:
            item = signals[artifact_id]
            explanation = {
                "citation_distance": item["citation_distance"] or None,
                "shared_seed_count": len(item["seed_ids"]),
                "seed_support_count": len(item["seed_ids"]),
                "candidate_degree": degrees.get(artifact_id, 0),
                "reference_count": len(item["references"]),
                "shared_author_count": len(item["authors"]),
                "shared_source_count": len(item["sources"]),
                "graph_paths": sorted(item["paths"], key=lambda path: (path["signal"], path["seed_artifact_id"], path["edge_id"])),
            }
            candidates.append({"artifact_id": artifact_id, "rank": len(candidates) + 1,
                               "raw_score": float(len(item["seed_ids"]) + len(item["authors"]) + len(item["sources"])),
                               "explanation": explanation})
        return RetrievalResult("graph", candidates, {"version": self.spec.version, "semantics": "explicit-seed-graph",
                              "max_seed_artifacts": 10,
                              "max_graph_neighbors_per_seed": 100, "max_total_graph_candidates": 500, "max_graph_depth": 2})

    @staticmethod
    def _record(signals: dict[str, dict[str, Any]], candidate: str, signal: str, seed: str,
                edge: dict[str, Any], *, entity_ids: list[str] | None = None,
                source_ids: list[str] | None = None) -> None:
        item = signals.setdefault(candidate, {"seed_ids": set(), "citation_distance": 0,
                                               "authors": set(), "sources": set(), "references": set(), "paths": []})
        item["seed_ids"].add(seed)
        if signal == "citation":
            item["citation_distance"] = 1
        elif signal == "author":
            item["authors"].update(entity_ids or [])
        elif signal == "source":
            item["sources"].update(source_ids or [])
        elif signal == "reference":
            item["references"].add(seed)
        item["paths"].append({
            "signal": signal, "seed_artifact_id": seed, "candidate_artifact_id": candidate,
            "predicate": str(edge["predicate"]), "edge_id": str(edge["edge_id"]),
            "entity_ids": sorted(set(entity_ids or [])),
            "source_ids": sorted(set(source_ids or [])),
            "evidence": [dict(value) for value in edge.get("evidence", [])[:3]],
        })


def _canonical(value: str, artifacts: dict[str, str], entities: dict[str, str]) -> str:
    if value.startswith("art-"):
        return _resolve_redirect(value, artifacts)
    if value.startswith("ent-"):
        return _resolve_redirect(value, entities)
    return value


def _resolve_redirect(value: str, redirects: dict[str, str]) -> str:
    return redirects.get(value, value)


def _flatten_redirects(rows: Sequence[dict[str, Any]], source_key: str, target_key: str) -> dict[str, str]:
    direct = {str(row[source_key]): str(row[target_key]) for row in rows}
    flattened: dict[str, str] = {}
    for source in direct:
        trail: list[str] = []
        seen: set[str] = set()
        current = source
        while current in direct:
            if current in seen:
                raise ValueError("identity redirect cycle detected")
            seen.add(current)
            trail.append(current)
            current = direct[current]
        if current in seen:
            raise ValueError("identity redirect cycle detected")
        for item in trail:
            flattened[item] = current
    return flattened
