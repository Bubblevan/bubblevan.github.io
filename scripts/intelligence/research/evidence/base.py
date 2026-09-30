from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EvidenceBudget:
    max_retrieved_artifacts: int = 20
    max_evidence_artifacts: int = 12
    max_evidence_refs: int = 50
    max_refs_per_artifact: int = 6
    max_evidence_chars: int = 80_000


class EvidenceBackend(Protocol):
    def gather(self, question: str, artifact_ids: list[str], budget: EvidenceBudget) -> list[dict]: ...
