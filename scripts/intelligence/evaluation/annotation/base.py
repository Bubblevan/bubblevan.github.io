from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
from typing import Any, Protocol


QUALITY_ISSUES = (
    "insufficient_metadata", "broken_url", "suspected_duplicate", "identity_problem", "none",
)
FORBIDDEN_BLIND_FIELDS = {
    "route", "routes", "rank", "score", "raw_score", "fusion", "retriever", "retriever_id",
    "retrieval_route", "route_candidates", "contributions", "explanation",
}


class AnnotationAdapter(Protocol):
    def export(self, pack: Mapping[str, Any], target: Any) -> Mapping[str, Any]: ...

    def import_labels(self, pack: Mapping[str, Any], source: Any, target: Any, *,
                      reviewed_by: str | None = None, reviewed_at: str | None = None,
                      judge_type: str = "human", judge_name: str | None = None,
                      judge_model: str | None = None) -> Mapping[str, Any]: ...


def annotation_records(pack: Mapping[str, Any], *, display_fallbacks: Mapping[str, Mapping[str, str]] | None = None) -> list[dict[str, Any]]:
    """Create stable, blind records in the already shuffled label-pack order."""
    _validate_pack(pack)
    fallback = display_fallbacks or {}
    result = []
    for query in pack["queries"]:
        query_id = str(query["query_id"])
        for candidate in query.get("candidates", []):
            artifact_id = str(candidate["artifact_id"])
            stable_key = "|".join((str(pack["benchmark_hash"]), query_id, artifact_id))
            external_id = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
            summary = str(candidate.get("summary_excerpt") or "").strip()
            display = fallback.get(artifact_id, {})
            if not summary and display.get("summary_excerpt"):
                summary = "[Display-only context; benchmark/corpus unchanged] " + str(display["summary_excerpt"])
            fields = {
                "query": str(query.get("query") or ""),
                "category": str(query.get("category") or ""),
                "specificity": str(query.get("specificity") or ""),
                "artifact_id": artifact_id,
                "artifact_type": str(candidate.get("artifact_type") or ""),
                "title": str(candidate.get("title") or display.get("title") or ""),
                "canonical_url": str(candidate.get("canonical_url") or display.get("canonical_url") or ""),
                "published_at": str(candidate.get("published_at") or ""),
                "summary_excerpt": summary,
            }
            _assert_blind(fields)
            result.append({
                "external_id": external_id,
                "fields": fields,
                "metadata": {
                    "benchmark_hash": str(pack["benchmark_hash"]),
                    "corpus_hash": str(pack["corpus_hash"]),
                    "query_id": query_id,
                    "artifact_id": artifact_id,
                },
                "responses": {},
            })
    return result


