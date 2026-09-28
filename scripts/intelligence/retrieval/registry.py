from __future__ import annotations

from typing import Any

from .base import Retriever


class RetrieverRegistry:
    def __init__(self) -> None:
        self._items: dict[str, Retriever] = {}

    def register(self, retriever: Retriever) -> None:
        route = retriever.spec.route
        if route in self._items:
            raise ValueError(f"retriever route already registered: {route}")
        self._items[route] = retriever

    def get(self, route: str) -> Retriever:
        try:
            return self._items[route]
        except KeyError as exc:
            raise ValueError(f"unknown retrieval route: {route}") from exc

    def routes(self) -> list[str]:
        return sorted(self._items)

    def versions(self) -> dict[str, Any]:
        return {name: self._items[name].spec.version for name in sorted(self._items)}
