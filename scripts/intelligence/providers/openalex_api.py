from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
from typing import Any, Mapping

from ..environment import environment_value


RATE_LIMIT_URL = "https://api.openalex.org/rate-limit"


def api_key(environment: Mapping[str, str] | None = None) -> str | None:
    value = environment_value("OPENALEX_API_KEY", environment)
    return value or None


def request_headers(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    key = api_key(environment)
    return {"Authorization": f"Bearer {key}"} if key else {}


def get(client: Any, url: str, *, environment: Mapping[str, str] | None = None) -> Any:
    headers = request_headers(environment)
    return client.get(url, headers=headers) if headers else client.get(url)


def rate_limit_numbers(response: Any) -> dict[str, int | float]:
    """Return only nonnegative numeric OpenAlex budget fields."""
    raw = {str(key).casefold(): value for key, value in response.headers.items()}
    names = {
        "x-ratelimit-limit": "rate_limit_limit",
        "x-ratelimit-remaining": "rate_limit_remaining",
        "x-ratelimit-credits-used": "rate_limit_credits_used",
        "x-ratelimit-reset": "rate_limit_reset_seconds",
    }
    result: dict[str, int | float] = {}
    for header, output in names.items():
        if header not in raw:
            continue
        parsed = _number(raw[header])
        if parsed is not None:
            result[output] = parsed
    if {"rate_limit_limit", "rate_limit_remaining"} - result.keys():
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (AttributeError, UnicodeError, json.JSONDecodeError):
            payload = None
        budget = payload.get("rate_limit") if isinstance(payload, dict) else None
        if isinstance(budget, dict):
            aliases = {
                "credits_limit": "rate_limit_limit",
                "credits_remaining": "rate_limit_remaining",
                "credits_used": "rate_limit_credits_used",
                "resets_in_seconds": "rate_limit_reset_seconds",
            }
            for source, target in aliases.items():
                if target not in result:
                    parsed = _number(budget.get(source))
                    if parsed is not None:
                        result[target] = parsed
    return result


def _number(raw: Any) -> int | float | None:
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite() or value < 0:
        return None
    return int(value) if value == value.to_integral_value() else float(value)


def below_budget_threshold(values: Mapping[str, int | float], *, threshold: float = 0.10) -> bool:
    limit = values.get("rate_limit_limit")
    remaining = values.get("rate_limit_remaining")
    return bool(limit and remaining is not None and float(remaining) / float(limit) < threshold)
