from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Iterable

from ...aliases import ArtifactAliases
from ...entity_aliases import EntityAliases, normalize_entity_alias
from ...graph.models import make_edge
from ...ids import entity_id
from ...models import new_artifact, new_entity
from ...store import JsonlStore
from ..store import GraphStore


def build_openalex_edges(
    artifact: Mapping[str, Any],
    expansion: Mapping[str, Any],
    store: JsonlStore,
    graph: GraphStore,
    aliases: EntityAliases,
    *,
    now: str,
) -> dict[str, int]:
    if expansion.get("provider") != "openalex" or expansion.get("status") != "succeeded":
        raise ValueError("OpenAlex expansion is not successful")
    work = expansion.get("work") if isinstance(expansion.get("work"), Mapping) else {}
    provider_record_id = str(work.get("id") or "")
    artifact_id_value = str(artifact["artifact_id"])
    entities_added = edges_added = 0
    for author in work.get("authors", []):
        if not isinstance(author, Mapping) or not author.get("id"):
            continue
        external = {
            "openalex_author": str(author["id"]),
            "orcid": str(author.get("orcid") or "") or None,
        }
        entity, created = materialize_exact_entity(
            store, aliases, entity_type="person", name=str(author.get("name") or "Unknown author"),
            external_ids=external, url=f"https://openalex.org/{author['id']}",
            provider="openalex", provider_record_id=provider_record_id, now=now,
        )
        entities_added += int(created)
        graph.add_edge(make_edge(
            artifact_id_value, "authored_by", str(entity["entity_id"]),
            _provider_evidence("openalex", provider_record_id, now), observed_at=now,
        ))
        edges_added += 1
        for institution in author.get("institutions", []):
            if not isinstance(institution, Mapping) or not institution.get("id"):
                continue
            inst_external = {
                "openalex_institution": str(institution["id"]),
                "ror": str(institution.get("ror") or "") or None,
            }
            inst, inst_created = materialize_exact_entity(
                store, aliases, entity_type="institution",
                name=str(institution.get("name") or "Unknown institution"),
                external_ids=inst_external, url=f"https://openalex.org/{institution['id']}",
                provider="openalex", provider_record_id=str(author["id"]), now=now,
            )
            entities_added += int(inst_created)
            graph.add_edge(make_edge(
                str(entity["entity_id"]), "affiliated_with", str(inst["entity_id"]),
                _provider_evidence("openalex", str(author["id"]), now), observed_at=now,
            ))
            edges_added += 1

    venue = work.get("venue") if isinstance(work.get("venue"), Mapping) else None
    if venue and venue.get("id"):
        external = {
            "openalex_source": str(venue["id"]),
            "issn": str(venue.get("issn_l") or "") or None,
        }
        venue_entity, created = materialize_exact_entity(
            store, aliases, entity_type="venue", name=str(venue.get("name") or "Unknown venue"),
            external_ids=external, url=f"https://openalex.org/{venue['id']}",
            provider="openalex", provider_record_id=provider_record_id, now=now,
        )
        entities_added += int(created)
        graph.add_edge(make_edge(
            artifact_id_value, "published_in", str(venue_entity["entity_id"]),
            _provider_evidence("openalex", provider_record_id, now), observed_at=now,
        ))
        edges_added += 1

    # OpenAlex provides only referenced Work IDs in this response; citation edges are
    # materialized from Semantic Scholar records that include the required paper metadata.
    return {"entities_added": entities_added, "edges_added": edges_added, "citations_added": 0}


