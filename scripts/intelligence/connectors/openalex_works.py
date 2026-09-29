from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from typing import Any, Mapping
from urllib.parse import urlencode

from ..canonicalize import canonicalize_url, extract_arxiv_id, extract_doi
from ..models import new_observation, parse_datetime
from .base import ConnectorCheckpoint, ConnectorContext, ConnectorDeferred, ConnectorFailure, ConnectorSpec, FetchResult
from .http import HttpResponse, SharedHttpClient
from .privacy import redact_private_text
from ..discovery.source_proposals import SourceProbeResult
from ..providers.openalex_api import (
    RATE_LIMIT_URL, api_key, below_budget_threshold, get as openalex_get, rate_limit_numbers,
)


_SELECT = "id,doi,title,type,publication_date,authorships,primary_topic,topics,primary_location,best_oa_location,ids"
_PAGE_SIZE = 100
_RUN_LIMIT = 200


class OpenAlexWorksConnector:
    spec = ConnectorSpec(
        connector_id="openalex-works", version="1", modes=("api",),
        capabilities=frozenset({"pull", "incremental", "exact_id_query", "publication_window"}),
        supports_incremental=True,
    )

    def fetch(self, source: dict[str, Any], checkpoint: ConnectorCheckpoint | None,
              context: ConnectorContext) -> FetchResult:
        acquisition = source.get("acquisition") if isinstance(source.get("acquisition"), Mapping) else {}
        query_config = acquisition.get("query") if isinstance(acquisition.get("query"), Mapping) else {}
        _validate_query(query_config)
        today = _today(context.now())
        continuation = _continuation(checkpoint.cursor if checkpoint else None)
        if continuation:
            start, end, cursor = continuation
        else:
            start, end, cursor = (today - timedelta(days=7)).isoformat(), today.isoformat(), "*"
        filters = _query_filters(query_config, start, end)
        client = context.http or SharedHttpClient()
        environment = context.environment
        budget_metrics: dict[str, int | float] = {}
        budget_mode = "free_api_key" if api_key(environment) else "anonymous"
        if api_key(environment):
            try:
                budget_response = openalex_get(client, RATE_LIMIT_URL, environment=environment)
            except Exception:
                raise ConnectorDeferred("OpenAlex budget status unavailable", retry_after_seconds=300) from None
            if budget_response.status == 429:
                raise ConnectorDeferred("OpenAlex budget status deferred",
                                        retry_after_seconds=client.retry_after_seconds(budget_response.headers) or 3600)
            if budget_response.status in {401, 403}:
                raise ConnectorFailure("OpenAlex authentication rejected", cause_class="OpenAlexAuthenticationError",
                                       error_category="auth_required") from None
            if budget_response.status != 200:
                raise ConnectorDeferred("OpenAlex budget status unavailable", retry_after_seconds=300)
            budget_metrics = rate_limit_numbers(budget_response)
            if "rate_limit_limit" not in budget_metrics or "rate_limit_remaining" not in budget_metrics:
                raise ConnectorDeferred("OpenAlex budget headers unavailable", retry_after_seconds=300)
            if below_budget_threshold(budget_metrics):
                raise ConnectorDeferred("OpenAlex free daily budget below guard threshold",
                                        retry_after_seconds=max(60, int(budget_metrics.get("rate_limit_reset_seconds", 3600))))
        observations = []
        fetched = 0
        requests = 0
        next_cursor = None
        budget_guard_triggered = False
        while requests < 2 and fetched < _RUN_LIMIT:
            params = {"filter": ",".join(filters), "select": _SELECT, "per-page": _PAGE_SIZE,
                      "cursor": cursor}
            url = "https://api.openalex.org/works?" + urlencode(params)
            response: HttpResponse = openalex_get(client, url, environment=environment)
            if response.status == 429:
                raise ConnectorDeferred(retry_after_seconds=client.retry_after_seconds(response.headers))
            if response.status in {401, 403}:
                raise RuntimeError("OpenAlex API rejected the source query")
            if response.status != 200:
                raise RuntimeError(f"OpenAlex API HTTP status {response.status}")
            requests += 1
            try:
                payload = json.loads(response.body.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                raise RuntimeError("OpenAlex returned invalid structured data") from None
            if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                raise RuntimeError("OpenAlex response is malformed")
            latest_budget = rate_limit_numbers(response)
            if latest_budget:
                budget_metrics.update(latest_budget)
            results = payload["results"]
            fetched += len(results)
            for work in results:
                observation = _observation(source, work, context.now())
                if observation:
                    observations.append(observation)
            next_cursor = (payload.get("meta") or {}).get("next_cursor") if isinstance(payload.get("meta"), dict) else None
            if not next_cursor or not results:
                cursor = None
                break
            cursor = str(next_cursor)
            if below_budget_threshold(budget_metrics):
                budget_guard_triggered = True
                break
        truncated = bool(cursor and next_cursor and fetched >= _RUN_LIMIT)
        saved_cursor = _encode_continuation(start, end, cursor) if cursor else None
        next_checkpoint = ConnectorCheckpoint(cursor=saved_cursor, last_window_end=end,
                                              last_success_at=context.now())
        return FetchResult(observations, next_checkpoint, True,
                           {"entries_fetched": fetched, "pages": requests, "from_publication_date": start,
                            "to_publication_date": end, "query_ids": _safe_query_echo(query_config),
                            "truncated_at_bound": truncated, "sync_mode": "publication_window",
                            "budget_mode": budget_mode, "budget_guard_triggered": budget_guard_triggered,
                            **budget_metrics})


def probe_openalex_query(
    query: Any,
    *,
    http: Any = None,
    now: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> SourceProbeResult:
    if not isinstance(query, Mapping):
        return SourceProbeResult("invalid", "exact_id_query_required", "")
    try:
        _validate_query(query)
    except ValueError:
        return SourceProbeResult("invalid", "exact_id_query_invalid", "")
    client = http or SharedHttpClient()
    end = _today(now or datetime.now(timezone.utc).isoformat())
    start = (end - timedelta(days=7)).isoformat()
    params = {"filter": ",".join(_query_filters(query, start, end)), "select": "id", "per-page": 1, "cursor": "*"}
    endpoint = "https://api.openalex.org/works?" + urlencode(params)
    try:
        response = openalex_get(client, endpoint, environment=environment)
    except Exception:
        return SourceProbeResult("temporarily_unavailable", "transport_failure", endpoint)
    if response.status in {401, 403}:
        return SourceProbeResult("auth_required", "http_auth_required", endpoint)
    if response.status == 429 or 500 <= response.status <= 599:
        return SourceProbeResult("temporarily_unavailable", "provider_unavailable", endpoint)
    if response.status != 200:
        return SourceProbeResult("invalid", "http_status_invalid", endpoint)
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return SourceProbeResult("invalid", "structured_data_invalid", endpoint)
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        return SourceProbeResult("invalid", "structured_data_invalid", endpoint)
    return SourceProbeResult("valid", "exact_id_query_valid", endpoint, len(payload["results"]))


def _observation(source: Mapping[str, Any], work: Any, observed_at: str) -> dict[str, Any] | None:
    if not isinstance(work, Mapping):
        return None
    openalex_id = _openalex_id(work.get("id"))
    if not openalex_id:
        return None
    ids = work.get("ids") if isinstance(work.get("ids"), Mapping) else {}
    doi = extract_doi(str(work.get("doi") or ids.get("doi") or ""))
    arxiv = extract_arxiv_id(str(ids.get("arxiv") or ""))
    title = redact_private_text(str(work.get("title") or "")).strip()
    publication_date = str(work.get("publication_date") or "")
    published_at = _date_to_datetime(publication_date)
    primary_location = work.get("primary_location") if isinstance(work.get("primary_location"), Mapping) else {}
    best_oa = work.get("best_oa_location") if isinstance(work.get("best_oa_location"), Mapping) else {}
    landing_url = _safe_location(primary_location.get("landing_page_url")) or _safe_location(best_oa.get("landing_page_url"))
    canonical = (f"https://doi.org/{doi}" if doi else f"https://arxiv.org/abs/{arxiv}" if arxiv
                 else f"https://openalex.org/W{openalex_id}")
    authors = []
    organizations = []
    for authorship in work.get("authorships", []) if isinstance(work.get("authorships"), list) else []:
        if not isinstance(authorship, Mapping):
            continue
        author = authorship.get("author") if isinstance(authorship.get("author"), Mapping) else {}
        if author.get("display_name"):
            authors.append(redact_private_text(str(author["display_name"]))[:240])
        for institution in authorship.get("institutions", []) if isinstance(authorship.get("institutions"), list) else []:
            if isinstance(institution, Mapping) and institution.get("display_name"):
                organizations.append(redact_private_text(str(institution["display_name"]))[:240])
    authors = sorted(set(authors))
    organizations = sorted(set(organizations))
    urls = sorted({value for value in (canonical, landing_url) if value})
    candidate = {
        "artifact_type": "dataset" if work.get("type") == "dataset" else "paper",
        "title": title, "canonical_url": canonical,
        "identifiers": {"doi": doi, "arxiv": arxiv, "openalex": "W" + openalex_id},
        "authors": authors, "organizations": organizations, "summary": "",
        "published_at": published_at, "topics": list(source.get("topics", [])),
        "mention": {"role": "primary", "evidence_level": "api_metadata",
                    "origin": "openalex_work", "confidence": 1.0},
    }
    return new_observation(
        identity=f"openalex|{openalex_id}", source_id=str(source["source_id"]), platform="openalex",
        platform_object_id="openalex:" + openalex_id, kind="indexed_work", title=title,
        text="", urls=urls, media=[], published_at=published_at, observed_at=observed_at,
        topics=[str(value) for value in source.get("topics", [])], authors=authors,
        provenance={"retrieval_mode": "openalex_api", "evidence_level": "api_metadata",
                    "source_url": f"https://openalex.org/W{openalex_id}", "collector": "openalex-works"},
        metadata={"connector": "openalex-works", "openalex_id": "W" + openalex_id,
                  "publication_date": publication_date or None, "work_type": str(work.get("type") or "unknown"),
                  "primary_topic_id": _topic_id(work.get("primary_topic")),
                  "topics": [_topic_id(item) for item in work.get("topics", []) if _topic_id(item)]},
        artifact_candidates=[candidate],
    )


def _validate_query(query: Mapping[str, Any]) -> None:
    fields = {"topic_ids": "T", "author_ids": "A", "institution_ids": "I", "source_ids": "S"}
    if not isinstance(query, Mapping) or set(query) - set(fields):
        raise ValueError("OpenAlex accepts only exact topic, author, institution, or source IDs")
    count = 0
    for key, prefix in fields.items():
        values = query.get(key, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError("OpenAlex exact IDs must be arrays of strings")
        normalized = [value.removeprefix("https://openalex.org/") for value in values]
        if len(set(normalized)) != len(normalized) or len(normalized) > 20:
            raise ValueError("OpenAlex exact IDs must be unique and bounded")
        if any(len(value) < 2 or value[0] != prefix or not value[1:].isalnum() for value in normalized):
            raise ValueError("OpenAlex query contains a mismatched exact ID")
        count += len(values)
    if count == 0:
        raise ValueError("OpenAlex source requires at least one exact identifier")


def _query_filters(query: Mapping[str, Any], start: str, end: str) -> list[str]:
    filters = [f"from_publication_date:{start}", f"to_publication_date:{end}"]
    openalex_fields = {"topic_ids": "topics.id", "author_ids": "authorships.author.id",
                       "institution_ids": "authorships.institutions.id", "source_ids": "primary_location.source.id"}
    for key, field in openalex_fields.items():
        values = [str(value).removeprefix("https://openalex.org/") for value in query.get(key, [])]
        if values:
            filters.append(field + ":" + "|".join(values))
    return filters


def _safe_query_echo(query: Mapping[str, Any]) -> dict[str, list[str]]:
    return {key: sorted(str(value).removeprefix("https://openalex.org/") for value in values)
            for key, values in sorted(query.items())}


def _continuation(value: str | None) -> tuple[str, str, str] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
        start, end, cursor = str(parsed["from"]), str(parsed["to"]), str(parsed["cursor"])
        date.fromisoformat(start); date.fromisoformat(end)
        if not cursor or len(cursor) > 3800 or date.fromisoformat(start) > date.fromisoformat(end):
            raise ValueError
        return start, end, cursor
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise ValueError("OpenAlex checkpoint continuation is malformed") from None


def _encode_continuation(start: str, end: str, cursor: str | None) -> str | None:
    if not cursor:
        return None
    value = json.dumps({"from": start, "to": end, "cursor": cursor}, sort_keys=True, separators=(",", ":"))
    if len(value) > 4000:
        raise ValueError("OpenAlex continuation cursor exceeds the checkpoint limit")
    return value


def _openalex_id(value: Any) -> str:
    text = str(value or "").rstrip("/").rsplit("/", 1)[-1]
    return text[1:] if text.startswith("W") and len(text) > 1 else ""


def _topic_id(value: Any) -> str | None:
    if isinstance(value, Mapping):
        text = str(value.get("id") or "").rstrip("/").rsplit("/", 1)[-1]
        return text if text.startswith("T") else None
    return None


def _safe_location(value: Any) -> str:
    return canonicalize_url(str(value or ""))


def _date_to_datetime(value: str) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat() + "T00:00:00Z"
    except ValueError:
        return None


def _today(value: str) -> date:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date()
