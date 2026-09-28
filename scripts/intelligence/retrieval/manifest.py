from __future__ import annotations

from datetime import datetime, timezone
import json
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


def _hash(value: Any) -> str:
    return __import__("hashlib").sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
