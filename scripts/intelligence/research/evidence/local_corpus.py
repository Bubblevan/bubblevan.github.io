from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from ...aliases import ArtifactAliases
from ...graph.store import GraphStore
from ...ids import stable_id
from ...models import now_utc
from ...repositories.artifacts import ArtifactRepository
from ...retrieval.bm25 import BM25Retriever
from ...retrieval.corpus import CorpusSnapshot, build_snapshot
from ...retrieval.dense import DenseRetriever, SentenceTransformerBackend
from ...retrieval.engine import RetrievalEngine, infer_topic_ids
from ...retrieval.graph import GraphRetriever
from ...retrieval.manifest import dense_freshness
from ...retrieval.request import make_request
from ...retrieval.registry import RetrieverRegistry
from ...retrieval.source import SourceRetriever
from ...retrieval.topic import TopicRetriever
from ...store import JsonlStore
from .base import EvidenceBudget


class LocalCorpusEvidenceBackend:
    """Offline evidence extraction from canonical local records and exact graph edges."""

    def __init__(self, store_dir: str | Path, runtime_dir: str | Path, *, allow_dense: bool = True):
        self.store_dir = Path(store_dir)
        self.runtime_dir = Path(runtime_dir)
        self.allow_dense = allow_dense
        self.store = JsonlStore(self.store_dir)
        self.artifacts = ArtifactRepository(self.store)
        self.last_retrieval: dict[str, Any] = {}

    def gather(self, question: str, artifact_ids: list[str], budget: EvidenceBudget) -> list[dict[str, Any]]:
        snapshot = build_snapshot(self.store)
        documents = snapshot.by_id()
        seeds = list(dict.fromkeys(self.artifacts.resolve_id(str(item)) for item in artifact_ids))
        missing = [item for item in seeds if item not in documents]
        if missing:
            raise ValueError(f"unknown research seed Artifact ID(s): {missing}")
        if len(seeds) > budget.max_evidence_artifacts:
            raise ValueError(f"selected seed Artifacts exceed evidence limit ({budget.max_evidence_artifacts})")
        if len(seeds) > budget.max_retrieved_artifacts:
            raise ValueError(f"selected seed Artifacts exceed retrieval limit ({budget.max_retrieved_artifacts})")

        status = dense_freshness(snapshot, self.runtime_dir)
        registry = RetrieverRegistry()
        registry.register(BM25Retriever())
        registry.register(TopicRetriever())
        registry.register(SourceRetriever(str(self.store_dir)))
        registry.register(GraphRetriever(str(self.store_dir)))
        engine = RetrievalEngine(snapshot, registry, store_dir=str(self.store_dir), runtime_dir=str(self.runtime_dir))
        build_result = engine.build(routes=["bm25", "topic", "source", "graph"])
        query = question.strip() or " ".join(documents[item].title for item in seeds).strip()
        request = make_request(query, seed_artifact_ids=seeds, top_k=budget.max_retrieved_artifacts)
        route_status: dict[str, Any] = {key: value for key, value in build_result["failed_routes"].items()}
        route_ids: dict[str, list[str]] = {"seed": seeds, "bm25": [], "dense": [], "topic": [], "source": [], "graph": []}

        def search(route_names: list[str], req) -> list[str]:
            if any(name in engine.build_failures for name in route_names):
                return []
            result = engine.search(req, routes=route_names, persist=False)
            route_status.update(result["route_status"])
            return [str(item["artifact_id"]) for item in result["candidates"]]

        route_ids["bm25"] = search(["bm25"], request)
        topic_ids = infer_topic_ids(query)
        if topic_ids:
            topic_request = make_request(query, seed_artifact_ids=seeds, topic_ids=topic_ids,
                                         top_k=budget.max_retrieved_artifacts)
            route_ids["topic"] = search(["topic"], topic_request)

        initial_ids = list(dict.fromkeys(seeds + route_ids["bm25"] + route_ids["topic"]))
        source_ids = sorted({source_id for artifact_id in initial_ids[:budget.max_retrieved_artifacts]
                             for source_id in documents.get(artifact_id, ()).source_ids})
        if source_ids:
            source_request = make_request(query, seed_artifact_ids=seeds, source_ids=source_ids,
                                          top_k=budget.max_retrieved_artifacts)
            route_ids["source"] = search(["source"], source_request)

        graph_seeds = list(dict.fromkeys(seeds + route_ids["bm25"][:5]))[:10]
        if graph_seeds:
            graph_request = make_request(query, seed_artifact_ids=graph_seeds,
                                         top_k=budget.max_retrieved_artifacts)
            route_ids["graph"] = search(["graph"], graph_request)

        if not self.allow_dense:
            route_status["dense"] = {"status": "skipped", "reason": "dense disabled in Streamlit request path"}
        elif status["dense_status"] == "fresh":
            try:
                manifest_path = self.runtime_dir / "retrieval" / "dense" / "manifest.json"
                import json
                dense_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                model_id = str(dense_manifest.get("model_id") or "Qwen/Qwen3-Embedding-0.6B")
                revision = dense_manifest.get("model_revision")
                registry.register(DenseRetriever(SentenceTransformerBackend(model_id, revision=revision)))
                engine.build(routes=["dense"])
                if "dense" not in engine.build_failures:
                    route_ids["dense"] = search(["dense"], request)
                else:
                    route_status["dense"] = {"status": "unavailable", "reason": "index build failed"}
            except Exception as exc:
                route_status["dense"] = {"status": "unavailable", "reason": type(exc).__name__}
                status["dense_status"] = "unavailable"
        else:
            route_status["dense"] = {"status": "skipped", "reason": status["dense_status"]}

        candidates: list[str] = []
        for route in ("seed", "bm25", "dense", "topic", "source", "graph"):
            for artifact_id in route_ids[route]:
                if artifact_id in documents and artifact_id not in candidates:
                    candidates.append(artifact_id)
        candidates = candidates[:budget.max_retrieved_artifacts]
        evidence_artifacts = candidates[:budget.max_evidence_artifacts]
        refs = self._make_evidence(snapshot, evidence_artifacts, budget)
        self.last_retrieval = {
            "corpus_hash": snapshot.corpus_hash,
            "source_tree_hash": snapshot.source_tree_hash,
            "dense_status": status["dense_status"],
            "dense_manifest_corpus_hash": status.get("dense_manifest_corpus_hash"),
            "routes": route_status,
            "route_candidates": {key: len(value) for key, value in route_ids.items()},
            "candidate_artifact_ids": candidates,
            "evidence_artifact_ids": evidence_artifacts,
        }
        return refs

    def _make_evidence(self, snapshot: CorpusSnapshot, artifact_ids: list[str], budget: EvidenceBudget) -> list[dict[str, Any]]:
        canonical = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        observations = {str(row["observation_id"]): row for row in self.store.iter_records("observation")}
        aliases = ArtifactAliases(self.store_dir)
        redirects = aliases.canonical_redirect_map()
        graph_evidence: dict[str, list[tuple[str, str | None, str | None]]] = {}
        selected = set(artifact_ids)
        for edge in GraphStore(self.store_dir).iter_edges():
            endpoints = []
            for raw in (str(edge["subject_id"]), str(edge["object_id"])):
                if raw.startswith("art-"):
                    endpoints.append(redirects.get(raw, raw))
            for artifact_id in set(endpoints).intersection(selected):
                for item in edge.get("evidence", []):
                    evidence_type = str(item.get("evidence_type") or "")
                    if evidence_type not in {"exact_provider_metadata", "explicit_source_link"}:
                        continue
                    source_id = str(edge["subject_id"]) if str(edge["subject_id"]).startswith("src-") else None
                    text = (f"Exact graph relation: {edge['subject_id']} --{edge['predicate']}--> "
                            f"{edge['object_id']}; edge={edge['edge_id']}; evidence_type={evidence_type}; "
                            f"provider={item.get('provider') or 'local-graph'}")
                    graph_evidence.setdefault(artifact_id, []).append(
                        (f"graph-edge:{edge['edge_id']}", source_id,
                         str(item.get("observation_id") or "") or None, text))
        refs: list[dict[str, Any]] = []
        chars = 0
        for artifact_id in artifact_ids:
            artifact = canonical.get(artifact_id)
            if not artifact:
                continue
            doc = snapshot.by_id().get(artifact_id)
            url = _safe_url(str(artifact.get("canonical_url") or ""))
            entries: list[tuple[str, str, str | None, str | None, str, str]] = []
            stored_title = str(artifact.get("title") or "").strip()
            title = stored_title or str(doc.title if doc else "").strip()
            summary = str(artifact.get("summary") or "").strip()
            if stored_title:
                entries.append(("metadata", "title", None, None, stored_title, "explicit_provider_metadata"))
            if summary:
                entries.append(("metadata", "summary", None, None, summary[:4000], "explicit_provider_metadata"))
            observation_ids = [str(item) for item in artifact.get("observation_ids", [])]
            observation_ids.sort(key=lambda item: (str(observations.get(item, {}).get("observed_at") or ""), item), reverse=True)
            for observation_id in observation_ids[:3]:
                observation = observations.get(observation_id)
                if not observation:
                    continue
                body = "\n\n".join(part.strip() for part in
                                    (str(observation.get("title") or ""), str(observation.get("text") or "")) if part.strip())
                if body:
                    entries.append(("observation", observation_id,
                                    str(observation.get("source_id") or "") or None,
                                    observation_id, body[:20_000], "observation_text"))
            entries.extend(("section", locator, source_id, observation_id, body,
                            "explicit_provider_metadata")
                           for locator, source_id, observation_id, body in graph_evidence.get(artifact_id, []))
            used_for_artifact = 0
            for locator_type, locator_value, source_id, observation_id, text_value, evidence_type in entries:
                if len(refs) >= budget.max_evidence_refs or used_for_artifact >= budget.max_refs_per_artifact:
                    break
                remaining = budget.max_evidence_chars - chars
                if remaining <= 0:
                    break
                text_value = text_value[:remaining]
                if not text_value.strip():
                    continue
                text_hash = hashlib.sha256(text_value.encode("utf-8")).hexdigest()
                locator = {"type": locator_type, "value": locator_value}
                identity = f"{artifact_id}|{locator_type}|{locator_value}|{text_hash}"
                row = {
                    "schema": "bubblevan/evidence-ref/v1",
                    "evidence_id": stable_id("ev", "research-evidence", identity),
                    "artifact_id": artifact_id,
                    "observation_id": observation_id,
                    "source_id": source_id,
                    "canonical_url": url or None,
                    "title": title or None,
                    "published_at": artifact.get("published_at"),
                    "locator": locator,
                    "text": text_value,
                    "text_sha256": text_hash,
                    "evidence_type": evidence_type,
                    "retrieved_at": now_utc(),
                }
                refs.append(row)
                chars += len(text_value)
                used_for_artifact += 1
            if len(refs) >= budget.max_evidence_refs or chars >= budget.max_evidence_chars:
                break
        return refs


def _safe_url(value: str) -> str:
    if not value:
        return ""
    parts = urlsplit(value)
    # Evidence must remain reviewable without leaking share tokens or credentials.
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
