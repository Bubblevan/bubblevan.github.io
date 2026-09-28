from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from .corpus import CorpusSnapshot, RetrievalDocument
from .request import RetrievalRequest


@dataclass(frozen=True)
class RetrieverSpec:
    route: str
    version: str
    independent_local: bool = True
    optional: bool = False


@dataclass
class RetrievalResult:
    route: str
    candidates: list[dict[str, Any]] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)
    status: str = "succeeded"
    reason: str | None = None
    elapsed_ms: float = 0.0


class Retriever(Protocol):
    spec: RetrieverSpec

    def build(self, snapshot: CorpusSnapshot, runtime_dir: str) -> dict[str, Any]: ...

    def retrieve(self, request: RetrievalRequest, *, documents: Sequence[RetrievalDocument], top_k: int) -> RetrievalResult: ...
