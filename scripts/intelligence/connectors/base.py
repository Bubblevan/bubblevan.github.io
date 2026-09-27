from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol


class ConnectorFailure(RuntimeError):
    """A source-scoped connector failure safe to report without provider payloads."""

    def __init__(self, message: str = "connector fetch failed", *, cause_class: str | None = None):
        super().__init__(message)
        self.cause_class = cause_class or type(self).__name__


class ConnectorDeferred(ConnectorFailure):
    """A source-scoped failure with an optional provider-directed retry deadline."""

    def __init__(
        self,
        message: str = "connector deferred by provider",
        *,
        retry_at: str | None = None,
        retry_after_seconds: float | None = None,
    ):
        super().__init__(message)
        self.retry_at = retry_at
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class ConnectorSpec:
    connector_id: str
    version: str
    modes: tuple[str, ...]
    capabilities: frozenset[str]
    requires_auth: bool = False
    supports_incremental: bool = False


@dataclass
class ConnectorCheckpoint:
    cursor: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    high_watermark: str | None = None
    last_success_at: str | None = None


@dataclass
class FetchResult:
    observations: list[dict[str, Any]]
    next_checkpoint: ConnectorCheckpoint
    exhausted: bool = True
    diagnostics: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConnectorContext:
    store: Any = None
    http: Any = None
    environment: Mapping[str, str] = field(default_factory=dict)
    import_payload: Mapping[str, Any] | None = None
    now: Callable[[], str] = lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    fault_injector: Callable[[str], None] | None = None


class Connector(Protocol):
    spec: ConnectorSpec

    def fetch(
        self,
        source: dict[str, Any],
        checkpoint: ConnectorCheckpoint | None,
        context: ConnectorContext,
    ) -> FetchResult: ...
