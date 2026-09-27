from __future__ import annotations

import json
from typing import Any, Mapping
from urllib.parse import quote, urlencode

from .aliases import ArtifactAliases, normalize_alias_key
from .canonicalize import extract_arxiv_id, extract_doi
from .connectors.base import ConnectorContext
from .connectors.http import SharedHttpClient
from .models import new_artifact
from .store import JsonlStore


FIELDS = "paperId,corpusId,externalIds,title,url,authors,year,publicationDate,venue"


class SemanticScholarResolver:
    """Resolve only explicit DOI/arXiv identifiers; never search by title."""

    def resolve(
        self,
        candidate: Mapping[str, Any],
        candidate_artifact_id: str,
        aliases: ArtifactAliases,
        context: ConnectorContext,
    ) -> dict[str, Any]:
        identifiers = candidate.get("identifiers") if isinstance(candidate.get("identifiers"), Mapping) else {}
        doi = extract_doi(str(identifiers.get("doi") or ""))
        arxiv = extract_arxiv_id(str(identifiers.get("arxiv") or ""))
        explicit_aliases = [f"doi:{doi}" if doi else "", f"arxiv:{arxiv}" if arxiv else ""]
        explicit_aliases = [item for item in explicit_aliases if item]
        if not explicit_aliases:
            if str(candidate.get("title") or "").strip():
                return {
                    "classification": "title_candidate",
                    "resolution_candidate": {"title": str(candidate["title"]).strip(), "artifact_id": candidate_artifact_id},
                    "canonical_artifact_id": None,
                    "aliases": [],
                }
            return {"classification": "unresolved", "canonical_artifact_id": None, "aliases": []}

        for key in explicit_aliases:
            existing = aliases.resolve_alias(key)
            if existing:
                incoming = aliases.resolve_artifact_id(candidate_artifact_id)
                if incoming != existing:
                    aliases.add_redirect(incoming, existing, reason="exact_identifier_alias", created_at=context.now())
                for exact in explicit_aliases:
                    aliases.register_alias(exact, existing, resolver="local-exact", resolver_id=key)
                return {"classification": "exact_identifier", "canonical_artifact_id": existing, "aliases": explicit_aliases}

        lookup = f"DOI:{doi}" if doi else f"ARXIV:{arxiv}"
        url = "https://api.semanticscholar.org/graph/v1/paper/" + quote(lookup, safe=":./-_") + "?" + urlencode({"fields": FIELDS})
        environment = dict(context.environment)
        if "SEMANTIC_SCHOLAR_API_KEY" not in environment:
            import os
            environment["SEMANTIC_SCHOLAR_API_KEY"] = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
        headers = {"Accept": "application/json"}
        api_key = environment.get("SEMANTIC_SCHOLAR_API_KEY")
        if api_key:
            headers["x-api-key"] = api_key
        client = context.http or SharedHttpClient()
        response = client.get(url, headers=headers)
        if response.status == 404:
            return {"classification": "unresolved", "canonical_artifact_id": None, "aliases": [],
                    "diagnostics": client.diagnostics(response)}
        if response.status != 200:
            return {"classification": "unresolved", "canonical_artifact_id": None, "aliases": [],
                    "diagnostics": client.diagnostics(response)}
        try:
            paper = json.loads(response.body.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return {"classification": "unresolved", "canonical_artifact_id": None, "aliases": [],
                    "diagnostics": {"status": response.status, "error": "invalid-json"}}
        if not isinstance(paper, Mapping) or not paper.get("paperId"):
            return {"classification": "unresolved", "canonical_artifact_id": None, "aliases": [],
                    "diagnostics": {"status": response.status, "error": "missing-paper-id"}}

        external = paper.get("externalIds") if isinstance(paper.get("externalIds"), Mapping) else {}
        resolved_doi = extract_doi(str(external.get("DOI") or ""))
        resolved_arxiv = extract_arxiv_id(str(external.get("ArXiv") or ""))
        if (doi and resolved_doi and doi != resolved_doi) or (arxiv and resolved_arxiv and arxiv != resolved_arxiv):
            return {"classification": "conflict", "canonical_artifact_id": None, "aliases": [],
                    "diagnostics": {"status": response.status, "error": "explicit-identifier-mismatch"}}
        remote_aliases = [f"semantic-scholar:{paper['paperId']}"]
        if resolved_doi:
            remote_aliases.append(f"doi:{resolved_doi}")
        if resolved_arxiv:
            remote_aliases.append(f"arxiv:{resolved_arxiv}")
        openalex = str(external.get("OpenAlexID") or "").strip()
        if openalex:
            remote_aliases.append(f"openalex:{openalex}")
        landing_url = str(paper.get("url") or "").strip()
        if landing_url.startswith("http"):
            remote_aliases.append(f"url:{landing_url}")
        remote_aliases = sorted({normalize_alias_key(item) for item in remote_aliases})

        known_roots = sorted({
            root
            for key in remote_aliases
            if (root := aliases.resolve_alias(key)) is not None
        })
        canonical = known_roots[0] if known_roots else aliases.resolve_artifact_id(candidate_artifact_id)
        resolver_id = str(paper["paperId"])
        for old in known_roots:
            if old != canonical:
                aliases.add_redirect(old, canonical, reason="semantic_scholar_provider_equivalence", created_at=context.now())
        incoming_root = aliases.resolve_artifact_id(candidate_artifact_id)
        if incoming_root != canonical:
            aliases.add_redirect(incoming_root, canonical, reason="semantic_scholar_provider_equivalence", created_at=context.now())
        for key in sorted(set(remote_aliases + explicit_aliases)):
            aliases.register_alias(key, canonical, resolver="semantic-scholar", resolver_id=resolver_id, resolved_at=context.now())
        return {
            "classification": "provider_equivalence",
            "canonical_artifact_id": canonical,
            "aliases": sorted(set(remote_aliases + explicit_aliases)),
            "paper": {
                "paperId": str(paper["paperId"]), "corpusId": paper.get("corpusId"),
                "externalIds": dict(external), "title": str(paper.get("title") or ""),
                "url": landing_url, "authors": paper.get("authors", []), "year": paper.get("year"),
                "publicationDate": paper.get("publicationDate"), "venue": paper.get("venue"),
            },
            "diagnostics": client.diagnostics(response),
        }


def materialize_semantic_scholar_result(
    result: Mapping[str, Any],
    artifact: Mapping[str, Any],
    store: JsonlStore,
) -> dict[str, Any] | None:
    """Persist exact provider metadata while preserving conflicts and canonical ID."""
    paper = result.get("paper") if isinstance(result.get("paper"), Mapping) else None
    canonical_id = result.get("canonical_artifact_id")
    if not paper or not canonical_id or result.get("classification") not in {"exact_identifier", "provider_equivalence"}:
        return None
    external = paper.get("externalIds") if isinstance(paper.get("externalIds"), Mapping) else {}
    doi = extract_doi(str(external.get("DOI") or ""))
    arxiv = extract_arxiv_id(str(external.get("ArXiv") or ""))
    identifiers = {
        "doi": doi, "arxiv": arxiv,
        "semantic_scholar": str(paper.get("paperId") or "") or None,
        "openalex": str(external.get("OpenAlexID") or "") or None,
        "acl": str(external.get("ACL") or "") or None,
        "pmid": str(external.get("PMID") or "") or None,
        "pmcid": str(external.get("PMCID") or "") or None,
    }
    authors = sorted({
        str(person.get("name") or "").strip()
        for person in paper.get("authors", [])
        if isinstance(person, Mapping) and str(person.get("name") or "").strip()
    })
    timestamp = str(paper.get("publicationDate") or "")
    if not timestamp and paper.get("year"):
        timestamp = f"{paper['year']}-01-01T00:00:00Z"
    provenance = {"source": "semantic-scholar", "observation_id": None}
    record = new_artifact(
        identity=f"semantic-scholar:{paper.get('paperId')}", artifact_type="paper",
        title=str(paper.get("title") or ""), identifiers=identifiers, authors=authors,
        published_at=timestamp or None, topics=[str(item) for item in artifact.get("topics", [])],
        observation_ids=[str(item) for item in artifact.get("observation_ids", [])],
        entity_ids=[str(item) for item in artifact.get("entity_ids", [])],
        status=str(artifact.get("status") or "candidate"),
        field_provenance={
            "title": provenance,
            "identifiers": {key: provenance for key, value in identifiers.items() if value},
        },
    )
    record["artifact_id"] = str(canonical_id)
    record["canonical_url"] = str(artifact.get("canonical_url") or "")
    record["summary"] = str(artifact.get("summary") or "")
    record["organizations"] = [str(item) for item in artifact.get("organizations", [])]
    return store.upsert_artifact(record)
