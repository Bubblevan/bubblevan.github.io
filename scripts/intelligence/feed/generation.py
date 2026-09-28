from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..aliases import ArtifactAliases
from ..graph.store import GraphStore
from ..ids import source_id, stable_id
from ..models import now_utc
from ..retrieval.bm25 import BM25Retriever
from ..retrieval.corpus import CorpusSnapshot, RetrievalDocument, build_snapshot
from ..retrieval.dense import DenseRetriever, SentenceTransformerBackend
from ..retrieval.graph import GraphRetriever
from ..retrieval.request import make_request
from ..retrieval.source import SourceRetriever
from ..retrieval.topic import TopicRetriever
from ..schema_validator import validate_record
from ..store import JsonlStore
from ..topics import topic_aliases
from .feedback_projection import project_feedback
from .models import profile_hash, stable_hash
from .policy import rank_and_select
from .storage import FeedRepository


ROOT = Path(__file__).resolve().parents[3]
SOURCE_CATALOG = ROOT / "data" / "intelligence" / "sources.yaml"
TOPIC_CATALOG = ROOT / "data" / "intelligence" / "topics.yaml"
POLICY_VERSION = "feed-v0"


def build_feed(store_dir: Path | str, runtime_dir: Path | str, repository: FeedRepository, *,
               feed_date: str, refresh: bool = False, lookback_days: int = 7,
               model: str = "Qwen/Qwen3-Embedding-0.6B", revision: str | None = None,
               device: str | None = None, experimental_graph: bool = False,
               dense_resource_factory: Any = None) -> dict[str, Any]:
    requested_date = date.fromisoformat(feed_date).isoformat()
    if lookback_days < 1 or lookback_days > 90:
        raise ValueError("lookback_days must be between 1 and 90")
    current = repository.current_run(requested_date)
    if current is not None and not refresh:
        return current
    profile = repository.load_profile()
    if not repository.profile_path.exists():
        repository.save_profile(profile)
    store = JsonlStore(store_dir)
    snapshot = build_snapshot(store)
    all_feedback = repository.all_feedback(store)
    projection = project_feedback(all_feedback)
    eligible, all_docs = _recent_documents(snapshot, requested_date, lookback_days)
    source_names = _source_names(store)
    topic_names = _topic_names()

    bm25 = BM25Retriever()
    bm25_status = "unavailable"
    dense: DenseRetriever | None = None
    dense_status = "unavailable"
    try:
        bm25.build(snapshot, str(runtime_dir))
        bm25_status = "available"
    except Exception as exc:  # one local route failure must not prevent a useful recent feed
        bm25_status = f"unavailable:{type(exc).__name__}"
    if dense_resource_factory:
        dense, dense_status = dense_resource_factory(snapshot, str(runtime_dir), model, revision, device)
    else:
        dense, dense_status = load_dense_resource(snapshot, str(runtime_dir), model, revision, device)

    topics = TopicRetriever()
    source = SourceRetriever(str(store_dir))
    source.build(snapshot, str(runtime_dir))
    graph = None
    if experimental_graph:
        graph = GraphRetriever(str(store_dir))
        graph.build(snapshot, str(runtime_dir))
    candidates = _candidate_features(eligible, profile, projection, source_names, topic_names)
    by_id = {row["artifact_id"]: row for row in candidates}
    routes: dict[str, Any] = {"recent-primary": {"status": "succeeded", "candidates": len(eligible)},
                              "source": {"status": "succeeded", "candidates": 0},
                              "topic": {"status": "succeeded", "candidates": 0},
                              "bm25": {"status": bm25_status, "candidates": 0},
                              "dense": {"status": dense_status, "candidates": 0}}
    selected_sources = sorted(set(profile.get("followed_source_ids", [])))
    if selected_sources:
        request = make_request(source_ids=selected_sources, as_of=_end_of_day(requested_date), top_k=100)
        result = source.retrieve(request, documents=all_docs, top_k=100)
        _merge_route(by_id, result.candidates, "followed_source")
        routes["source"]["candidates"] = len(result.candidates)
        exact_source_candidates = {row["artifact_id"] for row in result.candidates}
        for item in eligible:
            if set(selected_sources).intersection(item.source_ids):
                exact_source_candidates.add(item.artifact_id)
                if item.artifact_id in by_id:
                    _add_evidence(by_id[item.artifact_id], "source", 1, {"matched_source_ids": sorted(set(selected_sources).intersection(item.source_ids))})
        for artifact in exact_source_candidates:
            if artifact in by_id:
                by_id[artifact]["followed_source_match"] = True
        routes["source"]["candidates"] = len(exact_source_candidates)

    selected_topics = sorted(set(profile.get("selected_topic_ids", [])))
    for topic_id in selected_topics:
        query = _topic_query(topic_id, topic_names)
        request = make_request(query, topic_ids=[topic_id], as_of=_end_of_day(requested_date), top_k=50)
        topic_result = topics.retrieve(request, documents=all_docs, top_k=50)
        _merge_route(by_id, topic_result.candidates, "topic_exact")
        routes["topic"]["candidates"] += len(topic_result.candidates)
        if bm25_status == "available":
            result = bm25.retrieve(request, documents=all_docs, top_k=20)
            _merge_route(by_id, result.candidates, "bm25_selected_topic")
            routes["bm25"]["candidates"] += len(result.candidates)
        if dense is not None:
            result = dense.retrieve(request, documents=all_docs, top_k=30)
            _merge_route(by_id, result.candidates, "dense_selected_topic")
            routes["dense"]["candidates"] += len(result.candidates)

    exemplar_ids = list(projection.get("useful_artifact_ids", []))
    doc_by_id = snapshot.by_id()
    for exemplar_id in exemplar_ids[:20]:
        exemplar = doc_by_id.get(exemplar_id)
        if not exemplar or dense is None:
            continue
        query = " ".join((exemplar.title, exemplar.body[:500])).strip()
        if not query:
            continue
        request = make_request(query, seed_artifact_ids=[exemplar_id], as_of=_end_of_day(requested_date), top_k=10)
        result = dense.retrieve(request, documents=all_docs, top_k=10)
        for row in result.candidates:
            if row.get("artifact_id") == exemplar_id:
                continue
            if row.get("artifact_id") in by_id:
                by_id[row["artifact_id"]].setdefault("useful_exemplar_matches", []).append(exemplar_id)
                _add_evidence(by_id[row["artifact_id"]], "dense_useful_exemplar", row.get("rank"), {"exemplar_artifact_id": exemplar_id})
        routes["dense"]["candidates"] += len(result.candidates)

    if graph is not None:
        seeds = exemplar_ids[:10]
        if seeds:
            request = make_request(seed_artifact_ids=seeds, as_of=_end_of_day(requested_date), top_k=100)
            graph_result = graph.retrieve(request, documents=all_docs, top_k=100)
            _merge_route(by_id, graph_result.candidates, "experimental_graph")
            routes["experimental_graph"] = {"status": graph_result.status, "candidates": len(graph_result.candidates)}

    for row in by_id.values():
        row["selected_topic_matches"] = sorted(set(row["selected_topic_matches"]))
        row["useful_exemplar_matches"] = sorted(set(row["useful_exemplar_matches"]))
        row["topic_exact"] = bool(row["selected_topic_matches"] or row.get("topic_exact"))
        row["source_names"] = [source_names.get(item, item) for item in row["source_ids"]]
        row["topic_names"] = [topic_names.get(item, item) for item in row["topics"]]
        row["selected_topic_names"] = [topic_names.get(item, item) for item in row["selected_topic_matches"]]
    selected, metrics = rank_and_select(list(by_id.values()), profile=profile, projection=projection,
                                         feed_date=requested_date)
    for row in selected:
        row["card"] = _card_snapshot(row, store)
    revision_number = int(current["revision"]) + 1 if current else 1
    generated_at = now_utc()
    identity = stable_hash({"date": requested_date, "revision": revision_number, "corpus_hash": snapshot.corpus_hash,
                            "profile_hash": profile_hash(profile), "projection_hash": projection["projection_hash"],
                            "policy": POLICY_VERSION})
    run_id = stable_id("feed", "feed-run", identity)
    run = {
        "schema": "bubblevan/feed-run/v1", "feed_run_id": run_id,
        "feed_date": requested_date, "revision": revision_number, "generated_at": generated_at,
        "corpus_hash": snapshot.corpus_hash, "profile_hash": profile_hash(profile),
        "feedback_projection_hash": projection["projection_hash"], "policy_version": POLICY_VERSION,
        "lookback_days": lookback_days, "candidate_count": len(by_id), "items": selected,
        "supersedes_feed_run_id": current["feed_run_id"] if current else None,
        "metrics": metrics, "retrieval_routes": routes, "experimental_graph": experimental_graph,
    }
    validate_record("feed_run", run)
    repository.save_run(run)
    return run


