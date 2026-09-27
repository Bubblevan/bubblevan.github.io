from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml


CATALOG = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "topics.yaml"


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def topic_aliases(path: Path | str = CATALOG) -> dict[str, str]:
    payload: Any = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for topic in payload.get("topics", []) if isinstance(payload, dict) else []:
        if not isinstance(topic, dict):
            continue
        identifier = str(topic.get("topic_id") or "").strip()
        if not identifier:
            continue
        for value in [identifier, topic.get("name"), *(topic.get("aliases") or [])]:
            key = _key(value)
            if key:
                previous = result.get(key)
                if previous and previous != identifier:
                    raise ValueError(f"topic alias collision for {value!r}: {previous} / {identifier}")
                result[key] = identifier
    return result


def map_topics(values: list[str], path: Path | str = CATALOG) -> list[str]:
    """Map exact topic names and aliases; unknown labels remain only in native_tags."""
    aliases = topic_aliases(path)
    return sorted({aliases[key] for value in values if (key := _key(value)) in aliases})
