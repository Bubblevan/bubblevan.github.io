"""Clean up raw inbox files older than a configurable threshold (default 3 days)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re

RAW_PATTERN = re.compile(r"(\d{4})-(\d{2})-(\d{2})\.md$")


def cleanup_raw(root: Path, max_age_days: int = 3) -> tuple[int, int]:
    raw_dir = root / "inbox" / "raw"
    if not raw_dir.exists():
        return 0, 0

    cutoff_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=max_age_days)
    cutoff = cutoff_dt.date()
    removed = 0
    kept = 0

    for md_path in sorted(raw_dir.rglob("*.md")):
        match = RAW_PATTERN.search(md_path.name)
        if not match:
            continue
        try:
            file_date = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            continue
        if file_date < cutoff:
            md_path.unlink()
            removed += 1
        else:
            kept += 1

    # also clean empty year/month dirs
    for parent in sorted(raw_dir.rglob("*"), reverse=True):
        if parent.is_dir() and parent != raw_dir:
            try:
                parent.rmdir()
            except OSError:
                pass

    return removed, kept
