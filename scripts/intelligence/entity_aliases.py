from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from .schema_validator import validate_record


ALIAS_SCHEMA = "bubblevan/intelligence-entity-alias/v1"
REDIRECT_SCHEMA = "bubblevan/intelligence-entity-redirect/v1"
_ENTITY_ID = re.compile(r"^ent-[0-9a-f]{24}$")
_ALIAS_PREFIXES = {
    "semantic-scholar-author", "openalex-author", "orcid", "github-user", "github-org",
    "openalex-institution", "ror", "openalex-source", "issn",
}


def normalize_entity_alias(value: str) -> str:
    prefix, separator, raw = str(value or "").strip().partition(":")
    prefix = prefix.casefold()
    raw = raw.strip()
    if not separator or prefix not in _ALIAS_PREFIXES or not raw or any(char.isspace() for char in raw):
        raise ValueError("unsupported exact entity alias")
    if prefix == "orcid":
        raw = raw.removeprefix("https://orcid.org/").removeprefix("http://orcid.org/")
        compact = raw.replace("-", "").upper()
        if not re.fullmatch(r"\d{15}[\dX]", compact):
            raise ValueError("invalid ORCID alias")
        raw = "-".join((compact[:4], compact[4:8], compact[8:12], compact[12:]))
    elif prefix == "ror":
        raw = raw.removeprefix("https://ror.org/").casefold()
        if not re.fullmatch(r"0[a-hj-km-np-tv-z0-9]{6}[0-9]{2}", raw):
            raise ValueError("invalid ROR alias")
    elif prefix in {"openalex-author", "openalex-institution", "openalex-source"}:
        if raw.startswith("https://openalex.org/"):
            raw = raw.rsplit("/", 1)[-1]
        code = {"openalex-author": "A", "openalex-institution": "I", "openalex-source": "S"}[prefix]
        if not re.fullmatch(code + r"\d+", raw, re.IGNORECASE):
            raise ValueError(f"invalid {prefix} alias")
        raw = raw.upper()
    elif prefix in {"github-user", "github-org"}:
        if not raw.isdigit():
            raise ValueError(f"{prefix} requires a numeric GitHub ID")
    elif prefix == "issn":
        raw = raw.upper()
        if not re.fullmatch(r"\d{4}-?\d{3}[\dX]", raw):
            raise ValueError("invalid ISSN alias")
        raw = raw.replace("-", "")
        raw = f"{raw[:4]}-{raw[4:]}"
    else:
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,120}", raw):
            raise ValueError(f"invalid {prefix} alias")
        raw = raw.casefold()
    return f"{prefix}:{raw}"


