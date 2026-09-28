from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ..schema_validator import validate_instance


SCHEMA = "bubblevan/intelligence-retrieval-benchmark/v1"


def freeze_benchmark(*, version: str, split: str, corpus_hash: str, queries: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {"schema": SCHEMA, "version": version, "split": split, "corpus_hash": corpus_hash,
               "queries": queries}
    payload["benchmark_hash"] = benchmark_hash(payload)
    _validate_qrels(payload, None)
    return payload


def benchmark_hash(payload: dict[str, Any]) -> str:
    semantic = {key: value for key, value in payload.items() if key != "benchmark_hash"}
    return hashlib.sha256(_canonical(semantic)).hexdigest()


def validate_benchmark(payload: dict[str, Any], known_artifact_ids: Iterable[str]) -> None:
    _validate_qrels(payload, set(map(str, known_artifact_ids)))
    if payload.get("benchmark_hash") != benchmark_hash(payload):
        raise ValueError("retrieval benchmark hash does not match its frozen content")


def load_benchmark(path: str | Path, known_artifact_ids: Iterable[str]) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("benchmark must be a JSON object")
    validate_benchmark(payload, known_artifact_ids)
    return payload


def _validate_qrels(payload: dict[str, Any], known: set[str] | None) -> None:
    schema_path = Path(__file__).resolve().parents[3] / "schemas" / "intelligence" / "retrieval_benchmark.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate_instance(payload, schema)
    ids: set[str] = set()
    for query in payload["queries"]:
        if query["query_id"] in ids:
            raise ValueError("benchmark contains duplicate query IDs")
        ids.add(query["query_id"])
        if known is not None:
            unknown = set(query["qrels"]) - known
            if unknown:
                raise ValueError(f"benchmark qrels reference unknown Artifact IDs: {sorted(unknown)[:3]}")
        label_source = query["provenance"]["label_source"]
        if payload["split"] in {"dev", "holdout"} and label_source not in {"human", "model"}:
            raise ValueError("DEV and HOLDOUT qrels require explicit human or model judgments")
        if payload["split"] in {"dev", "holdout"} and (
            not query["provenance"].get("reviewed_by") or not query["provenance"].get("reviewed_at")
        ):
            raise ValueError("development qrels require reviewer identity and timestamp")
        if label_source == "model":
            provenance = query["provenance"]
            if (provenance.get("judge_type") != "model" or not provenance.get("judge_model")
                    or not provenance.get("guideline_version") or not provenance.get("prompt_hash")):
                raise ValueError("model-judged qrels require model, guideline, and prompt hash provenance")


def save_benchmark(path: str | Path, payload: dict[str, Any], known_artifact_ids: Iterable[str]) -> None:
    validate_benchmark(payload, known_artifact_ids)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
