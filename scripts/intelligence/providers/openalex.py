from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import quote

from ..connectors.base import ConnectorContext
from ..discovery.budget import ExpansionBudget
from .base import GraphProviderFailure, ProviderCache, default_headers, request_json


WORK_FIELDS = "id,doi,title,publication_date,primary_topic,topics,authorships,primary_location,referenced_works"


class OpenAlexGraphProvider:
    provider_id = "openalex"
    WORK_TTL_DAYS = 7
    AUTHOR_TTL_DAYS = 7
    INSTITUTION_TTL_DAYS = 30

    def __init__(self, cache: ProviderCache):
        self.cache = cache

    def expand_artifact(
        self, artifact: Mapping[str, Any], context: ConnectorContext, budget: ExpansionBudget,
    ) -> dict[str, Any]:
        identifiers = artifact.get("identifiers") if isinstance(artifact.get("identifiers"), Mapping) else {}
        openalex_id = str(identifiers.get("openalex") or "").strip()
        doi = str(identifiers.get("doi") or "").strip()
        if openalex_id:
            work_key = _openalex_id(openalex_id)
            identity = f"work:{work_key}"
        elif doi:
            work_key = ""
            identity = f"doi:{doi.casefold()}"
        else:
            return {"provider": self.provider_id, "status": "skipped", "reason": "exact-doi-or-openalex-id-required"}
        cached = self.cache.get(self.provider_id, identity, self.WORK_TTL_DAYS, now=context.now())
        if cached:
            selected = cached["selected"]
            diagnostics = {"cached": True, "etag": cached.get("etag")}
            requests = 0
        else:
            if not budget.request():
                return {"provider": self.provider_id, "status": "budget_exhausted", "requests": 0}
            path = work_key or "https://doi.org/" + quote(doi, safe="/.")
            from urllib.parse import urlencode
            url = "https://api.openalex.org/works/" + quote(path, safe=":/") + "?" + urlencode({"select": WORK_FIELDS})
            payload, diagnostics, response = request_json(self.provider_id, url, context, headers={"Accept": "application/json"})
            selected = _select_work(payload)
            if not selected.get("id"):
                raise GraphProviderFailure(self.provider_id, status=200, cause_class="MissingWorkId")
            self.cache.put(self.provider_id, identity, selected, fetched_at=context.now(), etag=_header(response.headers, "etag"))
            requests = 1
        authors = []
        for authorship in selected.get("authorships", []):
            if not isinstance(authorship, Mapping):
                continue
            author_raw = authorship.get("author") if isinstance(authorship.get("author"), Mapping) else {}
            author_id = _last_id(str(author_raw.get("id") or ""))
            if not author_id:
                continue
            institutions = []
            for item in authorship.get("institutions", []):
                if not isinstance(item, Mapping):
                    continue
                institution_id = _last_id(str(item.get("id") or ""))
                if not institution_id:
                    continue
                institutions.append({
                    "id": institution_id,
                    "name": str(item.get("display_name") or "Unknown institution"),
                    "ror": str(item.get("ror") or "") or None,
                })
            authors.append({
                "id": author_id,
                "name": str(author_raw.get("display_name") or "Unknown author"),
                "orcid": str(author_raw.get("orcid") or "") or None,
                "institutions": sorted(institutions, key=lambda item: item["id"]),
            })
        location = selected.get("primary_location") if isinstance(selected.get("primary_location"), Mapping) else {}
        source_raw = location.get("source") if isinstance(location.get("source"), Mapping) else {}
        venue = None
        if source_raw.get("id"):
            venue = {
                "id": _last_id(str(source_raw["id"])),
                "name": str(source_raw.get("display_name") or ""),
                "issn_l": str(source_raw.get("issn_l") or "") or None,
            }
        topics = selected.get("topics") if isinstance(selected.get("topics"), list) else []
        return {
            "provider": self.provider_id,
            "status": "succeeded",
            "requests": requests,
            "diagnostics": diagnostics,
            "work": {
                "id": _last_id(str(selected.get("id") or "")),
                "doi": str(selected.get("doi") or "") or None,
                "title": str(selected.get("title") or ""),
                "publication_date": str(selected.get("publication_date") or "") or None,
                "primary_topic": _topic(selected.get("primary_topic")),
                "topics": sorted({str(item["display_name"]) for item in topics if isinstance(item, Mapping) and item.get("display_name")}),
                "authors": sorted(authors, key=lambda item: item["id"]),
                "venue": venue,
                "referenced_works": sorted({
                    _last_id(str(item)) for item in selected.get("referenced_works", [])
                    if _last_id(str(item))
                }),
            },
        }

    def expand_entity(
        self, entity: Mapping[str, Any], context: ConnectorContext, budget: ExpansionBudget,
    ) -> dict[str, Any]:
        # OpenAlex Work metadata already carries the bounded authorship and affiliation facts used in M2.
        return {"provider": self.provider_id, "status": "skipped", "reason": "entity-expansion-not-required"}


def _select_work(value: Mapping[str, Any]) -> dict[str, Any]:
    authorships = []
    for row in value.get("authorships", []) if isinstance(value.get("authorships"), list) else []:
        if not isinstance(row, Mapping):
            continue
        author = row.get("author") if isinstance(row.get("author"), Mapping) else {}
        institutions = []
        for institution in row.get("institutions", []) if isinstance(row.get("institutions"), list) else []:
            if isinstance(institution, Mapping):
                institutions.append({
                    "id": institution.get("id"),
                    "display_name": institution.get("display_name"),
                    "ror": institution.get("ror"),
                })
        authorships.append({"author": {
            "id": author.get("id"), "display_name": author.get("display_name"), "orcid": author.get("orcid"),
        }, "institutions": institutions})
    primary_location = value.get("primary_location") if isinstance(value.get("primary_location"), Mapping) else {}
    source = primary_location.get("source") if isinstance(primary_location.get("source"), Mapping) else {}
    return {
        "id": value.get("id"), "doi": value.get("doi"), "title": value.get("title"),
        "publication_date": value.get("publication_date"), "primary_topic": _select_topic(value.get("primary_topic")),
        "topics": [_select_topic(item) for item in value.get("topics", []) if isinstance(item, Mapping)],
        "authorships": authorships,
        "primary_location": {"source": {
            "id": source.get("id"), "display_name": source.get("display_name"), "issn_l": source.get("issn_l"),
        }},
        "referenced_works": list(value.get("referenced_works", []))[:20],
    }


def _select_topic(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    return {"id": value.get("id"), "display_name": value.get("display_name")}


def _topic(value: Any) -> str | None:
    return str(value.get("display_name") or "") or None if isinstance(value, Mapping) else None


def _last_id(value: str) -> str:
    return value.rstrip("/").rsplit("/", 1)[-1]


def _openalex_id(value: str) -> str:
    value = _last_id(value)
    if not value.startswith("W"):
        raise ValueError("invalid OpenAlex Work ID")
    return value


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return next((str(value) for key, value in headers.items() if key.casefold() == name.casefold()), None)
