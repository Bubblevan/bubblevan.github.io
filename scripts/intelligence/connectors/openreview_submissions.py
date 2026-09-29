from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping
from urllib.parse import quote, urljoin

from ..canonicalize import extract_arxiv_id, extract_doi
from ..models import new_observation, parse_datetime
from ..topics import map_topics
from ..discovery.source_proposals import SourceProbeResult
from .base import ConnectorCheckpoint, ConnectorContext, ConnectorDeferred, ConnectorSpec, FetchResult
from .http import HttpTransportError
from .privacy import redact_private_text


class OpenReviewSubmissionsConnector:
    spec = ConnectorSpec(
        connector_id="openreview-submissions", version="1", modes=("api",),
        capabilities=frozenset({"pull", "incremental", "bounded_backfill"}), supports_incremental=True,
    )

    def __init__(self, client_factory: Callable[[int], Any] | None = None):
        self.client_factory = client_factory or _openreview_client

    def fetch(self, source: dict[str, Any], checkpoint: ConnectorCheckpoint | None,
              context: ConnectorContext) -> FetchResult:
        venue = _venue_config(source)
        version = int(venue["api_version"])
        invitation = str(venue["invitation"])
        cap = int(venue.get("max_backfill", 100))
        client = self.client_factory(version)
        notes = _get_notes(client, version, invitation, cap + 1)
        truncated = len(notes) > cap
        observations = []
        papers_by_forum: dict[str, dict[str, Any]] = {}
        for note in notes[:cap]:
            normalized = _note_dict(note)
            # This connector reads only the explicitly configured submission invitation.
            # It never requests direct replies or review/comment threads.
            if not _public_note(normalized):
                continue
            content = normalized.get("content") if isinstance(normalized.get("content"), Mapping) else {}
            note_id = str(normalized.get("forum") or normalized.get("id") or "").strip()
            note_object_id = str(normalized.get("id") or note_id).strip()
            if not note_object_id:
                continue
            title = _text(content.get("title"))
            abstract = _text(content.get("abstract"))[:12000]
            authors = _authors(content.get("authors"))
            forum_id = str(normalized.get("forum") or normalized.get("id") or "")
            forum_url = "https://openreview.net/forum?id=" + quote(forum_id, safe="") if forum_id else ""
            pdf_url = _public_pdf(content.get("pdf"))
            submitted_at = _timestamp(normalized.get("cdate"))
            publication_at = _timestamp(normalized.get("pdate"))
            search_text = "\n".join((title, abstract, pdf_url))
            doi = extract_doi(search_text)
            arxiv = extract_arxiv_id(search_text)
            canonical = (f"https://doi.org/{doi}" if doi else
                         f"https://arxiv.org/abs/{arxiv}" if arxiv else forum_url)
            identifiers = {"doi": doi, "arxiv": arxiv, "openreview": note_id or note_object_id}
            candidate = {
                "artifact_type": "paper", "title": title, "canonical_url": canonical,
                "identifiers": identifiers, "authors": authors, "organizations": [],
                "summary": abstract[:4000], "published_at": publication_at,
                "topics": list(source.get("topics", [])),
                "mention": {"role": "primary", "evidence_level": "api_metadata",
                            "origin": "openreview_submission", "confidence": 1.0},
            }
            papers_by_forum[forum_id or note_object_id] = candidate
            urls = [value for value in (forum_url, pdf_url) if value]
            decision_visibility = "public" if _public_note(normalized) else "unknown"
            observations.append(new_observation(
                identity=f"openreview|{source['source_id']}|{note_object_id}",
                source_id=str(source["source_id"]), platform="openreview",
                platform_object_id="openreview:" + note_object_id, kind="paper_submission",
                title=title, text=abstract, urls=urls,
                media=[], published_at=publication_at, observed_at=context.now(),
                topics=map_topics(source.get("topics", [])), authors=authors,
                provenance={"retrieval_mode": "openreview_api", "evidence_level": "api_metadata",
                            "source_url": forum_url, "collector": self.spec.connector_id},
                metadata={"openreview_note_id": note_object_id, "openreview_forum_id": forum_id or note_object_id,
                          "submission_invitation": invitation, "submitted_at": submitted_at,
                          "publication_at": publication_at, "public_pdf_url": pdf_url or None,
                          "decision_visibility": decision_visibility},
                artifact_candidates=[candidate],
            ))
        decision_invitation = str(venue.get("decision_invitation") or "").strip()
        decision_count = 0
        if decision_invitation:
            decision_notes = _get_notes(client, version, decision_invitation, cap + 1)
            for note in decision_notes[:cap]:
                normalized = _note_dict(note)
                if not _public_note(normalized):
                    continue
                note_object_id = str(normalized.get("id") or "").strip()
                forum_id = str(normalized.get("forum") or "").strip()
                content = normalized.get("content") if isinstance(normalized.get("content"), Mapping) else {}
                decision = _text(content.get("decision") or content.get("recommendation") or "")
                if not note_object_id or not forum_id or not decision:
                    continue
                paper = papers_by_forum.get(forum_id)
                if paper is None:
                    paper = {
                        "artifact_type": "paper", "title": _text(content.get("title")),
                        "canonical_url": "https://openreview.net/forum?id=" + quote(forum_id, safe=""),
                        "identifiers": {"doi": None, "arxiv": None, "openreview": forum_id},
                        "authors": [], "organizations": [], "summary": "", "published_at": None,
                        "topics": list(source.get("topics", [])),
                        "mention": {"role": "primary", "evidence_level": "api_metadata",
                                    "origin": "openreview_public_decision", "confidence": 1.0},
                    }
                forum_url = "https://openreview.net/forum?id=" + quote(forum_id, safe="")
                observations.append(new_observation(
                    identity=f"openreview-decision|{source['source_id']}|{note_object_id}",
                    source_id=str(source["source_id"]), platform="openreview",
                    platform_object_id="openreview-decision:" + note_object_id, kind="decision",
                    title=decision, text="", urls=[forum_url], media=[], published_at=_timestamp(normalized.get("pdate")),
                    observed_at=context.now(), topics=map_topics(source.get("topics", [])), authors=[],
                    provenance={"retrieval_mode": "openreview_api", "evidence_level": "api_metadata",
                                "source_url": forum_url, "collector": self.spec.connector_id},
                    metadata={"openreview_note_id": note_object_id, "openreview_forum_id": forum_id,
                              "decision_invitation": decision_invitation, "decision_visibility": "public"},
                    artifact_candidates=[paper],
                ))
                decision_count += 1
        now = context.now()
        next_checkpoint = ConnectorCheckpoint(cursor=None, last_success_at=now)
        return FetchResult(observations, next_checkpoint, True,
                           {"entries_fetched": len(notes[:cap]) + decision_count, "pages": 1,
                            "truncated_at_bound": truncated, "decision_observations": decision_count,
                            "api_version": version})

    def probe(self, *, api_version: int, invitation: str,
              decision_invitation: str | None = None) -> SourceProbeResult:
        if api_version not in {1, 2} or not invitation.strip():
            return SourceProbeResult("invalid", "explicit_version_and_invitation_required", "")
        try:
            client = self.client_factory(api_version)
            result = _official_request(client.get_invitation, id=invitation)
            found_id = str(getattr(result, "id", "") or (result.get("id") if isinstance(result, dict) else ""))
            if found_id != invitation:
                return SourceProbeResult("invalid", "invitation_id_mismatch", "")
            if decision_invitation:
                decision = _official_request(client.get_invitation, id=decision_invitation)
                decision_id = str(getattr(decision, "id", "") or
                                  (decision.get("id") if isinstance(decision, dict) else ""))
                if decision_id != decision_invitation:
                    return SourceProbeResult("invalid", "decision_invitation_id_mismatch", "")
        except HttpTransportError:
            return SourceProbeResult("temporarily_unavailable", "transport_failure", "")
        except Exception:
            return SourceProbeResult("invalid", "invitation_not_found_or_unavailable", "")
        return SourceProbeResult("valid", f"openreview_api{api_version}_invitation_valid", "")


