from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from ..connectors.state import ConnectorStateStore
from ..feed.environment import feed_private_dir, normalize_feed_mode
from ..feed.storage import FeedRepository
from ..models import now_utc
from ..runner import load_merged_source_catalog
from .models import parse_utc
from .storage import DailyRunStore


def source_health(*, runtime_dir: Path | str, now: str | None = None,
                  sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    moment = parse_utc(now or now_utc())
    catalog = sources if sources is not None else load_merged_source_catalog()
    states = ConnectorStateStore(runtime_dir)
    rows: list[dict[str, Any]] = []
    for source in catalog:
        state = states.load(str(source["source_id"]))
        operations = source.get("operations") if isinstance(source.get("operations"), dict) else {}
        sla_hours = float(operations.get("poll_sla_hours", 36))
        if state and state.backoff_until and parse_utc(state.backoff_until) > moment:
            status = "deferred"
        elif state and state.consecutive_failures > 0:
            status = "failing"
        elif state is None or not state.last_success_at:
            status = "never_run"
        else:
            age_hours = max(0.0, (moment - parse_utc(state.last_success_at)).total_seconds() / 3600)
            status = "healthy" if age_hours <= sla_hours else "stale"
        age_hours = None
        if state and state.last_success_at:
            age_hours = round(max(0.0, (moment - parse_utc(state.last_success_at)).total_seconds() / 3600), 2)
        rows.append({
            "source_id": str(source["source_id"]),
            "name": str(source.get("name") or source["source_id"]),
            "status": status,
            "poll_sla_hours": sla_hours,
            "last_attempt_at": state.last_attempt_at if state else None,
            "last_success_at": state.last_success_at if state else None,
            "consecutive_failures": state.consecutive_failures if state else 0,
            "backoff_until": state.backoff_until if state else None,
            "age_since_success_hours": age_hours,
            "last_error_class": state.last_error_class if state else None,
        })
    counts = {key: sum(row["status"] == key for row in rows)
              for key in ("healthy", "deferred", "stale", "failing", "never_run")}
    return {"active_sources": len(rows), **counts, "sources": rows}


def ops_status(*, store_dir: Path | str, runtime_dir: Path | str,
               mode: str = "production", today: str | None = None,
               now: str | None = None, private_root: Path | str | None = None) -> dict[str, Any]:
    selected_mode = normalize_feed_mode(mode)
    latest = DailyRunStore(runtime_dir).latest(mode=selected_mode)
    health = source_health(runtime_dir=runtime_dir, now=now)
    private_dir = feed_private_dir(selected_mode, private_root=private_root)
    repository = FeedRepository(private_dir)
    current_run = repository.current_run(today or (latest["run_date"] if latest else "1970-01-01"))
    pending = bool(latest and latest.get("feed_refresh_pending"))
    if pending and current_run and current_run.get("feed_run_id") != latest.get("feed_run_id"):
        pending = False
    successful = [row for row in DailyRunStore(runtime_dir).all(mode=selected_mode)
                  if row["status"] in {"completed", "partial"}]
    last_success = successful[-1] if successful else None
    return {
        "mode": selected_mode,
        "active_sources": health["active_sources"],
        "healthy_sources": health["healthy"],
        "deferred_sources": health["deferred"],
        "stale_sources": health["stale"],
        "failed_sources": health["failing"],
        "never_run_sources": health["never_run"],
        "last_successful_pipeline": {
            "run_id": last_success["run_id"], "run_date": last_success["run_date"],
            "finished_at": last_success["finished_at"], "status": last_success["status"],
        } if last_success else None,
        "latest_pipeline": latest,
        "latest_corpus_hash": latest.get("corpus_hash_after") if latest else None,
        "latest_feed_run": ({"feed_run_id": current_run["feed_run_id"],
                              "feed_date": current_run["feed_date"],
                              "revision": current_run["revision"],
                              "card_count": len(current_run["items"])} if current_run else None),
        "feed_refresh_pending": pending,
        "source_health": health["sources"],
    }


def write_health_manifest(runtime_dir: Path | str, value: dict[str, Any]) -> Path:
    target = Path(runtime_dir) / "ops" / "health.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=target.parent,
                                         prefix=".health.", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return target


def read_health_manifest(runtime_dir: Path | str) -> dict[str, Any] | None:
    path = Path(runtime_dir) / "ops" / "health.json"
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("health manifest is malformed")
    return value
