from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .base import annotation_records, import_judgments


class JsonFallbackAdapter:
    """Portable offline export/import format for environments without Argilla."""

    def export(self, pack: Mapping[str, Any], target: str | Path, *,
               display_fallbacks: Mapping[str, Mapping[str, str]] | None = None) -> Mapping[str, Any]:
        records = annotation_records(pack, display_fallbacks=display_fallbacks)
        expected = {record["external_id"]: record for record in records}
        target_path = Path(target)
        prior_by_id: dict[str, Mapping[str, Any]] = {}
        if target_path.exists():
            prior = json.loads(target_path.read_text(encoding="utf-8"))
            if (prior.get("schema") != "bubblevan/retrieval-annotation-json/v1"
                    or prior.get("benchmark_hash") != pack.get("benchmark_hash")
                    or prior.get("corpus_hash") != pack.get("corpus_hash")):
                raise ValueError("existing annotation JSON hashes do not match the blind label pack")
            for row in prior.get("records", []):
                external_id = str(row.get("external_id") or "")
                if external_id not in expected or external_id in prior_by_id:
                    raise ValueError("existing annotation JSON has unknown or duplicate record IDs")
                expected_metadata = expected[external_id]["metadata"]
                if row.get("metadata") != expected_metadata:
                    raise ValueError("existing annotation JSON identity metadata does not match the blind pack")
                prior_by_id[external_id] = row
        for record in records:
            prior = prior_by_id.get(record["external_id"])
            if prior:
                record["responses"] = dict(prior.get("responses") or {})
        payload = {"schema": "bubblevan/retrieval-annotation-json/v1",
                   "benchmark_hash": pack["benchmark_hash"], "corpus_hash": pack["corpus_hash"],
                   "records": records}
        _write_json(target_path, payload)
        return {"records": len(records), "records_added": len(records) - len(prior_by_id),
                "preserved_existing": len(prior_by_id), "duplicates": 0, "path": str(target_path)}

    def import_labels(self, pack: Mapping[str, Any], source: str | Path, target: str | Path, *,
                      reviewed_by: str | None = None, reviewed_at: str | None = None,
                      judge_type: str = "human", judge_name: str | None = None,
                      judge_model: str | None = None) -> Mapping[str, Any]:
        payload = json.loads(Path(source).read_text(encoding="utf-8"))
        if payload.get("schema") != "bubblevan/retrieval-annotation-json/v1":
            raise ValueError("unsupported annotation JSON schema")
        if payload.get("benchmark_hash") != pack.get("benchmark_hash") or payload.get("corpus_hash") != pack.get("corpus_hash"):
            raise ValueError("annotation JSON hashes do not match the blind label pack")
        qrels_path = Path(target)
        existing = json.loads(qrels_path.read_text(encoding="utf-8")) if qrels_path.exists() else None
        rows = []
        for record in payload.get("records", []):
            metadata = record.get("metadata") or {}
            responses = record.get("responses") or {}
            rows.append({"benchmark_hash": metadata.get("benchmark_hash"),
                         "corpus_hash": metadata.get("corpus_hash"),
                         "query_id": metadata.get("query_id"), "artifact_id": metadata.get("artifact_id"),
                         "external_id": record.get("external_id"),
                         "grade": responses.get("relevance"), "quality_issue": responses.get("quality_issue")})
        qrels, report = import_judgments(pack, rows, reviewed_by=reviewed_by, reviewed_at=reviewed_at,
                                         existing_qrels=existing, judge_type=judge_type,
                                         judge_name=judge_name, judge_model=judge_model)
        _write_json(qrels_path, qrels)
        return report


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
