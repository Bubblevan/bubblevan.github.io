from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import quote

from ..connectors.base import ConnectorContext
from ..discovery.budget import ExpansionBudget
from .base import GraphProviderFailure, ProviderCache, default_headers, query_url, request_json


PAPER_FIELDS = "paperId,externalIds,title,url,year,publicationDate,authors"
GRAPH_FIELDS = "paperId,externalIds,title,year,publicationDate,authors"
AUTHOR_PAPER_FIELDS = "paperId,externalIds,title,url,year,publicationDate,authors"


class SemanticScholarGraphProvider:
    provider_id = "semantic-scholar"
    PAPER_TTL_DAYS = 7
    AUTHOR_TTL_DAYS = 7

    def __init__(self, cache: ProviderCache):
        self.cache = cache

    def expand_artifact(
        self, artifact: Mapping[str, Any], context: ConnectorContext, budget: ExpansionBudget,
    ) -> dict[str, Any]:
        identifiers = artifact.get("identifiers") if isinstance(artifact.get("identifiers"), Mapping) else {}
        paper_id = str(identifiers.get("semantic_scholar") or "").strip()
        if not paper_id:
            return {"provider": self.provider_id, "status": "skipped", "reason": "resolved-semantic-scholar-paper-id-required"}
        selected, diagnostics, requests = self._paper(paper_id, context, budget)
        if selected is None:
            return {"provider": self.provider_id, "status": "budget_exhausted", "requests": requests}
        references: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        remaining_ref = budget.max_references_per_artifact
        remaining_cites = budget.max_citations_per_artifact
        provider_errors = []
        request_budget_exhausted = False
        for route, count, destination in (
            ("references", remaining_ref, references),
            ("citations", remaining_cites, citations),
        ):
            if count <= 0:
                continue
            if not budget.request():
                request_budget_exhausted = True
                continue
            url = query_url(
                f"https://api.semanticscholar.org/graph/v1/paper/{quote(paper_id, safe='')}/{route}",
                {"fields": GRAPH_FIELDS, "limit": count},
            )
            requests += 1
            try:
                payload, route_diag, _ = request_json(self.provider_id, url, context, headers=_headers(context))
                diagnostics[f"{route}_status"] = route_diag.get("status")
                data = payload.get("data") if isinstance(payload.get("data"), list) else []
                for row in data[:count]:
                    nested_key = "citedPaper" if route == "references" else "citingPaper"
                    paper = row.get(nested_key) if isinstance(row, Mapping) and isinstance(row.get(nested_key), Mapping) else row
                    selected_paper = _select_paper(paper)
                    if selected_paper.get("paperId"):
                        destination.append(selected_paper)
            except GraphProviderFailure as exc:
                provider_errors.append({
                    "provider": exc.provider_id,
                    "operation": route,
                    "error_class": exc.cause_class,
                    "http_status": exc.status,
                    "retry_at": exc.retry_at,
                    "retry_after_seconds": exc.retry_after_seconds,
                })
        authors = []
        for author in selected.get("authors", []):
            if not isinstance(author, Mapping) or not author.get("authorId"):
                continue
            authors.append({"id": str(author["authorId"]), "name": str(author.get("name") or "Unknown author")})
        return {
            "provider": self.provider_id,
            "status": "partial" if provider_errors or request_budget_exhausted else "succeeded",
            "requests": requests,
            "diagnostics": diagnostics,
            "provider_errors": provider_errors,
            "budget_exhausted": request_budget_exhausted,
            "paper": {**selected, "authors": sorted(authors, key=lambda item: item["id"])},
            "references": sorted(references, key=lambda item: item["paperId"])[:remaining_ref],
            "citations": sorted(citations, key=lambda item: item["paperId"])[:remaining_cites],
        }

    def expand_entity(
        self, entity: Mapping[str, Any], context: ConnectorContext, budget: ExpansionBudget,
    ) -> dict[str, Any]:
        external = entity.get("external_ids") if isinstance(entity.get("external_ids"), Mapping) else {}
        author_id = str(external.get("semantic_scholar_author") or "").strip()
        if not author_id:
            return {"provider": self.provider_id, "status": "skipped", "reason": "semantic-scholar-author-id-required"}
        identity = f"author:{author_id}"
        cached = self.cache.get(self.provider_id, identity, self.AUTHOR_TTL_DAYS, now=context.now())
        if cached:
            return {"provider": self.provider_id, "status": "succeeded", "requests": 0,
                    "diagnostics": {"cached": True, "etag": cached.get("etag")},
                    "recent_works": cached["selected"].get("recent_works", [])[:budget.max_recent_works_per_author]}
        count = budget.max_recent_works_per_author
        if count <= 0 or not budget.request():
            return {"provider": self.provider_id, "status": "budget_exhausted", "requests": 0, "recent_works": []}
        url = query_url(
            f"https://api.semanticscholar.org/graph/v1/author/{quote(author_id, safe='')}/papers",
            {"fields": AUTHOR_PAPER_FIELDS, "limit": count, "offset": 0},
        )
        payload, diagnostics, response = request_json(self.provider_id, url, context, headers=_headers(context))
        rows = payload.get("data") if isinstance(payload.get("data"), list) else []
        selected = {
            "recent_works": [
                _select_paper(item) for item in rows[:count] if isinstance(item, Mapping) and item.get("paperId")
            ],
        }
        self.cache.put(self.provider_id, identity, selected, fetched_at=context.now(), etag=_header(response.headers, "etag"))
        return {"provider": self.provider_id, "status": "succeeded", "requests": 1,
                "diagnostics": diagnostics, **selected}

    def _paper(self, paper_id: str, context: ConnectorContext, budget: ExpansionBudget):
        identity = f"paper:{paper_id}"
        cached = self.cache.get(self.provider_id, identity, self.PAPER_TTL_DAYS, now=context.now())
        if cached:
            return cached["selected"], {"cached": True, "etag": cached.get("etag")}, 0
        if not budget.request():
            return None, {}, 0
        url = query_url(
            f"https://api.semanticscholar.org/graph/v1/paper/{quote(paper_id, safe='')}",
            {"fields": PAPER_FIELDS},
        )
        payload, diagnostics, response = request_json(self.provider_id, url, context, headers=_headers(context))
        selected = _select_paper(payload)
        if not selected.get("paperId"):
            raise GraphProviderFailure(self.provider_id, status=200, cause_class="MissingPaperId")
        self.cache.put(self.provider_id, identity, selected, fetched_at=context.now(), etag=_header(response.headers, "etag"))
        return selected, diagnostics, 1


