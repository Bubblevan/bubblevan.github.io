from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .artifacts import materialize_artifact_candidates
from .canonicalize import canonicalize_url, extract_artifact_candidates
from .ids import observation_id
from .models import new_observation, new_source, parse_datetime
from .topics import map_topics


def bridge_capture(capture: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convert only PKB link/bookmark captures into a source and observation."""
    type_hint = str(capture.get("type_hint", ""))
    if type_hint not in {"link", "bookmark"}:
        raise ValueError("only PKB link/bookmark captures can bridge to an observation")
    capture_id = str(capture.get("capture_id", "")).strip()
    if not capture_id:
        raise ValueError("capture record requires capture_id")

    source_platform = str(capture.get("source_platform") or "unknown").strip()
    source_agent = str(capture.get("source_agent") or "manual").strip()
    source_channel = str(capture.get("source_channel") or "cli").strip()
    source_identity = f"pkb|{source_platform}|{source_agent}|{source_channel}"
    source = new_source(
        identity=source_identity,
        source_type="platform",
        platform="bubblevan-pkb",
        name=f"PKB capture ({source_agent})",
        external_ids={"platform": source_platform, "channel": source_channel},
        connector="pkb-capture",
        mode="manual",
        created_at=str(capture.get("created_at") or ""),
    )

    raw_urls = capture.get("urls", [])
    if not isinstance(raw_urls, list):
        raise ValueError("capture urls must be an array")
    raw_topics = capture.get("topics", [])
    if not isinstance(raw_topics, list):
        raise ValueError("capture topics must be an array")
    urls = sorted(
        {
            canonicalize_url(str(value))
            for value in raw_urls
            if isinstance(value, str) and canonicalize_url(value)
        }
    )
    title = str(capture.get("title") or "").strip()
    text = str(capture.get("text") or "").strip()
    native_tags = [str(topic).strip() for topic in raw_topics if str(topic).strip()]
    observed_at = parse_datetime(capture.get("created_at"), default_now=True)
    candidates = extract_artifact_candidates(" ".join([title, text]), urls)
    obs = new_observation(
        identity=f"bubblevan-pkb|{capture_id}",
        source_id=source["source_id"],
        platform="bubblevan-pkb",
        platform_object_id=capture_id,
        kind="capture",
        title=title,
        text=text,
        urls=urls,
        media=[],
        published_at=None,
        observed_at=observed_at,
        topics=map_topics(native_tags),
        native_tags=native_tags,
        provenance={
            "retrieval_mode": "manual",
            "evidence_level": "source_text",
            "source_url": urls[0] if urls else "",
            "collector": "scripts.pkb.capture",
        },
        artifact_candidates=candidates,
    )
    # Keep the identity derivation explicit and stable even if the factory changes.
    obs["observation_id"] = observation_id(f"bubblevan-pkb|{capture_id}")
    return source, obs


def ingest_capture(capture: Mapping[str, Any], store: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    source, observation = bridge_capture(capture)
    source = store.upsert_source(source)
    store.append_observation(observation)
    materialize_artifact_candidates(observation, store)
    return source, observation
