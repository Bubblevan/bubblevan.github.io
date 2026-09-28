from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from .annotation.base import QUALITY_ISSUES, _assert_blind
from .annotation.base import _timestamp
from .pool_coverage import pool_pairs


MODEL_JUDGMENT_SCHEMA = "bubblevan/retrieval-model-judgment/v1"
JUDGE_INPUT_SCHEMA = "bubblevan/retrieval-model-judge-input/v1"
JUDGE_INPUT_FIELDS = {
    "query_id", "artifact_id", "query", "category", "specificity",
    "artifact_type", "title", "summary_excerpt", "canonical_url", "published_at",
}


class ModelJudgmentError(ValueError):
    """Raised when a model judgment batch does not exactly match its blind input."""


def prompt_hash(prompt: str | bytes) -> str:
    payload = prompt.encode("utf-8") if isinstance(prompt, str) else prompt
    return hashlib.sha256(payload).hexdigest()


def build_judge_input(*, benchmark_id: str, benchmark_hash: str, corpus_hash: str,
                      pairs: Sequence[tuple[str, str]], queries: Sequence[Mapping[str, Any]],
                      documents: Mapping[str, Any], artifacts: Mapping[str, Mapping[str, Any]],
                      grading_prompt_hash: str) -> dict[str, Any]:
    """Create an identity-preserving blind payload containing only new pool pairs."""
    query_map = {str(item["query_id"]): item for item in queries}
    rows = []
    for query_id, artifact_id in sorted(set((str(q), str(a)) for q, a in pairs)):
        query = query_map.get(query_id)
        document = documents.get(artifact_id)
        artifact = artifacts.get(artifact_id)
        if query is None or document is None or artifact is None:
            missing = [name for name, value in (("query", query), ("document", document),
                                                 ("artifact", artifact)) if value is None]
            raise ModelJudgmentError(
                f"missing blind context ({', '.join(missing)}) for {query_id}/{artifact_id}"
            )
        excerpt = str(getattr(document, "body", "") or "").strip()
        row = {
            "query_id": query_id,
            "artifact_id": artifact_id,
            "query": str(query.get("query") or ""),
            "category": str(query.get("category") or ""),
            "specificity": str(query.get("specificity") or ""),
            "artifact_type": str(getattr(document, "artifact_type", "") or ""),
            "title": str(getattr(document, "title", "") or ""),
            "summary_excerpt": excerpt[:2000],
            "canonical_url": str(artifact.get("canonical_url") or ""),
            "published_at": str(getattr(document, "published_at", "") or ""),
        }
        if set(row) != JUDGE_INPUT_FIELDS:
            raise ModelJudgmentError("blind judge input fields do not match the approved contract")
        _assert_blind(row)
        rows.append(row)
    payload = {
        "schema": JUDGE_INPUT_SCHEMA,
        "benchmark_id": benchmark_id,
        "benchmark_hash": benchmark_hash,
        "corpus_hash": corpus_hash,
        "prompt_hash": grading_prompt_hash,
        "judgments": rows,
    }
    _assert_blind(payload)
    return payload


