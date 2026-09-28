from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping

from ..aliases import ArtifactAliases
from ..entity_aliases import EntityAliases
from ..graph.store import GraphStore
from ..store import JsonlStore
from ..canonicalize import artifact_identity
from ..ids import artifact_id as make_artifact_id
from ..topics import map_topics


NORMALIZATION_VERSION = "retrieval-document-v2"
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
    mention_role: str = "referenced"
    eligibility: str = "full_text"
    native_tags: tuple[str, ...] = ()
    pipeline_tag: str | None = None
    metadata_enriched: bool = False
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("authors", "organizations", "topics", "source_ids", "graph_entities", "observation_excerpts", "native_tags"):
            value[key] = list(value[key])
        return value

    @property
    def retrieval_text(self) -> str:
        return "\n".join(part for part in (
            self.title, self.body, " ".join(self.authors), " ".join(self.organizations), " ".join(self.topics),
            " ".join(self.native_tags), self.pipeline_tag or "",
        ) if part)

    @property
    def document_hash(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()


@dataclass(frozen=True)
class CorpusSnapshot:
    documents: tuple[RetrievalDocument, ...]
    corpus_hash: str
    source_tree_hash: str
    quality: Mapping[str, Any] = field(default_factory=dict)
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
    primary_observations: dict[str, set[str]] = {}
    artifact_roles: dict[str, set[str]] = {}
    source_evidence: dict[str, set[str]] = {}
    graph_entity_ids: dict[str, set[str]] = {}
    for artifact_id, rows in canonical_artifacts.items():
        ids = set()
        for artifact in rows:
            ids.update(str(value) for value in artifact.get("observation_ids", []))
        artifact_obs[artifact_id] = ids
    for observation in observations:
        observation_id = str(observation["observation_id"])
        for candidate in observation.get("artifact_candidates", []):
            if not isinstance(candidate, Mapping):
                continue
            role = str((candidate.get("mention") or {}).get("role") or "referenced")
            if role not in {"primary", "referenced", "incidental"}:
                role = "referenced"
            try:
                canonical_id = aliases.resolve_artifact_id(make_artifact_id(artifact_identity(candidate)))
            except ValueError:
                continue
            artifact_roles.setdefault(canonical_id, set()).add(role)
            if role == "primary":
                primary_observations.setdefault(canonical_id, set()).add(observation_id)
    for canonical_id, rows in canonical_artifacts.items():
        for artifact in rows:
            mention = ((artifact.get("field_provenance") or {}).get("mention") or {})
            role = str(mention.get("mention_role") or "")
            if role in {"primary", "referenced", "incidental"}:
                artifact_roles.setdefault(canonical_id, set()).add(role)
            if role == "primary":
                observation_id = str(mention.get("observation_id") or "")
                if observation_id:
                    primary_observations.setdefault(canonical_id, set()).add(observation_id)
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
    source_by_id = {str(item["source_id"]): item for item in sources}
    documents: list[RetrievalDocument] = []
    for canonical_id in sorted(canonical_artifacts):
        rows = canonical_artifacts[canonical_id]
        # Deterministic field selection handles historical aliases that resolve to one Artifact.
        rows.sort(key=lambda item: str(item["artifact_id"]))
        artifact = rows[0]
        roles = artifact_roles.get(canonical_id, set()) or {"referenced"}
        mention_role = "primary" if "primary" in roles else ("incidental" if roles == {"incidental"} else "referenced")
        excerpt_ids = primary_observations.get(canonical_id, set()) if mention_role == "primary" else set()
        excerpt_rows = [observation_by_id[item] for item in sorted(excerpt_ids) if item in observation_by_id]
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
        provider_metadata = artifact.get("provider_metadata") if isinstance(artifact.get("provider_metadata"), Mapping) else {}
        hf_metadata = provider_metadata.get("huggingface") if isinstance(provider_metadata.get("huggingface"), Mapping) else {}
        hf_card = hf_metadata.get("card") if isinstance(hf_metadata.get("card"), Mapping) else {}
        title = str(artifact.get("title") or hf_card.get("model_name") or "").strip()
        hf_repo_id = _hf_repo_id(artifact)
        if not title and hf_repo_id:
            title = hf_repo_id
        summary = str(artifact.get("summary") or hf_card.get("description") or "").strip()[:4000]
        body_parts = [summary] if summary else []
        body_parts.extend(str(item["text"]) for item in excerpts)
        body = "\n\n".join(body_parts)
        authors = _unique_strings(artifact.get("authors", []))
        organizations = _unique_strings(artifact.get("organizations", []))
        native_tags = _unique_strings(hf_metadata.get("tags", []))
        topic_ids = set(_unique_strings(artifact.get("topics", [])))
        topic_ids.update(map_topics(list(native_tags) + ([str(hf_metadata.get("pipeline_tag"))] if hf_metadata.get("pipeline_tag") else [])))
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
        if mention_role == "primary":
            for source_id in linked_source_ids:
                topic_ids.update(str(item) for item in source_by_id.get(source_id, {}).get("topics", []))
        published_at = str(artifact.get("published_at") or "") or None
        if not published_at and mention_role == "primary":
            obs_published = [str(item.get("published_at")) for item in excerpt_rows if item.get("published_at")]
            if obs_published:
                published_at = min(obs_published)
        observed_values = [str(item.get("observed_at")) for item in observations_for_ids(artifact_obs.get(canonical_id, set()), observation_by_id) if item.get("observed_at")]
        first_observed_at = min(observed_values) if observed_values else None
        freshness_basis = ("published_at" if published_at else "provider_created_at" if hf_metadata.get("created_at")
                           else "observed_at_fallback")
        body = "\n\n".join(body_parts)
        artifact_type = str(artifact.get("artifact_type") or "other")
        metadata_enriched = bool(str(hf_card.get("description") or "").strip())
        eligibility = _eligibility(artifact, artifact_type, title, body, mention_role, metadata_enriched)
        documents.append(RetrievalDocument(
            artifact_id=canonical_id,
            artifact_type=artifact_type,
            title=title,
            body=body,
            authors=authors,
            organizations=organizations,
            topics=tuple(sorted(topic_ids)),
            published_at=published_at,
            first_observed_at=first_observed_at,
            source_ids=tuple(sorted(linked_source_ids)),
            graph_entities=tuple(graph_entities),
            observation_excerpts=tuple(excerpts),
            language=_language(title + " " + body),
            freshness_basis=freshness_basis,
            mention_role=mention_role,
            eligibility=eligibility,
            native_tags=native_tags,
            pipeline_tag=str(hf_metadata.get("pipeline_tag") or "") or None,
            metadata_enriched=metadata_enriched,
            created_at=str(hf_metadata.get("created_at") or "") or None,
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
    quality = build_quality_manifest(documents, artifacts)
    return CorpusSnapshot(tuple(documents), corpus_hash, source_tree_hash, quality)


def filter_documents(snapshot: CorpusSnapshot, request: Any, *, include_graph_only: bool = False) -> tuple[RetrievalDocument, ...]:
    result = []
    filters = request.filters
    types = set(map(str, filters.get("artifact_types", [])))
    languages = set(map(str, filters.get("languages", [])))
    after = _parse(filters.get("published_after"))
    before = _parse(filters.get("published_before"))
    profile = str(filters.get("corpus_profile") or "research-default")
    as_of = _parse(request.as_of)
    for document in snapshot.documents:
        if include_graph_only:
            if document.eligibility == "excluded":
                continue
        elif not _profile_includes(document, profile):
            continue
        content_time = _parse(document.published_at)
        if as_of:
            if document.artifact_type in {"model", "dataset", "space"}:
                temporal_time = _parse(document.created_at) or _parse(document.first_observed_at)
            else:
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


def build_quality_manifest(documents: list[RetrievalDocument], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    types: dict[str, int] = {}
    eligibility: dict[str, int] = {key: 0 for key in ("full_text", "metadata_only", "graph_only", "excluded")}
    topic_by_type: dict[str, list[int]] = {}
    topic_by_source: dict[str, list[int]] = {}
    topic_by_role: dict[str, list[int]] = {}
    for document in documents:
        types[document.artifact_type] = types.get(document.artifact_type, 0) + 1
        eligibility[document.eligibility] += 1
        if document.artifact_type in {"model", "dataset", "space"}:
            continue
        # Reserved for future type balance diagnostics; no quotas are imposed.
    for document in documents:
        for key, value in (("type", document.artifact_type), ("role", document.mention_role)):
            target = topic_by_type if key == "type" else topic_by_role
            row = target.setdefault(value, [0, 0])
            row[0] += int(bool(document.topics)); row[1] += 1
        for source_id in document.source_ids or ("unattributed",):
            row = topic_by_source.setdefault(source_id, [0, 0])
            row[0] += int(bool(document.topics)); row[1] += 1
    searchable = [item for item in documents if _has_title_or_body(item) and item.eligibility != "excluded"]
    total = len(documents)
    return {
        "artifact_total": total,
        "eligible": eligibility,
        "types": dict(sorted(types.items())),
        "indexed_by_route": {"bm25": len(searchable), "dense": len(searchable), "graph": total},
        "missing_title": sum(not item.title for item in documents),
        "missing_body": sum(not item.body.strip() for item in documents),
        "missing_published_at": sum(not item.published_at for item in documents),
        "primary_count": sum(item.mention_role == "primary" for item in documents),
        "referenced_count": sum(item.mention_role == "referenced" for item in documents),
        "topic_coverage": {
            "artifacts_with_topic": sum(bool(item.topics) for item in documents),
            "topic_coverage_rate": round(sum(bool(item.topics) for item in documents) / total, 6) if total else 0.0,
            "by_artifact_type": _coverage(topic_by_type),
            "by_source": _coverage(topic_by_source),
            "by_mention_role": _coverage(topic_by_role),
        },
        "profile_counts": {profile: sum(_profile_includes(item, profile) for item in documents)
                           for profile in ("research-default", "all-artifacts", "models")},
    }


def _coverage(source: Mapping[str, list[int]]) -> dict[str, dict[str, Any]]:
    return {key: {"with_topic": value[0], "total": value[1],
                  "rate": round(value[0] / value[1], 6) if value[1] else 0.0}
            for key, value in sorted(source.items())}


def _profile_includes(document: RetrievalDocument, profile: str) -> bool:
    if not _has_title_or_body(document) or document.eligibility in {"excluded", "graph_only"}:
        return False
    if profile == "all-artifacts":
        return True
    if profile == "models":
        return document.artifact_type in {"model", "dataset", "space"}
    if profile != "research-default":
        raise ValueError(f"unsupported retrieval corpus profile: {profile}")
    if document.artifact_type in {"model", "dataset", "space"}:
        return document.eligibility == "full_text" or document.mention_role == "primary" or document.metadata_enriched
    return True


def _has_title_or_body(document: RetrievalDocument) -> bool:
    return bool(document.title.strip() or document.body.strip())


def _eligibility(artifact: Mapping[str, Any], artifact_type: str, title: str, body: str,
                 role: str, metadata_enriched: bool) -> str:
    if role == "incidental":
        return "excluded"
    if title and len(" ".join(" ".join((title, body)).split())) >= 40:
        return "full_text"
    if artifact_type in {"model", "dataset", "space"} and (
        metadata_enriched or _hf_repo_id(artifact) or role == "primary"
    ):
        return "metadata_only"
    if title or body.strip():
        return "metadata_only"
    if artifact.get("canonical_url") or artifact.get("identifiers"):
        return "graph_only"
    return "excluded"


def _hf_repo_id(artifact: Mapping[str, Any]) -> str:
    identifiers = artifact.get("identifiers") if isinstance(artifact.get("identifiers"), Mapping) else {}
    value = identifiers.get("huggingface")
    if isinstance(value, Mapping):
        return str(value.get("repo_id") or "").strip()
    raw = str(value or "").strip()
    if raw and "/" in raw:
        return raw
    return ""


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