def _select_paper(value: Mapping[str, Any]) -> dict[str, Any]:
    external = value.get("externalIds") if isinstance(value.get("externalIds"), Mapping) else {}
    authors = []
    for item in value.get("authors", []) if isinstance(value.get("authors"), list) else []:
        if isinstance(item, Mapping):
            authors.append({"authorId": item.get("authorId"), "name": item.get("name")})
    return {
        "paperId": str(value.get("paperId") or ""),
        "externalIds": {
            key: external.get(key) for key in ("DOI", "ArXiv", "OpenAlexID") if external.get(key)
        },
        "title": str(value.get("title") or ""),
        "url": str(value.get("url") or ""),
        "year": value.get("year"),
        "publicationDate": str(value.get("publicationDate") or ""),
        "authors": authors,
    }


def _headers(context: ConnectorContext) -> dict[str, str]:
    result = _credentials(context)
    return result


def _credentials(context: ConnectorContext) -> dict[str, str]:
    import os
    environment = dict(context.environment)
    if "SEMANTIC_SCHOLAR_API_KEY" not in environment:
        environment["SEMANTIC_SCHOLAR_API_KEY"] = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    headers = {"Accept": "application/json"}
    if environment.get("SEMANTIC_SCHOLAR_API_KEY"):
        headers["x-api-key"] = environment["SEMANTIC_SCHOLAR_API_KEY"]
    return headers


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return next((str(value) for key, value in headers.items() if key.casefold() == name.casefold()), None)
