from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .environment import feed_private_dir
from .storage import FeedRepository


def archive_m4_smoke_state(private_root: Path | str, runtime_dir: Path | str, *,
                           now: datetime | None = None) -> dict[str, Any]:
    root = Path(private_root)
    legacy = root / "feed"
    smoke = feed_private_dir("smoke", private_root=root)
    production = feed_private_dir("production", private_root=root)
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    smoke.mkdir(parents=True, exist_ok=True)
    production.mkdir(parents=True, exist_ok=True)
    if legacy.exists():
        source_repository = FeedRepository(legacy)
        source_profile = source_repository.load_profile() if source_repository.profile_path.exists() else None
        archived_run_count = len(source_repository.runs())
        archived_feedback_count = len(source_repository.all_feedback())
        target = smoke / f"m4-v0-{stamp}"
        suffix = 1
        while target.exists():
            target = smoke / f"m4-v0-{stamp}-{suffix:02d}"
            suffix += 1
        production_repository = FeedRepository(production)
        if production_repository.runs() or production_repository.all_feedback():
            raise ValueError("production feed already contains runs or feedback; migration will not overwrite it")
        if production_repository.profile_path.exists():
            raise ValueError("production feed profile already exists; migration will not overwrite it")
        os.replace(legacy, target)
        if source_profile is not None:
            production_repository.save_profile(source_profile)
        status = "archived_and_migrated"
        profile_topics = len(source_profile.get("selected_topic_ids", [])) if source_profile else 0
        profile_sources = len(source_profile.get("followed_source_ids", [])) if source_profile else 0
        archived_path = str(target)
    else:
        archives = sorted(smoke.glob("m4-v0-*"), key=lambda path: path.name)
        status = "already_archived" if archives else "no_legacy_state"
        archived_path = str(archives[-1]) if archives else None
        archived_run_count = archived_feedback_count = profile_topics = profile_sources = 0

    production_repository = FeedRepository(production)
    production_runs = production_repository.runs()
    production_feedback = production_repository.all_feedback()
    if production_repository.profile_path.exists() and not profile_topics and not profile_sources:
        copied_profile = production_repository.load_profile()
        profile_topics = len(copied_profile.get("selected_topic_ids", []))
        profile_sources = len(copied_profile.get("followed_source_ids", []))
    if production_runs or production_feedback:
        raise ValueError("production environment must start with zero FeedRuns and zero Feedback")
    report = {
        "schema": "bubblevan/feed-smoke-archive/v1",
        "status": status,
        "created_at": (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "archived_directory": archived_path,
        "archived_m4_feed_runs": archived_run_count,
        "archived_m4_feedback_events": archived_feedback_count,
        "production_profile_copied": bool(production_repository.profile_path.exists()),
        "production_profile_topic_count": profile_topics,
        "production_profile_followed_source_count": profile_sources,
        "production_feed_runs": len(production_runs),
        "production_feedback_events": len(production_feedback),
    }
    report_path = Path(runtime_dir) / "ops" / "migrations" / f"m4-smoke-{stamp}.json"
    _atomic_json(report_path, report)
    return {**report, "report_path": str(report_path)}


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
