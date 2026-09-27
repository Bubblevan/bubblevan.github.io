from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from .canonicalize import canonicalize_url, extract_arxiv_id, extract_doi, extract_github_repo, extract_huggingface_reference
from .schema_validator import validate_record


ALIAS_SCHEMA = "bubblevan/intelligence-artifact-alias/v1"
REDIRECT_SCHEMA = "bubblevan/intelligence-artifact-redirect/v1"
_ARTIFACT_ID = re.compile(r"^art-[0-9a-f]{24}$")
_SUPPORTED = {"doi", "arxiv", "semantic-scholar", "openalex", "github", "huggingface", "url"}


def normalize_alias_key(value: str) -> str:
    key = str(value or "").strip()
    prefix, sep, raw = key.partition(":")
    prefix = prefix.casefold()
    if not sep or prefix not in _SUPPORTED or not raw.strip():
        raise ValueError(f"unsupported artifact alias: {value!r}")
    if prefix == "doi":
        normalized = extract_doi(raw)
        if not normalized:
            raise ValueError("invalid DOI alias")
        return f"doi:{normalized}"
    if prefix == "arxiv":
        normalized = extract_arxiv_id(raw)
        if not normalized:
            raise ValueError("invalid arXiv alias")
        return f"arxiv:{normalized}"
    if prefix == "github":
        repo = extract_github_repo(raw) or _normalize_repo(raw)
        if not repo:
            raise ValueError("invalid GitHub alias")
        return f"github:{repo}"
    if prefix == "huggingface":
        reference = extract_huggingface_reference(raw)
        if reference:
            repo_type, repo_id = reference
        else:
            repo_type, sep2, repo_id = raw.partition(":")
            if not sep2:
                repo_type, repo_id = "model", raw
            repo_type = repo_type.casefold()
            repo_id = _normalize_repo(repo_id)
        if repo_type not in {"model", "dataset", "space"} or not repo_id:
            raise ValueError("invalid Hugging Face alias")
        return f"huggingface:{repo_type}:{repo_id}"
    if prefix == "url":
        url = canonicalize_url(raw)
        if not url:
            raise ValueError("invalid URL alias")
        return f"url:{url}"
    return f"{prefix}:{raw.strip().casefold()}"


def _normalize_repo(value: str) -> str | None:
    text = value.strip().strip("/")
    if text.endswith(".git"):
        text = text[:-4]
    return text.casefold() if re.fullmatch(r"[^/\s]+/[^/\s]+", text) else None


