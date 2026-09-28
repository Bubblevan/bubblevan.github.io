from __future__ import annotations

from collections import Counter
from typing import Any, Mapping
from urllib.parse import urlsplit

from .artifacts import materialize_artifact_candidates
from .aliases import ArtifactAliases
from .canonicalize import artifact_identity, canonicalize_url, extract_arxiv_id
from .hf_identity import audit_huggingface_reserved_namespace_models
from .ids import artifact_id
from .models import new_artifact, now_utc
from .runner import load_source_catalog


def rematerialize_primary_artifacts(store: Any) -> dict[str, Any]:
    """Rebuild RSS primary Artifact records from local Observations, without network access."""
    identity_repair = repair_huggingface_blog_identities(store)
    configs = {str(item["source_id"]): item for item in load_source_catalog()}
    sources = {str(item["source_id"]): item for item in store.iter_records("source")}
    counts: Counter[str] = Counter()
    artifact_ids: set[str] = set()
    aliases = ArtifactAliases(store.directory)
    existing_ids = {str(item["artifact_id"]) for item in store.iter_records("artifact")}
    artifacts_by_id = {str(item["artifact_id"]): item for item in store.iter_records("artifact")}
    for observation in store.iter_records("observation"):
        source_id = str(observation.get("source_id") or "")
        config = configs.get(source_id)
        source = sources.get(source_id)
        if config is None or not source or str(source.get("acquisition", {}).get("connector") or "") != "rss-atom":
            continue
        if observation.get("platform") != "rss" or observation.get("provenance", {}).get("retrieval_mode") != "rss":
            continue
        acquisition = config.get("acquisition") if isinstance(config.get("acquisition"), Mapping) else {}
        policy = config.get("artifact_policy") or acquisition.get("artifact_policy") or {}
        primary_type = str(policy.get("primary_type") or "blog")
        url = _primary_url(observation, str(source.get("platform") or ""))
        title = str(observation.get("title") or "").strip()
        if not url and not title:
            counts["skipped_missing_identity"] += 1
            continue
        topics = sorted(set(str(item) for item in source.get("topics", [])) |
                        set(str(item) for item in observation.get("topics", [])))
        candidate = {
            "artifact_type": primary_type,
            "title": title,
            "canonical_url": url,
            "identifiers": ({"arxiv": extract_arxiv_id(url or title or str(observation.get("text") or ""))}
                            if primary_type == "paper" and extract_arxiv_id(url or title or str(observation.get("text") or "")) else {}),
            "authors": list(observation.get("authors", [])),
            "organizations": [],
            "summary": str(observation.get("text") or "")[:4000],
            "published_at": observation.get("published_at"),
            "topics": topics,
            "mention": {"role": "primary", "evidence_level": "explicit_source_link",
                        "origin": "entry_url", "confidence": 1.0},
        }
        canonical_id = aliases.resolve_artifact_id(artifact_id(artifact_identity(candidate)))
        current = artifacts_by_id.get(canonical_id)
        current_mention = ((current or {}).get("field_provenance") or {}).get("mention", {})
        if (current and current.get("artifact_type") == primary_type
                and current_mention.get("mention_role") == "primary"
                and str(observation["observation_id"]) in set(current.get("observation_ids", []))):
            counts["already_materialized"] += 1
            continue
        is_new = canonical_id not in existing_ids
        ids = materialize_artifact_candidates({**observation,
                                               "metadata": {**dict(observation.get("metadata") or {}),
                                                            "entry_url": url, "connector": "rss-atom"},
                                               "artifact_candidates": [candidate]}, store)
        artifact_ids.update(ids)
        counts["materialized"] += 1
        if is_new:
            counts["new_artifacts"] += 1
            existing_ids.add(canonical_id)
        refreshed = store.get_by_id("artifact", canonical_id)
        if refreshed:
            artifacts_by_id[canonical_id] = refreshed
        counts[f"primary_type:{primary_type}"] += 1
    audit = audit_huggingface_reserved_namespace_models(store)
    if not audit["passed"]:
        raise ValueError(f"Hugging Face reserved namespace model audit failed: {audit}")
    return {"network_requests": 0, "observations_seen": counts.get("materialized", 0) + counts.get("already_materialized", 0) + counts.get("skipped_missing_identity", 0),
            "artifacts_touched": len(artifact_ids), "hf_identity_repair": identity_repair,
            "hf_reserved_namespace_audit": audit, "counts": dict(sorted(counts.items()))}


