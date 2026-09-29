from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from typing import Any, Mapping
from urllib.parse import urlencode

from ..canonicalize import canonicalize_url, extract_arxiv_id
from ..models import new_observation, parse_datetime
from .base import ConnectorCheckpoint, ConnectorContext, ConnectorDeferred, ConnectorSpec, FetchResult
from .http import HttpResponse, SharedHttpClient
from .privacy import redact_private_text
from ..discovery.source_proposals import SourceProbeResult


class HuggingFaceDailyPapersConnector:
    spec = ConnectorSpec(
        connector_id="huggingface-daily-papers", version="1", modes=("api",),
        capabilities=frozenset({"pull", "daily_overlap", "structured_api", "auth_optional"}),
        requires_auth=False, supports_incremental=True,
    )

    def fetch(self, source: dict[str, Any], checkpoint: ConnectorCheckpoint | None,
              context: ConnectorContext) -> FetchResult:
        client = context.http or SharedHttpClient()
        today = _today(context.now())
        dates = [today, today - timedelta(days=1)]
        observations = []
        total_items = 0
        request_count = 0
        for day in dates:
            url = "https://huggingface.co/api/daily_papers?" + urlencode({"date": day.isoformat(), "limit": 100})
            response = client.get(url)
            if response.status == 429:
                raise ConnectorDeferred(retry_after_seconds=client.retry_after_seconds(response.headers))
            token = _hf_token(context) if response.status == 401 else None
            if token:
                response = client.get(url, headers={"Authorization": "Bearer " + token})
            if response.status in {401, 403}:
                raise RuntimeError("Hugging Face Daily Papers requires authentication")
            if response.status != 200:
                raise RuntimeError(f"Hugging Face Daily Papers HTTP status {response.status}")
            request_count += 1
            try:
                payload = json.loads(response.body.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                raise RuntimeError("Hugging Face Daily Papers returned invalid structured data") from None
            items = payload.get("results", []) if isinstance(payload, dict) else payload
            if not isinstance(items, list):
                raise RuntimeError("Hugging Face Daily Papers payload is malformed")
            total_items += len(items)
            for item in items[:100]:
                observation = _observation(source, item, day, context.now())
                if observation:
                    observations.append(observation)
        checkpoint = ConnectorCheckpoint(last_successful_date=today.isoformat(), last_success_at=context.now())
        return FetchResult(observations, checkpoint, True,
                           {"entries_fetched": total_items, "pages": request_count,
                            "dates": [item.isoformat() for item in dates], "curator": "huggingface"})


def probe_huggingface_daily(*, http: Any = None, now: str | None = None) -> SourceProbeResult:
    client = http or SharedHttpClient()
    day = _today(now or datetime.now(timezone.utc).isoformat()).isoformat()
    endpoint = "https://huggingface.co/api/daily_papers?" + urlencode({"date": day, "limit": 1})
    try:
        response = client.get(endpoint)
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
    if not isinstance(payload, (list, dict)):
        return SourceProbeResult("invalid", "structured_data_invalid", endpoint)
    return SourceProbeResult("valid", "anonymous_structured_endpoint_valid", endpoint,
                             len(payload.get("results", [])) if isinstance(payload, dict)
                             and isinstance(payload.get("results"), list) else len(payload) if isinstance(payload, list) else 0)


def _observation(source: Mapping[str, Any], item: Any, daily_date: date, observed_at: str) -> dict[str, Any] | None:
    if not isinstance(item, Mapping):
        return None
    paper = item.get("paper") if isinstance(item.get("paper"), Mapping) else item
    paper_id = str(paper.get("id") or paper.get("paperId") or item.get("id") or "").strip()
    if not paper_id:
        return None
    title = redact_private_text(str(paper.get("title") or item.get("title") or "")).strip()
    abstract = redact_private_text(str(paper.get("summary") or paper.get("abstract") or item.get("summary") or ""))
    authors_raw = paper.get("authors", item.get("authors", []))
    if isinstance(authors_raw, list):
        authors = sorted({redact_private_text(str(author.get("name") if isinstance(author, Mapping) else author)).strip()
                          for author in authors_raw if str(author).strip()})
    else:
        authors = []
    arxiv = extract_arxiv_id(paper_id) or extract_arxiv_id(str(paper.get("url") or ""))
    paper_url = f"https://huggingface.co/papers/{paper_id}"
    arxiv_url = f"https://arxiv.org/abs/{arxiv}" if arxiv else ""
    project_url = _safe_url(paper.get("projectUrl") or item.get("projectUrl"))
    github_url = _safe_url(paper.get("githubUrl") or paper.get("github") or item.get("githubUrl"))
    published_at = _date_value(paper.get("publishedAt") or paper.get("published_at") or paper.get("submittedAt"))
    upvotes = item.get("upvotes", paper.get("upvotes"))
    if isinstance(upvotes, bool) or not isinstance(upvotes, int):
        upvotes = None
    submitter = item.get("submittedBy") or paper.get("submittedBy")
    if isinstance(submitter, Mapping):
        submitter = submitter.get("name") or submitter.get("username")
    submitter = redact_private_text(str(submitter or "")).strip() or None
    primary = {
        "artifact_type": "paper", "title": title,
        "canonical_url": arxiv_url or paper_url,
        "identifiers": {"doi": None, "arxiv": arxiv, "hf_paper": paper_id},
        "authors": authors, "organizations": [], "summary": abstract[:4000], "published_at": published_at,
        "topics": list(source.get("topics", [])),
        "mention": {"role": "primary", "evidence_level": "api_metadata",
                    "origin": "huggingface_daily_papers", "confidence": 1.0},
    }
    urls = sorted({value for value in (paper_url, arxiv_url, project_url, github_url) if value})
    return new_observation(
        identity=f"huggingface-daily|{daily_date.isoformat()}|{paper_id}",
        source_id=str(source["source_id"]), platform="huggingface", platform_object_id=f"daily:{daily_date}:{paper_id}",
        kind="recommendation", title=title, text=abstract, urls=urls, media=[], published_at=published_at,
        observed_at=observed_at, topics=[str(value) for value in source.get("topics", [])], authors=authors,
        provenance={"retrieval_mode": "huggingface_daily_api", "evidence_level": "api_metadata",
                    "source_url": "https://huggingface.co/api/daily_papers", "collector": "huggingface-daily-papers"},
        metadata={"connector": "huggingface-daily-papers", "daily_date": daily_date.isoformat(),
                  "hf_paper_id": paper_id, "upvotes": upvotes, "submitter": submitter,
                  "project_url": project_url or None, "github_url": github_url or None},
        artifact_candidates=[primary],
    )


def _today(value: str) -> date:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date()


def _date_value(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        text = str(value)
        if len(text) == 10:
            return text + "T00:00:00Z"
        return parse_datetime(text)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _safe_url(value: Any) -> str:
    return canonicalize_url(str(value or ""))


def _hf_token(context: ConnectorContext) -> str | None:
    import os
    value = context.environment.get("HF_TOKEN") or os.environ.get("HF_TOKEN")
    return str(value) if value else None