class ArtifactAliases:
    def __init__(self, directory: Path | str):
        self.directory = Path(directory)
        self.alias_path = self.directory / "artifact_aliases.jsonl"
        self.redirect_path = self.directory / "artifact_redirects.jsonl"

    def resolve_alias(self, alias_key: str) -> str | None:
        key = normalize_alias_key(alias_key)
        found = [record["artifact_id"] for record in self._alias_rows() if record["alias_key"] == key]
        if not found:
            return None
        roots = sorted({self.resolve_artifact_id(item) for item in found})
        if len(roots) != 1:
            raise ValueError(f"alias maps to conflicting artifacts: {key}")
        return roots[0]

    def register_alias(
        self,
        alias_key: str,
        artifact_id: str,
        *,
        resolver: str,
        resolver_id: str,
        resolved_at: str | None = None,
    ) -> dict[str, Any]:
        key = normalize_alias_key(alias_key)
        if not _ARTIFACT_ID.fullmatch(artifact_id):
            raise ValueError("invalid artifact_id for alias")
        existing = self.resolve_alias(key)
        root = self.resolve_artifact_id(artifact_id)
        if existing and existing != root:
            raise ValueError(f"alias conflict for {key}: {existing} != {root}")
        record = {
            "schema": ALIAS_SCHEMA,
            "alias_key": key,
            "artifact_id": root,
            "evidence": {
                "resolver": str(resolver), "resolver_id": str(resolver_id),
                "resolved_at": resolved_at or _now(),
            },
        }
        validate_record("artifact_alias", record)
        rows = self._alias_rows()
        same = next((row for row in rows if row["alias_key"] == key and row["artifact_id"] == root), None)
        if same is None:
            rows.append(record)
            self._atomic_jsonl(self.alias_path, rows)
        return same or record

    def resolve_artifact_id(self, artifact_id: str) -> str:
        if not _ARTIFACT_ID.fullmatch(artifact_id):
            raise ValueError("invalid artifact_id")
        redirect_map: dict[str, str] = {}
        for row in self._redirect_rows():
            source, target = row.get("from_artifact_id"), row.get("to_artifact_id")
            if source == target:
                raise ValueError("artifact redirect cannot target itself")
            redirect_map[str(source)] = str(target)
        trail: list[str] = []
        current = artifact_id
        seen: set[str] = set()
        while current in redirect_map:
            if current in seen:
                raise ValueError("artifact redirect cycle detected")
            seen.add(current)
            trail.append(current)
            current = redirect_map[current]
        if current in seen:
            raise ValueError("artifact redirect cycle detected")
        if trail:
            rows = self._redirect_rows()
            by_source = {row["from_artifact_id"]: row for row in rows}
            changed = False
            for source in trail:
                if by_source[source]["to_artifact_id"] != current:
                    by_source[source]["to_artifact_id"] = current
                    changed = True
            if changed:
                self._atomic_jsonl(self.redirect_path, sorted(by_source.values(), key=lambda row: row["from_artifact_id"]))
        return current

    def add_redirect(self, from_artifact_id: str, to_artifact_id: str, *, reason: str = "identifier_equivalence", created_at: str | None = None) -> dict[str, Any]:
        if not _ARTIFACT_ID.fullmatch(from_artifact_id) or not _ARTIFACT_ID.fullmatch(to_artifact_id):
            raise ValueError("invalid artifact redirect id")
        if from_artifact_id == to_artifact_id:
            raise ValueError("canonical artifact id cannot self-redirect")
        target = self.resolve_artifact_id(to_artifact_id)
        rows = self._redirect_rows()
        prior = next((row for row in rows if row["from_artifact_id"] == from_artifact_id), None)
        if self.resolve_artifact_id(from_artifact_id) == target:
            if prior:
                return prior
            raise ValueError("artifact redirect would create a cycle or redundant canonical edge")
        if target == from_artifact_id:
            raise ValueError("artifact redirect would create a cycle")
        record = {
            "schema": REDIRECT_SCHEMA, "from_artifact_id": from_artifact_id,
            "to_artifact_id": target, "reason": reason, "created_at": created_at or _now(),
        }
        if prior and prior["to_artifact_id"] != target:
            # Existing redirects are immutable unless both resolve to the same root.
            if self.resolve_artifact_id(str(prior["to_artifact_id"])) != target:
                raise ValueError("artifact redirect conflict")
            return prior
        if not prior:
            rows.append(record)
            self._atomic_jsonl(self.redirect_path, sorted(rows, key=lambda row: row["from_artifact_id"]))
        return prior or record

    def _read(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows = []
        try:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError
                rows.append(row)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"corrupt identity index: {path.name}") from exc
        return rows

    def _alias_rows(self) -> list[dict[str, Any]]:
        rows = self._read(self.alias_path)
        for row in rows:
            validate_record("artifact_alias", row)
            if normalize_alias_key(str(row["alias_key"])) != row["alias_key"]:
                raise ValueError("artifact alias index contains a non-canonical alias")
        return rows

    def _redirect_rows(self) -> list[dict[str, Any]]:
        rows = self._read(self.redirect_path)
        for row in rows:
            if (row.get("schema") != REDIRECT_SCHEMA
                    or not _ARTIFACT_ID.fullmatch(str(row.get("from_artifact_id") or ""))
                    or not _ARTIFACT_ID.fullmatch(str(row.get("to_artifact_id") or ""))
                    or not str(row.get("reason") or "").strip()):
                raise ValueError("corrupt artifact redirect index")
            try:
                datetime.fromisoformat(str(row.get("created_at") or "").replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("corrupt artifact redirect timestamp") from exc
            if row["from_artifact_id"] == row["to_artifact_id"]:
                raise ValueError("artifact redirect cannot target itself")
        if len({row["from_artifact_id"] for row in rows}) != len(rows):
            raise ValueError("artifact redirect index has duplicate sources")
        return rows

    @staticmethod
    def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_name = ""
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                             prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
                temp_name = handle.name
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