def _openreview_client(version: int) -> Any:
    try:
        if version == 2:
            from openreview.api import OpenReviewClient
            return OpenReviewClient(baseurl="https://api2.openreview.net")
        if version == 1:
            import openreview
            return openreview.Client(baseurl="https://api.openreview.net")
    except ImportError as exc:
        raise RuntimeError("OpenReview connector requires requirements-sources.txt") from exc
    raise ValueError("OpenReview API version must be 1 or 2")


def _venue_config(source: Mapping[str, Any]) -> Mapping[str, Any]:
    acquisition = source.get("acquisition") if isinstance(source.get("acquisition"), Mapping) else {}
    venue = acquisition.get("venue") if isinstance(acquisition.get("venue"), Mapping) else None
    if (not venue or set(venue) - {"api_version", "invitation", "decision_invitation", "max_backfill"}
            or type(venue.get("api_version")) is not int or venue.get("api_version") not in {1, 2}
            or not str(venue.get("invitation") or "").strip()
            or ("decision_invitation" in venue and not str(venue.get("decision_invitation") or "").strip())):
        raise ValueError("OpenReview source requires explicit API version and invitation config")
    return venue


def _get_notes(client: Any, version: int, invitation: str, limit: int) -> list[Any]:
    # `invitation` is the only query selector; no replies or unrestricted fetch is made.
    # openreview-py 2.x's `get_all_notes` does not accept a limit; its supported
    # bounded API is `get_notes(..., limit=...)`. Use the same bounded method for v1.
    if hasattr(client, "get_notes"):
        return list(_official_request(client.get_notes, invitation=invitation, limit=limit))
    if hasattr(client, "get_all_notes"):
        return list(_official_request(client.get_all_notes, invitation=invitation, number=limit))
    raise RuntimeError("installed OpenReview client cannot fetch notes with an invitation bound")


