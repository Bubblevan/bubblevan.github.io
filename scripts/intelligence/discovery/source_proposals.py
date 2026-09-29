from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping
from urllib.parse import urljoin

from ..canonicalize import canonicalize_url
from ..ids import stable_id
from ..models import new_source, now_utc
from ..schema_validator import validate_record
from ..connectors.http import HttpResponse, SharedHttpClient


SCHEMA = "bubblevan/intelligence-source-proposal/v1"
PROPOSAL_PATH = Path(__file__).resolve().parents[3] / "data" / "intelligence" / "private" / "sources" / "proposals.jsonl"
SUBSCRIPTION_PATH = PROPOSAL_PATH.with_name("subscriptions.jsonl")


@dataclass(frozen=True)
class SourceProbeResult:
    status: str
    detail: str
    endpoint: str
    entries: int = 0


class SourceProposalStore:
    def __init__(self, path: Path | str = PROPOSAL_PATH):
        self.path = Path(path)

    def list(self, *, status: str | None = None) -> list[dict[str, Any]]:
        rows = _read_jsonl(self.path, "source proposal store")
        for row in rows:
            validate_record("source_proposal", row)
        if status:
            rows = [row for row in rows if row["status"] == status]
        return sorted(rows, key=lambda row: (str(row.get("created_at") or ""), str(row["proposal_id"])))

    def upsert(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        row = dict(proposal)
        validate_record("source_proposal", row)
        rows = {str(item["proposal_id"]): item for item in self.list()}
        old = rows.get(str(row["proposal_id"]))
        if old and old["status"] in {"rejected", "approved", "deferred"}:
            row["status"] = old["status"]
            row["reviewed_at"] = old.get("reviewed_at")
            row["reason_code"] = old.get("reason_code")
        rows[str(row["proposal_id"])] = row
        _atomic_jsonl(self.path, [rows[key] for key in sorted(rows)])
        return row

    def review(self, proposal_id: str, status: str, *, reviewed_at: str | None = None,
               reason_code: str | None = None) -> dict[str, Any]:
        if status not in {"approved", "rejected", "deferred"}:
            raise ValueError("invalid proposal review status")
        rows = {str(item["proposal_id"]): item for item in self.list()}
        try:
            row = dict(rows[proposal_id])
        except KeyError as exc:
            raise ValueError("source proposal not found") from exc
        if row["status"] == "rejected" and status != "rejected":
            raise ValueError("rejected source proposal cannot be reactivated")
        if status == "approved" and row["probe_status"] != "valid":
            raise ValueError("only a valid source probe can be approved")
        row.update({"status": status, "reviewed_at": reviewed_at or now_utc(), "reason_code": reason_code})
        validate_record("source_proposal", row)
        rows[proposal_id] = row
        _atomic_jsonl(self.path, [rows[key] for key in sorted(rows)])
        return row


class SourceSubscriptionRegistry:
    def __init__(self, path: Path | str = SUBSCRIPTION_PATH):
        self.path = Path(path)

    def list(self) -> list[dict[str, Any]]:
        rows = _read_jsonl(self.path, "private source subscription registry")
        for row in rows:
            validate_record("source", row)
        ids = [str(row["source_id"]) for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("private source subscription registry has duplicate source_id")
        return sorted(rows, key=lambda row: str(row["source_id"]))

    def add(self, source: Mapping[str, Any]) -> dict[str, Any]:
        row = dict(source)
        validate_record("source", row)
        existing = {str(item["source_id"]): item for item in self.list()}
        source_id = str(row["source_id"])
        if source_id in existing:
            raise ValueError("source subscription already exists")
        existing[source_id] = row
        _atomic_jsonl(self.path, [existing[key] for key in sorted(existing)])
        return row


def source_from_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    if proposal.get("status") != "pending" or proposal.get("probe_status") != "valid":
        raise ValueError("source proposal is not pending and probe-valid")
    identity = "rss|discovered|" + str(proposal["canonical_url"])
    source = new_source(
        identity=identity,
        source_type=str(proposal["source_type"]),
        platform=str(proposal["platform"]),
        name=str(proposal["name"]),
        canonical_url=str(proposal["canonical_url"]),
        topics=[str(item) for item in proposal.get("topics", [])],
        connector=str(proposal["acquisition"]["connector"]),
        mode=str(proposal["acquisition"]["mode"]),
        status="active",
        created_at=str(proposal.get("created_at") or now_utc()),
    )
    validate_record("source", source)
    return source


def discover_rss_proposals(candidates: Iterable[Mapping[str, Any]], entities: Iterable[Mapping[str, Any]],
                           proposals: SourceProposalStore, *, http: Any = None,
                           now: str | None = None, max_candidates: int = 12) -> list[dict[str, Any]]:
    """Discover standard feed links from reviewed or pending candidates; never activates them."""
    entity_by_id = {str(row["entity_id"]): row for row in entities}
    client = http or SharedHttpClient()
    discovered = []
    selected = [row for row in candidates if row.get("status") in {"approved", "pending"}][:max_candidates]
    for candidate in selected:
        entity = entity_by_id.get(str(candidate.get("entity_id")))
        homepage = canonicalize_url(str(candidate.get("canonical_url") or ""))
        if entity and (not homepage or homepage not in (entity.get("urls") or [])):
            urls = sorted(canonicalize_url(str(url)) for url in entity.get("urls", []) if canonicalize_url(str(url)))
            homepage = next((url for url in urls if _is_public_homepage(url)), homepage)
        if not _is_public_homepage(homepage):
            continue
        try:
            response = client.get(homepage)
        except Exception:
            continue
        if response.status != 200 or len(response.body) > 2_000_000:
            continue
        parser = _AlternateFeedLinks()
        try:
            parser.feed(response.body.decode("utf-8", errors="replace"))
            parser.close()
        except Exception:
            continue
        seen_endpoints: set[str] = set()
        for mime_type, href in parser.links[:5]:
            endpoint = canonicalize_url(urljoin(homepage, href))
            if endpoint in seen_endpoints or not _is_public_homepage(endpoint):
                continue
            seen_endpoints.add(endpoint)
            probe = probe_rss_endpoint(endpoint, http=client)
            proposal = _proposal_from_candidate(candidate, endpoint, probe,
                                                discovered_at=now or now_utc())
            discovered.append(proposals.upsert(proposal))
    return discovered


def probe_rss_endpoint(endpoint: str, *, http: Any = None) -> SourceProbeResult:
    url = canonicalize_url(endpoint)
    if not url:
        return SourceProbeResult("invalid", "endpoint_invalid", "")
    client = http or SharedHttpClient()
    try:
        response: HttpResponse = client.get(url)
    except Exception:
        return SourceProbeResult("temporarily_unavailable", "transport_failure", url)
    if response.status in {401, 403}:
        return SourceProbeResult("auth_required", "http_auth_required", url)
    if response.status == 429 or 500 <= response.status <= 599:
        return SourceProbeResult("temporarily_unavailable", "provider_unavailable", url)
    if response.status != 200:
        return SourceProbeResult("invalid", "http_status_invalid", url)
    try:
        import feedparser
        parsed = feedparser.parse(response.body)
    except ImportError:
        return SourceProbeResult("unsupported", "feedparser_unavailable", url)
    except Exception:
        return SourceProbeResult("invalid", "feed_parse_failed", url)
    if not parsed.entries and getattr(parsed, "bozo", False):
        return SourceProbeResult("invalid", "feed_parse_failed", url)
    return SourceProbeResult("valid", "feed_valid", url, len(parsed.entries))


def _proposal_from_candidate(candidate: Mapping[str, Any], endpoint: str, probe: SourceProbeResult,
                             *, discovered_at: str) -> dict[str, Any]:
    candidate_type = str(candidate.get("candidate_type") or "")
    source_type = {"person": "author", "institution": "lab", "organization": "lab",
                   "repository": "repository"}.get(candidate_type, "feed")
    candidate_id_value = str(candidate.get("candidate_id") or "") or None
    return {
        "schema": SCHEMA,
        "proposal_id": stable_id("sp", "source-proposal", "rss|" + endpoint),
        "candidate_id": candidate_id_value,
        "source_type": source_type,
        "platform": "rss",
        "name": str(candidate.get("name") or endpoint),
        "canonical_url": probe.endpoint,
        "acquisition": {"connector": "rss-atom", "mode": "rss"},
        "probe_status": probe.status,
        "probe_detail": probe.detail,
        "discovered_via": f"source-candidate:{candidate_id_value}" if candidate_id_value else str(candidate.get("canonical_url") or "manual-probe"),
        "topics": sorted(set(str(item) for item in candidate.get("topics", []))),
        "evidence_path": list(candidate.get("evidence_paths", [])),
        "status": "pending",
        "created_at": discovered_at,
        "reviewed_at": None,
        "reason_code": None,
    }


class _AlternateFeedLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._anchor: tuple[dict[str, str], list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag not in {"link", "a"}:
            return
        values = {str(key).casefold(): str(value or "") for key, value in attrs}
        if tag == "link":
            rel = {item.casefold() for item in values.get("rel", "").split()}
            mime = values.get("type", "").split(";", 1)[0].strip().casefold()
            if "alternate" in rel and mime in {"application/rss+xml", "application/atom+xml"} and values.get("href"):
                self.links.append((mime, values["href"]))
        else:
            self._anchor = (values, [])

    def handle_data(self, data: str) -> None:
        if self._anchor is not None:
            self._anchor[1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "a" or self._anchor is None:
            return
        values, text = self._anchor
        self._anchor = None
        href = values.get("href", "")
        explicit_type = values.get("type", "").casefold()
        label = " ".join(text).casefold()
        if not href or not re.search(r"\b(?:rss|atom|feeds?)\b", label + " " + explicit_type):
            return
        mime = ("application/atom+xml" if "atom" in explicit_type or "atom" in label
                else "application/rss+xml")
        self.links.append((mime, href))


def _is_public_homepage(value: str) -> bool:
    import ipaddress
    from urllib.parse import urlsplit
    parts = urlsplit(value)
    host = (parts.hostname or "").casefold().rstrip(".")
    if (parts.scheme != "https" or not host or not parts.netloc
            or parts.username or parts.password or host == "localhost"
            or host.endswith((".local", ".internal", ".test", ".example"))):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return "." in host


def _read_jsonl(path: Path, description: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError
                rows.append(row)
        return rows
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{description} is corrupt") from exc


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temp = handle.name
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)
