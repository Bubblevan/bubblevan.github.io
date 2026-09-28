from __future__ import annotations

from collections import Counter
from typing import Any, Mapping
from urllib.parse import urlsplit

from .artifacts import materialize_artifact_candidates
from .aliases import ArtifactAliases
from .canonicalize import artifact_identity, canonicalize_url, extract_arxiv_id
from .ids import artifact_id
from .runner import load_source_catalog


def rematerialize_primary_artifacts(store: Any) -> dict[str, Any]:
    """Rebuild RSS primary Artifact records from local Observations, without network access."""
    restored_models = _restore_misparsed_hf_model_identities(store)
    repaired = _repair_truncated_hf_blog_artifacts(store)
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
        policy = config.get("artifact_policy") or {}
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
    return {"network_requests": 0, "observations_seen": counts.get("materialized", 0) + counts.get("already_materialized", 0) + counts.get("skipped_missing_identity", 0),
            "artifacts_touched": len(artifact_ids), "repaired_truncated_hf_blog_artifacts": repaired,
            "restored_legacy_hf_model_ids": restored_models,
            "counts": dict(sorted(counts.items()))}


def _restore_misparsed_hf_model_identities(store: Any) -> int:
    """Split old HF blog URL aliases from model IDs created by the former URL parser."""
    aliases = ArtifactAliases(store.directory)
    artifacts = list(store.iter_records("artifact"))
    restored = 0
    restored_ids: set[str] = set()
    blog_urls: set[str] = set()
    for artifact in artifacts:
        if artifact.get("artifact_type") != "blog":
            continue
        canonical_url = canonicalize_url(str(artifact.get("canonical_url") or ""))
        parts = urlsplit(canonical_url)
        if (parts.hostname or "").casefold() != "huggingface.co" or not parts.path.casefold().startswith("/blog/"):
            continue
        value = (artifact.get("identifiers") or {}).get("huggingface")
        if not isinstance(value, Mapping):
            continue
        repo_type = str(value.get("repo_type") or "model").casefold()
        repo_id = str(value.get("repo_id") or "").strip()
        if repo_type != "model" or not repo_id or artifact_id(f"huggingface:model:{repo_id}") != str(artifact["artifact_id"]):
            continue

        # The old exact Hugging Face identity remains a graph object. Remove
        # URL aliases and redirects that incorrectly made the blog entry that model.
        restored_ids.add(str(artifact["artifact_id"]))
        blog_urls.add(canonical_url)

        mention = dict((artifact.get("field_provenance") or {}).get("mention") or {})
        mention.update({"mention_role": "referenced", "mention_origin": "legacy_hf_blog_url_identity"})
        artifact["artifact_type"] = "model"
        artifact["canonical_url"] = f"https://huggingface.co/{repo_id}"
        artifact["title"] = repo_id
        artifact["summary"] = ""
        artifact["authors"] = []
        artifact["organizations"] = []
        artifact["published_at"] = None
        artifact["topics"] = []
        provenance = dict(artifact.get("field_provenance") or {})
        provenance.update({
            "title": {"source": "huggingface_repo_id", "repo_id": repo_id},
            "canonical_url": {"source": "huggingface_repo_id", "repo_id": repo_id},
            "summary": {"source": "cleared_misparsed_feed_summary"},
            "authors": {"source": "cleared_misparsed_feed_authors"},
            "published_at": {"source": "cleared_misparsed_feed_publication_time"},
            "topics": {"source": "cleared_misparsed_feed_topics"},
            "mention": mention,
        })
        artifact["field_provenance"] = provenance
        restored += 1
    if restored:
        aliases.remove_huggingface_blog_aliases_for_artifacts(restored_ids, canonical_urls=blog_urls)
        store.replace_artifact_records(artifacts)
    return restored


def _repair_truncated_hf_blog_artifacts(store: Any) -> int:
    aliases = ArtifactAliases(store.directory)
    observations = {str(row["observation_id"]): row for row in store.iter_records("observation")}
    artifacts = list(store.iter_records("artifact"))
    repaired = 0
    for artifact in artifacts:
        if artifact.get("artifact_type") != "blog":
            continue
        canonical_url = canonicalize_url(str(artifact.get("canonical_url") or ""))
        parts = urlsplit(canonical_url)
        if (parts.hostname or "").casefold() != "huggingface.co" or not parts.path.casefold().startswith("/blog/"):
            continue
        mention = ((artifact.get("field_provenance") or {}).get("mention") or {})
        if mention.get("mention_role") != "primary":
            continue
        observation = observations.get(str(mention.get("observation_id") or ""))
        if not observation or canonical_url in set(observation.get("urls", [])):
            continue
        primary_url = _primary_url(observation, "huggingface")
        if primary_url and primary_url == canonical_url:
            # This is the correctly materialized primary blog Artifact. Historical
            # Observation candidates may still describe the same URL as a model.
            continue
        if not primary_url or not primary_url.startswith(canonical_url.rstrip("/") + "/"):
            # Only repair a provably truncated old Hugging Face blog path. A
            # different URL may be a valid linked object and must keep its identity.
            continue
        old_candidate = next((item for item in observation.get("artifact_candidates", [])
                              if isinstance(item, Mapping) and item.get("artifact_type") == "model"
                              and canonicalize_url(str(item.get("canonical_url") or "")) == canonical_url), None)
        if old_candidate is None:
            continue
        if primary_url and primary_url != canonical_url:
            intended_id = artifact_id(artifact_identity({
                "artifact_type": "blog", "canonical_url": primary_url, "identifiers": {},
            }))
            aliases.remove_url_aliases_below(
                canonical_url, expected_artifact_id=str(artifact["artifact_id"]),
            )
            aliases.remove_redirect(
                intended_id, expected_to_artifact_id=str(artifact["artifact_id"]),
            )
            alias_target = aliases.resolve_alias(f"url:{primary_url}")
            if alias_target == str(artifact["artifact_id"]):
                aliases.remove_alias(f"url:{primary_url}", expected_artifact_id=str(artifact["artifact_id"]))
        # The former URL parser mistook /blog/<namespace> for a model repo and
        # truncated deeper entry URLs. Restore that historical graph node as a
        # referenced model; the next pass creates the actual primary URL identity.
        artifact["artifact_type"] = "model"
        artifact["title"] = ""
        artifact["summary"] = ""
        artifact["authors"] = []
        artifact["published_at"] = None
        artifact["topics"] = sorted(set(str(item) for item in observation.get("topics", [])))
        provenance = dict(artifact.get("field_provenance") or {})
        base = {"source": str(observation.get("platform") or "rss"),
                "observation_id": str(observation["observation_id"])}
        provenance["title"] = base
        provenance["summary"] = base
        provenance.pop("authors", None)
        provenance.pop("published_at", None)
        provenance.pop("topics", None)
        provenance.pop("mention", None)
        artifact["field_provenance"] = provenance
        repaired += 1
    if repaired:
        store.replace_artifact_records(artifacts)
    return repaired


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
