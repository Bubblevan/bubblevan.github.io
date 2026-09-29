from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
from typing import Any

from ..models import now_utc
from ..schema_validator import validate_record


DAILY_RUN_SCHEMA = "bubblevan/intelligence-daily-run/v1"
DAILY_RUN_STATES = {"running", "completed", "partial", "failed"}


def new_daily_run(*, run_date: str, attempt: int, mode: str,
                  started_at: str | None = None) -> dict[str, Any]:
    normalized_date = date.fromisoformat(run_date).isoformat()
    if mode not in {"production", "smoke"}:
        raise ValueError("daily pipeline mode must be production or smoke")
    if attempt < 1:
        raise ValueError("daily pipeline attempt must be positive")
    started = started_at or now_utc()
    identity = f"{mode}|{normalized_date}|{attempt}|{started}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return {
        "schema": DAILY_RUN_SCHEMA,
        "run_id": f"daily-{normalized_date.replace('-', '')}-r{attempt:04d}-{digest}",
        "run_date": normalized_date,
        "attempt": attempt,
        "mode": mode,
        "started_at": started,
        "finished_at": None,
        "status": "running",
        "stages": [],
        "source_summary": {},
        "corpus_hash_before": None,
        "corpus_hash_after": None,
        "feed_run_id": None,
        "feed_refresh_pending": False,
        "feed_metrics": {},
        "source_health": {},
    }


def validate_daily_run(run: dict[str, Any]) -> None:
    validate_record("daily_pipeline_run", run)


def make_stage(*, stage: str, status: str, started_at: str, finished_at: str,
               duration_ms: int, metrics: dict[str, Any] | None = None,
               error_class: str | None = None, error: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "stage": stage,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": max(0, int(duration_ms)),
        "metrics": metrics or {},
        "error_class": error_class,
    }
    if error:
        row["error"] = error[:200]
    return row


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
