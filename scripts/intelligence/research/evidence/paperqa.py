from __future__ import annotations

import asyncio
from contextlib import contextmanager
import os
from pathlib import Path
from typing import Any, Mapping

from ...models import now_utc
from ...repositories.artifacts import ArtifactRepository
from ...schema_validator import validate_record
from ...store import JsonlStore
from ..ids import evidence_ref
from .base import EvidenceBudget
from .local_corpus import _safe_url


PAPERQA_MODEL_KEYS = ("RI_PAPERQA_LLM", "RI_PAPERQA_SUMMARY_LLM", "RI_PAPERQA_EMBEDDING")


class PaperQAUnconfigured(RuntimeError):
    pass


def paperqa_model_settings(environ: Mapping[str, str] | None = None) -> dict[str, str] | None:
    env = os.environ if environ is None else environ
    values = {key: str(env.get(key) or "").strip() for key in PAPERQA_MODEL_KEYS}
    if any(not value for value in values.values()):
        return None
    return {"llm": values[PAPERQA_MODEL_KEYS[0]],
            "summary_llm": values[PAPERQA_MODEL_KEYS[1]],
            "embedding": values[PAPERQA_MODEL_KEYS[2]]}


class PaperQA2EvidenceBackend:
    """Optional page-level evidence adapter; only caller-supplied local documents are accepted."""

    def __init__(self, store_dir: str | Path, document_paths: Mapping[str, str | Path],
                 runtime_dir: str | Path | None = None):
        self.store = JsonlStore(store_dir)
        self.artifacts = ArtifactRepository(self.store)
        self.document_paths = {str(key): Path(value).expanduser().resolve() for key, value in document_paths.items()}
        default_runtime = Path(store_dir).resolve().parent / "runtime"
        self.paperqa_home = Path(runtime_dir or default_runtime) / "paperqa"
        self.model_settings = paperqa_model_settings()

    @property
    def is_configured(self) -> bool:
        return self.model_settings is not None

    def gather(self, question: str, artifact_ids: list[str], budget: EvidenceBudget) -> list[dict[str, Any]]:
        if self.model_settings is None:
            raise PaperQAUnconfigured("RI_PAPERQA_LLM, RI_PAPERQA_SUMMARY_LLM and RI_PAPERQA_EMBEDDING are required")
        self.paperqa_home.mkdir(parents=True, exist_ok=True)
        with _paperqa_home(self.paperqa_home):
            try:
                from paperqa import Docs, Settings
            except ImportError as exc:
                raise RuntimeError("PaperQA2 is optional; install requirements-research-paper.txt") from exc
            return self._gather(question, artifact_ids, budget, Docs, Settings)

    def _gather(self, question: str, artifact_ids: list[str], budget: EvidenceBudget,
                docs_type: Any, settings_type: Any) -> list[dict[str, Any]]:
        artifacts = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        results: list[dict[str, Any]] = []
        total_chars = 0
        for requested_id in artifact_ids[:budget.max_evidence_artifacts]:
            artifact_id = self.artifacts.resolve_id(requested_id)
            artifact = artifacts.get(artifact_id)
            if not artifact or artifact.get("artifact_type") not in {"paper", "technical_report"}:
                continue
            path = self.document_paths.get(artifact_id)
            if not path or not path.is_file():
                continue
            if path.stat().st_size > 50 * 1024 * 1024:
                raise ValueError("user-supplied paper file exceeds the 50 MiB processing limit")
            docs = docs_type()
            settings = settings_type(**self.model_settings,
                                     parsing={"use_doc_details": False, "multimodal": False})
            # No path is fetched from Artifact URLs: a file must be supplied explicitly.
            asyncio.run(docs.aadd(str(path), settings=settings))
            answer = asyncio.run(docs.aquery(question, settings=settings))
            contexts = getattr(answer, "contexts", None) or getattr(answer, "context", None) or []
            if not isinstance(contexts, (list, tuple)):
                contexts = [contexts]
            for index, context in enumerate(contexts):
                text = str(getattr(context, "text", None) or getattr(context, "context", None) or "").strip()
                if not text:
                    continue
                remaining = min(20_000, budget.max_evidence_chars - total_chars)
                if remaining <= 0:
                    return results
                text = text[:remaining]
                page = getattr(context, "page", None)
                locator = (f"page-{page}" if page is not None else
                           str(getattr(context, "name", None) or getattr(context, "citation", None)
                               or f"page-or-passage-{index + 1}"))
                row = evidence_ref(artifact_id=artifact_id, observation_id=None, source_id=None,
                                  canonical_url=_safe_url(str(artifact.get("canonical_url") or "")) or None,
                                  title=artifact.get("title"),
                                  published_at=artifact.get("published_at"), locator_type="paper_page",
                                  locator_value=locator, text=text, evidence_type="paper_full_text",
                                  retrieved_at=now_utc())
                validate_record("evidence_ref", row)
                results.append(row)
                total_chars += len(text)
                if len(results) >= budget.max_evidence_refs:
                    return results
        return results


@contextmanager
def _paperqa_home(path: Path):
    previous = os.environ.get("PQA_HOME")
    os.environ["PQA_HOME"] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("PQA_HOME", None)
        else:
            os.environ["PQA_HOME"] = previous