class EntityAliases:
    """Exact provider identifier map and redirects; names are never alias keys."""

    def __init__(self, directory: Path | str):
        self.directory = Path(directory)
        self.alias_path = self.directory / "entity_aliases.jsonl"
        self.redirect_path = self.directory / "entity_redirects.jsonl"

    def resolve_alias(self, key: str) -> str | None:
        normalized = normalize_entity_alias(key)
        rows = self._read_aliases()
        found = sorted({
            self.resolve_entity_id(str(row["entity_id"]))
            for row in rows if row["alias_key"] == normalized
        })
        if len(found) > 1:
            raise ValueError(f"entity alias maps to conflicting canonical ids: {normalized}")
        return found[0] if found else None

    def register_alias(
        self,
        key: str,
        entity_id: str,
        *,
        provider: str,
        provider_record_id: str,
        resolved_at: str,
    ) -> dict[str, Any]:
        normalized = normalize_entity_alias(key)
        if not _ENTITY_ID.fullmatch(entity_id):
            raise ValueError("invalid entity id for alias")
        root = self.resolve_entity_id(entity_id)
        current = self.resolve_alias(normalized)
        if current and current != root:
            raise ValueError(f"exact entity alias conflict: {normalized}")
        record = {
            "schema": ALIAS_SCHEMA,
            "alias_key": normalized,
            "entity_id": root,
            "evidence": {
                "provider": str(provider),
                "provider_record_id": str(provider_record_id),
                "resolved_at": _timestamp(resolved_at),
            },
        }
        validate_record("entity_alias", record)
        rows = self._read_aliases()
        prior = next((row for row in rows if row["alias_key"] == normalized), None)
        if prior:
            if self.resolve_entity_id(str(prior["entity_id"])) != root:
                raise ValueError(f"exact entity alias conflict: {normalized}")
            return prior
        rows.append(record)
        self._atomic_jsonl(self.alias_path, sorted(rows, key=lambda item: item["alias_key"]))
        return record

    def resolve_entity_id(self, entity_id: str) -> str:
        if not _ENTITY_ID.fullmatch(entity_id):
            raise ValueError("invalid entity_id")
        rows = self._read_redirects()
        redirects = {row["from_entity_id"]: row["to_entity_id"] for row in rows}
        trail: list[str] = []
        seen: set[str] = set()
        current = entity_id
        while current in redirects:
            if current in seen:
                raise ValueError("entity redirect cycle detected")
            seen.add(current)
            trail.append(current)
            current = redirects[current]
        if current in seen:
            raise ValueError("entity redirect cycle detected")
        if trail:
            by_source = {row["from_entity_id"]: row for row in rows}
            for source in trail:
                by_source[source]["to_entity_id"] = current
            self._atomic_jsonl(self.redirect_path, sorted(by_source.values(), key=lambda item: item["from_entity_id"]))
        return current

    def add_redirect(self, from_entity_id: str, to_entity_id: str, *, provider: str, provider_record_id: str, created_at: str) -> dict[str, Any]:
        if not _ENTITY_ID.fullmatch(from_entity_id) or not _ENTITY_ID.fullmatch(to_entity_id):
            raise ValueError("invalid entity redirect id")
        if from_entity_id == to_entity_id:
            raise ValueError("entity redirect cannot target itself")
        target = self.resolve_entity_id(to_entity_id)
        source_root = self.resolve_entity_id(from_entity_id)
        if source_root == target:
            existing = next((row for row in self._read_redirects() if row["from_entity_id"] == from_entity_id), None)
            if existing:
                return existing
            raise ValueError("entity redirect would create a cycle or redundant redirect")
        rows = self._read_redirects()
        prior = next((row for row in rows if row["from_entity_id"] == from_entity_id), None)
        if prior:
            if self.resolve_entity_id(str(prior["to_entity_id"])) != target:
                raise ValueError("entity redirect conflict")
            return prior
        record = {
            "schema": REDIRECT_SCHEMA,
            "from_entity_id": from_entity_id,
            "to_entity_id": target,
            "reason": "exact_provider_equivalence",
            "provider": str(provider),
            "provider_record_id": str(provider_record_id),
            "created_at": _timestamp(created_at),
        }
        rows.append(record)
        self._atomic_jsonl(self.redirect_path, sorted(rows, key=lambda item: item["from_entity_id"]))
        return record

    def _read_aliases(self) -> list[dict[str, Any]]:
        rows = self._read(self.alias_path)
        for row in rows:
            validate_record("entity_alias", row)
            if normalize_entity_alias(str(row["alias_key"])) != row["alias_key"]:
                raise ValueError("entity alias store contains a non-canonical alias")
        if len({row["alias_key"] for row in rows}) != len(rows):
            raise ValueError("entity alias store contains duplicate keys")
        return rows

    def _read_redirects(self) -> list[dict[str, Any]]:
        rows = self._read(self.redirect_path)
        for row in rows:
            if (
                row.get("schema") != REDIRECT_SCHEMA
                or not _ENTITY_ID.fullmatch(str(row.get("from_entity_id") or ""))
                or not _ENTITY_ID.fullmatch(str(row.get("to_entity_id") or ""))
                or row.get("reason") != "exact_provider_equivalence"
            ):
                raise ValueError("corrupt entity redirect store")
            _timestamp(str(row.get("created_at") or ""))
            if row["from_entity_id"] == row["to_entity_id"]:
                raise ValueError("entity redirect cannot target itself")
        if len({row["from_entity_id"] for row in rows}) != len(rows):
            raise ValueError("entity redirect store contains duplicate sources")
        redirects = {str(row["from_entity_id"]): str(row["to_entity_id"]) for row in rows}
        for start in redirects:
            seen: set[str] = set()
            current = start
            while current in redirects:
                if current in seen:
                    raise ValueError("entity redirect cycle detected")
                seen.add(current)
                current = redirects[current]
        return rows

    @staticmethod
    def _read(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        result = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        raise ValueError
                    result.append(item)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"corrupt entity identity store: {path.name}") from exc
        return result

    @staticmethod
    def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        _atomic_bytes(path, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows).encode("utf-8"))


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid entity identity timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("entity identity timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
