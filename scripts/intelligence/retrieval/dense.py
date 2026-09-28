from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Protocol, Sequence

from .base import RetrievalResult, RetrieverSpec
from .corpus import CorpusSnapshot, RetrievalDocument
from .expansion import expanded_query_text
from .request import RetrievalRequest
from .tokenization import tokenize


class EmbeddingBackend(Protocol):
    model_id: str
    model_revision: str
    dimension: int

    def encode_documents(self, texts: Sequence[str]) -> Any: ...
    def encode_queries(self, texts: Sequence[str]) -> Any: ...


class DeterministicFakeEmbedding:
    """Small deterministic bag embedding for CI; never downloads a model."""

    def __init__(self, dimension: int = 64, *, token_vectors: dict[str, list[float]] | None = None):
        if dimension < 2 or dimension > 1024:
            raise ValueError("fake embedding dimension must be between 2 and 1024")
        self.model_id = "fake/deterministic-token-hash"
        self.model_revision = "v1"
        self.dimension = dimension
        self.token_vectors = token_vectors or {}

    def encode_documents(self, texts: Sequence[str]) -> Any:
        return self._encode(texts)

    def encode_queries(self, texts: Sequence[str]) -> Any:
        return self._encode(texts)

    def _encode(self, texts: Sequence[str]) -> Any:
        import numpy as np
        rows = []
        for text in texts:
            vector = np.zeros(self.dimension, dtype=np.float32)
            tokens = tokenize(text)
            for token in tokens:
                explicit = self.token_vectors.get(token)
                if explicit is not None:
                    item = np.asarray(explicit, dtype=np.float32)
                    vector[:min(len(item), self.dimension)] += item[:self.dimension]
                    continue
                digest = sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % self.dimension
                sign = 1.0 if digest[4] % 2 else -1.0
                vector[index] += sign
            rows.append(vector)
        return np.asarray(rows, dtype=np.float32)


class SentenceTransformerBackend:
    def __init__(self, model_id: str = "Qwen/Qwen3-Embedding-0.6B", *, revision: str | None = None,
                 device: str | None = None, dimension: int = 1024):
        if dimension < 1 or dimension > 1024:
            raise ValueError("embedding dimension must be between 1 and 1024")
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Dense live route requires sentence-transformers and PyTorch; install requirements-retrieval-dense.txt") from exc
        self.model_id = model_id
        self.model_revision = revision or _cached_revision(model_id) or "main"
        self.dimension = dimension
        target_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        kwargs: dict[str, Any] = {"device": target_device, "trust_remote_code": True,
                                  "model_kwargs": {"torch_dtype": "auto"}}
        if revision:
            kwargs["revision"] = revision
        self.model = SentenceTransformer(model_id, **kwargs)
        self.model_revision = revision or _cached_revision(model_id) or self.model_revision
        self.device = target_device

    def encode_documents(self, texts: Sequence[str]) -> Any:
        return self.model.encode(list(texts), batch_size=2, show_progress_bar=False, convert_to_numpy=True,
                                 normalize_embeddings=True, truncate_dim=self.dimension)

    def encode_queries(self, texts: Sequence[str]) -> Any:
        kwargs = {"batch_size": 2, "show_progress_bar": False, "convert_to_numpy": True,
                  "normalize_embeddings": True, "truncate_dim": self.dimension}
        if self.model_id.casefold() == "qwen/qwen3-embedding-0.6b":
            return self.model.encode(list(texts), prompt_name="query", **kwargs)
        return self.model.encode_query(list(texts), **kwargs)


