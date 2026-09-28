from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Sequence

from ..aliases import ArtifactAliases
from .base import RetrievalResult
from .corpus import CorpusSnapshot, RetrievalDocument, filter_documents
from .expansion import expand_query
from .fusion import reciprocal_rank_fusion
from .registry import RetrieverRegistry
from .request import RetrievalRequest, make_request


class RetrievalEngine:
    def __init__(self, snapshot: CorpusSnapshot, registry: RetrieverRegistry, *, store_dir: str,
                 runtime_dir: str):
        self.snapshot = snapshot
        self.registry = registry
        self.artifact_aliases = ArtifactAliases(store_dir)
        self.runtime_dir = Path(runtime_dir) / "retrieval"
        self.manifests: dict[str, dict[str, Any]] = {}
        self.build_failures: dict[str, str] = {}

    def build(self, routes: Sequence[str] | None = None) -> dict[str, Any]:
        selected = list(routes or self.registry.routes())
        for route in selected:
            retriever = self.registry.get(route)
            try:
                self.manifests[route] = retriever.build(self.snapshot, str(self.runtime_dir))
                self.build_failures.pop(route, None)
            except Exception as exc:
                self.build_failures[route] = f"{type(exc).__name__}: {exc}"
        return {"corpus_hash": self.snapshot.corpus_hash, "routes": self.manifests,
                "failed_routes": dict(self.build_failures)}

    def search(self, request: RetrievalRequest, *, routes: Sequence[str] | None = None,
               persist: bool = True, route_depth: int = 50) -> dict[str, Any]:
        if route_depth < 1 or route_depth > 500:
            raise ValueError("route_depth must be between 1 and 500")
        total_started = time.perf_counter()
        entity_names = {
            str(name)
            for document in self.snapshot.documents
            for name in (*document.authors, *document.organizations,
                         *(str(item.get("name") or "") for item in document.graph_entities))
            if str(name).strip()
        }
        terms = list(request.expanded_terms) or expand_query(request.query, entity_names=entity_names)
        if tuple(terms) != request.expanded_terms:
            request = make_request(
                request.query, seed_artifact_ids=request.seed_artifact_ids,
                negative_seed_artifact_ids=request.negative_seed_artifact_ids,
                topic_ids=request.topic_ids, source_ids=request.source_ids, as_of=request.as_of,
                filters=request.filters, top_k=request.top_k, expanded_terms=terms,
            )
        selected = list(routes) if routes else self.eligible_routes(request)
        filtered = filter_documents(self.snapshot, request)
        graph_filtered = filter_documents(self.snapshot, request, include_graph_only=True)
        route_outputs: dict[str, list[dict[str, Any]]] = {}
        route_status: dict[str, dict[str, Any]] = {}
        route_manifests = {}
        for route in selected:
            if route == "graph-expand":
                graph = self.registry.get("graph")
                ranked_seeds = sorted(
                    ((int(row.get("rank") or position), route_id, str(row.get("artifact_id") or ""))
                     for route_id in ("bm25", "dense")
                     for position, row in enumerate(route_outputs.get(route_id, [])[:route_depth], 1)),
                    key=lambda item: (item[0], item[1], item[2]),
                )
                seed_origins: dict[str, dict[str, Any]] = {}
                for rank, source_route, artifact_id in ranked_seeds:
                    if artifact_id and artifact_id not in seed_origins:
                        seed_origins[artifact_id] = {"seed_source_route": source_route, "seed_rank": rank}
                    if len(seed_origins) >= 5:
                        break
                if not seed_origins:
                    route_status[route] = {"status": "skipped", "reason": "no BM25/Dense seeds"}
                    continue
                expand_request = make_request(
                    request.query, seed_artifact_ids=list(seed_origins),
                    negative_seed_artifact_ids=request.negative_seed_artifact_ids,
                    topic_ids=request.topic_ids, source_ids=request.source_ids, as_of=request.as_of,
                    filters=request.filters, top_k=request.top_k, expanded_terms=request.expanded_terms,
                )
                started = time.perf_counter()
                result = graph.retrieve(expand_request, documents=graph_filtered, top_k=route_depth)
                for candidate in result.candidates:
                    paths = candidate.get("explanation", {}).get("graph_paths", [])
                    for path in paths:
                        path.update(seed_origins.get(str(path.get("seed_artifact_id") or ""), {}))
                    candidate.setdefault("explanation", {})["seed_sources"] = sorted(
                        (dict(seed_id=seed_id, **origin) for seed_id, origin in seed_origins.items()),
                        key=lambda item: (item["seed_source_route"], item["seed_rank"], item["seed_id"]),
                    )
                route_outputs[route] = result.candidates
                route_status[route] = {"status": "succeeded", "candidate_count": len(result.candidates),
                                       "elapsed_ms": result.elapsed_ms or round((time.perf_counter() - started) * 1000, 3)}
                route_manifests[route] = {**(result.manifest or {}), "semantics": "query-seeded-graph-expansion",
                                          "seed_limit": 5, "seed_routes": ["bm25", "dense"]}
                continue
            retriever = self.registry.get(route)
            if route not in self.manifests and route not in self.build_failures:
                try:
                    self.manifests[route] = retriever.build(self.snapshot, str(self.runtime_dir))
                except Exception as exc:
                    self.build_failures[route] = f"{type(exc).__name__}: {exc}"
            if route in self.build_failures:
                route_status[route] = {"status": "failed", "reason": self.build_failures[route]}
                continue
            started = time.perf_counter()
            try:
                route_documents = graph_filtered if route == "graph" else filtered
                result: RetrievalResult = retriever.retrieve(request, documents=route_documents, top_k=route_depth)
                if result.status == "succeeded":
                    route_outputs[route] = result.candidates
                    route_status[route] = {"status": "succeeded", "candidate_count": len(result.candidates),
                                           "elapsed_ms": result.elapsed_ms or round((time.perf_counter() - started) * 1000, 3)}
                else:
                    route_status[route] = {"status": result.status, "reason": result.reason}
                route_manifests[route] = result.manifest or self.manifests.get(route, {})
            except Exception as exc:
                route_status[route] = {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}
        candidates = reciprocal_rank_fusion(route_outputs, request_id=request.request_id,
                                            top_k=request.top_k, k=60,
                                            canonicalize=self.artifact_aliases.resolve_artifact_id)
        docs = self.snapshot.by_id()
        for candidate in candidates:
            document = docs.get(candidate["artifact_id"])
            if not document:
                continue
            candidate["explanation"]["matched_topics"] = sorted(set(request.topic_ids).intersection(document.topics))
            candidate["explanation"]["freshness_basis"] = document.freshness_basis
            candidate["explanation"]["content_published_at"] = document.published_at
        result = {
            "request": request.to_dict(),
            "corpus_hash": self.snapshot.corpus_hash,
            "source_tree_hash": self.snapshot.source_tree_hash,
            "index_manifests": route_manifests,
            "routes_requested": selected,
            "routes_executed": [route for route, value in route_status.items() if value["status"] == "succeeded"],
            "routes_skipped": [{"route": route, **value} for route, value in route_status.items() if value["status"] in {"skipped", "deferred"}],
            "routes_failed": [{"route": route, **value} for route, value in route_status.items() if value["status"] == "failed"],
            "route_status": route_status,
            "route_candidates": route_outputs,
            "candidates": candidates,
            "timings": {"routes_ms": {route: value.get("elapsed_ms", 0.0) for route, value in route_status.items()}},
            "reproducibility": {"retriever_versions": self.registry.versions(), "config": {
                                    "rrf_k": 60, "route_depth": route_depth, "final_top_k": request.top_k,
                                    "corpus_profile": request.filters.get("corpus_profile", "research-default")},
                                "embedding_model_revision": _dense_revision(self.registry)},
        }
        result["timings"]["total_ms"] = round((time.perf_counter() - total_started) * 1000, 3)
        if persist:
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
            path = self.runtime_dir / "runs" / f"{request.request_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            result["run_path"] = str(path)
        return result

    def eligible_routes(self, request: RetrievalRequest) -> list[str]:
        routes = []
        if request.query:
            routes.extend(route for route in ("bm25", "dense") if route in self.registry.routes())
        if request.seed_artifact_ids and "graph" in self.registry.routes():
            routes.append("graph")
        if request.topic_ids and "topic" in self.registry.routes():
            routes.append("topic")
        if request.source_ids and "source" in self.registry.routes():
            routes.append("source")
        if request.seed_artifact_ids and "semantic-scholar" in self.registry.routes():
            routes.append("semantic-scholar")
        return routes


