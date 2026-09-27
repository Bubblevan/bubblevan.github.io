from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time
from typing import Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HttpTransportError(RuntimeError):
    """Network error with no URL, headers, or response body that could hold secrets."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""


class Transport(Protocol):
    def send(self, url: str, headers: Mapping[str, str], timeout: float) -> HttpResponse: ...


class UrllibTransport:
    def send(self, url: str, headers: Mapping[str, str], timeout: float) -> HttpResponse:
        request = Request(url, headers=dict(headers), method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:
                return HttpResponse(response.status, dict(response.headers.items()), response.read())
        except HTTPError as response:
            return HttpResponse(response.code, dict(response.headers.items()), b"")
        except (URLError, TimeoutError, OSError) as exc:
            raise HttpTransportError("HTTP request failed") from None


class SharedHttpClient:
    RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    def __init__(
        self,
        transport: Transport | None = None,
        *,
        timeout: float = 20,
        user_agent: str = "BubblevanResearchIntelligence/1.0 (+https://github.com/Bubblevan/bubblevan.github.io)",
        max_attempts: int = 3,
        max_retry_wait: float = 60,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.transport = transport or UrllibTransport()
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_attempts = max_attempts
        self.max_retry_wait = max_retry_wait
        self.sleep = sleep
        self.now = now

    def get(self, url: str, *, headers: Mapping[str, str] | None = None) -> HttpResponse:
        request_headers = {"User-Agent": self.user_agent, "Accept": "*/*", **dict(headers or {})}
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.transport.send(url, request_headers, self.timeout)
            except (HttpTransportError, TimeoutError, OSError):
                if attempt == self.max_attempts:
                    raise HttpTransportError("HTTP request failed") from None
                self.sleep(min(2 ** (attempt - 1), 8))
                continue
            if response.status not in self.RETRYABLE_STATUS or attempt == self.max_attempts:
                return response
            if response.status == 429:
                delay = self._retry_after(response.headers.get("Retry-After"))
                if delay is None:
                    delay = min(2 ** (attempt - 1), 8)
                # If the server asks for a long wait, defer this poll instead of retrying early.
                if delay > self.max_retry_wait:
                    return response
            else:
                delay = min(2 ** (attempt - 1), 8)
            self.sleep(delay)
        raise AssertionError("bounded request loop ended unexpectedly")

    def diagnostics(self, response: HttpResponse) -> dict[str, str | int]:
        wanted = {
            "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-used",
            "x-ratelimit-reset", "retry-after", "etag", "last-modified",
        }
        values = {str(key).casefold(): str(value) for key, value in response.headers.items()}
        result: dict[str, str | int] = {"status": response.status}
        result.update({key: values[key] for key in sorted(wanted) if key in values})
        return result

    def _retry_after(self, value: str | None) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value.strip()))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
            except (TypeError, ValueError, OverflowError):
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0.0, (parsed - self.now()).total_seconds())