def load_dense_resource(snapshot: CorpusSnapshot, runtime_dir: str, model: str,
                        revision: str | None, device: str | None) -> tuple[DenseRetriever | None, str]:
    old_offline = os.environ.get("HF_HUB_OFFLINE")
    old_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        backend = SentenceTransformerBackend(model, revision=revision, device=device)
        dense = DenseRetriever(backend)
        dense.build(snapshot, runtime_dir)
        return dense, "available"
    except Exception as exc:
        return None, f"unavailable:{type(exc).__name__}"
    finally:
        if old_offline is None: os.environ.pop("HF_HUB_OFFLINE", None)
        else: os.environ["HF_HUB_OFFLINE"] = old_offline
        if old_transformers_offline is None: os.environ.pop("TRANSFORMERS_OFFLINE", None)
        else: os.environ["TRANSFORMERS_OFFLINE"] = old_transformers_offline


def _recent_documents(snapshot: CorpusSnapshot, feed_date: str, lookback_days: int) -> tuple[list[RetrievalDocument], tuple[RetrievalDocument, ...]]:
    end = datetime.combine(date.fromisoformat(feed_date), time.max, tzinfo=timezone.utc)
    start = end - timedelta(days=lookback_days)
    all_docs = tuple(item for item in snapshot.documents
                     if item.eligibility in {"full_text", "metadata_only"}
                     and item.mention_role != "incidental"
                     and bool(item.title.strip() or item.body.strip()))
    recent = []
    for item in all_docs:
        value = item.published_at or item.first_observed_at
        if not value:
            continue
        try:
            moment = _parse_dt(value)
        except ValueError:
            continue
        if start <= moment <= end:
            recent.append(item)
    return sorted(recent, key=lambda item: item.artifact_id), all_docs


