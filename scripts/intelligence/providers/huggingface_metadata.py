from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from ..repositories.artifacts import ArtifactRepository


ALLOWED_TYPES = {"model": "models", "dataset": "datasets", "space": "spaces"}
EXPAND_FIELDS = ("author", "createdAt", "lastModified", "pipeline_tag", "tags", "cardData")


class HuggingFaceMetadataProvider:
    """Bounded metadata-only reader for exact Hub repository identifiers."""

    def __init__(self, cache_dir: str | Path, *, transport: Callable[[str], Mapping[str, Any]] | None = None):
        self.cache_dir = Path(cache_dir)
        self.transport = transport or self._request_json
        self.api_requests = 0
        self.cache_hits = 0

    def get(self, artifact_type: str, repo_id: str) -> dict[str, Any] | None:
        if artifact_type not in ALLOWED_TYPES or not _valid_repo_id(repo_id):
            raise ValueError("Hugging Face enrichment requires an exact model, dataset, or space repo ID")
        cache_path = self.cache_dir / f"{_key(artifact_type, repo_id)}.json"
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if cached.get("repo_id", "").casefold() == repo_id.casefold() and cached.get("artifact_type") == artifact_type:
                    self.cache_hits += 1
                    return dict(cached["metadata"])
            except (OSError, ValueError, KeyError, TypeError):
                pass
        endpoint = f"https://huggingface.co/api/{ALLOWED_TYPES[artifact_type]}/{quote(repo_id, safe='/')}"
        query = urlencode([("expand[]", field) for field in EXPAND_FIELDS])
        self.api_requests += 1
        try:
            response = self.transport(f"{endpoint}?{query}")
        except (HTTPError, URLError, TimeoutError, OSError):
            return None
        metadata = _select_metadata(response, repo_id)
        if metadata is None:
            return None
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"repo_id": repo_id, "artifact_type": artifact_type,
                                         "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                         "metadata": metadata}, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                              encoding="utf-8")
        return metadata

    @staticmethod
    def _request_json(url: str) -> Mapping[str, Any]:
        request = Request(url, headers={"User-Agent": "bubblevan-research-intelligence/1.0", "Accept": "application/json"})
        with urlopen(request, timeout=20) as response:
            value = json.loads(response.read().decode("utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError("Hub metadata response must be an object")
        return value


def select_huggingface_artifacts(store: Any, *, limit: int, benchmark_pool: set[str] | None = None) -> list[dict[str, Any]]:
    if limit < 1 or limit > 20:
        raise ValueError("HF metadata enrichment limit must be between 1 and 20")
    benchmark_pool = benchmark_pool or set()
    artifacts = list(ArtifactRepository(store).iter_canonical())
    graph_path = store.directory / "graph_edges.jsonl"
    high_signal_refs: set[str] = set()
    if graph_path.exists():
        for line in graph_path.read_text(encoding="utf-8").splitlines():
            try:
                edge = json.loads(line)
            except ValueError:
                continue
            if edge.get("predicate") == "references" and str(edge.get("subject_id", "")).startswith("art-"):
                high_signal_refs.add(str(edge.get("object_id") or ""))
    candidates = []
    for artifact in artifacts:
        kind = str(artifact.get("artifact_type") or "")
        if kind not in ALLOWED_TYPES:
            continue
        repo_id = _repo_id(artifact)
        if not _valid_repo_id(repo_id):
            continue
        if (artifact.get("provider_metadata") or {}).get("huggingface"):
            continue
        aid = str(artifact.get("artifact_id") or "")
        mention = (artifact.get("field_provenance") or {}).get("mention") or {}
        if mention.get("mention_origin") == "legacy_hf_blog_url_identity":
            continue
        primary = mention.get("mention_role") == "primary"
        multiple = len(set(artifact.get("observation_ids", []))) > 1
        in_pool = aid in benchmark_pool
        referenced = aid in high_signal_refs
        priority = 0 if primary else 1 if multiple else 2 if in_pool else 3 if referenced else 4
        candidates.append((priority, aid, artifact, repo_id))
    candidates.sort(key=lambda item: (item[0], item[1]))
    return [{"artifact": artifact, "repo_id": repo_id, "priority": priority}
            for priority, _aid, artifact, repo_id in candidates[:limit]]


def enrich_huggingface_metadata(store: Any, provider: HuggingFaceMetadataProvider, *, limit: int,
                                benchmark_pool: set[str] | None = None) -> dict[str, Any]:
    from ..artifacts import upsert_artifact_record

    selected = select_huggingface_artifacts(store, limit=limit, benchmark_pool=benchmark_pool)
    metadata_found = 0
    updated = 0
    for item in selected:
        artifact = dict(item["artifact"])
        metadata = provider.get(str(artifact["artifact_type"]), str(item["repo_id"]))
        if metadata is None:
            continue
        metadata_found += 1
        card = metadata.get("card") if isinstance(metadata.get("card"), Mapping) else {}
        name = str(card.get("model_name") or "").strip()
        if name and not str(artifact.get("title") or "").strip():
            artifact["title"] = name
            artifact.setdefault("field_provenance", {})["title"] = {
                "source": "huggingface_hub_api", "observation_id": None, "repo_id": item["repo_id"],
            }
        description = str(card.get("description") or "").strip()[:4000]
        if description and not str(artifact.get("summary") or "").strip():
            artifact["summary"] = description
            artifact.setdefault("field_provenance", {})["summary"] = {
                "source": "huggingface_hub_api", "observation_id": None, "repo_id": item["repo_id"],
            }
        current = dict((artifact.get("provider_metadata") or {}).get("huggingface") or {})
        current.update({key: value for key, value in metadata.items() if key != "card"})
        current["card"] = {key: value for key, value in card.items() if key in {"model_name", "description"}}
        artifact["provider_metadata"] = {**dict(artifact.get("provider_metadata") or {}), "huggingface": current}
        upsert_artifact_record(artifact, store, resolver="huggingface-hub", resolver_id=str(item["repo_id"]))
        updated += 1
    return {"limit": limit, "selected": len(selected), "metadata_found": metadata_found, "artifacts_updated": updated,
            "api_requests": provider.api_requests, "cache_hits": provider.cache_hits,
            "selection_priority_counts": {str(priority): sum(item["priority"] == priority for item in selected)
                                          for priority in range(5)}}


def _select_metadata(value: Mapping[str, Any], requested_repo: str) -> dict[str, Any] | None:
    response_id = str(value.get("id") or "")
    if response_id.casefold() != requested_repo.casefold():
        return None
    raw_card = value.get("cardData") if isinstance(value.get("cardData"), Mapping) else {}
    card = {key: str(raw_card[key])[:4000] for key in ("model_name", "description") if raw_card.get(key)}
    result = {"repo_id": response_id, "author": str(value.get("author") or "") or None,
              "created_at": value.get("createdAt"), "last_modified": value.get("lastModified"),
              "pipeline_tag": str(value.get("pipeline_tag") or "") or None,
              "tags": sorted({str(item) for item in value.get("tags", []) if isinstance(item, (str, int, float))}),
              "card": card}
    return result


def _repo_id(artifact: Mapping[str, Any]) -> str:
    value = (artifact.get("identifiers") or {}).get("huggingface")
    if isinstance(value, Mapping):
        return str(value.get("repo_id") or "")
    return str(value or "")


def _valid_repo_id(value: str) -> bool:
    parts = value.split("/")
    return bool(value and len(value) <= 200 and len(parts) == 2
                and all(part and part not in {".", ".."} for part in parts)
                and parts[0].casefold() not in {"blog", "datasets", "spaces", "models", "papers", "api"})


def _key(kind: str, repo_id: str) -> str:
    return hashlib.sha256(f"{kind}:{repo_id.casefold()}".encode("utf-8")).hexdigest()
