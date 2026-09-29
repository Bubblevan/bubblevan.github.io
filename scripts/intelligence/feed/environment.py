from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PRIVATE_ROOT = REPO_ROOT / "data" / "intelligence" / "private"


def normalize_feed_mode(mode: str | None = None) -> str:
    value = str(mode if mode is not None else os.environ.get("RI_FEED_ENV", "production")).strip().lower()
    if value not in {"production", "smoke"}:
        raise ValueError("feed environment must be production or smoke")
    return value


def feed_private_dir(mode: str | None = None, *, private_root: Path | str | None = None) -> Path:
    selected = normalize_feed_mode(mode)
    root = Path(private_root) if private_root is not None else PRIVATE_ROOT
    return root / f"feed-{selected}"
