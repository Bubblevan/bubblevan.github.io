from __future__ import annotations

from collections.abc import Iterator, Mapping
import re
from typing import Any

from ..aliases import ArtifactAliases
from ..store import JsonlStore


_ARTIFACT_ID = re.compile(r"^art-[0-9a-f]{24}$")


class ArtifactRepository:
    """Read Artifacts through canonical IDs; raw rows are reserved for migrations/audits."""

    def __init__(self, store: JsonlStore):
        self.store = store
        self.aliases = ArtifactAliases(store.directory)
        self._redirects = self.aliases.canonical_redirect_map()

    def resolve_id(self, artifact_id: str) -> str:
        value = str(artifact_id)
        if not _ARTIFACT_ID.fullmatch(value):
            raise ValueError("invalid artifact_id")
        return self._redirects.get(value, value)

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        wanted = self.resolve_id(artifact_id)
        for row in self.iter_canonical():
            if str(row.get("artifact_id")) == wanted:
                return row
        return None

    def iter_canonical(self) -> Iterator[dict[str, Any]]:
        physical = list(self.store.iter_records("artifact"))
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in physical:
            raw_id = str(row.get("artifact_id") or "")
            canonical_id = self._redirects.get(raw_id, raw_id)
            groups.setdefault(canonical_id, []).append(row)
        for canonical_id in sorted(groups):
            rows = groups[canonical_id]
            rows.sort(key=lambda item: (str(item.get("artifact_id")) != canonical_id,
                                        str(item.get("artifact_id"))))
            canonical = dict(rows[0])
            canonical["artifact_id"] = canonical_id
            yield canonical

    def raw_rows(self) -> list[dict[str, Any]]:
        """Return physical rows explicitly for migration, audit and debugging use."""
        return list(self.store.iter_records("artifact"))