def repair_huggingface_blog_identities(store: Any) -> dict[str, Any]:
    """Redirect legacy Hugging Face blog identities to canonical URL-based Blog Artifacts."""
    aliases = ArtifactAliases(store.directory)
    artifacts = list(store.iter_records("artifact"))
    artifacts_by_id = {str(item["artifact_id"]): item for item in artifacts}
    observations = list(store.iter_records("observation"))
    observations_by_id = {str(item["observation_id"]): item for item in observations}
    observations_by_entry: dict[str, list[dict[str, Any]]] = {}
    for observation in observations:
        metadata = observation.get("metadata") if isinstance(observation.get("metadata"), Mapping) else {}
        entry_url = canonicalize_url(str(metadata.get("entry_url") or ""))
        if _is_hf_blog_url(entry_url):
            observations_by_entry.setdefault(entry_url, []).append(observation)

    repairs: dict[str, str] = {}
    old_model_ids: set[str] = set()
    for artifact in artifacts:
        canonical_url = canonicalize_url(str(artifact.get("canonical_url") or ""))
        if not _is_hf_blog_url(canonical_url):
            continue
        artifact_type = str(artifact.get("artifact_type") or "")
        target_url = _hf_blog_target_url(artifact, canonical_url, observations_by_id)
        is_model_identity = artifact_type == "model"
        is_truncated_blog = artifact_type == "blog" and target_url != canonical_url
        if is_model_identity or is_truncated_blog:
            repairs[str(artifact["artifact_id"])] = target_url
            if is_model_identity:
                old_model_ids.add(str(artifact["artifact_id"]))

    if not repairs:
        return {"reclassified": 0, "redirected": 0, "canonical_blog_artifacts_created": 0,
                "bogus_model_aliases_removed": 0,
                "audit": audit_huggingface_reserved_namespace_models(store)}

    created = 0
    target_ids: dict[str, str] = {}
    for old_id, target_url in sorted(repairs.items()):
        target_id = artifact_id(f"url:{target_url}")
        target_ids[old_id] = target_id
        target = artifacts_by_id.get(target_id)
        primary_rows = sorted(
            observations_by_entry.get(target_url, []),
            key=lambda row: (str(row.get("observed_at") or ""), str(row.get("observation_id") or "")),
        )
        primary = primary_rows[-1] if primary_rows else None
        if target is None:
            observation_ids = ([str(item["observation_id"]) for item in primary_rows]
                               if primary_rows else list(artifacts_by_id[old_id].get("observation_ids", [])))
            mention = {"mention_role": "primary" if primary else "referenced",
                       "mention_origin": "rss_entry" if primary else "legacy_hf_blog_url_identity"}
            if primary:
                mention.update({"observation_id": str(primary["observation_id"]),
                                "source_id": str(primary.get("source_id") or "")})
            target = new_artifact(
                identity=f"url:{target_url}", artifact_type="blog",
                title=str(primary.get("title") or "") if primary else "",
                canonical_url=target_url,
                authors=list(primary.get("authors", [])) if primary else [],
                published_at=primary.get("published_at") if primary else None,
                summary=str(primary.get("text") or "")[:4000] if primary else "",
                topics=sorted(set(str(item) for item in primary.get("topics", []))) if primary else [],
                observation_ids=observation_ids,
                field_provenance={"mention": mention, "identity_correction": {
                    "reason": "legacy_huggingface_blog_url_was_model_identity", "source_artifact_id": old_id,
                }},
            )
            artifacts.append(target)
            artifacts_by_id[target_id] = target
            created += 1
        elif str(target.get("artifact_type") or "") != "blog":
            target["artifact_type"] = "blog"
            target["canonical_url"] = target_url
            identifiers = dict(target.get("identifiers") or {})
            hf = identifiers.get("huggingface")
            if isinstance(hf, Mapping) and str(hf.get("repo_id") or "").casefold().startswith("blog/"):
                identifiers.pop("huggingface", None)
            target["identifiers"] = identifiers

    removed_aliases = aliases.remove_huggingface_model_aliases_for_artifacts(old_model_ids)
    for old_id, target_id in sorted(target_ids.items()):
        if target_id != old_id:
            aliases.remove_redirect(target_id, expected_to_artifact_id=old_id)
            aliases.add_redirect(
                old_id, target_id, reason="legacy_huggingface_blog_model_identity", created_at=now_utc(),
            )
        aliases.register_alias(
            f"url:{repairs[old_id]}", target_id, resolver="legacy-hf-blog-identity-migration",
            resolver_id=old_id, resolved_at=now_utc(),
        )

    redirected = 0
    reclassified = 0
    for old_id, target_url in sorted(repairs.items()):
        old = artifacts_by_id[old_id]
        target_id = target_ids[old_id]
        target = artifacts_by_id[target_id]
        was_model = old_id in old_model_ids
        old["artifact_type"] = "blog"
        old["canonical_url"] = target_url
        identifiers = dict(old.get("identifiers") or {})
        hf = identifiers.get("huggingface")
        if isinstance(hf, Mapping) and str(hf.get("repo_id") or "").casefold().startswith("blog/"):
            identifiers.pop("huggingface", None)
        old["identifiers"] = identifiers
        if old_id != target_id:
            old["title"] = str(target.get("title") or "")
            old["summary"] = str(target.get("summary") or "")
            old["authors"] = list(target.get("authors", []))
            old["organizations"] = list(target.get("organizations", []))
            old["published_at"] = target.get("published_at")
            old["topics"] = list(target.get("topics", []))
            provenance = dict(old.get("field_provenance") or {})
            provenance["identity_correction"] = {
                "reason": "legacy_huggingface_blog_url_was_model_identity",
                "canonical_artifact_id": target_id,
            }
            provenance["mention"] = {
                "mention_role": "referenced", "mention_origin": "legacy_hf_blog_url_identity",
            }
            old["field_provenance"] = provenance
            redirected += 1
        reclassified += int(was_model)

    store.replace_artifact_records(artifacts)
    audit = audit_huggingface_reserved_namespace_models(store)
    if not audit["passed"]:
        raise ValueError(f"Hugging Face reserved namespace model audit failed: {audit}")
    return {"reclassified": reclassified, "redirected": redirected,
            "canonical_blog_artifacts_created": created, "bogus_model_aliases_removed": removed_aliases,
            "audit": audit}


