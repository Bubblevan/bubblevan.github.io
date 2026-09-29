from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


class BrowserStatus:
    READY = "ready"
    CONTENT_READABLE = "content_readable"
    LOGIN_REQUIRED = "login_required"
    CHALLENGE_REQUIRED = "challenge_required"
    RELAY_UNAVAILABLE = "relay_unavailable"
    DOM_CHANGED = "dom_changed"
    NOT_FOUND = "not_found"
    PARTIAL = "partial"
    COMPLETED = "completed"


@dataclass
class SocialItem:
    platform: str
    object_id: str
    canonical_url: str
    record: Mapping[str, Any]
    status: str = BrowserStatus.CONTENT_READABLE
    diagnostics: dict[str, Any] = field(default_factory=dict)


class InteractiveAcquirer(Protocol):
    platform: str

    def probe(self, url: str) -> Mapping[str, Any]: ...

    def discover(self, url: str, *, limit: int = 20) -> Mapping[str, Any]: ...

    def acquire(self, url: str) -> SocialItem: ...
