from __future__ import annotations

from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
from typing import Any, Mapping

from .corpus import CorpusSnapshot


MANIFEST_SCHEMA = "bubblevan/intelligence-retrieval-manifest/v2"


def make_manifest(snapshot: CorpusSnapshot, *, retriever_versions: Mapping[str, Any] | None = None,
                  built_at: str | None = None) -> dict[str, Any]:
    stamp = built_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    document_hashes = {item.artifact_id: item.document_hash for item in snapshot.documents}
    semantic = {
        "schema": MANIFEST_SCHEMA,
        "corpus_hash": snapshot.corpus_hash,
        "artifact_count": len(snapshot.documents),
        "corpus_quality": dict(snapshot.quality),
        "source_tree_hash": snapshot.source_tree_hash,
        "normalization_version": snapshot.normalization_version,
        "retriever_versions": dict(sorted((retriever_versions or {}).items())),
        "document_hashes": dict(sorted(document_hashes.items())),
    }
    return {**semantic, "manifest_hash": _hash(semantic), "built_at": stamp}


def write_manifest(path: str, snapshot: CorpusSnapshot, *, retriever_versions: Mapping[str, Any] | None = None,
                   built_at: str | None = None) -> dict[str, Any]:
    from pathlib import Path
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = make_manifest(snapshot, retriever_versions=retriever_versions, built_at=built_at)
    target.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest


def dense_freshness(snapshot: CorpusSnapshot, runtime_dir: str | Path) -> dict[str, Any]:
    path = Path(runtime_dir) / "retrieval" / "dense" / "manifest.json"
    if not path.exists():
        return {"current_corpus_hash": snapshot.corpus_hash,
                "dense_manifest_corpus_hash": None, "dense_manifest_hash": None, "dense_status": "missing"}
    try:
        raw_manifest = path.read_bytes()
        manifest = json.loads(raw_manifest.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"current_corpus_hash": snapshot.corpus_hash,
                "dense_manifest_corpus_hash": None, "dense_manifest_hash": None, "dense_status": "unavailable"}
    if not isinstance(manifest, dict) or not isinstance(manifest.get("corpus_hash"), str):
        return {"current_corpus_hash": snapshot.corpus_hash,
                "dense_manifest_corpus_hash": None, "dense_manifest_hash": None, "dense_status": "unavailable"}
    corpus_hash = manifest["corpus_hash"]
    return {"current_corpus_hash": snapshot.corpus_hash,
            "dense_manifest_corpus_hash": corpus_hash,
            "dense_manifest_hash": hashlib.sha256(raw_manifest).hexdigest(),
            "dense_status": "fresh" if corpus_hash == snapshot.corpus_hash else "stale"}


def _hash(value: Any) -> str:
    return __import__("hashlib").sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