def _candidate_features(docs: list[RetrievalDocument], profile: Mapping[str, Any], projection: Mapping[str, Any],
                        source_names: Mapping[str, str], topic_names: Mapping[str, str]) -> list[dict[str, Any]]:
    selected_topics = set(profile.get("selected_topic_ids", []))
    selected_sources = set(profile.get("followed_source_ids", []))
    hidden = set(projection.get("hidden_artifact_ids", []))
    blocked_sources = set(profile.get("blocked_source_ids", [])) | set(projection.get("blocked_source_ids", []))
    blocked_topics = set(profile.get("blocked_topic_ids", [])) | set(projection.get("blocked_topic_ids", []))
    rows = []
    for doc in docs:
        sources, topics = set(doc.source_ids), set(doc.topics)
        if doc.artifact_id in hidden or sources.intersection(blocked_sources) or topics.intersection(blocked_topics):
            continue
        role = doc.mention_role
        freshness = "published_at" if doc.published_at else "observed_at_fallback"
        rows.append({
            "artifact_id": doc.artifact_id, "artifact_type": doc.artifact_type,
            "title": doc.title, "summary": doc.body[:500], "canonical_url": "",
            "source_ids": sorted(sources), "topics": sorted(topics), "source_names": [], "topic_names": [],
            "followed_source_match": bool(selected_sources.intersection(sources)),
            "selected_topic_matches": sorted(selected_topics.intersection(topics)),
            "useful_exemplar_matches": [], "dense_best_rank": None, "bm25_best_rank": None,
            "topic_exact": bool(selected_topics.intersection(topics)), "published_at": doc.published_at,
            "first_observed_at": doc.first_observed_at, "freshness_basis": freshness,
        "mention_role": role, "evidence": [],
        })
    return rows


