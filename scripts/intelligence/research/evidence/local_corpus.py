from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
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
from ...retrieval.engine import RetrievalEngine
from ...retrieval.expansion import expand_query
from ...retrieval.fusion import reciprocal_rank_fusion
from ...retrieval.manifest import dense_freshness
from ...retrieval.request import make_request
from ...retrieval.registry import RetrieverRegistry
from ...store import JsonlStore
from .base import EvidenceBudget, ResearchPerspectivePlan
from ..quality import classify_artifact


class LocalCorpusEvidenceBackend:
    """Offline evidence extraction from canonical local records and exact graph edges."""

    def __init__(self, store_dir: str | Path, runtime_dir: str | Path, *, allow_dense: bool = True,
                 real_case: bool = False,
                 perspective_plan: ResearchPerspectivePlan | dict[str, Any] | None = None):
        self.store_dir = Path(store_dir)
        self.runtime_dir = Path(runtime_dir)
        self.allow_dense = allow_dense
        self.real_case = real_case
        self.perspective_plan = ResearchPerspectivePlan.from_value(perspective_plan)
        self.store = JsonlStore(self.store_dir)
        self.artifacts = ArtifactRepository(self.store)
        self.last_retrieval: dict[str, Any] = {}
        self.metadata_fallback = False

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

        canonical = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        sources = {str(row["source_id"]): row for row in self.store.iter_records("source")}
        class_by_artifact = {artifact_id: classify_artifact(artifact, sources)
                             for artifact_id, artifact in canonical.items()}
        status = dense_freshness(snapshot, self.runtime_dir)
        registry = RetrieverRegistry()
        registry.register(BM25Retriever())
        routes = ["bm25"]
        dense_ready = self.allow_dense and status["dense_status"] == "fresh"
        if dense_ready:
            manifest_path = self.runtime_dir / "retrieval" / "dense" / "manifest.json"
            import json
            dense_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            model_id = str(dense_manifest.get("model_id") or "Qwen/Qwen3-Embedding-0.6B")
            revision = dense_manifest.get("model_revision")
            registry.register(DenseRetriever(SentenceTransformerBackend(model_id, revision=revision)))
            routes.append("dense")
        engine = RetrievalEngine(snapshot, registry, store_dir=str(self.store_dir), runtime_dir=str(self.runtime_dir))
        build_result = engine.build(routes=routes)
        query = question.strip() or " ".join(documents[item].title for item in seeds).strip()
        entity_names = {str(name) for document in snapshot.documents
                        for name in (*document.authors, *document.organizations,
                                     *(str(item.get("name") or "") for item in document.graph_entities))
                        if str(name).strip()}
        request = make_request(query, seed_artifact_ids=seeds,
                               top_k=max(20, budget.max_retrieved_artifacts),
                               expanded_terms=expand_query(query, entity_names=entity_names))
        route_status: dict[str, Any] = {key: value for key, value in build_result["failed_routes"].items()}
        base_routes = ["bm25"] + (["dense"] if dense_ready else [])
        if not dense_ready:
            route_status["dense"] = {"status": "skipped", "reason": status["dense_status"] if self.allow_dense else "dense_disabled"}

        lane_limits = {"general": min(20, budget.max_retrieved_artifacts),
                       "first_party": 12, "curator": 8, "discussion": 5}
        plan = self.perspective_plan
        enabled_lanes = ["general", *(name for name in ("first_party", "curator", "discussion")
                                        if bool(getattr(plan, name)))]
        lane_results: dict[str, list[dict[str, Any]]] = {}
        lane_routes: dict[str, dict[str, list[dict[str, Any]]]] = {}
        lane_status: dict[str, dict[str, Any]] = {}
        for lane in enabled_lanes:
            if lane == "general":
                eligible_docs = list(snapshot.documents)
            else:
                eligible_docs = [document for document in snapshot.documents
                                 if class_by_artifact.get(document.artifact_id) == lane]
            route_outputs: dict[str, list[dict[str, Any]]] = {}
            lane_request = replace(request, top_k=lane_limits[lane])
            for route in base_routes:
                route_key = f"{lane}:{route}"
                if route in engine.build_failures:
                    lane_status[route_key] = {"status": "failed", "reason": engine.build_failures[route]}
                    continue
                try:
                    result = registry.get(route).retrieve(
                        lane_request, documents=eligible_docs, top_k=lane_limits[lane])
                    route_outputs[route] = result.candidates
                    lane_status[route_key] = {"status": result.status,
                                               "candidate_count": len(result.candidates),
                                               "elapsed_ms": result.elapsed_ms}
                except Exception as exc:
                    lane_status[route_key] = {"status": "failed", "reason": type(exc).__name__}
            lane_routes[lane] = route_outputs
            lane_results[lane] = reciprocal_rank_fusion(
                route_outputs, request_id=request.request_id, top_k=lane_limits[lane],
                canonicalize=engine.artifact_aliases.resolve_artifact_id)
        route_status.update(lane_status)
        route_ids_by_lane = {lane: [str(item["artifact_id"]) for item in rows]
                             for lane, rows in lane_results.items()}
        # Keep the explicitly selected seed papers eligible even when a broad lane
        # ranks them below its fixed candidate depth.
        candidate_union: list[str] = [item for item in seeds if item in documents]
        for lane in enabled_lanes:
            for artifact_id in route_ids_by_lane.get(lane, []):
                if artifact_id in documents and artifact_id not in candidate_union:
                    candidate_union.append(artifact_id)
        seed_titles = [documents[item].title for item in seeds]
        observation_texts = self._observation_text_by_artifact(candidate_union, canonical)
        relevance = self._relevant_candidates(lane_routes, observation_texts, class_by_artifact,
                                             query, seed_titles, set(seeds))
        selection_lane_ids = dict(route_ids_by_lane)
        if plan.first_party:
            seeded_first_party = [item for item in seeds if class_by_artifact.get(item) == "first_party"]
            selection_lane_ids["first_party"] = list(dict.fromkeys(
                [*seeded_first_party, *route_ids_by_lane.get("first_party", [])]))
        if self.real_case:
            evidence_artifacts = self._select_lane_evidence(
                candidate_union, selection_lane_ids, relevance, canonical,
                class_by_artifact, plan, budget.max_evidence_artifacts)
        else:
            evidence_artifacts = candidate_union[:budget.max_evidence_artifacts]
        refs = self._make_evidence(snapshot, evidence_artifacts, budget)
        substantive_refs = sum(1 for row in refs
                               if str(row.get("evidence_type") or "") != "explicit_provider_metadata")
        metadata_refs = len(refs) - substantive_refs
        metadata_share = metadata_refs / len(refs) if refs else 0.0
        self.metadata_fallback = bool(metadata_refs and substantive_refs < budget.max_evidence_refs)
        self.last_retrieval = {
            "corpus_hash": snapshot.corpus_hash,
            "source_tree_hash": snapshot.source_tree_hash,
            "dense_status": status["dense_status"],
            "dense_manifest_corpus_hash": status.get("dense_manifest_corpus_hash"),
            "routes": route_status,
            "routes_requested": [f"{lane}:{route}" for lane in enabled_lanes for route in base_routes],
            "graph_mode": "exact_provenance_lookup_only",
            "perspective_plan": plan.to_dict(),
            "lane_limits": lane_limits,
            "lane_candidates": route_ids_by_lane,
            "lane_candidate_counts": {lane: len(ids) for lane, ids in route_ids_by_lane.items()},
            "candidate_union_count": len(candidate_union),
            "relevant_curator_candidate_count": sum(1 for item in route_ids_by_lane.get("curator", [])
                                                     if item in relevance),
            "relevant_discussion_candidate_count": sum(1 for item in route_ids_by_lane.get("discussion", [])
                                                        if item in relevance),
            "route_candidates": {
                "seed": len(seeds),
                "bm25": len(lane_routes.get("general", {}).get("bm25", [])),
                "dense": len(lane_routes.get("general", {}).get("dense", [])),
                "bm25_dense_fused": len(lane_results.get("general", [])),
                "general": len(route_ids_by_lane.get("general", [])),
                **{lane: len(ids) for lane, ids in route_ids_by_lane.items()},
            },
            "candidate_artifact_ids": candidate_union,
            "evidence_artifact_ids": evidence_artifacts,
            "metadata_ref_count": metadata_refs,
            "substantive_ref_count": substantive_refs,
            "metadata_share": metadata_share,
            "metadata_fallback": self.metadata_fallback,
        }
        return refs

    @staticmethod
    def _relevant_candidates(lane_routes: dict[str, dict[str, list[dict[str, Any]]]],
                             observation_texts: dict[str, str], class_by_artifact: dict[str, str],
                             question: str, seed_titles: list[str], seed_ids: set[str]) -> set[str]:
        ranked: set[str] = set()
        for route_outputs in lane_routes.values():
            for route, rows in route_outputs.items():
                for row in rows:
                    score = row.get("raw_score")
                    if isinstance(score, (int, float)) and not isinstance(score, bool):
                        if (route == "bm25" and score > 0) or (route == "dense" and score >= 0.20):
                            ranked.add(str(row.get("artifact_id") or ""))
        # Explicit research seeds remain eligible even when a route ranks them
        # below its fixed candidate depth. They are user-selected context, not
        # unrequested retrieval expansion.
        result: set[str] = {artifact_id for artifact_id in seed_ids
                            if class_by_artifact.get(artifact_id) == "first_party"}
        for artifact_id in ranked:
            kind = class_by_artifact.get(artifact_id)
            content = observation_texts.get(artifact_id, "")
            if kind == "first_party":
                if artifact_id in seed_ids or LocalCorpusEvidenceBackend._has_first_party_topic_match(content):
                    result.add(artifact_id)
            elif kind in {"curator", "discussion"}:
                if LocalCorpusEvidenceBackend._has_specific_perspective_anchor(content, question, seed_titles):
                    result.add(artifact_id)
            else:
                result.add(artifact_id)
        return result

    @staticmethod
    def _has_first_party_topic_match(text: str) -> bool:
        content = " ".join(re.sub(r"[^a-z0-9]+", " ", str(text).casefold()).split())
        has_search_agent = bool(re.search(r"\bsearch agents?\b", content))
        has_training_method = bool(re.search(
            r"\b(training|trained|post training|fine tuning|finetuning|distillation|"
            r"self evolving|self evolution|reinforcement learning|\brl\b|reward|"
            r"credit assignment|policy optimization)\b", content))
        return has_search_agent and has_training_method

    def _observation_text_by_artifact(self, artifact_ids: list[str],
                                      artifacts: dict[str, dict[str, Any]]) -> dict[str, str]:
        observation_ids = {str(value) for artifact_id in artifact_ids
                           for value in artifacts.get(artifact_id, {}).get("observation_ids", [])}
        observations = {str(row["observation_id"]): row
                        for row in self.store.iter_records("observation")
                        if str(row.get("observation_id") or "") in observation_ids}
        result = {}
        for artifact_id in artifact_ids:
            parts = []
            for observation_id in artifacts.get(artifact_id, {}).get("observation_ids", []):
                observation = observations.get(str(observation_id))
                if not observation:
                    continue
                text = "\n".join(str(observation.get(key) or "") for key in ("title", "text")).strip()
                if text:
                    parts.append(text)
            result[artifact_id] = "\n\n".join(parts)
        return result

    @staticmethod
    def _has_specific_perspective_anchor(text: str, question: str, seed_titles: list[str]) -> bool:
        def normalize(value: str) -> str:
            return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).split())

        content = normalize(text)
        has_search_agent_scope = bool(re.search(r"\bsearch[\s-]+agents?\b", content))
        method_anchors = {
            "igsd", "environment verified", "hindsight self distillation",
            "difficulty rewards", "process credit assignment", "rubric grounded",
            "information gain gated", "dr free", "dr credit",
        }
        for title in seed_titles:
            raw = str(title)
            method_anchors.update(normalize(item) for item in re.findall(r"\b[A-Z][A-Z0-9]{2,}\b", raw))
        has_seed_method = any(re.search(rf"\b{re.escape(anchor)}\b", content) for anchor in method_anchors)
        return has_search_agent_scope or has_seed_method

    def _select_lane_evidence(self, candidates: list[str], lane_ids: dict[str, list[str]],
                              relevant: set[str], artifacts: dict[str, dict[str, Any]],
                              class_by_artifact: dict[str, str], plan: ResearchPerspectivePlan,
                              limit: int) -> list[str]:
        if limit <= 0:
            return []
        lane_order = ("first_party", "curator", "discussion")
        enabled = {"first_party": plan.first_party, "curator": plan.curator,
                   "discussion": plan.discussion}
        ordered_by_kind: dict[str, list[str]] = {lane: [] for lane in lane_order}
        for lane in lane_order:
            if not enabled[lane]:
                continue
            ordered = [*lane_ids.get(lane, []), *lane_ids.get("general", [])]
            for artifact_id in ordered:
                if (artifact_id not in candidates or class_by_artifact.get(artifact_id) != lane
                        or artifact_id in ordered_by_kind[lane]):
                    continue
                if lane in {"first_party", "curator", "discussion"} and artifact_id not in relevant:
                    continue
                ordered_by_kind[lane].append(artifact_id)

        goals = {"first_party": min(8, len(ordered_by_kind["first_party"])),
                 "curator": min(3, len(ordered_by_kind["curator"])),
                 "discussion": min(2, len(ordered_by_kind["discussion"]))}
        while sum(goals.values()) > limit:
            if goals["first_party"] > 6:
                goals["first_party"] -= 1
            elif goals["discussion"]:
                goals["discussion"] -= 1
            elif goals["curator"]:
                goals["curator"] -= 1
            else:
                goals["first_party"] -= 1

        selected: list[str] = []
        source_counts: dict[str, int] = {}
        for lane in lane_order:
            added = 0
            for artifact_id in ordered_by_kind[lane]:
                if artifact_id in selected or added >= goals[lane] or len(selected) >= limit:
                    continue
                artifact_sources = sorted(str(item) for item in artifacts.get(artifact_id, {}).get("source_ids", []) if item)
                if any(source_counts.get(source_id, 0) >= 3 for source_id in artifact_sources):
                    continue
                selected.append(artifact_id)
                added += 1
                for source_id in artifact_sources:
                    source_counts[source_id] = source_counts.get(source_id, 0) + 1
        return selected

    def _make_evidence(self, snapshot: CorpusSnapshot, artifact_ids: list[str], budget: EvidenceBudget) -> list[dict[str, Any]]:
        canonical = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        observations = {str(row["observation_id"]): row for row in self.store.iter_records("observation")}
        aliases = ArtifactAliases(self.store_dir)
        redirects = aliases.canonical_redirect_map()
        graph_evidence: dict[str, list[tuple[str, str | None, str | None, str]]] = {}
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
        substantive_by_artifact: dict[str, list[tuple[str, str, str | None, str | None, str, str]]] = {}
        metadata_by_artifact: dict[str, list[tuple[str, str, str | None, str | None, str, str]]] = {}
        for artifact_id in artifact_ids:
            artifact = canonical.get(artifact_id)
            if not artifact:
                continue
            doc = snapshot.by_id().get(artifact_id)
            url = _safe_url(str(artifact.get("canonical_url") or ""))
            stored_title = str(artifact.get("title") or "").strip()
            title = stored_title or str(doc.title if doc else "").strip()
            summary = str(artifact.get("summary") or "").strip()
            substantive_entries: list[tuple[str, str, str | None, str | None, str, str]] = []
            metadata_entries: list[tuple[str, str, str | None, str | None, str, str]] = []
            observation_ids = [str(item) for item in artifact.get("observation_ids", [])]
            observation_ids.sort(key=lambda item: (str(observations.get(item, {}).get("observed_at") or ""), item), reverse=True)
            for observation_id in observation_ids[:3]:
                observation = observations.get(observation_id)
                if not observation:
                    continue
                body = "\n\n".join(part.strip() for part in
                                    (str(observation.get("title") or ""), str(observation.get("text") or "")) if part.strip())
                if body:
                    substantive_entries.append(("observation", observation_id,
                                                str(observation.get("source_id") or "") or None,
                                                observation_id, body[:20_000], "observation_text"))
            if summary:
                metadata_entries.append(("metadata", "summary", None, None, summary[:4000],
                                         "explicit_provider_metadata"))
            metadata_entries.extend(("section", locator, source_id, observation_id, body,
                                     "explicit_provider_metadata")
                                    for locator, source_id, observation_id, body
                                    in graph_evidence.get(artifact_id, []))
            substantive_by_artifact[artifact_id] = substantive_entries
            metadata_by_artifact[artifact_id] = metadata_entries

        refs: list[dict[str, Any]] = []
        chars = 0
        per_artifact_counts: dict[str, int] = {}
        metadata_counts: dict[str, int] = {}

        def append_ref(artifact_id: str, entry: tuple[str, str, str | None, str | None, str, str]) -> bool:
            nonlocal chars
            if len(refs) >= budget.max_evidence_refs:
                return False
            if per_artifact_counts.get(artifact_id, 0) >= budget.max_refs_per_artifact:
                return False
            remaining = budget.max_evidence_chars - chars
            if remaining <= 0:
                return False
            locator_type, locator_value, source_id, observation_id, text_value, evidence_type = entry
            text_value = text_value[:remaining]
            if not text_value.strip():
                return False
            artifact = canonical[artifact_id]
            document = snapshot.by_id().get(artifact_id)
            title = str(artifact.get("title") or (document.title if document else "")).strip()
            url = _safe_url(str(artifact.get("canonical_url") or ""))
            text_hash = hashlib.sha256(text_value.encode("utf-8")).hexdigest()
            locator = {"type": locator_type, "value": locator_value}
            identity = f"{artifact_id}|{locator_type}|{locator_value}|{text_hash}"
            refs.append({
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
            })
            chars += len(text_value)
            per_artifact_counts[artifact_id] = per_artifact_counts.get(artifact_id, 0) + 1
            if evidence_type == "explicit_provider_metadata":
                metadata_counts[artifact_id] = metadata_counts.get(artifact_id, 0) + 1
            return True

        # Fill the packet with source/Observation text first across all selected Artifacts.
        for artifact_id in artifact_ids:
            for entry in substantive_by_artifact.get(artifact_id, []):
                if not append_ref(artifact_id, entry):
                    if len(refs) >= budget.max_evidence_refs or chars >= budget.max_evidence_chars:
                        break
            if len(refs) >= budget.max_evidence_refs or chars >= budget.max_evidence_chars:
                break

        # Metadata may fill a bounded remainder only. Three substantive refs permit at most one
        # metadata ref, which guarantees metadata is no more than 25% of the final packet.
        substantive_count = len(refs)
        metadata_cap = min(
            budget.max_metadata_refs_per_artifact * len(artifact_ids),
            substantive_count // 3,
            max(0, budget.max_evidence_refs - len(refs)),
        )
        added_metadata = 0
        for artifact_id in artifact_ids:
            if added_metadata >= metadata_cap:
                break
            if metadata_counts.get(artifact_id, 0) >= budget.max_metadata_refs_per_artifact:
                continue
            for entry in metadata_by_artifact.get(artifact_id, []):
                if append_ref(artifact_id, entry):
                    added_metadata += 1
                    break
                if len(refs) >= budget.max_evidence_refs or chars >= budget.max_evidence_chars:
                    break
        self.metadata_fallback = bool(added_metadata and substantive_count < budget.max_evidence_refs)
        return refs


def _safe_url(value: str) -> str:
    if not value:
        return ""
    parts = urlsplit(value)
    # Evidence must remain reviewable without leaking share tokens or credentials.
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