class DenseRetriever:
    spec = RetrieverSpec("dense", "exact-dot-product-v1", independent_local=True)

    def __init__(self, backend: EmbeddingBackend):
        self.backend = backend
        self.document_ids: list[str] = []
        self.matrix: Any = None
        self.corpus_hash: str | None = None
        self.cache_stats = {"reused": 0, "embedded": 0}
        self.manifest: dict[str, Any] = {}

    def build(self, snapshot: CorpusSnapshot, runtime_dir: str) -> dict[str, Any]:
        import numpy as np
        started = time.perf_counter()
        root = Path(runtime_dir) / "embeddings" / _slug(self.backend.model_id) / _hash(self.backend.model_revision)
        root.mkdir(parents=True, exist_ok=True)
        vectors: dict[str, Any] = {}
        missing: list[tuple[RetrievalDocument, str]] = []
        reused = 0
        embedding_seconds = 0.0
        for document in snapshot.documents:
            text_hash = sha256(document.retrieval_text.encode("utf-8")).hexdigest()
            cache_key = _hash({"model_revision": self.backend.model_revision, "text_hash": text_hash})
            cache_path = root / f"{cache_key}.npy"
            vector = None
            if cache_path.exists():
                try:
                    candidate = np.load(cache_path, allow_pickle=False)
                    if candidate.ndim == 1 and len(candidate) == self.backend.dimension and np.isfinite(candidate).all():
                        vector = _normalize(candidate)
                        reused += 1
                except (OSError, ValueError):
                    vector = None
            if vector is None:
                missing.append((document, cache_key))
            else:
                vectors[document.artifact_id] = vector
        if missing:
            embedding_started = time.perf_counter()
            encoded = np.asarray(self.backend.encode_documents([item.retrieval_text for item, _ in missing]), dtype=np.float32)
            embedding_seconds = time.perf_counter() - embedding_started
            if encoded.ndim != 2 or encoded.shape != (len(missing), self.backend.dimension):
                raise ValueError("embedding backend returned an unexpected document matrix shape")
            encoded = _normalize(encoded)
            for (document, cache_key), vector in zip(missing, encoded):
                vectors[document.artifact_id] = vector
                np.save(root / f"{cache_key}.npy", vector, allow_pickle=False)
        self.document_ids = [item.artifact_id for item in snapshot.documents]
        self.matrix = np.stack([vectors[item] for item in self.document_ids]) if self.document_ids else np.zeros((0, self.backend.dimension), dtype=np.float32)
        self.corpus_hash = snapshot.corpus_hash
        self.cache_stats = {"reused": reused, "embedded": len(missing)}
        manifest = {
            "route": "dense", "version": self.spec.version,
            "model_id": self.backend.model_id, "model_revision": self.backend.model_revision,
            "dimension": int(self.backend.dimension), "normalize_embeddings": True,
            "similarity": "exact_normalized_dot_product", "corpus_hash": snapshot.corpus_hash,
            "document_hashes": {item.artifact_id: sha256(item.retrieval_text.encode("utf-8")).hexdigest() for item in snapshot.documents},
            "document_order_hash": _hash(self.document_ids), "cache": dict(self.cache_stats),
            "index_bytes": int(self.matrix.nbytes), "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "embedding_seconds": round(embedding_seconds, 3),
            "embedding_docs_per_sec": round(len(missing) / embedding_seconds, 3) if embedding_seconds > 0 else None,
            "query_prompt": "query" if self.backend.model_id.casefold() == "qwen/qwen3-embedding-0.6b" else None,
        }
        out = Path(runtime_dir) / "dense"
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "vectors.npy", self.matrix, allow_pickle=False)
        (out / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        self.manifest = manifest
        return manifest

    def retrieve(self, request: RetrievalRequest, *, documents: Sequence[RetrievalDocument], top_k: int) -> RetrievalResult:
        import numpy as np
        started = time.perf_counter()
        if self.matrix is None:
            raise RuntimeError("Dense index has not been built")
        if not request.query or not self.document_ids:
            return RetrievalResult("dense", manifest=dict(self.manifest))
        query_text = expanded_query_text(request.query, request.expanded_terms)
        query = np.asarray(self.backend.encode_queries([query_text]), dtype=np.float32)
        if query.shape != (1, self.backend.dimension):
            raise ValueError("embedding backend returned an unexpected query matrix shape")
        scores = self.matrix @ _normalize(query)[0]
        eligible = {item.artifact_id for item in documents}
        order = sorted(range(len(scores)), key=lambda idx: (-float(scores[idx]), self.document_ids[idx]))
        candidates = []
        for index in order:
            artifact_id = self.document_ids[index]
            if artifact_id not in eligible:
                continue
            candidates.append({
                "artifact_id": artifact_id, "rank": len(candidates) + 1, "raw_score": float(scores[index]),
                "explanation": {"semantic_similarity_rank": len(candidates) + 1, "similarity": "cosine"},
            })
            if len(candidates) >= top_k:
                break
        return RetrievalResult("dense", candidates, dict(self.manifest), elapsed_ms=round((time.perf_counter() - started) * 1000, 3))


def _normalize(value: Any) -> Any:
    import numpy as np
    matrix = np.asarray(value, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")[:120]


def _cached_revision(model_id: str) -> str | None:
    hub = Path(os.environ.get("HF_HUB_CACHE", Path.home() / ".cache" / "huggingface" / "hub"))
    folder = hub / ("models--" + model_id.replace("/", "--")) / "refs" / "main"
    try:
        value = folder.read_text(encoding="utf-8").strip()
        return value or None
    except OSError:
        return None
