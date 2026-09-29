from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
import errno
import http.client
import socket
import ssl
import time
from typing import Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, HTTPHandler, Request, build_opener


class HttpTransportError(RuntimeError):
    """Network error with no URL, headers, or response body that could hold secrets."""

    ALLOWED_CATEGORIES = frozenset({
        "dns_error", "connect_timeout", "read_timeout", "connection_reset",
        "tls_error", "network_unreachable", "connection_refused", "transport_other",
    })

    def __init__(self, category: str = "transport_other"):
        if category not in self.ALLOWED_CATEGORIES:
            category = "transport_other"
        self.category = category
        super().__init__("HTTP request failed")


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
        opener = build_opener(_CategorizedHTTPHandler(),
                              _CategorizedHTTPSHandler(context=ssl.create_default_context()))
        try:
            with opener.open(request, timeout=timeout) as response:
                try:
                    body = response.read()
                except (TimeoutError, OSError, ssl.SSLError) as exc:
                    category = "read_timeout" if isinstance(exc, (TimeoutError, socket.timeout)) else _transport_category(exc)
                    raise HttpTransportError(category) from None
                return HttpResponse(response.status, dict(response.headers.items()), body)
        except HTTPError as response:
            return HttpResponse(response.code, dict(response.headers.items()), b"")
        except HttpTransportError:
            raise
        except (URLError, TimeoutError, OSError, ssl.SSLError) as exc:
            reason = exc.reason if isinstance(exc, URLError) else exc
            if isinstance(reason, HttpTransportError):
                raise reason from None
            raise HttpTransportError(_transport_category(reason)) from None


class _CategorizedHTTPConnection(http.client.HTTPConnection):
    def connect(self) -> None:
        try:
            super().connect()
        except (TimeoutError, OSError, ssl.SSLError) as exc:
            raise HttpTransportError(_transport_category(exc)) from None

    def getresponse(self):
        try:
            return super().getresponse()
        except (TimeoutError, OSError, ssl.SSLError) as exc:
            category = "read_timeout" if isinstance(exc, (TimeoutError, socket.timeout)) else _transport_category(exc)
            raise HttpTransportError(category) from None


class _CategorizedHTTPSConnection(http.client.HTTPSConnection):
    def connect(self) -> None:
        try:
            super().connect()
        except (TimeoutError, OSError, ssl.SSLError) as exc:
            raise HttpTransportError(_transport_category(exc)) from None

    def getresponse(self):
        try:
            return super().getresponse()
        except (TimeoutError, OSError, ssl.SSLError) as exc:
            category = "read_timeout" if isinstance(exc, (TimeoutError, socket.timeout)) else _transport_category(exc)
            raise HttpTransportError(category) from None


class _CategorizedHTTPHandler(HTTPHandler):
    def http_open(self, request):
        return self.do_open(_CategorizedHTTPConnection, request)


class _CategorizedHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        return self.do_open(_CategorizedHTTPSConnection, request, context=self._context)


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
            except (HttpTransportError, TimeoutError, OSError) as exc:
                if attempt == self.max_attempts:
                    category = exc.category if isinstance(exc, HttpTransportError) else _transport_category(exc)
                    raise HttpTransportError(category) from None
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

    def retry_after_seconds(self, headers: Mapping[str, str]) -> float | None:
        values = {str(key).casefold(): str(value) for key, value in headers.items()}
        return self._retry_after(values.get("retry-after"))

    def _retry_after(self, value: str | None) -> float | None:
        if not value:
            return None
        try:
            parsed = float(value.strip())
            return max(0.0, parsed) if math.isfinite(parsed) else None
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
            except (TypeError, ValueError, OverflowError):
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0.0, (parsed - self.now()).total_seconds())


def _transport_category(error: object) -> str:
    """Map exception types/codes only; never inspect or persist provider text."""
    if isinstance(error, ssl.SSLError):
        return "tls_error"
    if isinstance(error, socket.gaierror):
        return "dns_error"
    if isinstance(error, (TimeoutError, socket.timeout)):
        # urllib does not expose whether the timeout happened during connect or read.
        return "connect_timeout"
    if isinstance(error, ConnectionResetError):
        return "connection_reset"
    if isinstance(error, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(error, OSError):
        if error.errno in {errno.ENETUNREACH, errno.EHOSTUNREACH}:
            return "network_unreachable"
        if error.errno == errno.ECONNRESET:
            return "connection_reset"
        if error.errno == errno.ECONNREFUSED:
            return "connection_refused"
        if error.errno == errno.ETIMEDOUT:
            return "connect_timeout"
    if isinstance(error, URLError):
        return _transport_category(error.reason)
    return "transport_other"
