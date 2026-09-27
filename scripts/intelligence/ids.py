from __future__ import annotations

import hashlib
import re
import unicodedata


_SPACE = re.compile(r"\s+")
_NON_SLUG = re.compile(r"[^a-z0-9]+")


def normalize_identity(value: object) -> str:
    """Normalize free-form identity input without changing URL semantics."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    return _SPACE.sub(" ", text).strip().casefold()


def stable_id(prefix: str, namespace: str, identity: object) -> str:
    normalized = normalize_identity(identity)
    if not normalized:
        raise ValueError(f"{namespace} identity must not be empty")
    payload = f"bubblevan/intelligence/{namespace}/v1\0{normalized}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:24]
    return f"{prefix}-{digest}"


def source_id(identity: object) -> str:
    return stable_id("src", "source", identity)


def observation_id(identity: object) -> str:
    return stable_id("obs", "observation", identity)


def artifact_id(identity: object) -> str:
    return stable_id("art", "artifact", identity)


def entity_id(identity: object) -> str:
    return stable_id("ent", "entity", identity)


def feedback_id(identity: object) -> str:
    return stable_id("fb", "feedback", identity)


def topic_slug(value: object) -> str:
    text = normalize_identity(value)
    slug = _NON_SLUG.sub("-", text).strip("-")
    if slug:
        return slug
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"topic-{digest}"


def topic_id(value: object) -> str:
    slug = topic_slug(value)
    return slug if slug.startswith("topic-") else f"topic-{slug}"
