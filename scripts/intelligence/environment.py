from __future__ import annotations

import os
from typing import Mapping
from unicodedata import category


def environment_value(name: str, environment: Mapping[str, str] | None = None) -> str:
    value = environment.get(name) if environment is not None else None
    if value is None:
        value = os.environ.get(name)
    value = str(value or "").strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        return value[1:-1].strip()
    if len(value) >= 2 and category(value[0]) == "Pi" and category(value[-1]) == "Pf":
        return value[1:-1].strip()
    return value
