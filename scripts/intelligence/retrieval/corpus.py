from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping

from ..aliases import ArtifactAliases
from ..entity_aliases import EntityAliases
from ..graph.store import GraphStore
from ..store import JsonlStore


NORMALIZATION_VERSION = "retrieval-document-v1"
MAX_EXCERPTS = 3
MAX_EXCERPT_CHARS = 2000


@dataclass(frozen=True)
class RetrievalDocument:
    artifact_id: str
    artifact_type: str
    title: str
    body: str
    authors: tuple[str, ...]
    organizations: tuple[str, ...]
    topics: tuple[str, ...]
    published_at: str | None
    first_observed_at: str | None
    source_ids: tuple[str, ...]
    graph_entities: tuple[Mapping[str, str], ...]
    observation_excerpts: tuple[Mapping[str, str | None], ...]
    language: str
    freshness_basis: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("authors", "organizations", "topics", "source_ids", "graph_entities", "observation_excerpts"):
            value[key] = list(value[key])
        return value

    @property
    def retrieval_text(self) -> str:
        return "\n".join(part for part in (
            self.title, self.body, " ".join(self.authors), " ".join(self.organizations), " ".join(self.topics),
        ) if part)

    @property
    def document_hash(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()


@dataclass(frozen=True)
class CorpusSnapshot:
    documents: tuple[RetrievalDocument, ...]
    corpus_hash: str
    source_tree_hash: str
    normalization_version: str = NORMALIZATION_VERSION

    def by_id(self) -> dict[str, RetrievalDocument]:
        return {item.artifact_id: item for item in self.documents}


def build_snapshot(store: JsonlStore, *, graph: GraphStore | None = None) -> CorpusSnapshot:
    """Build bounded, deterministic search documents from canonical local records."""
    graph = graph or GraphStore(store.directory)
    aliases = ArtifactAliases(store.directory)
    entity_aliases = EntityAliases(store.directory)
    artifacts = list(store.iter_records("artifact"))
    observations = list(store.iter_records("observation"))
    entities = list(store.iter_records("entity"))
    sources = list(store.iter_records("source"))
    artifact_by_id = {str(item["artifact_id"]): item for item in artifacts}
    observation_by_id = {str(item["observation_id"]): item for item in observations}
    entity_by_id: dict[str, dict[str, Any]] = {}
    for entity in entities:
        canonical_id = entity_aliases.resolve_entity_id(str(entity["entity_id"]))
        prior = entity_by_id.get(canonical_id)
        if prior is None or str(entity.get("name", "")).casefold() < str(prior.get("name", "")).casefold():
            entity_by_id[canonical_id] = entity

    canonical_artifacts: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        canonical_id = aliases.resolve_artifact_id(str(artifact["artifact_id"]))
        canonical_artifacts.setdefault(canonical_id, []).append(artifact)

    graph_edges = graph.iter_edges()
    canonical_edges = []
    for edge in graph_edges:
        row = dict(edge)
        for key in ("subject_id", "object_id"):
            node_id = str(row[key])
            if node_id.startswith("art-"):
                row[key] = aliases.resolve_artifact_id(node_id)
            elif node_id.startswith("ent-"):
                row[key] = entity_aliases.resolve_entity_id(node_id)
        canonical_edges.append(row)

    artifact_obs: dict[str, set[str]] = {}
    source_evidence: dict[str, set[str]] = {}
    graph_entity_ids: dict[str, set[str]] = {}
    for artifact_id, rows in canonical_artifacts.items():
        ids = set()
        for artifact in rows:
            ids.update(str(value) for value in artifact.get("observation_ids", []))
        artifact_obs[artifact_id] = ids
    for edge in canonical_edges:
        predicate = str(edge["predicate"])
        subject, obj = str(edge["subject_id"]), str(edge["object_id"])
        if predicate in {"mentions", "recommends"} and subject.startswith("src-") and obj.startswith("art-"):
            source_evidence.setdefault(obj, set()).add(subject)
            artifact_obs.setdefault(obj, set()).update(
                str(item["observation_id"]) for item in edge.get("evidence", []) if item.get("observation_id")
            )
        if subject.startswith("art-") and obj.startswith("ent-"):
            graph_entity_ids.setdefault(subject, set()).add(obj)
        elif obj.startswith("art-") and subject.startswith("ent-"):
            graph_entity_ids.setdefault(obj, set()).add(subject)

    source_ids_known = {str(item["source_id"]) for item in sources}
    documents: list[RetrievalDocument] = []
    for canonical_id in sorted(canonical_artifacts):
        rows = canonical_artifacts[canonical_id]
        # Deterministic field selection handles historical aliases that resolve to one Artifact.
        rows.sort(key=lambda item: str(item["artifact_id"]))
        artifact = rows[0]
        excerpt_rows = [observation_by_id[item] for item in sorted(artifact_obs.get(canonical_id, set())) if item in observation_by_id]
        excerpt_rows.sort(key=lambda item: (str(item.get("observed_at") or ""), str(item["observation_id"])), reverse=True)
        excerpt_rows = excerpt_rows[:MAX_EXCERPTS]
        excerpts: list[dict[str, str | None]] = []
        for observation in excerpt_rows:
            text = " ".join(part.strip() for part in (str(observation.get("title") or ""), str(observation.get("text") or "")) if part.strip())
            if not text:
                continue
            excerpts.append({
                "observation_id": str(observation["observation_id"]),
                "source_id": str(observation.get("source_id") or ""),
                "text": text[:MAX_EXCERPT_CHARS],
                "published_at": observation.get("published_at"),
                "observed_at": observation.get("observed_at"),
            })
        title = str(artifact.get("title") or "").strip()
        summary = str(artifact.get("summary") or "").strip()
        body_parts = [summary] if summary else []
        body_parts.extend(str(item["text"]) for item in excerpts)
        body = "\n\n".join(body_parts)
        authors = _unique_strings(artifact.get("authors", []))
        organizations = _unique_strings(artifact.get("organizations", []))
        topic_ids = _unique_strings(artifact.get("topics", []))
        graph_entities = []
        for entity_id in sorted(graph_entity_ids.get(canonical_id, set())):
            entity = entity_by_id.get(entity_id)
            if entity:
                graph_entities.append({"entity_id": entity_id, "name": str(entity.get("name") or "")})
        linked_source_ids = set(source_evidence.get(canonical_id, set()))
        linked_source_ids.update(
            str(item.get("source_id")) for item in excerpts
            if item.get("source_id") in source_ids_known
        )
        linked_source_ids.intersection_update(source_ids_known)
        published_at = str(artifact.get("published_at") or "") or None
        if not published_at:
            obs_published = [str(item.get("published_at")) for item in excerpt_rows if item.get("published_at")]
            if obs_published:
                published_at = min(obs_published)
        observed_values = [str(item.get("observed_at")) for item in observations_for_ids(artifact_obs.get(canonical_id, set()), observation_by_id) if item.get("observed_at")]
        first_observed_at = min(observed_values) if observed_values else None
        freshness_basis = "published_at" if published_at else "observed_at_fallback"
        documents.append(RetrievalDocument(
            artifact_id=canonical_id,
            artifact_type=str(artifact.get("artifact_type") or "other"),
            title=title,
            body=body,
            authors=authors,
            organizations=organizations,
            topics=topic_ids,
            published_at=published_at,
            first_observed_at=first_observed_at,
            source_ids=tuple(sorted(linked_source_ids)),
            graph_entities=tuple(graph_entities),
            observation_excerpts=tuple(excerpts),
            language=_language(title + " " + body),
            freshness_basis=freshness_basis,
        ))
    serialized = [item.to_dict() for item in documents]
    corpus_hash = hashlib.sha256(_canonical(serialized)).hexdigest()
    source_tree_hash = hashlib.sha256(_canonical({
        "artifact_hashes": sorted(_canonical(row).decode("utf-8") for row in artifacts),
        "observation_hashes": sorted(_canonical(row).decode("utf-8") for row in observations),
        "entity_hashes": sorted(_canonical(row).decode("utf-8") for row in entities),
        "source_hashes": sorted(_canonical(row).decode("utf-8") for row in sources),
        "graph_hashes": sorted(_canonical(row).decode("utf-8") for row in graph_edges),
    })).hexdigest()
    return CorpusSnapshot(tuple(documents), corpus_hash, source_tree_hash)


def filter_documents(snapshot: CorpusSnapshot, request: Any) -> tuple[RetrievalDocument, ...]:
    result = []
    filters = request.filters
    types = set(map(str, filters.get("artifact_types", [])))
    languages = set(map(str, filters.get("languages", [])))
    after = _parse(filters.get("published_after"))
    before = _parse(filters.get("published_before"))
    as_of = _parse(request.as_of)
    for document in snapshot.documents:
        content_time = _parse(document.published_at)
        if as_of:
            temporal_time = content_time or _parse(document.first_observed_at)
            if temporal_time is None or temporal_time > as_of:
                continue
        if types and document.artifact_type not in types:
            continue
        if languages and document.language not in languages:
            continue
        if after and (content_time is None or content_time < after):
            continue
        if before and (content_time is None or content_time > before):
            continue
        result.append(document)
    return tuple(result)


def _unique_strings(value: Any) -> tuple[str, ...]:
    return tuple(sorted({str(item).strip() for item in value or [] if str(item).strip()}))


def _language(value: str) -> str:
    if any("\u3400" <= char <= "\u9fff" for char in value):
        return "zh"
    return "en" if value.strip() else "und"


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def observations_for_ids(ids: set[str], rows: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [rows[item] for item in sorted(ids) if item in rows]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
