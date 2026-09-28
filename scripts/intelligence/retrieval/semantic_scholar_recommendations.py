from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Sequence

from ..store import JsonlStore
from .base import RetrievalResult, RetrieverSpec
from .corpus import CorpusSnapshot, RetrievalDocument
from .request import RetrievalRequest


class SemanticScholarRecommendationsRetriever:
    """Optional exact-paper-ID route. Inject a bounded transport; tests use a fake."""

    spec = RetrieverSpec("semantic-scholar", "s2-recommendations-v1", independent_local=False, optional=True)

    def __init__(self, store: JsonlStore, runtime_dir: str | Path,
                 transport: Callable[[list[str], list[str]], Sequence[Mapping[str, Any]]] | None = None):
        self.store = store
        self.cache_dir = Path(runtime_dir) / "semantic-scholar-recommendations"
        self.transport = transport
        self.paper_ids: dict[str, str] = {}
        self.doc_ids: set[str] = set()

    def build(self, snapshot: CorpusSnapshot, runtime_dir: str) -> dict:
        self.doc_ids = set(snapshot.by_id())
        self.paper_ids = {}
        for artifact in self.store.iter_records("artifact"):
            artifact_id = str(artifact["artifact_id"])
            identifiers = artifact.get("identifiers") if isinstance(artifact.get("identifiers"), dict) else {}
            metadata = artifact.get("provider_metadata", {}).get("semantic-scholar", {})
            paper_id = identifiers.get("semantic_scholar") or metadata.get("paper_id")
            if paper_id and artifact_id in self.doc_ids:
                self.paper_ids[artifact_id] = str(paper_id)
        return {"route": self.spec.route, "version": self.spec.version, "paper_ids": len(self.paper_ids),
                "paper_id_map_hash": hashlib.sha256(json.dumps(self.paper_ids, sort_keys=True,
                                                                 separators=(",", ":")).encode("utf-8")).hexdigest()}

    def retrieve(self, request: RetrievalRequest, *, documents: Sequence[RetrievalDocument], top_k: int) -> RetrievalResult:
        if not request.seed_artifact_ids:
            return RetrievalResult(self.spec.route, status="skipped", reason="no seed artifacts")
        positive = sorted({self.paper_ids[item] for item in request.seed_artifact_ids if item in self.paper_ids})[:10]
        negative = sorted({self.paper_ids[item] for item in request.negative_seed_artifact_ids if item in self.paper_ids})[:10]
        if not positive:
            return RetrievalResult(self.spec.route, status="skipped", reason="no resolvable exact Semantic Scholar seed paperId")
        if self.transport is None:
            return RetrievalResult(self.spec.route, status="skipped", reason="Semantic Scholar transport not configured")
        cache_key = hashlib.sha256(json.dumps({"positive": positive, "negative": negative}, sort_keys=True).encode()).hexdigest()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.cache_dir / f"{cache_key}.json"
        started = time.perf_counter()
        try:
            if cache_path.exists():
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
            else:
                payload = list(self.transport(positive, negative))[:500]
                cache_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            return RetrievalResult(self.spec.route, status="deferred", reason=f"provider unavailable: {type(exc).__name__}")
        by_paper = {paper_id: artifact_id for artifact_id, paper_id in self.paper_ids.items()}
        candidates = []
        for row in payload:
            paper_id = str(row.get("paperId") or row.get("paper_id") or "")
            artifact_id = by_paper.get(paper_id)
            if not artifact_id or artifact_id not in self.doc_ids:
                continue
            candidates.append({"artifact_id": artifact_id, "rank": len(candidates) + 1,
                               "raw_score": float(row.get("score") or 0.0),
                               "explanation": {"provider": "semantic-scholar", "paper_id": paper_id,
                                               "exact_identifier": True}})
            if len(candidates) >= min(top_k, 100):
                break
        return RetrievalResult(self.spec.route, candidates, {"positive_seed_count": len(positive),
                              "negative_seed_count": len(negative), "cached": cache_path.exists()},
                              elapsed_ms=round((time.perf_counter() - started) * 1000, 3))