def validate_model_judgment_output(judge_input: Mapping[str, Any],
                                   output: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Validate an exact, complete model response against its supplied pair inventory."""
    if judge_input.get("schema") != JUDGE_INPUT_SCHEMA:
        raise ModelJudgmentError("unsupported model judge input schema")
    if output.get("schema") != MODEL_JUDGMENT_SCHEMA:
        raise ModelJudgmentError("model output must use retrieval-model-judgment/v1")
    for key in ("benchmark_hash", "corpus_hash", "prompt_hash"):
        if output.get(key) != judge_input.get(key):
            raise ModelJudgmentError(f"model judgment {key} does not match the blind input")
    expected = {(str(item["query_id"]), str(item["artifact_id"]))
                for item in judge_input.get("judgments", [])}
    seen: set[tuple[str, str]] = set()
    normalized = []
    rows = output.get("judgments")
    if not isinstance(rows, list):
        raise ModelJudgmentError("model output judgments must be a list")
    allowed = {"query_id", "artifact_id", "grade", "quality_issue"}
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != allowed:
            raise ModelJudgmentError("model judgment row has missing or unexpected fields")
        identity = (str(row.get("query_id") or ""), str(row.get("artifact_id") or ""))
        if identity not in expected:
            raise ModelJudgmentError(f"unknown model judgment pair: {identity[0]}/{identity[1]}")
        if identity in seen:
            raise ModelJudgmentError(f"duplicate model judgment pair: {identity[0]}/{identity[1]}")
        seen.add(identity)
        grade = row.get("grade")
        if isinstance(grade, bool) or str(grade) not in {"0", "1", "2"}:
            raise ModelJudgmentError("model judgment grade must be 0, 1, or 2")
        quality_issue = row.get("quality_issue")
        if quality_issue not in QUALITY_ISSUES:
            raise ModelJudgmentError("model judgment quality_issue is invalid")
        normalized.append({**dict(row), "grade": int(grade),
                           "query_id": identity[0], "artifact_id": identity[1]})
    missing = expected - seen
    if missing:
        query_id, artifact_id = sorted(missing)[0]
        raise ModelJudgmentError(f"model output is incomplete; missing {query_id}/{artifact_id}")
    return sorted(normalized, key=lambda row: (row["query_id"], row["artifact_id"]))


def make_judge_provenance(*, judged_at: str, prompt_digest: str,
                          guideline_version: str = "m3-2-1-gpt-6-luna") -> dict[str, Any]:
    return {
        "type": "model",
        "name": "GPT-6 Luna",
        "model": "GPT-6 Luna",
        "model_revision": None,
        "reviewer": "GPT-6 Luna (automated model judge; not human)",
        "guideline_version": guideline_version,
        "prompt_hash": prompt_digest,
        "judged_at": _timestamp(judged_at),
        "temperature": None,
        "provider_request_id": None,
        "grade_scale": [0, 1, 2],
    }


def historical_model_provenance(*, judged_at: str | None,
                                guideline_version: str | None) -> dict[str, Any]:
    """Describe legacy judgments without inventing their unavailable prompt/runtime metadata."""
    return {
        "type": "model",
        "name": "GPT-6 Luna",
        "model": "GPT-6 Luna",
        "model_revision": None,
        "reviewer": "GPT-6 Luna (automated model judge; not human)",
        "guideline_version": guideline_version or "m3-2-v1-gpt-6-luna",
        "prompt_hash": None,
        "judged_at": judged_at,
        "temperature": None,
        "provider_request_id": None,
        "grade_scale": [0, 1, 2],
    }


def assemble_model_qrels(*, current_pack: Mapping[str, Any], judge_input: Mapping[str, Any],
                         judge_output: Mapping[str, Any], previous_benchmark: Mapping[str, Any],
                         judged_at: str) -> dict[str, Any]:
    """Merge only current-pool judgments, reusing the immutable DEV-v1 decisions."""
    if current_pack.get("benchmark_id") != "dev-v1.1":
        raise ModelJudgmentError("incremental model qrels require a dev-v1.1 pool pack")
    if current_pack.get("corpus_hash") != previous_benchmark.get("corpus_hash"):
        raise ModelJudgmentError("DEV-v1.1 must use the frozen DEV-v1 corpus hash")
    if any(judge_input.get(key) != current_pack.get(key)
           for key in ("benchmark_hash", "corpus_hash")):
        raise ModelJudgmentError("blind judge input hashes do not match the current pool pack")
    new_rows = validate_model_judgment_output(judge_input, judge_output)
    new_by_id = {(row["query_id"], row["artifact_id"]): row for row in new_rows}
    current = pool_pairs({str(query["query_id"]): [str(candidate["artifact_id"])
                                                    for candidate in query.get("candidates", [])]
                          for query in current_pack.get("queries", [])})
    old_qrels = {(str(row["query_id"]), str(row["artifact_id"])): row
                 for row in previous_benchmark.get("qrels", [])}
    old_pairs = set(old_qrels)
    expected_new = current - old_pairs
    if set(new_by_id) != expected_new:
        raise ModelJudgmentError("blind judge input must contain exactly current-pool pairs absent from DEV-v1")

    previous_quality = {
        (str(row["query_id"]), str(row["artifact_id"])): str(row.get("quality_issue") or "none")
        for row in previous_benchmark.get("quality_issues", [])
    }
    previous_meta = historical_model_provenance(
        judged_at=str(previous_benchmark.get("reviewed_at") or "") or None,
        guideline_version=str(previous_benchmark.get("guideline_version") or "m3-2-v1-gpt-6-luna"),
    )
    current_meta = make_judge_provenance(judged_at=judged_at, prompt_digest=str(judge_input["prompt_hash"]))
    qrels = []
    quality_issues = []
    for identity in sorted(current):
        if identity in old_qrels:
            grade = old_qrels[identity].get("grade")
            quality_issue = previous_quality.get(identity, "none")
            judge = previous_meta
        else:
            row = new_by_id[identity]
            grade = row["grade"]
            quality_issue = row["quality_issue"]
            judge = current_meta
        if isinstance(grade, bool) or grade not in (0, 1, 2) or quality_issue not in QUALITY_ISSUES:
            raise ModelJudgmentError("DEV-v1 contains invalid grade or quality issue values")
        qrels.append({"query_id": identity[0], "artifact_id": identity[1],
                      "grade": int(grade), "judge": judge})
        quality_issues.append({"query_id": identity[0], "artifact_id": identity[1],
                               "quality_issue": quality_issue})
    qrels_hash = hashlib.sha256(json.dumps(
        sorted((row["query_id"], row["artifact_id"], row["grade"]) for row in qrels),
        separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "schema": "bubblevan/retrieval-qrels/v2",
        "benchmark_id": "dev-v1.1",
        "benchmark_hash": current_pack["benchmark_hash"],
        "corpus_hash": current_pack["corpus_hash"],
        "status": "draft",
        "judge": current_meta,
        "provenance": {
            "judgment_type": "model-judged",
            "inherited_from": "dev-v1",
            "inherited_pairs": len(current & old_pairs),
            "new_pairs_judged": len(new_rows),
            "removed_from_current_pool": len(old_pairs - current),
            "historical_prompt_hash": None,
            "historical_runtime_metadata": "unknown; not reconstructed",
        },
        "reviewed_by": current_meta["reviewer"],
        "reviewed_at": _timestamp(judged_at),
        "guideline_version": current_meta["guideline_version"],
        "qrels": qrels,
        "quality_issues": quality_issues,
        "qrels_hash": qrels_hash,
    }


def model_judgment_output(judge_input: Mapping[str, Any],
                          judgments: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema": MODEL_JUDGMENT_SCHEMA,
        "benchmark_hash": judge_input["benchmark_hash"],
        "corpus_hash": judge_input["corpus_hash"],
        "prompt_hash": judge_input["prompt_hash"],
        "judgments": [dict(item) for item in judgments],
    }


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("judged_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("judged_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