def _official_request(operation: Callable[..., Any], **kwargs: Any) -> Any:
    """Convert known requests transport failures to safe categories without exception text."""
    try:
        return operation(**kwargs)
    except Exception as exc:
        module = type(exc).__module__
        name = type(exc).__name__
        category = None
        if module.startswith("requests."):
            category = {
                "ConnectTimeout": "connect_timeout",
                "ReadTimeout": "read_timeout",
                "Timeout": "read_timeout",
                "SSLError": "tls_error",
                "ConnectionError": "transport_other",
            }.get(name)
        if category:
            raise HttpTransportError(category) from None
        raise


def _note_dict(note: Any) -> dict[str, Any]:
    if isinstance(note, Mapping):
        return dict(note)
    if hasattr(note, "to_json"):
        value = note.to_json()
        if isinstance(value, Mapping):
            return dict(value)
    value = getattr(note, "__dict__", {})
    return dict(value) if isinstance(value, Mapping) else {}


def _public_note(note: Mapping[str, Any]) -> bool:
    readers = note.get("readers")
    if not readers:
        return False
    values = {str(value).casefold() for value in readers} if isinstance(readers, list) else set()
    return "everyone" in values or "openreview.net" in values


def _text(value: Any) -> str:
    if isinstance(value, Mapping) and "value" in value:
        value = value["value"]
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return redact_private_text(str(value or "")).strip()


def _authors(value: Any) -> list[str]:
    if isinstance(value, Mapping) and "value" in value:
        value = value["value"]
    values = value if isinstance(value, list) else str(value or "").split(",")
    return sorted({redact_private_text(str(item)).strip() for item in values if str(item).strip()})


def _public_pdf(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    url = urljoin("https://openreview.net", text)
    from ..canonicalize import canonicalize_url
    safe = canonicalize_url(url)
    if not safe.startswith("https://openreview.net/"):
        return ""
    return safe


def _timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            parsed = datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
            return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")
        return parse_datetime(str(value))
    except (TypeError, ValueError, OverflowError, OSError):
        return None
