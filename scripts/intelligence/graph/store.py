from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

from .models import validate_edge


class GraphStore:
    """Single-writer materialized JSONL store for deterministic graph edges."""

    def __init__(self, directory: Path | str):
        self.directory = Path(directory)
        self.path = self.directory / "graph_edges.jsonl"

    def iter_edges(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        result: list[dict[str, Any]] = []
        try:
            for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError
                validate_edge(value)
                result.append(value)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"corrupt graph edge store: {self.path.name}") from exc
        ids = [str(item["edge_id"]) for item in result]
        if len(ids) != len(set(ids)):
            raise ValueError("graph edge store contains duplicate edge ids")
        return sorted(result, key=lambda item: str(item["edge_id"]))

    def add_edge(self, incoming: Mapping[str, Any]) -> dict[str, Any]:
        return self.add_edges([incoming])[0]

    def add_edges(self, incoming_edges: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        rows = self.iter_edges()
        by_id = {str(row["edge_id"]): row for row in rows}
        result = []
        for incoming in incoming_edges:
            validate_edge(incoming)
            edge_id = str(incoming["edge_id"])
            existing = by_id.get(edge_id)
            if existing is None:
                merged = dict(incoming)
            else:
                identity = ("subject_id", "predicate", "object_id")
                if any(existing[field] != incoming[field] for field in identity):
                    raise ValueError("graph edge id collision")
                merged = dict(existing)
                evidence = {_evidence_key(item): dict(item) for item in existing["evidence"]}
                for item in incoming["evidence"]:
                    key = _evidence_key(item)
                    old = evidence.get(key)
                    if old is None or _time_key(item["observed_at"]) > _time_key(old["observed_at"]):
                        evidence[key] = dict(item)
                merged["evidence"] = [evidence[key] for key in sorted(evidence)]
                merged["first_observed_at"] = min(
                    str(existing["first_observed_at"]), str(incoming["first_observed_at"]), key=_time_key,
                )
                merged["last_observed_at"] = max(
                    str(existing["last_observed_at"]), str(incoming["last_observed_at"]), key=_time_key,
                )
            validate_edge(merged)
            by_id[edge_id] = merged
            result.append(merged)
        if result:
            self._atomic_write([by_id[key] for key in sorted(by_id)])
        return result

    def neighbors(
        self,
        node_id: str,
        *,
        predicate: str | None = None,
        entity_id_resolver: Any = None,
    ) -> list[dict[str, Any]]:
        target = entity_id_resolver.resolve_entity_id(node_id) if entity_id_resolver and node_id.startswith("ent-") else node_id
        result = []
        for edge in self.iter_edges():
            subject = edge["subject_id"]
            obj = edge["object_id"]
            if entity_id_resolver:
                if subject.startswith("ent-"):
                    subject = entity_id_resolver.resolve_entity_id(subject)
                if obj.startswith("ent-"):
                    obj = entity_id_resolver.resolve_entity_id(obj)
            if predicate and edge["predicate"] != predicate:
                continue
            if subject == target or obj == target:
                result.append(edge)
        return sorted(result, key=lambda edge: (edge["predicate"], edge["subject_id"], edge["object_id"]))

    def rebuild_indexes(self, runtime_dir: Path | str, *, entity_id_resolver: Any = None) -> dict[str, int]:
        """Rebuild disposable deterministic in/out adjacency indexes from source of truth."""
        out_index: dict[str, list[dict[str, str]]] = {}
        in_index: dict[str, list[dict[str, str]]] = {}
        for edge in self.iter_edges():
            subject = str(edge["subject_id"])
            obj = str(edge["object_id"])
            if entity_id_resolver:
                if subject.startswith("ent-"):
                    subject = entity_id_resolver.resolve_entity_id(subject)
                if obj.startswith("ent-"):
                    obj = entity_id_resolver.resolve_entity_id(obj)
            entry = {"edge_id": edge["edge_id"], "predicate": edge["predicate"]}
            out_index.setdefault(subject, []).append({**entry, "object_id": obj})
            in_index.setdefault(obj, []).append({**entry, "subject_id": subject})
        for index in (out_index, in_index):
            for key in index:
                index[key].sort(key=lambda item: (item["predicate"], item.get("object_id", item.get("subject_id", "")), item["edge_id"]))
        directory = Path(runtime_dir) / "graph"
        self._atomic_json(directory / "out_edges.json", out_index)
        self._atomic_json(directory / "in_edges.json", in_index)
        return {"nodes": len(set(out_index) | set(in_index)), "edges": sum(map(len, out_index.values()))}

    def _atomic_write(self, edges: Iterable[Mapping[str, Any]]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        _atomic_bytes(self.path, "".join(_json_line(row) for row in edges).encode("utf-8"))

    @staticmethod
    def _atomic_json(path: Path, value: Any) -> None:
        _atomic_bytes(path, (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))


def _evidence_key(item: Mapping[str, Any]) -> tuple[str, str, str, str, str]:
    return tuple(str(item.get(key) or "") for key in (
        "evidence_type", "provider", "source_id", "observation_id", "provider_record_id",
    ))  # type: ignore[return-value]


def _time_key(value: str) -> float:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _json_line(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
