from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from typing import Sequence

from ..aliases import ArtifactAliases
from ..graph.store import GraphStore
from .base import RetrievalResult, RetrieverSpec
from .corpus import CorpusSnapshot, RetrievalDocument
from .request import RetrievalRequest


class SourceRetriever:
    spec = RetrieverSpec("source", "exact-source-evidence-v1", independent_local=True)

    def __init__(self, store_dir: str):
        self.graph = GraphStore(store_dir)
        self.aliases = ArtifactAliases(store_dir)
        self.edges = []

    def build(self, snapshot: CorpusSnapshot, runtime_dir: str) -> dict:
        self.edges = self.graph.iter_edges()
        return {"route": "source", "version": self.spec.version, "corpus_hash": snapshot.corpus_hash,
                "edge_count": len(self.edges),
                "edge_hash": hashlib.sha256(json.dumps(self.edges, ensure_ascii=False, sort_keys=True,
                                                         separators=(",", ":")).encode("utf-8")).hexdigest()}

    def retrieve(self, request: RetrievalRequest, *, documents: Sequence[RetrievalDocument], top_k: int) -> RetrievalResult:
        requested = set(request.source_ids)
        if not requested:
            return RetrievalResult("source", status="skipped", reason="no exact source IDs")
        eligible = {item.artifact_id for item in documents}
        evidence: dict[str, list[dict]] = defaultdict(list)
        for edge in self.edges:
            if edge["predicate"] not in {"mentions", "recommends"} or edge["subject_id"] not in requested:
                continue
            artifact_id = self.aliases.resolve_artifact_id(str(edge["object_id"]))
            if artifact_id in eligible:
                for item in edge.get("evidence", []):
                    evidence[artifact_id].append({"source_id": edge["subject_id"], "predicate": edge["predicate"],
                                                  "edge_id": edge["edge_id"], "observation_id": item.get("observation_id"),
                                                  "evidence_type": item.get("evidence_type")})
        order = sorted(evidence, key=lambda item: (item not in evidence, item))
        candidates = [{"artifact_id": item, "rank": rank, "raw_score": float(len(evidence[item])),
                       "explanation": {"source_evidence": sorted(evidence[item], key=lambda row: (row["source_id"], row["predicate"], str(row["observation_id"])))} }
                      for rank, item in enumerate(order[:top_k], 1)]
        return RetrievalResult("source", candidates)