def build_semantic_scholar_edges(
    artifact: Mapping[str, Any],
    expansion: Mapping[str, Any],
    store: JsonlStore,
    graph: GraphStore,
    aliases: EntityAliases,
    *,
    now: str,
    max_references: int = 20,
    max_citations: int = 20,
) -> dict[str, int]:
    if expansion.get("provider") != "semantic-scholar" or expansion.get("status") not in {"succeeded", "partial"}:
        raise ValueError("Semantic Scholar expansion is not successful")
    paper = expansion.get("paper") if isinstance(expansion.get("paper"), Mapping) else {}
    paper_id = str(paper.get("paperId") or "")
    artifact_id_value = str(artifact["artifact_id"])
    entities_added = edges_added = 0
    for author in paper.get("authors", []):
        if not isinstance(author, Mapping) or not author.get("id"):
            continue
        author_id = str(author["id"])
        entity, created = materialize_exact_entity(
            store, aliases, entity_type="person", name=str(author.get("name") or "Unknown author"),
            external_ids={"semantic_scholar_author": author_id},
            url=f"https://www.semanticscholar.org/author/{author_id}",
            provider="semantic-scholar", provider_record_id=paper_id, now=now,
        )
        entities_added += int(created)
        graph.add_edge(make_edge(
            artifact_id_value, "authored_by", str(entity["entity_id"]),
            _provider_evidence("semantic-scholar", paper_id, now), observed_at=now,
        ))
        edges_added += 1

    artifact_alias_store = ArtifactAliases(store.directory)
    citations_added = 0
    for route, maximum in (
        ("references", min(20, max_references)),
        ("citations", min(20, max_citations)),
    ):
        # Citation direction is canonicalized as cited paper --cites--> citing paper.
        for item in sorted(expansion.get(route, []), key=lambda value: str(value.get("paperId") or ""))[:maximum]:
            if not isinstance(item, Mapping) or not item.get("paperId"):
                continue
            cited_paper = str(item["paperId"])
            target_id = _materialize_s2_paper(item, artifact_alias_store, store, now, paper_id)
            if route == "references":
                subject_id, object_id = artifact_id_value, target_id
            else:
                subject_id, object_id = target_id, artifact_id_value
            graph.add_edge(make_edge(
                subject_id, "cites", object_id,
                _provider_evidence("semantic-scholar", paper_id, now), observed_at=now,
            ))
            edges_added += 1
            citations_added += 1
    return {"entities_added": entities_added, "edges_added": edges_added, "citations_added": citations_added}


def build_semantic_scholar_recent_works_edges(
    entity: Mapping[str, Any],
    expansion: Mapping[str, Any],
    store: JsonlStore,
    graph: GraphStore,
    entity_aliases: EntityAliases,
    *,
    now: str,
    max_recent_works: int = 10,
) -> dict[str, int]:
    if expansion.get("provider") != "semantic-scholar" or expansion.get("status") != "succeeded":
        raise ValueError("Semantic Scholar author expansion is not successful")
    author_id = str(entity["entity_id"])
    external = entity.get("external_ids") if isinstance(entity.get("external_ids"), Mapping) else {}
    if not external.get("semantic_scholar_author"):
        raise ValueError("author expansion requires an exact Semantic Scholar author id")
    artifact_alias_store = ArtifactAliases(store.directory)
    entities_added = edges_added = 0
    works = sorted(
        expansion.get("recent_works", []),
        key=lambda item: (str(item.get("publicationDate") or ""), str(item.get("paperId") or "")),
        reverse=True,
    )[:min(10, max_recent_works)]
    for item in works:
        if not isinstance(item, Mapping) or not item.get("paperId"):
            continue
        paper_id = str(item["paperId"])
        artifact_id_value = _materialize_s2_paper(item, artifact_alias_store, store, now, str(external["semantic_scholar_author"]))
        author_record = store.get_by_id("entity", entity_aliases.resolve_entity_id(author_id))
        if author_record is None:
            raise ValueError("author entity is missing from local store")
        graph.add_edge(make_edge(
            artifact_id_value, "authored_by", str(author_record["entity_id"]),
            _provider_evidence("semantic-scholar", paper_id, now), observed_at=now,
        ))
        edges_added += 1
        for other_author in item.get("authors", []):
            if not isinstance(other_author, Mapping) or not other_author.get("authorId"):
                continue
            other_id = str(other_author["authorId"])
            other_entity, created = materialize_exact_entity(
                store, entity_aliases, entity_type="person",
                name=str(other_author.get("name") or "Unknown author"),
                external_ids={"semantic_scholar_author": other_id},
                url=f"https://www.semanticscholar.org/author/{other_id}",
                provider="semantic-scholar", provider_record_id=paper_id, now=now,
            )
            entities_added += int(created)
            graph.add_edge(make_edge(
                artifact_id_value, "authored_by", str(other_entity["entity_id"]),
                _provider_evidence("semantic-scholar", paper_id, now), observed_at=now,
            ))
            edges_added += 1
    return {"entities_added": entities_added, "edges_added": edges_added, "recent_works_added": len(works)}


def materialize_exact_entity(
    store: JsonlStore,
    aliases: EntityAliases,
    *,
    entity_type: str,
    name: str,
    external_ids: Mapping[str, Any],
    url: str,
    provider: str,
    provider_record_id: str,
    now: str,
) -> tuple[dict[str, Any], bool]:
    normalized = sorted({normalize_entity_alias(key) for key in _entity_alias_keys(external_ids)})
    if not normalized:
        raise ValueError("exact provider entity identity is required")
    known = sorted({root for key in normalized if (root := aliases.resolve_alias(key))})
    preferred = _preferred_alias(normalized)
    canonical_id = min(known) if known else entity_id(preferred)
    for old_id in known:
        if old_id != canonical_id:
            aliases.add_redirect(
                old_id, canonical_id, provider=provider, provider_record_id=provider_record_id, created_at=now,
            )
    for key in normalized:
        aliases.register_alias(
            key, canonical_id, provider=provider, provider_record_id=provider_record_id, resolved_at=now,
        )
    prior = store.get_by_id("entity", canonical_id)
    entity = new_entity(
        identity=preferred, entity_type=entity_type, name=name or "Unknown entity",
        urls=[url] if url else [], external_ids=dict(external_ids), resolution_state="resolved",
    )
    entity["entity_id"] = canonical_id
    return store.upsert_entity(entity), prior is None


