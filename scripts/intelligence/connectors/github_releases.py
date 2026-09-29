from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlsplit

from ..canonicalize import canonicalize_url, candidate_from_url, extract_artifact_candidates, extract_github_repo
from ..models import new_artifact, new_observation
from .base import ConnectorCheckpoint, ConnectorContext, ConnectorDeferred, ConnectorSpec, FetchResult
from .http import HttpResponse, SharedHttpClient
from .privacy import redact_private_text


class GitHubReleasesConnector:
    spec = ConnectorSpec(
        connector_id="github-releases", version="1", modes=("api",),
        capabilities=frozenset({"pull", "incremental", "etag", "last_modified", "auth_optional"}),
        requires_auth=False, supports_incremental=True,
    )

    def fetch(
        self,
        source: dict[str, Any],
        checkpoint: ConnectorCheckpoint | None,
        context: ConnectorContext,
    ) -> FetchResult:
        repo = str((source.get("external_ids") or {}).get("github_repo") or "")
        repo = repo.casefold() or (extract_github_repo(str(source.get("canonical_url") or "")) or "")
        if not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+", repo):
            raise ValueError("GitHub release source must identify owner/repo")
        previous = checkpoint or ConnectorCheckpoint()
        env = {**dict(context.environment)}
        token = env.get("GITHUB_TOKEN")
        if token is None:
            import os
            token = os.environ.get("GITHUB_TOKEN")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if previous.etag:
            headers["If-None-Match"] = previous.etag
        if previous.last_modified:
            headers["If-Modified-Since"] = previous.last_modified
        client = context.http or SharedHttpClient()
        repository_candidate = candidate_from_url(f"https://github.com/{repo}")
        repository_artifact = new_artifact(
            identity=f"github:{repo}", artifact_type="repository", title=str(source.get("name") or repo),
            canonical_url=f"https://github.com/{repo}", identifiers=dict(repository_candidate["identifiers"]),
            topics=[str(item) for item in source.get("topics", [])], status="candidate",
            field_provenance={"title": {"source": "github-source", "observation_id": None}},
        )
        url = f"https://api.github.com/repos/{repo}/releases?per_page=100"
        observations: list[dict[str, Any]] = []
        diagnostics: dict[str, Any] = {}
        first_response: HttpResponse | None = None
        pages = 0
        while url:
            pages += 1
            if pages > 20:
                raise RuntimeError("GitHub releases pagination exceeded 20 pages")
            response = client.get(url, headers=headers if pages == 1 else {
                "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            })
            if pages == 1:
                first_response = response
            diagnostics = client.diagnostics(response)
            if response.status == 304:
                first_headers = _headers(response.headers)
                return FetchResult([], ConnectorCheckpoint(
                    cursor=None,
                    etag=first_headers.get("etag", previous.etag),
                    last_modified=first_headers.get("last-modified", previous.last_modified),
                    high_watermark=previous.high_watermark,
                    last_success_at=context.now(),
                ), True, {**diagnostics, "pages": pages, "releases": 0}, artifacts=[repository_artifact])
            rate = _headers(response.headers)
            if response.status == 429:
                raise ConnectorDeferred(retry_after_seconds=client.retry_after_seconds(response.headers))
            if response.status == 403 and rate.get("x-ratelimit-remaining") == "0":
                reset = rate.get("x-ratelimit-reset")
                if reset:
                    try:
                        retry_at = datetime.fromtimestamp(float(reset), timezone.utc).isoformat().replace("+00:00", "Z")
                    except (ValueError, OverflowError, OSError):
                        retry_at = None
                    if retry_at:
                        raise ConnectorDeferred(retry_at=retry_at)
            if response.status != 200:
                raise RuntimeError(f"GitHub API status {response.status}")
            try:
                releases = json.loads(response.body.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise RuntimeError("GitHub releases returned invalid JSON") from exc
            if not isinstance(releases, list):
                raise RuntimeError("GitHub releases response must be an array")
            for release in releases:
                if not isinstance(release, Mapping) or not release.get("published_at"):
                    continue
                release_id = str(release.get("id") or "").strip()
                if not release_id:
                    continue
                tag = redact_private_text(str(release.get("tag_name") or "").strip())
                title = redact_private_text(str(release.get("name") or tag or f"Release {release_id}").strip())
                html_url = canonicalize_url(str(release.get("html_url") or f"https://github.com/{repo}/releases/tag/{tag}"))
                body = redact_private_text(str(release.get("body") or "").strip())
                author_obj = release.get("author") if isinstance(release.get("author"), Mapping) else {}
                author = redact_private_text(str(author_obj.get("login") or "").strip())
                repository_url = f"https://github.com/{repo}"
                candidates = extract_artifact_candidates(body, [repository_url])
                for candidate in candidates:
                    if candidate.get("identifiers", {}).get("github") == repo:
                        candidate["mention"] = {"evidence_level": "api_metadata", "origin": "repository", "confidence": 1.0}
                observations.append(new_observation(
                    identity=f"github-release|{repo}|{release_id}",
                    source_id=str(source["source_id"]), platform="github", platform_object_id=release_id,
                    kind="release", title=title, text=body, urls=sorted(set(filter(None, [html_url, repository_url])),),
                    media=[], published_at=str(release.get("published_at") or ""), observed_at=context.now(),
                    topics=[], native_tags=[], authors=[author] if author else [],
                    metadata={"tag_name": tag, "prerelease": bool(release.get("prerelease"))},
                    provenance={"retrieval_mode": "api", "evidence_level": "api_metadata",
                                "source_url": html_url, "collector": "scripts.intelligence.connectors.github_releases"},
                    artifact_candidates=candidates,
                ))
            url = _next_link(response.headers.get("Link") or response.headers.get("link"), repo)
        assert first_response is not None
        response_headers = _headers(first_response.headers)
        published = [str(item["published_at"]) for item in observations if item.get("published_at")]
        high_watermark = max([previous.high_watermark or "", *published]) or None
        return FetchResult(
            observations,
            ConnectorCheckpoint(
                cursor=None,
                etag=response_headers.get("etag", previous.etag),
                last_modified=response_headers.get("last-modified", previous.last_modified),
                high_watermark=high_watermark,
                last_success_at=context.now(),
            ),
            True,
            {**diagnostics, "pages": pages, "releases": len(observations)},
            artifacts=[repository_artifact],
        )


def _headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).casefold(): str(value) for key, value in headers.items()}


def _next_link(value: str | None, repo: str) -> str:
    value = value or ""
    for link in value.split(","):
        match = re.match(r"\s*<([^>]+)>\s*;\s*rel=\"next\"", link)
        if not match:
            continue
        candidate = match.group(1)
        parts = urlsplit(candidate)
        expected_path = f"/repos/{repo}/releases"
        same_repo_path = parts.path == expected_path
        github_numeric_repo_path = bool(re.fullmatch(r"/repositories/[0-9]+/releases", parts.path))
        query = parse_qsl(parts.query, keep_blank_values=True)
        query_is_pagination = (
            bool(query)
            and all(key in {"page", "per_page"} and value.isdigit() for key, value in query)
            and ("page" in dict(query) or "per_page" in dict(query))
        )
        if (parts.scheme != "https" or parts.hostname != "api.github.com"
                or parts.port not in (None, 443) or parts.username or parts.password or parts.fragment
                or not (same_repo_path or github_numeric_repo_path) or not query_is_pagination):
            raise ValueError("GitHub pagination returned an unexpected URL")
        return candidate
    return ""
