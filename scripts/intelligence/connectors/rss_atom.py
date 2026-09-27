from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html.parser import HTMLParser
from typing import Any, Mapping

from ..canonicalize import canonicalize_url, extract_artifact_candidates
from ..models import new_observation, parse_datetime
from ..topics import map_topics
from .base import ConnectorCheckpoint, ConnectorContext, ConnectorDeferred, ConnectorSpec, FetchResult
from .http import HttpResponse, SharedHttpClient


class _TextOnlyHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in {"script", "style", "noscript"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth and data.strip():
            self.parts.append(data.strip())


def strip_html(value: object) -> str:
    parser = _TextOnlyHTML()
    parser.feed(str(value or ""))
    parser.close()
    import re
    text = " ".join(parser.parts).strip()
    return re.sub(r"\s+([,.;:!?])", r"\1", text)


def _redact_private_text(value: str) -> str:
    """Remove private URL query parameters and common credential assignments from feed text."""
    import re

    url_pattern = re.compile(r"https?://[^\s<>\u0000-\u0020\"']+", re.IGNORECASE)
    assignment_pattern = re.compile(
        r"(?i)\b(xsec_token|session(?:_token)?|access_token|refresh_token|token)\s*([:=])\s*[^\s,;&]+"
    )
    header_pattern = re.compile(r"(?i)\b(authorization|cookie)\s*([:=])\s*[^\r\n]+")

    def safe_url(match: re.Match[str]) -> str:
        raw = match.group(0)
        trailing = ""
        while raw and raw[-1] in ".,;:!?)]}":
            trailing = raw[-1] + trailing
            raw = raw[:-1]
        return canonicalize_url(raw) + trailing

    value = url_pattern.sub(safe_url, value)
    value = assignment_pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", value)
    return header_pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", value)


class RssAtomConnector:
    spec = ConnectorSpec(
        connector_id="rss-atom", version="1", modes=("rss",),
        capabilities=frozenset({"pull", "incremental", "etag", "last_modified"}),
        supports_incremental=True,
    )

    def fetch(
        self,
        source: dict[str, Any],
        checkpoint: ConnectorCheckpoint | None,
        context: ConnectorContext,
    ) -> FetchResult:
        try:
            import feedparser
        except ImportError as exc:
            raise RuntimeError("RSS connector requires feedparser; install requirements-intelligence.txt") from exc
        url = canonicalize_url(str(source.get("canonical_url") or ""))
        if not url:
            raise ValueError("RSS source requires a canonical feed URL")
        previous = checkpoint or ConnectorCheckpoint()
        request_headers: dict[str, str] = {}
        if previous.etag:
            request_headers["If-None-Match"] = previous.etag
        if previous.last_modified:
            request_headers["If-Modified-Since"] = previous.last_modified
        client = context.http or SharedHttpClient()
        response: HttpResponse = client.get(url, headers=request_headers)
        headers = _headers(response.headers)
        if response.status == 429:
            delay = client.retry_after_seconds(response.headers)
            raise ConnectorDeferred(retry_after_seconds=delay)
        next_checkpoint = ConnectorCheckpoint(
            cursor=None,
            etag=headers.get("etag", previous.etag),
            last_modified=headers.get("last-modified", previous.last_modified),
            high_watermark=previous.high_watermark,
            last_success_at=context.now(),
        )
        if response.status == 304:
            return FetchResult([], next_checkpoint, True, {"status": 304, "entries": 0})
        if response.status != 200:
            raise RuntimeError(f"RSS HTTP status {response.status}")

        parsed = feedparser.parse(response.body)
        observations = []
        high_watermark = previous.high_watermark
        for entry in parsed.entries:
            title = _redact_private_text(strip_html(entry.get("title", "")))
            summary = _redact_private_text(strip_html(entry.get("summary", "") or entry.get("description", "")))
            content_parts = entry.get("content", [])
            content = " ".join(_redact_private_text(strip_html(part.get("value", "")))
                                for part in content_parts if isinstance(part, Mapping))
            body = summary or content
            published_at = _entry_date(entry)
            if published_at and (not high_watermark or published_at > high_watermark):
                high_watermark = published_at
            links = _entry_links(entry)
            entry_url = canonicalize_url(str(entry.get("link") or ""))
            if entry_url and entry_url not in links:
                links.insert(0, entry_url)
            identity_value = _entry_identity(entry, source, entry_url, published_at, "\n".join((title, body)))
            platform_object_id = "rss:" + sha256(identity_value.encode("utf-8")).hexdigest()[:32]
            topics_native = [
                _redact_private_text(strip_html(tag.get("term", "")))
                for tag in entry.get("tags", [])
                if isinstance(tag, Mapping) and strip_html(tag.get("term", ""))
            ]
            text = "\n\n".join(part for part in (summary, content if content != summary else "") if part)
            candidates = extract_artifact_candidates(text, links)
            authors = [_redact_private_text(author) for author in _entry_authors(entry)]
            observations.append(new_observation(
                identity=f"rss-atom|{source['source_id']}|{identity_value}",
                source_id=str(source["source_id"]), platform="rss", platform_object_id=platform_object_id,
                kind="post", title=title, text=text, urls=links, media=[], published_at=published_at,
                observed_at=context.now(), topics=map_topics(topics_native), native_tags=topics_native,
                authors=authors,
                provenance={"retrieval_mode": "rss", "evidence_level": "rendered_page",
                            "source_url": url, "collector": "scripts.intelligence.connectors.rss_atom"},
                artifact_candidates=candidates,
            ))
        next_checkpoint.high_watermark = high_watermark
        return FetchResult(
            observations, next_checkpoint, True,
            {"status": response.status, "entries": len(observations), **client.diagnostics(response)},
        )


def _headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).casefold(): str(value) for key, value in headers.items()}


def _entry_identity(entry: Mapping[str, Any], source: Mapping[str, Any], link: str, published: str | None, text: str) -> str:
    guid = str(entry.get("id") or "").strip()
    if guid:
        return "guid:" + guid
    if link:
        return "url:" + link
    digest = sha256(text.encode("utf-8")).hexdigest()
    return "fallback:" + "|".join((str(source["source_id"]), published or "", digest))


def _entry_links(entry: Mapping[str, Any]) -> list[str]:
    values = []
    for item in entry.get("links", []):
        if isinstance(item, Mapping) and item.get("href"):
            value = canonicalize_url(str(item["href"]))
            if value:
                values.append(value)
    return sorted(set(values))


def _entry_date(entry: Mapping[str, Any]) -> str | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
            except (TypeError, ValueError):
                continue
    for key in ("published", "updated", "created"):
        raw = str(entry.get(key) or "")
        if raw:
            try:
                return parse_datetime(parsedate_to_datetime(raw).isoformat())
            except (TypeError, ValueError, OverflowError):
                continue
    return None


def _entry_authors(entry: Mapping[str, Any]) -> list[str]:
    values = []
    for author in entry.get("authors", []):
        if isinstance(author, Mapping):
            name = strip_html(author.get("name", ""))
            if name:
                values.append(name)
    fallback = strip_html(entry.get("author", ""))
    if fallback:
        values.append(fallback)
    return sorted(set(values))
