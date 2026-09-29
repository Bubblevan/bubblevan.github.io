from __future__ import annotations

from datetime import datetime, timezone
from contextlib import contextmanager
from types import MappingProxyType
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping
from urllib.parse import urlsplit

from .canonicalize import canonicalize_url, extract_arxiv_id, extract_doi, extract_github_repo, extract_huggingface_reference
from .ids import artifact_id
from .schema_validator import validate_record


ALIAS_SCHEMA = "bubblevan/intelligence-artifact-alias/v1"
REDIRECT_SCHEMA = "bubblevan/intelligence-artifact-redirect/v1"
_ARTIFACT_ID = re.compile(r"^art-[0-9a-f]{24}$")
_SUPPORTED = {"doi", "arxiv", "semantic-scholar", "openalex", "openreview", "hf-paper", "github", "huggingface", "url"}


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
        self._alias_batch: list[dict[str, Any]] | None = None
        self._redirect_batch: list[dict[str, Any]] | None = None
        self._alias_dirty = False
        self._redirect_dirty = False
        self._alias_cache: list[dict[str, Any]] | None = None
        self._alias_lookup: dict[str, set[str]] | None = None
        self._alias_record_lookup: dict[tuple[str, str], dict[str, Any]] | None = None
        self._alias_signature: tuple[int, int] | None = None
        self._redirect_cache: list[dict[str, Any]] | None = None
        self._redirect_lookup: dict[str, str] | None = None
        self._redirect_signature: tuple[int, int] | None = None

    @contextmanager
    def bulk_update(self):
        """Keep alias/redirect indexes in memory and atomically write each once."""
        if self._alias_batch is not None or self._redirect_batch is not None:
            raise RuntimeError("nested artifact alias batches are not supported")
        aliases = self._alias_rows()
        redirects = self._redirect_rows()
        self._alias_batch, self._redirect_batch = aliases, redirects
        self._alias_lookup = _alias_lookup(aliases)
        self._alias_record_lookup = _alias_record_lookup(aliases)
        self._redirect_lookup = {str(row["from_artifact_id"]): str(row["to_artifact_id"]) for row in redirects}
        try:
            yield self
        except BaseException:
            self._alias_batch = self._redirect_batch = None
            self._alias_dirty = self._redirect_dirty = False
            self._alias_cache = self._redirect_cache = None
            self._alias_signature = self._redirect_signature = None
            self._alias_lookup = self._redirect_lookup = None
            self._alias_record_lookup = None
            raise
        alias_dirty, redirect_dirty = self._alias_dirty, self._redirect_dirty
        self._alias_batch = self._redirect_batch = None
        self._alias_dirty = self._redirect_dirty = False
        if alias_dirty:
            self._atomic_jsonl(self.alias_path, aliases)
            self._alias_cache = aliases
            self._alias_signature = _file_signature(self.alias_path)
        if redirect_dirty:
            self._atomic_jsonl(self.redirect_path,
                               sorted(redirects, key=lambda row: row["from_artifact_id"]))
            self._redirect_cache = redirects
            self._redirect_signature = _file_signature(self.redirect_path)

    def resolve_alias(self, alias_key: str) -> str | None:
        key = normalize_alias_key(alias_key)
        self._alias_rows()  # detect an external writer between calls
        if self._alias_lookup is None:
            self._alias_lookup = _alias_lookup(self._alias_rows())
        found = self._alias_lookup.get(key, set())
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
        if self._alias_record_lookup is None:
            self._alias_record_lookup = _alias_record_lookup(rows)
        same = self._alias_record_lookup.get((key, root))
        if same is None:
            rows.append(record)
            if self._alias_lookup is not None:
                self._alias_lookup.setdefault(key, set()).add(root)
            self._alias_record_lookup[(key, root)] = record
            if self._alias_batch is not None:
                self._alias_dirty = True
            else:
                self._atomic_jsonl(self.alias_path, rows)
        return same or record

    def remove_alias(self, alias_key: str, *, expected_artifact_id: str) -> int:
        """Remove a known incorrect exact alias without deleting its Artifact record."""
        key = normalize_alias_key(alias_key)
        expected_root = self.resolve_artifact_id(expected_artifact_id)
        rows = self._alias_rows()
        kept = [row for row in rows if not (
            row["alias_key"] == key and self.resolve_artifact_id(str(row["artifact_id"])) == expected_root
        )]
        removed = len(rows) - len(kept)
        if removed:
            self._atomic_jsonl(self.alias_path, kept)
            self._invalidate_alias_cache()
        return removed

    def remove_url_aliases_below(self, parent_url: str, *, expected_artifact_id: str) -> int:
        """Remove descendant URL aliases when an old parser truncated a path."""
        parent = canonicalize_url(parent_url)
        parent_parts = urlsplit(parent)
        parent_root = self.resolve_artifact_id(expected_artifact_id)
        prefix = parent_parts.path.rstrip("/") + "/"
        rows = self._alias_rows()
        kept = []
        removed = 0
        removed_urls: list[str] = []
        for row in rows:
            key = str(row["alias_key"])
            if not key.startswith("url:"):
                kept.append(row)
                continue
            candidate = canonicalize_url(key[4:])
            candidate_parts = urlsplit(candidate)
            same_origin = ((candidate_parts.scheme, (candidate_parts.hostname or "").casefold())
                           == (parent_parts.scheme, (parent_parts.hostname or "").casefold()))
            matches_target = self.resolve_artifact_id(str(row["artifact_id"])) == parent_root
            if same_origin and candidate_parts.path.startswith(prefix) and matches_target:
                removed += 1
                removed_urls.append(candidate)
            else:
                kept.append(row)
        if removed:
            self._atomic_jsonl(self.alias_path, kept)
            self._invalidate_alias_cache()
            redirects = self._redirect_rows()
            removed_sources = {
                artifact_id(f"url:{url}") for url in removed_urls
                if self.resolve_artifact_id(artifact_id(f"url:{url}")) == parent_root
            }
            if removed_sources:
                self._atomic_jsonl(
                    self.redirect_path,
                    [row for row in redirects if row["from_artifact_id"] not in removed_sources],
                )
        return removed

    def remove_huggingface_blog_aliases_for_artifacts(
        self, artifact_ids: set[str], *, canonical_urls: set[str] | None = None,
    ) -> int:
        """Bulk detach old blog URLs from model identities while retaining both records."""
        if not artifact_ids and not canonical_urls:
            return 0
        redirects = self._redirect_rows()
        redirect_map = {str(row["from_artifact_id"]): str(row["to_artifact_id"]) for row in redirects}

        def root(artifact_id: str) -> str:
            trail: set[str] = set()
            current = artifact_id
            while current in redirect_map:
                if current in trail:
                    raise ValueError("artifact redirect cycle detected")
                trail.add(current)
                current = redirect_map[current]
            return current

        target_roots = {root(str(item)) for item in artifact_ids}
        rows = self._alias_rows()
        kept = []
        removed_urls: set[str] = set()
        removed = 0
        for row in rows:
            key = str(row["alias_key"])
            if not key.startswith("url:"):
                kept.append(row)
                continue
            url = canonicalize_url(key[4:])
            parts = urlsplit(url)
            is_blog_url = ((parts.hostname or "").casefold() == "huggingface.co"
                           and parts.path.casefold().startswith("/blog/"))
            if is_blog_url and root(str(row["artifact_id"])) in target_roots:
                removed += 1
                removed_urls.add(url)
            else:
                kept.append(row)
        if canonical_urls:
            for value in canonical_urls:
                url = canonicalize_url(value)
                parts = urlsplit(url)
                if ((parts.hostname or "").casefold() == "huggingface.co"
                        and parts.path.casefold().startswith("/blog/")):
                    removed_urls.add(url)
        if removed:
            self._atomic_jsonl(self.alias_path, kept)
            self._invalidate_alias_cache()
        sources = {artifact_id(f"url:{url}") for url in removed_urls}
        removable = {source for source in sources if root(source) in target_roots}
        if removable:
            self._atomic_jsonl(
                self.redirect_path,
                [row for row in redirects if str(row["from_artifact_id"]) not in removable],
            )
            self._invalidate_redirect_cache()
        return removed

    def remove_huggingface_model_aliases_for_artifacts(self, artifact_ids: set[str]) -> int:
        """Remove reserved /blog paths that were incorrectly registered as model IDs."""
        if not artifact_ids:
            return 0
        rows = self._alias_rows()
        kept = [row for row in rows if not (
            str(row["alias_key"]).startswith("huggingface:model:")
            and str(row["artifact_id"]) in artifact_ids
        )]
        removed = len(rows) - len(kept)
        if removed:
            self._atomic_jsonl(self.alias_path, kept)
            self._invalidate_alias_cache()
        return removed

    def resolve_artifact_id(self, artifact_id: str) -> str:
        if not _ARTIFACT_ID.fullmatch(artifact_id):
            raise ValueError("invalid artifact_id")
        self._redirect_rows()  # detect an external writer between calls
        if self._redirect_lookup is None:
            self._redirect_lookup = {str(row["from_artifact_id"]): str(row["to_artifact_id"])
                                     for row in self._redirect_rows()}
        redirect_map = self._redirect_lookup
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
                if self._redirect_batch is not None:
                    self._redirect_batch[:] = sorted(by_source.values(), key=lambda row: row["from_artifact_id"])
                    self._redirect_dirty = True
                else:
                    self._atomic_jsonl(self.redirect_path, sorted(by_source.values(), key=lambda row: row["from_artifact_id"]))
                    self._redirect_cache = sorted(by_source.values(), key=lambda row: row["from_artifact_id"])
                    self._redirect_signature = _file_signature(self.redirect_path)
                self._redirect_lookup.update({str(source): str(current) for source in trail})
        return current

    def canonical_redirect_map(self) -> Mapping[str, str]:
        """Return a deterministic, flattened read-only redirect view without writing."""
        direct = {str(row["from_artifact_id"]): str(row["to_artifact_id"])
                  for row in self._redirect_rows()}
        flattened: dict[str, str] = {}
        for source in sorted(direct):
            current = source
            seen: set[str] = set()
            while current in direct:
                if current in seen:
                    raise ValueError("artifact redirect cycle detected")
                seen.add(current)
                current = direct[current]
            flattened[source] = current
        return MappingProxyType(dict(sorted(flattened.items())))

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
            if self._redirect_lookup is not None:
                self._redirect_lookup[from_artifact_id] = target
            if self._redirect_batch is not None:
                self._redirect_dirty = True
            else:
                self._atomic_jsonl(self.redirect_path, sorted(rows, key=lambda row: row["from_artifact_id"]))
        return prior or record

    def remove_redirect(self, from_artifact_id: str, *, expected_to_artifact_id: str) -> int:
        """Remove a known bad identity redirect after its evidence is corrected."""
        if not _ARTIFACT_ID.fullmatch(from_artifact_id):
            raise ValueError("invalid artifact redirect id")
        expected_root = self.resolve_artifact_id(expected_to_artifact_id)
        rows = self._redirect_rows()
        target = next((row for row in rows if row["from_artifact_id"] == from_artifact_id), None)
        if not target or self.resolve_artifact_id(str(target["to_artifact_id"])) != expected_root:
            return 0
        kept = [row for row in rows if row["from_artifact_id"] != from_artifact_id]
        self._atomic_jsonl(self.redirect_path, kept)
        self._invalidate_redirect_cache()
        return 1

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

    def _invalidate_alias_cache(self) -> None:
        self._alias_cache = self._alias_lookup = self._alias_record_lookup = None
        self._alias_signature = None

    def _invalidate_redirect_cache(self) -> None:
        self._redirect_cache = None
        self._redirect_lookup = None
        self._redirect_signature = None

    def _alias_rows(self) -> list[dict[str, Any]]:
        if self._alias_batch is not None:
            return self._alias_batch
        signature = _file_signature(self.alias_path)
        if self._alias_cache is None or signature != self._alias_signature:
            rows = self._read(self.alias_path)
            for row in rows:
                validate_record("artifact_alias", row)
                if normalize_alias_key(str(row["alias_key"])) != row["alias_key"]:
                    raise ValueError("artifact alias index contains a non-canonical alias")
            self._alias_cache = rows
            self._alias_signature = signature
            self._alias_lookup = _alias_lookup(rows)
            self._alias_record_lookup = _alias_record_lookup(rows)
        return self._alias_cache

    def _redirect_rows(self) -> list[dict[str, Any]]:
        if self._redirect_batch is not None:
            return self._redirect_batch
        signature = _file_signature(self.redirect_path)
        if self._redirect_cache is None or signature != self._redirect_signature:
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
            self._redirect_cache = rows
            self._redirect_signature = signature
            self._redirect_lookup = None
        rows = self._redirect_cache
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


def _file_signature(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return stat.st_size, stat.st_mtime_ns


def _alias_lookup(rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for row in rows:
        result.setdefault(str(row["alias_key"]), set()).add(str(row["artifact_id"]))
    return result


def _alias_record_lookup(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(str(row["alias_key"]), str(row["artifact_id"])): row for row in rows}
