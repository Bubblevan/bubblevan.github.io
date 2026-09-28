from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import quote

from ..connectors.base import ConnectorContext
from ..discovery.budget import ExpansionBudget
from .base import ProviderCache, default_headers, request_json


GITHUB_FIELDS = {
    "id", "full_name", "name", "owner", "html_url", "homepage", "topics",
    "description", "created_at", "updated_at", "pushed_at", "fork", "archived",
}


class GitHubGraphProvider:
    provider_id = "github"
    REPOSITORY_TTL_DAYS = 7

    def __init__(self, cache: ProviderCache):
        self.cache = cache

    def expand_artifact(
        self, artifact: Mapping[str, Any], context: ConnectorContext, budget: ExpansionBudget,
    ) -> dict[str, Any]:
        identifiers = artifact.get("identifiers") if isinstance(artifact.get("identifiers"), Mapping) else {}
        repo = str(identifiers.get("github") or "").strip()
        if not repo:
            url = str(artifact.get("canonical_url") or "")
            repo = _repo_from_url(url)
        if not repo or repo.count("/") != 1:
            return {"provider": self.provider_id, "status": "skipped", "reason": "exact-repository-identity-required"}
        identity = f"repository:{repo.casefold()}"
        cached = self.cache.get(self.provider_id, identity, self.REPOSITORY_TTL_DAYS, now=context.now())
        if cached:
            return {"provider": self.provider_id, "status": "succeeded", "requests": 0,
                    "diagnostics": {"cached": True, "etag": cached.get("etag")}, **cached["selected"]}
        if not budget.request():
            return {"provider": self.provider_id, "status": "budget_exhausted", "requests": 0}
        payload, diagnostics, response = request_json(
            self.provider_id, f"https://api.github.com/repos/{quote(repo, safe='/')}",
            context, headers={**default_headers(context), "X-GitHub-Api-Version": "2022-11-28"},
        )
        owner = payload.get("owner") if isinstance(payload.get("owner"), Mapping) else {}
        selected = {
            "repository": {
                "id": int(payload.get("id", 0)),
                "full_name": str(payload.get("full_name") or repo),
                "name": str(payload.get("name") or repo.rsplit("/", 1)[-1]),
                "html_url": str(payload.get("html_url") or ""),
                "homepage": str(payload.get("homepage") or ""),
                "topics": sorted({str(item) for item in payload.get("topics", []) if item}) if isinstance(payload.get("topics"), list) else [],
                "description": str(payload.get("description") or ""),
                "created_at": str(payload.get("created_at") or ""),
                "updated_at": str(payload.get("updated_at") or ""),
                "pushed_at": str(payload.get("pushed_at") or ""),
                "fork": bool(payload.get("fork")),
                "archived": bool(payload.get("archived")),
            },
            "owner": {
                "id": int(owner.get("id", 0)),
                "login": str(owner.get("login") or ""),
                "type": str(owner.get("type") or ""),
                "html_url": str(owner.get("html_url") or ""),
            },
        }
        self.cache.put(self.provider_id, identity, selected, fetched_at=context.now(), etag=_header(response.headers, "etag"))
        return {"provider": self.provider_id, "status": "succeeded", "requests": 1,
                "diagnostics": diagnostics, **selected}

    def expand_entity(
        self, entity: Mapping[str, Any], context: ConnectorContext, budget: ExpansionBudget,
    ) -> dict[str, Any]:
        return {"provider": self.provider_id, "status": "skipped", "reason": "owner-fanout-disabled"}


def _repo_from_url(url: str) -> str:
    from urllib.parse import urlsplit
    parsed = urlsplit(url)
    if parsed.hostname not in {"github.com", "www.github.com"}:
        return ""
    pieces = [part for part in parsed.path.strip("/").split("/") if part]
    return "/".join(pieces[:2]) if len(pieces) >= 2 else ""


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return next((str(value) for key, value in headers.items() if key.casefold() == name.casefold()), None)