def infer_topic_ids(query: str) -> list[str]:
    import yaml
    from ..topics import CATALOG
    value: Any = yaml.safe_load(Path(CATALOG).read_text(encoding="utf-8"))
    normalized = " ".join(query.casefold().replace("-", " ").split())
    result = set()
    for topic in value.get("topics", []) if isinstance(value, dict) else []:
        if not isinstance(topic, dict):
            continue
        options = [str(topic.get("name") or ""), str(topic.get("topic_id") or "").replace("topic-", "").replace("-", " "),
                   *(str(item).replace("-", " ") for item in topic.get("aliases", []))]
        if any(option and " ".join(option.casefold().split()) in normalized for option in options):
            result.add(str(topic["topic_id"]))
    bilingual = {"搜索智能体": "topic-search-agent", "agentic rl": "topic-agentic-rl",
                 "memory": "topic-memory", "rag": "topic-rag", "harness": "topic-agent-harness",
                 "verifier": "topic-verifier", "reward": "topic-reward",
                 "inference serving": "topic-efficiency-systems-and-deployment",
                 "multimodal agent": "topic-multimodal-models-and-world-models",
                 "post-training": "topic-post-training-and-alignment", "ai for science": "topic-domain-specific-llms-and-ai-for-science"}
    result.update(topic for phrase, topic in bilingual.items() if phrase in normalized)
    return sorted(result)


def read_run(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value.get("request", {}).get("request_id"):
        raise ValueError("retrieval run is malformed")
    return value


def explain_candidate(run: dict[str, Any], artifact_id: str) -> dict[str, Any]:
    canonical_id = str(artifact_id)
    candidate = next((item for item in run.get("candidates", []) if item.get("artifact_id") == canonical_id), None)
    if candidate is None:
        raise ValueError("retrieval candidate not found in run")
    return candidate


def _dense_revision(registry: RetrieverRegistry) -> str | None:
    try:
        return str(registry.get("dense").backend.model_revision)
    except (KeyError, AttributeError, ValueError):
        return None