def _merge_route(by_id: dict[str, dict[str, Any]], result_rows: list[dict[str, Any]], evidence_name: str) -> None:
    for result in result_rows:
        artifact_id = str(result.get("artifact_id") or "")
        target = by_id.get(artifact_id)
        if target is None:
            continue
        rank = result.get("rank")
        if evidence_name.startswith("dense"):
            target["dense_best_rank"] = min(target["dense_best_rank"] or rank, rank) if rank else target["dense_best_rank"]
        elif evidence_name.startswith("bm25"):
            target["bm25_best_rank"] = min(target["bm25_best_rank"] or rank, rank) if rank else target["bm25_best_rank"]
        elif evidence_name == "topic_exact":
            target["topic_exact"] = True
        _add_evidence(target, evidence_name, rank, result.get("explanation") or {})


def _add_evidence(target: dict[str, Any], route: str, rank: int | None, details: Mapping[str, Any]) -> None:
    target.setdefault("evidence", []).append({"route": route, "route_rank": rank, "details": dict(details)})


def _card_snapshot(row: Mapping[str, Any], store: JsonlStore) -> dict[str, Any]:
    artifact = next((item for item in store.iter_records("artifact") if item.get("artifact_id") == row["artifact_id"]), {})
    return {"title": str(artifact.get("title") or row.get("title") or "Untitled")[:400],
            "artifact_type": str(artifact.get("artifact_type") or row.get("artifact_type") or "other"),
            "summary": str(artifact.get("summary") or row.get("summary") or "")[:500],
            "canonical_url": str(artifact.get("canonical_url") or "")[:1000],
            "source_names": list(row.get("source_names", [])),
            "source_ids": list(row.get("source_ids", [])),
            "topic_names": list(row.get("topic_names", [])),
            "published_at": row.get("published_at"), "freshness_basis": row.get("freshness_basis")}


def _source_names(store: JsonlStore) -> dict[str, str]:
    result = {str(row["source_id"]): str(row.get("name") or row.get("canonical_url") or row["source_id"])
              for row in store.iter_records("source")}
    payload = yaml.safe_load(SOURCE_CATALOG.read_text(encoding="utf-8"))
    for row in payload.get("sources", []):
        result.setdefault(source_id(row.get("identity")), str(row.get("name") or row.get("identity")))
    return result


def _topic_names() -> dict[str, str]:
    payload = yaml.safe_load(TOPIC_CATALOG.read_text(encoding="utf-8"))
    result = {str(row["topic_id"]): str(row.get("name") or row["topic_id"])
              for row in payload.get("topics", [])}
    return result


def _topic_query(topic_id: str, names: Mapping[str, str]) -> str:
    payload = yaml.safe_load(TOPIC_CATALOG.read_text(encoding="utf-8"))
    row = next((item for item in payload.get("topics", []) if item.get("topic_id") == topic_id), {})
    return " ".join([str(names.get(topic_id) or topic_id), *map(str, row.get("aliases", []))])


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _end_of_day(feed_date: str) -> str:
    return datetime.combine(date.fromisoformat(feed_date), time.max, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
