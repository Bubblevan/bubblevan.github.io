from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import yaml

from ..connectors.http import SharedHttpClient
from ..ids import stable_id
from ..topics import topic_aliases
from ..models import now_utc


REPO_ROOT = Path(__file__).resolve().parents[3]
TOPIC_MAP_PATH = REPO_ROOT / "data" / "intelligence" / "openalex_topic_map.yaml"
TOPIC_PROPOSALS_PATH = REPO_ROOT / "data" / "intelligence" / "private" / "sources" / "openalex_topic_proposals.jsonl"


class OpenAlexTopicProposalStore:
    def __init__(self, path: Path | str = TOPIC_PROPOSALS_PATH):
        self.path = Path(path)

    def list(self, *, status: str | None = None) -> list[dict[str, Any]]:
        rows = _read_jsonl(self.path)
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return sorted(rows, key=lambda row: (str(row.get("internal_topic_id")),
                                             -int(row.get("works_count") or 0), str(row.get("openalex_topic_id"))))

    def propose(self, internal_topic_id: str, *, http: Any = None, now: str | None = None) -> list[dict[str, Any]]:
        topic_name, aliases = _internal_topic_descriptor(internal_topic_id)
        client = http or SharedHttpClient()
        results = [(topic_name, row) for row in _search_topics(client, topic_name)]
        # Narrow internal labels can have no direct OpenAlex match. In that
        # case, query the ontology's explicit aliases and preserve the search
        # term so a person can review why each mapping was proposed.
        if not results:
            for term in aliases:
                results.extend((term, row) for row in _search_topics(client, term))
        existing = {str(item["proposal_id"]): item for item in self.list()}
        created_at = now or now_utc()
        for term, row in results:
            topic_id = str(row.get("id") or "").rstrip("/").rsplit("/", 1)[-1]
            if not topic_id.startswith("T") or not topic_id[1:].isalnum():
                continue
            proposal_id = stable_id("ot", "openalex-topic-proposal", internal_topic_id + "|" + topic_id)
            old = existing.get(proposal_id)
            matched_terms = sorted(set((old or {}).get("matched_search_terms", [])) | {term})
            proposal = {
                "proposal_id": proposal_id,
                "internal_topic_id": internal_topic_id,
                "internal_topic_name": topic_name,
                "openalex_topic_id": topic_id,
                "display_name": str(row.get("display_name") or "")[:240],
                "description": str(row.get("description") or "")[:2000],
                "works_count": int(row.get("works_count") or 0),
                "matched_search_terms": matched_terms,
                "status": old.get("status", "pending") if old else "pending",
                "created_at": old.get("created_at", created_at) if old else created_at,
            }
            existing[proposal_id] = proposal
        _atomic_jsonl(self.path, [existing[key] for key in sorted(existing)])
        return [row for row in self.list() if row["internal_topic_id"] == internal_topic_id]

    def approve(self, proposal_id: str, *, reviewed_by: str, reviewed_at: str | None = None) -> dict[str, Any]:
        if not reviewed_by.strip():
            raise ValueError("reviewed_by is required for topic mapping approval")
        rows = {str(row["proposal_id"]): row for row in self.list()}
        if proposal_id not in rows:
            raise ValueError("OpenAlex topic proposal not found")
        proposal = dict(rows[proposal_id])
        if proposal["status"] == "rejected":
            raise ValueError("rejected OpenAlex topic proposal cannot be approved")
        timestamp = reviewed_at or now_utc()
        _write_topic_mapping(TOPIC_MAP_PATH, proposal, reviewed_by.strip(), timestamp)
        proposal["status"] = "approved"
        proposal["reviewed_by"] = reviewed_by.strip()
        proposal["reviewed_at"] = timestamp
        rows[proposal_id] = proposal
        _atomic_jsonl(self.path, [rows[key] for key in sorted(rows)])
        return proposal

    def reject(self, proposal_id: str, *, reviewed_at: str | None = None) -> dict[str, Any]:
        rows = {str(row["proposal_id"]): row for row in self.list()}
        if proposal_id not in rows:
            raise ValueError("OpenAlex topic proposal not found")
        row = dict(rows[proposal_id])
        if row["status"] == "approved":
            raise ValueError("approved OpenAlex topic proposal cannot be rejected in place")
        row.update({"status": "rejected", "reviewed_at": reviewed_at or now_utc()})
        rows[proposal_id] = row
        _atomic_jsonl(self.path, [rows[key] for key in sorted(rows)])
        return row


def _internal_topic_descriptor(topic_id: str) -> tuple[str, list[str]]:
    path = REPO_ROOT / "data" / "intelligence" / "topics.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    for topic in payload.get("topics", []):
        if str(topic.get("topic_id")) == topic_id:
            name = str(topic.get("name") or topic_id)
            values = topic.get("aliases", [])
            aliases = sorted({str(value).strip() for value in values if str(value).strip()})
            return name, aliases
    raise ValueError("unknown internal topic ID")


def _search_topics(client: Any, term: str) -> list[dict[str, Any]]:
    import urllib.parse
    url = "https://api.openalex.org/topics?" + urllib.parse.urlencode({
        "search": term, "per-page": 10, "select": "id,display_name,description,works_count",
    })
    response = client.get(url)
    if response.status == 429:
        from ..connectors.base import ConnectorDeferred
        raise ConnectorDeferred(retry_after_seconds=client.retry_after_seconds(response.headers))
    if response.status != 200:
        raise RuntimeError(f"OpenAlex topic search HTTP status {response.status}")
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise RuntimeError("OpenAlex topic search returned malformed data") from None
    results = payload.get("results", []) if isinstance(payload, dict) else []
    if not isinstance(results, list):
        raise RuntimeError("OpenAlex topic search response is malformed")
    return [row for row in results[:10] if isinstance(row, dict)]


def _write_topic_mapping(path: Path, proposal: dict[str, Any], reviewed_by: str, reviewed_at: str) -> None:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {
        "schema": "bubblevan/openalex-topic-map/v1", "mappings": []}
    mappings = payload.get("mappings") if isinstance(payload, dict) else None
    if not isinstance(mappings, list):
        raise ValueError("OpenAlex topic map is malformed")
    internal_id = proposal["internal_topic_id"]
    row = next((item for item in mappings if item.get("internal_topic_id") == internal_id), None)
    if row is None:
        row = {"internal_topic_id": internal_id, "openalex_topic_ids": [], "reviewed_mappings": []}
        mappings.append(row)
    topic_ids = set(str(item) for item in row.get("openalex_topic_ids", []))
    topic_ids.add(str(proposal["openalex_topic_id"]))
    row["openalex_topic_ids"] = sorted(topic_ids)
    reviewed = list(row.get("reviewed_mappings", []))
    evidence = {"openalex_topic_id": proposal["openalex_topic_id"],
                "display_name": proposal["display_name"], "description": proposal["description"],
                "works_count": proposal["works_count"], "reviewed_by": reviewed_by,
                "reviewed_at": reviewed_at}
    if evidence not in reviewed:
        reviewed.append(evidence)
    row["reviewed_mappings"] = sorted(reviewed, key=lambda item: str(item["openalex_topic_id"]))
    payload["mappings"] = sorted(mappings, key=lambda item: str(item["internal_topic_id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_text(path, yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError
        return rows
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("OpenAlex topic proposal store is corrupt") from exc


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    _atomic_text(path, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows))


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temp = handle.name
            handle.write(text); handle.flush(); os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)
