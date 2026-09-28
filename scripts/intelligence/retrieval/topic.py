from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from .base import RetrievalResult, RetrieverSpec
from .corpus import CorpusSnapshot, RetrievalDocument
from .request import RetrievalRequest


class TopicRetriever:
    spec = RetrieverSpec("topic", "exact-topic-v1", independent_local=True)

    def build(self, snapshot: CorpusSnapshot, runtime_dir: str) -> dict:
        return {"route": "topic", "version": self.spec.version, "corpus_hash": snapshot.corpus_hash,
                "document_count": len(snapshot.documents)}

    def retrieve(self, request: RetrievalRequest, *, documents: Sequence[RetrievalDocument], top_k: int) -> RetrievalResult:
        requested = set(request.topic_ids)
        if not requested:
            return RetrievalResult("topic", status="skipped", reason="no exact topic IDs")
        scored = []
        for doc in documents:
            overlap = sorted(requested.intersection(doc.topics))
            if not overlap:
                continue
            published = _timestamp(doc.published_at)
            scored.append((len(overlap), published, doc.artifact_id, overlap))
        scored.sort(key=lambda row: (-row[0], -(row[1].timestamp() if row[1] else float("-inf")), row[2]))
        candidates = [{"artifact_id": item[2], "rank": rank, "raw_score": float(item[0]),
                       "explanation": {"matched_topics": item[3], "sort": ["exact_overlap", "published_at_recency"]}}
                      for rank, item in enumerate(scored[:top_k], 1)]
        return RetrievalResult("topic", candidates)


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc)
