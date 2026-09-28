from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from ..ids import stable_id
from ..models import parse_datetime
from ..schema_validator import validate_record


EDGE_SCHEMA = "bubblevan/intelligence-graph-edge/v1"
EVIDENCE_TYPES = {
    "exact_provider_metadata", "explicit_source_link", "explicit_observation_text",
    "image_extract", "inferred_candidate",
}
_PREDICATES = Path(__file__).resolve().parents[3] / "data" / "intelligence" / "graph_predicates.yaml"


class GraphEdge(dict[str, Any]):
    """JSON-compatible graph edge record."""


def predicate_definitions(path: Path | str = _PREDICATES) -> dict[str, dict[str, Any]]:
    return _load_predicate_definitions(str(path))


@lru_cache(maxsize=8)
def _load_predicate_definitions(path: str) -> dict[str, dict[str, Any]]:
    try:
        value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError("graph predicate catalog is malformed") from exc
    predicates = value.get("predicates") if isinstance(value, Mapping) else None
    if not isinstance(value, Mapping) or value.get("schema") != "bubblevan/intelligence-graph-predicates/v1" or not isinstance(predicates, dict):
        raise ValueError("graph predicate catalog is malformed")
    result: dict[str, dict[str, Any]] = {}
    for predicate, definition in predicates.items():
        if not isinstance(predicate, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", predicate):
            raise ValueError("graph predicate catalog contains invalid predicate")
        if not isinstance(definition, dict) or not isinstance(definition.get("subjects"), list) or not isinstance(definition.get("objects"), list):
            raise ValueError("graph predicate catalog contains invalid definition")
        if any(not isinstance(item, str) for item in definition["subjects"] + definition["objects"]):
            raise ValueError("graph predicate catalog contains invalid node type")
        result[predicate] = definition
    return result


def edge_identity(subject_id: str, predicate: str, object_id: str) -> str:
    return stable_id("edge", "graph-edge", f"{subject_id}|{predicate}|{object_id}")


def make_edge(
    subject_id: str,
    predicate: str,
    object_id: str,
    evidence: Mapping[str, Any],
    *,
    observed_at: str | None = None,
    allow_candidate_evidence: bool = False,
) -> GraphEdge:
    definitions = predicate_definitions()
    if predicate not in definitions or definitions[predicate].get("projection_only"):
        raise ValueError("unsupported canonical graph predicate")
    if not _valid_node_id(subject_id) or not _valid_node_id(object_id):
        raise ValueError("graph edge contains an invalid node id")
    item = dict(evidence)
    evidence_type = str(item.get("evidence_type") or "")
    allowed = {"exact_provider_metadata", "explicit_source_link"}
    if allow_candidate_evidence:
        allowed |= EVIDENCE_TYPES
    if evidence_type not in allowed:
        raise ValueError("graph edge evidence is not eligible for canonical storage")
    timestamp = parse_datetime(observed_at or item.get("observed_at"), default_now=True)
    item = {
        "evidence_type": evidence_type,
        "provider": str(item.get("provider") or "") or None,
        "source_id": str(item.get("source_id") or "") or None,
        "observation_id": str(item.get("observation_id") or "") or None,
        "provider_record_id": str(item.get("provider_record_id") or "") or None,
        "confidence": float(item.get("confidence", 1.0)),
        "observed_at": timestamp,
    }
    edge = GraphEdge({
        "schema": EDGE_SCHEMA,
        "edge_id": edge_identity(subject_id, predicate, object_id),
        "subject_id": subject_id,
        "predicate": predicate,
        "object_id": object_id,
        "first_observed_at": timestamp,
        "last_observed_at": timestamp,
        "evidence": [item],
    })
    validate_record("graph_edge", edge)
    return edge


def validate_edge(edge: Mapping[str, Any]) -> None:
    validate_record("graph_edge", dict(edge))
    if edge.get("edge_id") != edge_identity(str(edge.get("subject_id")), str(edge.get("predicate")), str(edge.get("object_id"))):
        raise ValueError("graph edge id does not match its relation")
    definitions = predicate_definitions()
    if edge.get("predicate") not in definitions or definitions[edge["predicate"]].get("projection_only"):
        raise ValueError("graph edge uses an unknown predicate")
    first = _aware(str(edge["first_observed_at"]))
    last = _aware(str(edge["last_observed_at"]))
    if last < first:
        raise ValueError("graph edge last_observed_at precedes first_observed_at")
    eligible = {"exact_provider_metadata", "explicit_source_link"}
    evidence_keys: set[tuple[str, str, str, str, str]] = set()
    for item in edge.get("evidence", []):
        if item["evidence_type"] not in eligible:
            raise ValueError("non-canonical evidence found in graph store")
        key = _evidence_identity(item)
        if key in evidence_keys:
            raise ValueError("duplicate graph edge evidence")
        evidence_keys.add(key)


def _evidence_identity(item: Mapping[str, Any]) -> tuple[str, str, str, str, str]:
    return tuple(str(item.get(key) or "") for key in (
        "evidence_type", "provider", "source_id", "observation_id", "provider_record_id",
    ))  # type: ignore[return-value]


def _valid_node_id(value: str) -> bool:
    return bool(re.fullmatch(r"(?:src|obs|art|ent|topic)-[a-z0-9-]+", value))


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
