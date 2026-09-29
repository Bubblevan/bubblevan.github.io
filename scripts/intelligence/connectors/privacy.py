from __future__ import annotations

import re

from ..canonicalize import canonicalize_url


_URL = re.compile(r"https?://[^\s<>\u0000-\u0020\"']+", re.IGNORECASE)
_ASSIGNMENT = re.compile(
    r"(?i)(xsec_token|session(?:_token)?|access_token|refresh_token|token)\s*([:=])\s*[^\s,;&]+"
)
_HEADER = re.compile(r"(?i)\b(authorization|cookie)\s*([:=])\s*[^\r\n]+")


def redact_private_text(value: str) -> str:
    """Remove private URL query parameters and common credential assignments."""

    def safe_url(match: re.Match[str]) -> str:
        raw = match.group(0)
        trailing = ""
        while raw and raw[-1] in ".,;:!?)]}":
            trailing = raw[-1] + trailing
            raw = raw[:-1]
        return canonicalize_url(raw) + trailing

    value = _URL.sub(safe_url, value)
    value = _ASSIGNMENT.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", value)
    return _HEADER.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", value)
