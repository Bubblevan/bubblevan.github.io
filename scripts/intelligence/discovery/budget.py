from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExpansionBudget:
    max_depth: int = 2
    max_nodes: int = 100
    max_edges: int = 300
    max_candidates: int = 50
    max_references_per_artifact: int = 20
    max_citations_per_artifact: int = 20
    max_recent_works_per_author: int = 10
    max_provider_requests: int = 50
    nodes_visited: int = 0
    edges_traversed: int = 0
    provider_requests: int = 0
    candidates_generated: int = 0
    exhausted: bool = False

    def __post_init__(self) -> None:
        for name in (
            "max_depth", "max_nodes", "max_edges", "max_candidates",
            "max_references_per_artifact", "max_citations_per_artifact",
            "max_recent_works_per_author", "max_provider_requests",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.max_nodes == 0 or self.max_candidates == 0 or self.max_provider_requests == 0:
            raise ValueError("node, candidate, and request budgets must be positive")
        self.max_references_per_artifact = min(self.max_references_per_artifact, 20)
        self.max_citations_per_artifact = min(self.max_citations_per_artifact, 20)
        self.max_recent_works_per_author = min(self.max_recent_works_per_author, 10)

    def request(self) -> bool:
        if self.provider_requests >= self.max_provider_requests:
            self.exhausted = True
            return False
        self.provider_requests += 1
        return True

    def visit_node(self) -> bool:
        if self.nodes_visited >= self.max_nodes:
            self.exhausted = True
            return False
        self.nodes_visited += 1
        return True

    def traverse_edge(self) -> bool:
        if self.edges_traversed >= self.max_edges:
            self.exhausted = True
            return False
        self.edges_traversed += 1
        return True

    def candidate(self) -> bool:
        if self.candidates_generated >= self.max_candidates:
            self.exhausted = True
            return False
        self.candidates_generated += 1
        return True

    def as_dict(self) -> dict[str, int | bool]:
        return {
            "max_depth": self.max_depth,
            "max_nodes": self.max_nodes,
            "max_edges": self.max_edges,
            "max_candidates": self.max_candidates,
            "max_references_per_artifact": self.max_references_per_artifact,
            "max_citations_per_artifact": self.max_citations_per_artifact,
            "max_recent_works_per_author": self.max_recent_works_per_author,
            "max_provider_requests": self.max_provider_requests,
            "nodes_visited": self.nodes_visited,
            "edges_traversed": self.edges_traversed,
            "provider_requests": self.provider_requests,
            "candidates_generated": self.candidates_generated,
            "budget_exhausted": self.exhausted,
        }
