from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Protocol
from urllib.parse import urlencode

from ..connectors.base import ConnectorContext
from ..connectors.http import HttpResponse, SharedHttpClient
from ..discovery.budget import ExpansionBudget


class GraphProviderFailure(RuntimeError):
    """Safe provider failure with optional retry guidance and no URL/body."""

    def __init__(
        self,
        provider_id: str,
        *,
        status: int | None = None,
        retry_at: str | None = None,
        retry_after_seconds: float | None = None,
        cause_class: str = "ProviderFailure",
    ):
        super().__init__("graph provider request failed")
        self.provider_id = provider_id
        self.status = status
        self.retry_at = retry_at
        self.retry_after_seconds = retry_after_seconds
        self.cause_class = cause_class


class GraphProvider(Protocol):
    provider_id: str

    def expand_artifact(
        self, artifact: Mapping[str, Any], context: ConnectorContext, budget: ExpansionBudget,
    ) -> dict[str, Any]: ...

    def expand_entity(
        self, entity: Mapping[str, Any], context: ConnectorContext, budget: ExpansionBudget,
    ) -> dict[str, Any]: ...


class ProviderCache:
    """Small cache for selected normalized fields, never raw provider response dumps."""

    def __init__(self, directory: Path | str):
        self.directory = Path(directory)

    def get(self, provider: str, identity: str, ttl_days: int, *, now: str) -> dict[str, Any] | None:
        path = self._path(provider, identity)
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if (
                not isinstance(value, dict)
                or value.get("provider") != provider
                or value.get("provider_id") != identity
                or not isinstance(value.get("selected"), dict)
            ):
                raise ValueError
            fetched = _parse_time(str(value["fetched_at"]))
            if _parse_time(now) - fetched > timedelta(days=ttl_days):
                return None
            return value
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
            raise ValueError(f"corrupt provider cache entry: {provider}") from exc

    def put(
        self, provider: str, identity: str, selected: Mapping[str, Any], *,
        fetched_at: str, etag: str | None = None,
    ) -> dict[str, Any]:
        value = {
            "provider": provider,
            "provider_id": identity,
            "fetched_at": _timestamp(fetched_at),
            "etag": str(etag or "") or None,
            "selected": dict(selected),
        }
        path = self._path(provider, identity)
        _atomic_bytes(path, (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        return value

    def _path(self, provider: str, identity: str) -> Path:
        if not provider.replace("-", "").isalnum():
            raise ValueError("invalid provider cache namespace")
        key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return self.directory / provider / f"{key}.json"


def request_json(
    provider_id: str,
    url: str,
    context: ConnectorContext,
    *,
    headers: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], HttpResponse]:
    client = context.http or SharedHttpClient()
    try:
        response = client.get(url, headers=headers)
    except Exception as exc:
        raise GraphProviderFailure(provider_id, cause_class=type(exc).__name__) from None
    if response.status != 200:
        retry_after = client.retry_after_seconds(response.headers)
        retry_at = None
        values = {str(key).casefold(): str(value) for key, value in response.headers.items()}
        if provider_id == "github" and response.status == 403 and values.get("x-ratelimit-remaining") == "0":
            try:
                reset = datetime.fromtimestamp(float(values["x-ratelimit-reset"]), timezone.utc)
                retry_at = reset.isoformat(timespec="seconds").replace("+00:00", "Z")
                retry_after = max(0.0, (reset - _now(context)).total_seconds())
            except (KeyError, TypeError, ValueError, OverflowError):
                pass
        raise GraphProviderFailure(
            provider_id, status=response.status, retry_at=retry_at,
            retry_after_seconds=retry_after, cause_class="HTTPStatus",
        )
    try:
        value = json.loads(response.body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise GraphProviderFailure(provider_id, status=response.status, cause_class="InvalidJSON") from None
    if not isinstance(value, dict):
        raise GraphProviderFailure(provider_id, status=response.status, cause_class="InvalidPayload")
    diagnostics = client.diagnostics(response)
    return value, diagnostics, response


def default_headers(context: ConnectorContext) -> dict[str, str]:
    result = {"Accept": "application/json"}
    environment = dict(context.environment)
    if "GITHUB_TOKEN" not in environment:
        import os as _os
        environment["GITHUB_TOKEN"] = _os.environ.get("GITHUB_TOKEN", "")
    token = environment.get("GITHUB_TOKEN")
    if token:
        result["Authorization"] = f"Bearer {token}"
    return result


def query_url(base: str, params: Mapping[str, Any]) -> str:
    return f"{base}?{urlencode(params)}"


def _now(context: ConnectorContext) -> datetime:
    try:
        parsed = datetime.fromisoformat(context.now().replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.now(timezone.utc)
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _timestamp(value: str) -> str:
    return _parse_time(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
