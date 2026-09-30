from __future__ import annotations

import hashlib
from typing import Any

from ..ids import stable_id
from ..schema_validator import validate_record


def evidence_ref(*, artifact_id: str, observation_id: str | None, source_id: str | None,
                 canonical_url: str | None, locator_type: str, locator_value: str,
                 text: str, evidence_type: str, retrieved_at: str,
                 title: str | None = None, published_at: str | None = None) -> dict[str, Any]:
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    identity = f"{artifact_id}|{locator_type}|{locator_value}|{text_hash}"
    row = {
        "schema": "bubblevan/evidence-ref/v1",
        "evidence_id": stable_id("ev", "research-evidence", identity),
        "artifact_id": artifact_id,
        "observation_id": observation_id,
        "source_id": source_id,
        "canonical_url": canonical_url,
        "title": title,
        "published_at": published_at,
        "locator": {"type": locator_type, "value": locator_value},
        "text": text,
        "text_sha256": text_hash,
        "evidence_type": evidence_type,
        "retrieved_at": retrieved_at,
    }
    validate_record("evidence_ref", row)
    return row
