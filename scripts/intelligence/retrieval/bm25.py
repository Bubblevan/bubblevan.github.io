from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Sequence

from .base import RetrievalResult, RetrieverSpec
from .corpus import CorpusSnapshot, RetrievalDocument
from .expansion import expanded_query_text
from .request import RetrievalRequest
from .tokenization import tokenize


class BM25Retriever:
    spec = RetrieverSpec("bm25", "bm25s-0.3", independent_local=True)
    config = {"implementation": "bm25s", "k1": 1.5, "b": 0.75, "title_repeat": 2, "tokenizer": "jieba+unicode-bigrams-v1"}

    def __init__(self) -> None:
        self.index = None
        self.document_ids: list[str] = []
        self.corpus_hash: str | None = None
        self._bm25s = None

    def build(self, snapshot: CorpusSnapshot, runtime_dir: str) -> dict:
        try:
            import bm25s
        except ImportError as exc:
            raise RuntimeError("BM25 route requires bm25s; install requirements-intelligence.txt") from exc
        start = time.perf_counter()
        docs = [item for item in snapshot.documents if item.title.strip() or item.body.strip()]
        document_ids = [item.artifact_id for item in docs]
        document_hashes = {item.artifact_id: item.document_hash for item in docs}
        target = Path(runtime_dir) / "bm25"
        target.mkdir(parents=True, exist_ok=True)
        manifest_path = target / "manifest.json"
        index_dir = target / "index"
        prior_manifest = None
        if manifest_path.exists():
            try:
                prior_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                prior_manifest = None
        reusable = bool(
            prior_manifest
            and prior_manifest.get("corpus_hash") == snapshot.corpus_hash
            and prior_manifest.get("document_hashes") == document_hashes
            and prior_manifest.get("config") == self.config
            and index_dir.exists()
        )
        if reusable:
            index = bm25s.BM25.load(str(index_dir), load_corpus=False, show_progress=False)
        else:
            corpus = [self._index_text(doc) for doc in docs]
            index = bm25s.BM25(k1=self.config["k1"], b=self.config["b"], method="lucene")
            index.index([tokenize(item) for item in corpus], show_progress=False)
            index.save(str(index_dir), corpus=document_ids, show_progress=False)
        self.index = index
        self._bm25s = bm25s
        self.document_ids = document_ids
        self.corpus_hash = snapshot.corpus_hash
        manifest = {
            "route": "bm25", "version": self.spec.version, "library_version": bm25s.__version__,
            "corpus_hash": snapshot.corpus_hash,
            "document_count": len(docs), "document_order_hash": _hash(self.document_ids),
            "document_hashes": document_hashes,
            "config": dict(self.config), "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
            "index_file_hashes": _index_hashes(index_dir), "reused": reusable,
        }
        manifest.pop("elapsed_ms", None)
        manifest.pop("reused", None)
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return manifest

    def retrieve(self, request: RetrievalRequest, *, documents: Sequence[RetrievalDocument], top_k: int) -> RetrievalResult:
        if self.index is None or self._bm25s is None:
            raise RuntimeError("BM25 index has not been built")
        started = time.perf_counter()
        by_id = {item.artifact_id: item for item in documents}
        eligible_ids = [item for item in self.document_ids if item in by_id]
        if not request.query:
            return RetrievalResult("bm25", elapsed_ms=0.0, manifest={"corpus_hash": self.corpus_hash})
        query = expanded_query_text(request.query, request.expanded_terms)
        query_tokens = tokenize(query)
        if not query_tokens or not eligible_ids:
            return RetrievalResult("bm25", elapsed_ms=0.0, manifest={"corpus_hash": self.corpus_hash})
        # Retrieve across the full index, then apply request temporal/type filters before returning.
        ids, scores = self.index.retrieve([query_tokens], corpus=self.document_ids,
                                          k=len(self.document_ids),
                                          show_progress=False)
        candidates = []
        for artifact_id, score in zip(ids[0], scores[0]):
            artifact_id = str(artifact_id)
            document = by_id.get(artifact_id)
            if document is None:
                continue
            candidates.append({
                "artifact_id": artifact_id, "rank": len(candidates) + 1, "raw_score": float(score),
                "explanation": {"matched_lexical_terms": sorted(set(query_tokens).intersection(tokenize(self._index_text(document))))},
            })
            if len(candidates) >= top_k:
                break
        return RetrievalResult("bm25", candidates, {"corpus_hash": self.corpus_hash, "config": dict(self.config)},
                               elapsed_ms=round((time.perf_counter() - started) * 1000, 3))

    @staticmethod
    def _index_text(document: RetrievalDocument) -> str:
        # Stable title repetition is the first version's explicit field boost.
        fields = [document.title, document.title, document.body, " ".join(document.authors), " ".join(document.topics),
                  " ".join(str(item.get("name") or "") for item in document.graph_entities)]
        return "\n".join(item for item in fields if item)


def _hash(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _index_hashes(directory: Path) -> dict[str, str]:
    return {path.name: sha256(path.read_bytes()).hexdigest() for path in sorted(directory.iterdir()) if path.is_file()}