def import_judgments(pack: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], *,
                     reviewed_by: str | None = None, reviewed_at: str | None = None,
                     existing_qrels: Mapping[str, Any] | None = None,
                     judge_type: str = "human", judge_name: str | None = None,
                     judge_model: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate a partial annotation batch and merge it without overwriting prior judgments."""
    if judge_type not in {"human", "model"}:
        raise ValueError("judge_type must be human or model")
    _validate_pack(pack)
    benchmark_hash = str(pack["benchmark_hash"])
    corpus_hash = str(pack["corpus_hash"])
    expected: dict[tuple[str, str], dict[str, Any]] = {}
    expected_external_ids: dict[tuple[str, str], str] = {}
    for record in annotation_records(pack):
        metadata = record["metadata"]
        expected_external_ids[(str(metadata["query_id"]), str(metadata["artifact_id"]))] = record["external_id"]
    for query in pack["queries"]:
        for candidate in query.get("candidates", []):
            identity = (str(query["query_id"]), str(candidate["artifact_id"]))
            if identity in expected:
                raise ValueError("label pack contains duplicate query/artifact identity")
            expected[identity] = candidate

    prior: dict[tuple[str, str], int] = {}
    prior_quality: dict[tuple[str, str], str] = {}
    prior_judges: dict[tuple[str, str], dict[str, Any]] = {}
    if existing_qrels:
        if existing_qrels.get("benchmark_hash") not in (None, benchmark_hash):
            raise ValueError("existing qrels benchmark hash does not match label pack")
        if existing_qrels.get("corpus_hash") not in (None, corpus_hash):
            raise ValueError("existing qrels corpus hash does not match label pack")
        for item in existing_qrels.get("qrels", []):
            identity = (str(item.get("query_id") or ""), str(item.get("artifact_id") or ""))
            grade = _grade(item.get("grade"))
            if identity not in expected:
                raise ValueError("existing qrels contain an unknown query/artifact identity")
            prior[identity] = grade
            prior_judges[identity] = _read_judge_provenance(existing_qrels, item)
        for item in existing_qrels.get("quality_issues", []):
            identity = (str(item.get("query_id") or ""), str(item.get("artifact_id") or ""))
            issue = str(item.get("quality_issue") or "")
            if identity not in expected or issue not in QUALITY_ISSUES:
                raise ValueError("existing qrels contain an invalid quality issue")
            prior_quality[identity] = issue

    incoming: dict[tuple[str, str], int] = {}
    quality: dict[tuple[str, str], str] = {}
    invalid = 0
    invalid_reasons: dict[str, int] = {}
    for row in rows:
        row_benchmark = str(row.get("benchmark_hash") or "")
        row_corpus = str(row.get("corpus_hash") or "")
        identity = (str(row.get("query_id") or ""), str(row.get("artifact_id") or ""))
        if row_benchmark != benchmark_hash or row_corpus != corpus_hash:
            reason = "hash_mismatch"
        elif identity not in expected:
            reason = "unknown_identity"
        elif "external_id" in row and str(row.get("external_id") or "") != expected_external_ids[identity]:
            reason = "unknown_record_id"
        else:
            reason = ""
        grade_value = row.get("grade")
        if not reason and grade_value not in (None, ""):
            try:
                grade = _grade(grade_value)
            except ValueError:
                reason = "invalid_grade"
            else:
                if identity in incoming and incoming[identity] != grade:
                    raise ValueError("conflicting duplicate relevance grades")
                if identity in prior and prior[identity] != grade:
                    raise ValueError("incoming relevance grade conflicts with an existing judgment")
                incoming[identity] = grade
        quality_value = row.get("quality_issue")
        if not reason and quality_value not in (None, ""):
            if quality_value not in QUALITY_ISSUES:
                reason = "invalid_quality_issue"
            else:
                quality[identity] = str(quality_value)
        if reason:
            invalid += 1
            invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1

    # Invalid records fail closed; no partial write can silently discard a mismatch.
    if invalid:
        report = _completion_report(expected, prior, incoming, invalid, invalid_reasons)
        raise AnnotationImportError(report)
    merged = {**prior, **incoming}
    timestamp = _timestamp(reviewed_at) if reviewed_at else datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    merged_quality = {**prior_quality, **quality}
    current_judge = {"type": judge_type, "name": judge_name or reviewed_by, "model": judge_model}
    qrels = {
        "schema": "bubblevan/retrieval-qrels/v2",
        "benchmark_id": str(pack.get("benchmark_id") or "dev-v1"),
        "benchmark_hash": benchmark_hash,
        "corpus_hash": corpus_hash,
        "status": "draft",
        "judge": current_judge,
        "reviewed_by": (reviewed_by or (existing_qrels or {}).get("reviewed_by")),
        "reviewed_at": timestamp,
        "qrels": [
            {"query_id": query_id, "artifact_id": artifact_id, "grade": grade,
             "judge": prior_judges.get((query_id, artifact_id), current_judge)}
            for (query_id, artifact_id), grade in sorted(merged.items())
        ],
        "quality_issues": [
            {"query_id": query_id, "artifact_id": artifact_id, "quality_issue": issue}
            for (query_id, artifact_id), issue in sorted(merged_quality.items())
        ],
    }
    report = _completion_report(expected, merged, {}, 0, {})
    return qrels, report


def _read_judge_provenance(container: Mapping[str, Any], item: Mapping[str, Any]) -> dict[str, Any]:
    value = item.get("judge")
    if isinstance(value, Mapping) and value.get("type") in {"human", "model"}:
        return {"type": value["type"], "name": value.get("name"), "model": value.get("model")}
    value = container.get("judge")
    if isinstance(value, Mapping) and value.get("type") in {"human", "model"}:
        return {"type": value["type"], "name": value.get("name"), "model": value.get("model")}
    schema = str(container.get("schema") or "")
    if "model-qrels" in schema or "llm-qrels" in schema:
        return {"type": "model", "name": container.get("reviewed_by"),
                "model": container.get("judge_model") or container.get("reviewed_by")}
    return {"type": "human", "name": container.get("reviewed_by"), "model": None}


class AnnotationImportError(ValueError):
    def __init__(self, report: Mapping[str, Any]):
        self.report = dict(report)
        super().__init__("annotation import rejected; see invalid counts in report")


def _completion_report(expected: Mapping[tuple[str, str], Any], prior: Mapping[tuple[str, str], Any],
                       incoming: Mapping[tuple[str, str], Any], invalid: int,
                       invalid_reasons: Mapping[str, int]) -> dict[str, Any]:
    completed = set(prior) | set(incoming)
    query_ids = {item[0] for item in expected}
    complete_queries = sum(all(identity in completed for identity in expected if identity[0] == query_id)
                           for query_id in query_ids)
    return {"total": len(expected), "annotated": len(completed), "remaining": len(expected) - len(completed),
            "invalid": invalid, "invalid_reasons": dict(sorted(invalid_reasons.items())),
            "query_total": len(query_ids), "queries_complete": complete_queries}


def _validate_pack(pack: Mapping[str, Any]) -> None:
    if not isinstance(pack.get("queries"), list) or not pack.get("benchmark_hash") or not pack.get("corpus_hash"):
        raise ValueError("annotation requires a hashed blind label pack")
    for query in pack["queries"]:
        if not isinstance(query, Mapping) or not query.get("query_id"):
            raise ValueError("label pack has an invalid query")
        for candidate in query.get("candidates", []):
            if not isinstance(candidate, Mapping) or not candidate.get("artifact_id"):
                raise ValueError("label pack has an invalid candidate")
            _assert_blind(candidate)


def _assert_blind(value: Mapping[str, Any]) -> None:
    found = {str(key) for key in value if _is_blind_field(str(key))}
    if found:
        raise ValueError("blind annotation payload contains retrieval metadata")
    for child in value.values():
        if isinstance(child, Mapping):
            _assert_blind(child)
        elif isinstance(child, list):
            for item in child:
                if isinstance(item, Mapping):
                    _assert_blind(item)


def _is_blind_field(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    if normalized in FORBIDDEN_BLIND_FIELDS:
        return True
    return any(token.startswith(root) for token in normalized.split("_")
               for root in ("route", "rank", "score", "retriev", "fusion", "contribution"))


def _grade(value: Any) -> int:
    if isinstance(value, bool) or str(value) not in {"0", "1", "2"}:
        raise ValueError("relevance grade must be 0, 1, or 2")
    return int(value)


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("reviewed_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("reviewed_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
