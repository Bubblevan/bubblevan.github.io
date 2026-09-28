from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping

from ..schema_validator import validate_instance


REQUEST_SCHEMA = "bubblevan/intelligence-retrieval-request/v1"


@dataclass(frozen=True)
class RetrievalRequest:
    request_id: str
    query: str
    seed_artifact_ids: tuple[str, ...]
    negative_seed_artifact_ids: tuple[str, ...]
    topic_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    as_of: str | None
    filters: Mapping[str, Any]
    top_k: int
    original_query: str
    expanded_terms: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REQUEST_SCHEMA,
            "request_id": self.request_id,
            "query": self.query,
            "seed_artifact_ids": list(self.seed_artifact_ids),
            "negative_seed_artifact_ids": list(self.negative_seed_artifact_ids),
            "topic_ids": list(self.topic_ids),
            "source_ids": list(self.source_ids),
            "as_of": self.as_of,
            "filters": dict(self.filters),
            "top_k": self.top_k,
            "original_query": self.original_query,
            "expanded_terms": list(self.expanded_terms),
        }


def make_request(
    query: str = "",
    *,
    seed_artifact_ids: list[str] | tuple[str, ...] = (),
    negative_seed_artifact_ids: list[str] | tuple[str, ...] = (),
    topic_ids: list[str] | tuple[str, ...] = (),
    source_ids: list[str] | tuple[str, ...] = (),
    as_of: str | None = None,
    filters: Mapping[str, Any] | None = None,
    top_k: int = 50,
    expanded_terms: list[str] | tuple[str, ...] = (),
) -> RetrievalRequest:
    original = str(query).strip()
    if not original and not seed_artifact_ids and not topic_ids and not source_ids:
        raise ValueError("retrieval request needs a query, seed, topic, or source")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1 or top_k > 500:
        raise ValueError("top_k must be between 1 and 500")
    if as_of is not None:
        as_of = _timestamp(as_of)
    selected_filters = dict(filters or {})
    selected_filters.setdefault("artifact_types", [])
    selected_filters.setdefault("published_after", None)
    selected_filters.setdefault("published_before", None)
    selected_filters.setdefault("languages", [])
    payload = {
        "schema": REQUEST_SCHEMA,
        "query": original,
        "seed_artifact_ids": sorted(set(map(str, seed_artifact_ids))),
        "negative_seed_artifact_ids": sorted(set(map(str, negative_seed_artifact_ids))),
        "topic_ids": sorted(set(map(str, topic_ids))),
        "source_ids": sorted(set(map(str, source_ids))),
        "as_of": as_of,
        "filters": selected_filters,
        "top_k": top_k,
        "original_query": original,
        "expanded_terms": sorted(set(map(str, expanded_terms))),
    }
    request_id = "rq-" + hashlib.sha256(_canonical(payload)).hexdigest()[:24]
    payload["request_id"] = request_id
    from pathlib import Path
    schema = __import__("json").loads(
        (Path(__file__).resolve().parents[3] / "schemas" / "intelligence" / "retrieval_request.schema.json").read_text(encoding="utf-8")
    )
    validate_instance(payload, schema)
    return RetrievalRequest(
        request_id=request_id, query=original,
        seed_artifact_ids=tuple(payload["seed_artifact_ids"]),
        negative_seed_artifact_ids=tuple(payload["negative_seed_artifact_ids"]),
        topic_ids=tuple(payload["topic_ids"]), source_ids=tuple(payload["source_ids"]),
        as_of=as_of, filters=selected_filters, top_k=top_k,
        original_query=original, expanded_terms=tuple(payload["expanded_terms"]),
    )


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("as_of must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