def _hf_blog_target_url(artifact: Mapping[str, Any], canonical_url: str,
                        observations_by_id: Mapping[str, Mapping[str, Any]]) -> str:
    mention = ((artifact.get("field_provenance") or {}).get("mention") or {})
    provenance = artifact.get("field_provenance") if isinstance(artifact.get("field_provenance"), Mapping) else {}
    legacy_primary = mention.get("mention_role") == "primary" or _has_legacy_rss_primary_provenance(artifact)
    if not legacy_primary:
        return canonical_url
    evidence_ids = set(str(item) for item in artifact.get("observation_ids", []))
    evidence_ids.update(str(value) for value in mention.values() if str(value).startswith("obs-"))
    for name in ("title", "summary"):
        field = provenance.get(name) if isinstance(provenance.get(name), Mapping) else {}
        if field.get("observation_id"):
            evidence_ids.add(str(field["observation_id"]))
    base = urlsplit(canonical_url)
    prefix = base.path.rstrip("/") + "/"
    candidates = []
    for observation_id in evidence_ids:
        observation = observations_by_id.get(observation_id)
        if not observation:
            continue
        metadata = observation.get("metadata") if isinstance(observation.get("metadata"), Mapping) else {}
        entry_url = canonicalize_url(str(metadata.get("entry_url") or ""))
        parts = urlsplit(entry_url)
        same_host = (parts.hostname or "").casefold().removeprefix("www.") == "huggingface.co"
        if same_host and parts.path.startswith(prefix):
            candidates.append(entry_url)
    return sorted(candidates, key=lambda value: (-len(urlsplit(value).path.split("/")), value))[0] if candidates else canonical_url


def _has_legacy_rss_primary_provenance(artifact: Mapping[str, Any]) -> bool:
    provenance = artifact.get("field_provenance") if isinstance(artifact.get("field_provenance"), Mapping) else {}
    for name in ("title", "summary"):
        field = provenance.get(name) if isinstance(provenance.get(name), Mapping) else {}
        if str(field.get("source") or "").casefold() in {"rss", "huggingface"} and field.get("observation_id"):
            return True
    return False


def _is_hf_blog_url(value: str) -> bool:
    parts = urlsplit(value)
    return ((parts.hostname or "").casefold().removeprefix("www.") == "huggingface.co"
            and parts.path.casefold().startswith("/blog/"))


def _repair_truncated_hf_blog_artifacts(store: Any) -> int:
    """Compatibility wrapper; blog identity repair now preserves the old record type."""
    return int(repair_huggingface_blog_identities(store).get("redirected", 0))


def _primary_url(observation: Mapping[str, Any], platform: str) -> str:
    metadata = observation.get("metadata") if isinstance(observation.get("metadata"), Mapping) else {}
    explicit = canonicalize_url(str(metadata.get("entry_url") or ""))
    if explicit:
        return explicit
    urls = sorted({canonicalize_url(str(value)) for value in observation.get("urls", []) if canonicalize_url(str(value))})
    if platform.casefold() == "arxiv":
        arxiv = extract_arxiv_id(" ".join([str(observation.get("title") or ""), str(observation.get("text") or ""), *urls]))
        return f"https://arxiv.org/abs/{arxiv}" if arxiv else ""
    host = "huggingface.co" if platform.casefold() == "huggingface" else "openai.com" if platform.casefold() == "openai" else ""
    candidates = []
    for url in urls:
        parts = urlsplit(url)
        if host and (parts.hostname or "").casefold().removeprefix("www.") == host:
            if host != "huggingface.co" or parts.path.casefold().startswith("/blog/"):
                candidates.append(url)
    if candidates:
        return min(candidates, key=lambda value: (-len([part for part in urlsplit(value).path.split("/") if part]), value))
    return urls[0] if urls else ""
