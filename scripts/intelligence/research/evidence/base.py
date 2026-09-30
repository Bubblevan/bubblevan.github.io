from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EvidenceBudget:
    max_retrieved_artifacts: int = 20
    max_evidence_artifacts: int = 12
    max_evidence_refs: int = 50
    max_refs_per_artifact: int = 6
    max_metadata_refs_per_artifact: int = 1
    max_evidence_chars: int = 80_000


@dataclass(frozen=True)
class ResearchPerspectivePlan:
    """Explicit source perspectives to retrieve alongside the general lane."""

    first_party: bool = True
    curator: bool = False
    discussion: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {"first_party": bool(self.first_party), "curator": bool(self.curator),
                "discussion": bool(self.discussion)}

    @classmethod
    def from_value(cls, value: "ResearchPerspectivePlan | dict | None") -> "ResearchPerspectivePlan":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise TypeError("perspective plan must be an object")
        allowed = {"first_party", "curator", "discussion"}
        if set(value) - allowed:
            raise ValueError("perspective plan contains an unknown lane")
        for key in allowed.intersection(value):
            if not isinstance(value[key], bool):
                raise ValueError(f"perspective plan lane {key!r} must be boolean")
        return cls(first_party=value.get("first_party", True),
                   curator=value.get("curator", False),
                   discussion=value.get("discussion", False))


class EvidenceBackend(Protocol):
    def gather(self, question: str, artifact_ids: list[str], budget: EvidenceBudget) -> list[dict]: ...