def _entity_alias_keys(external: Mapping[str, Any]) -> list[str]:
    prefixes = {
        "semantic_scholar_author": "semantic-scholar-author",
        "openalex_author": "openalex-author",
        "orcid": "orcid",
        "github_user": "github-user",
        "github_org": "github-org",
        "openalex_institution": "openalex-institution",
        "ror": "ror",
        "openalex_source": "openalex-source",
        "issn": "issn",
    }
    return [f"{prefix}:{external[key]}" for key, prefix in prefixes.items() if external.get(key)]


def _preferred_alias(keys: Iterable[str]) -> str:
    order = {
        "orcid": 0, "ror": 0, "github-user": 1, "github-org": 1,
        "openalex-author": 2, "openalex-institution": 2, "openalex-source": 2,
        "semantic-scholar-author": 3, "issn": 4,
    }
    return min(keys, key=lambda value: (order.get(value.partition(":")[0], 99), value))


def _provider_evidence(provider: str, record_id: str, now: str) -> dict[str, Any]:
    return {
        "evidence_type": "exact_provider_metadata",
        "provider": provider,
        "provider_record_id": record_id,
        "confidence": 1.0,
        "observed_at": now,
    }


def _materialize_s2_paper(
    item: Mapping[str, Any],
    aliases: ArtifactAliases,
    store: JsonlStore,
    now: str,
    resolver_id: str,
) -> str:
    paper_id = str(item["paperId"])
    remote_aliases = [f"semantic-scholar:{paper_id}"]
    external = item.get("externalIds") if isinstance(item.get("externalIds"), Mapping) else {}
    for field, prefix in (("DOI", "doi"), ("ArXiv", "arxiv"), ("OpenAlexID", "openalex")):
        if external.get(field):
            remote_aliases.append(f"{prefix}:{external[field]}")
    roots = sorted({root for key in remote_aliases if (root := aliases.resolve_alias(key))})
    artifact_id_value = roots[0] if roots else None
    if artifact_id_value:
        for old_id in roots[1:]:
            aliases.add_redirect(
                old_id, artifact_id_value, reason="semantic_scholar_provider_equivalence", created_at=now,
            )
    if artifact_id_value is None:
        record = new_artifact(
            identity=f"semantic-scholar:{paper_id}", artifact_type="paper",
            title=str(item.get("title") or ""), canonical_url=str(item.get("url") or ""),
            identifiers={
                "semantic_scholar": paper_id, "doi": external.get("DOI"),
                "arxiv": external.get("ArXiv"), "openalex": external.get("OpenAlexID"),
            },
            authors=[str(author.get("name") or "") for author in item.get("authors", []) if isinstance(author, Mapping)],
            published_at=_publication_date(item), status="candidate",
            field_provenance={"title": {"source": "semantic-scholar", "observation_id": None}},
        )
        artifact_id_value = str(record["artifact_id"])
    else:
        record = store.get_by_id("artifact", artifact_id_value)
        if record is None:
            record = new_artifact(
                identity=f"semantic-scholar:{paper_id}", artifact_type="paper",
                title=str(item.get("title") or ""), canonical_url=str(item.get("url") or ""),
                identifiers={
                    "semantic_scholar": paper_id, "doi": external.get("DOI"),
                    "arxiv": external.get("ArXiv"), "openalex": external.get("OpenAlexID"),
                },
                authors=[str(author.get("name") or "") for author in item.get("authors", []) if isinstance(author, Mapping)],
                published_at=_publication_date(item), status="candidate",
                field_provenance={"title": {"source": "semantic-scholar", "observation_id": None}},
            )
            record["artifact_id"] = artifact_id_value
    store.upsert_artifact(record)
    for key in sorted(set(remote_aliases)):
        aliases.register_alias(key, artifact_id_value, resolver="semantic-scholar", resolver_id=resolver_id, resolved_at=now)
    return artifact_id_value


def _publication_date(item: Mapping[str, Any]) -> str | None:
    value = str(item.get("publicationDate") or "")
    if len(value) == 4 and value.isdigit():
        return f"{value}-01-01T00:00:00Z"
    if len(value) == 10:
        return f"{value}T00:00:00Z"
    return value or None
