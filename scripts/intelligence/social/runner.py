from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

from ..artifacts import materialize_artifact_candidates
from ..bridge_xhs import bridge_xhs
from ..bridge_zhihu import bridge_zhihu
from ..canonicalize import canonicalize_url
from ..connectors.http import SharedHttpClient
from ..discovery.source_proposals import (PROPOSAL_PATH, SourceProposalStore,
                                          _proposal_from_candidate, probe_rss_endpoint)
from ..ids import source_id as make_source_id
from ..models import now_utc
from ..retrieval.corpus import build_snapshot
from ..store import JsonlStore
from .base import BrowserStatus
from .chrome_use_driver import ChromeUseDriver, ChromeUseError
from .storage import SocialInbox, SocialRuntime
from .xiaohongshu import XiaohongshuAcquirer, canonical_xhs_url, note_id
from .zhihu import ZhihuAcquirer, canonical_zhihu_url


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INBOX = REPO_ROOT / "data" / "intelligence" / "private"
MAX_SOURCES = 3
MAX_ITEMS_PER_SOURCE = 10
MAX_PAGES = 20


def normalize_social_url(value: str) -> tuple[str, str]:
    text = str(value or "").strip()
    xhs = canonical_xhs_url(text)
    if xhs:
        return "xiaohongshu", xhs
    zhihu = canonical_zhihu_url(text) or _canonical_zhihu_profile(text)
    if zhihu:
        return "zhihu", zhihu
    raise ValueError("URL must be a public XHS note/link or Zhihu answer/profile URL")


def add_social_url(value: str, *, private_root: Path | str = DEFAULT_INBOX,
                   source_id: str | None = None) -> dict[str, Any]:
    platform, canonical = normalize_social_url(value)
    row = SocialInbox(private_root).add(canonical, platform, source_id)
    return {"status": row["status"], "platform": row["platform"], "source_id": row["source_id"],
            "url": row["url"], "added_at": row["added_at"]}


def propose_zhihu_rsshub(profile_url: str, *, environment: Mapping[str, str] | None = None,
                         proposals: SourceProposalStore | None = None,
                         http: Any = None) -> dict[str, Any]:
    canonical_profile = _canonical_zhihu_profile(profile_url)
    if not canonical_profile:
        return {"status": "invalid", "detail": "explicit_zhihu_profile_required"}
    member = urlsplit(canonical_profile).path.rstrip("/").rsplit("/", 1)[-1]
    base = _rsshub_base(environment)
    if not base:
        return {"status": "unavailable", "detail": "rsshub_unconfigured"}
    endpoint = base.rstrip("/") + "/zhihu/people/answers/" + member
    probe = probe_rss_endpoint(endpoint, http=http or SharedHttpClient())
    candidate = {"candidate_id": None, "candidate_type": "person", "name": "Zhihu public author",
                 "canonical_url": canonical_profile, "topics": [], "evidence_paths": []}
    proposal = _proposal_from_candidate(candidate, endpoint, probe, discovered_at=now_utc())
    proposal["acquisition"]["via"] = "rsshub"
    if probe.status != "valid":
        proposal["status"] = "deferred"
        proposal["reason_code"] = "probe_" + probe.status
        (proposals or SourceProposalStore()).upsert(proposal)
        return {"status": "deferred", "detail": probe.detail, "probe_status": probe.status,
                "proposal_id": proposal["proposal_id"]}
    saved = (proposals or SourceProposalStore()).upsert(proposal)
    return {"status": "valid", "detail": "human_approval_required", "probe_status": "valid",
            "entries": probe.entries, "proposal_id": saved["proposal_id"]}


def sync_source(source: Mapping[str, Any], store: JsonlStore, runtime_dir: Path | str, *,
                driver: ChromeUseDriver | None = None, limit: int = MAX_ITEMS_PER_SOURCE,
                postprocess: bool = False, enrich_images: bool = False,
                environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    platform = str(source.get("platform") or "")
    source_id = str(source.get("source_id") or "")
    profile_url = str(source.get("canonical_url") or "")
    if platform not in {"xiaohongshu", "zhihu"} or not source_id.startswith("src-"):
        raise ValueError("selected source is not a supported social source")
    if (source.get("operations") or {}).get("acquisition_mode") != "interactive":
        raise ValueError("social-sync requires an interactive source subscription")
    if platform == "zhihu" and _canonical_zhihu_profile(profile_url):
        rss = propose_zhihu_rsshub(profile_url, environment=environment)
        if rss.get("status") == "valid":
            return {"status": "rss_proposal_pending_approval", "source_id": source_id,
                    "platform": platform, "proposal_id": rss["proposal_id"],
                    "fetched": 0, "new_observations": 0, "duplicate_observations": 0,
                    "artifacts_touched": 0, "pages": 0, "diagnostics": []}
    active_driver = driver or ChromeUseDriver()
    adapter = _adapter(platform, active_driver)
    checkpoint = SocialRuntime(runtime_dir).load(source_id, platform)
    checkpoint["last_attempt_at"] = now_utc()
    SocialRuntime(runtime_dir).save(checkpoint)
    pages = 0
    attempted = 0
    new_count = 0
    duplicate_count = 0
    artifact_ids: set[str] = set()
    statuses: list[str] = []
    try:
        active_driver.adopt_tab(platform)
        if _is_detail_url(platform, profile_url):
            urls = [normalize_social_url(profile_url)[1]]
        else:
            try:
                found = adapter.discover(profile_url, limit=20)
            except ChromeUseError:
                raise
            except Exception:
                found = {"status": BrowserStatus.DOM_CHANGED, "urls": []}
            pages += 1
            if found.get("status") != BrowserStatus.READY:
                checkpoint["last_status"] = str(found.get("status") or BrowserStatus.DOM_CHANGED)
                checkpoint["consecutive_failures"] = int(checkpoint.get("consecutive_failures", 0)) + 1
                checkpoint["last_run"] = {"fetched": 0, "new_observations": 0,
                                          "duplicate_observations": 0, "artifacts_touched": 0,
                                          "pages": pages}
                SocialRuntime(runtime_dir).save(checkpoint)
                result = _sync_result(source_id, platform, checkpoint, status=checkpoint["last_status"])
                result["fallback"] = "social-inbox"
                return result
            urls = list(found.get("urls") or [])
        seen = set(str(item) for item in checkpoint.get("last_seen_object_ids", []))
        bounded_limit = max(0, min(int(limit), MAX_ITEMS_PER_SOURCE))
        over_budget = len(urls) > bounded_limit
        urls = urls[:bounded_limit]
        for item_url in urls:
            if pages >= MAX_PAGES or attempted >= MAX_ITEMS_PER_SOURCE:
                statuses.append(BrowserStatus.PARTIAL)
                break
            item_url = normalize_social_url(item_url)[1]
            # Deduplicate the URL identity before opening another page when a source has a prior id.
            expected_id = note_id(item_url) if platform == "xiaohongshu" else _answer_id(item_url)
            if expected_id and expected_id in seen:
                duplicate_count += 1
                continue
            attempted += 1
            pages += 1
            try:
                item = adapter.acquire(item_url)
            except ChromeUseError:
                raise
            except Exception:
                item = SocialItem(platform, expected_id, item_url, {}, BrowserStatus.DOM_CHANGED)
            statuses.append(item.status)
            if item.status != BrowserStatus.CONTENT_READABLE:
                break
            if enrich_images and platform == "xiaohongshu":
                item.record["image_artifact_candidates"] = _enrich_images_existing(item.record)
            new_observation, touched = _ingest(item, store)
            new_count += int(new_observation)
            duplicate_count += int(not new_observation)
            artifact_ids.update(touched)
            object_id = item.object_id
            seen.add(object_id)
            checkpoint.update({
                "last_success_at": now_utc(), "last_seen_object_ids": sorted(seen)[-500:],
                "consecutive_failures": 0, "last_status": BrowserStatus.COMPLETED,
                "last_attempt_at": now_utc(),
                "last_run": {"fetched": attempted, "new_observations": new_count,
                             "duplicate_observations": duplicate_count,
                             "artifacts_touched": len(artifact_ids), "pages": pages,
                             "login_required": 0, "challenge_required": 0, "dom_changed": 0},
            })
            SocialRuntime(runtime_dir).save(checkpoint)
        final_status = (BrowserStatus.PARTIAL if over_budget or BrowserStatus.PARTIAL in statuses else
                        statuses[-1] if statuses and statuses[-1] != BrowserStatus.CONTENT_READABLE else
                        BrowserStatus.COMPLETED)
        checkpoint["last_status"] = final_status
        checkpoint["last_run"] = {"fetched": attempted, "new_observations": new_count,
                                  "duplicate_observations": duplicate_count,
                                  "artifacts_touched": len(artifact_ids), "pages": pages,
                                  "login_required": int(BrowserStatus.LOGIN_REQUIRED in statuses),
                                  "challenge_required": int(BrowserStatus.CHALLENGE_REQUIRED in statuses),
                                  "dom_changed": int(BrowserStatus.DOM_CHANGED in statuses)}
        if final_status in {BrowserStatus.COMPLETED, BrowserStatus.CONTENT_READABLE}:
            checkpoint["last_success_at"] = checkpoint.get("last_success_at") or now_utc()
            checkpoint["consecutive_failures"] = 0
        else:
            checkpoint["consecutive_failures"] = int(checkpoint.get("consecutive_failures", 0)) + 1
        SocialRuntime(runtime_dir).save(checkpoint)
    except ChromeUseError as exc:
        checkpoint["last_status"] = exc.status
        checkpoint["consecutive_failures"] = int(checkpoint.get("consecutive_failures", 0)) + 1
        checkpoint["last_run"] = {"fetched": attempted, "new_observations": new_count,
                                  "duplicate_observations": duplicate_count,
                                  "artifacts_touched": len(artifact_ids), "pages": pages,
                                  "login_required": 0, "challenge_required": 0, "dom_changed": 0}
        SocialRuntime(runtime_dir).save(checkpoint)
    result = _sync_result(source_id, platform, checkpoint)
    if postprocess and result["new_observations"]:
        result["postprocess"] = _postprocess(store, runtime_dir)
    return result


def sync_inbox(store: JsonlStore, runtime_dir: Path | str, private_root: Path | str = DEFAULT_INBOX, *,
               driver: ChromeUseDriver | None = None, limit: int = 10,
               postprocess: bool = False, enrich_images: bool = False) -> dict[str, Any]:
    pending = [row for row in SocialInbox(private_root).list() if row["status"] == "pending"]
    rows = pending[:max(0, min(limit, 30))]
    groups: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["platform"], row.get("source_id")), []).append(row)
    results = []
    for (platform, source_id), items in list(groups.items())[:MAX_SOURCES]:
        identity = source_id or f"manual-{platform}"
        pseudo_source = {"source_id": source_id or make_source_id(identity),
                         "platform": platform, "canonical_url": items[0]["url"],
                         "operations": {"acquisition_mode": "interactive"}}
        # Manual inbox rows can point at individual public objects, not profiles.
        one = sync_urls(pseudo_source, [item["url"] for item in items[:MAX_ITEMS_PER_SOURCE]],
                        store, runtime_dir, driver=driver, postprocess=False,
                        enrich_images=enrich_images)
        completed_urls = {row["url"] for row in one.pop("item_results", [])
                          if row["status"] in {BrowserStatus.COMPLETED, BrowserStatus.CONTENT_READABLE}}
        for item in items:
            if item["url"] in completed_urls:
                SocialInbox(private_root).update_status(item["url"], "completed")
        results.append(one)
    total_new = sum(item.get("new_observations", 0) for item in results)
    output = {"sources_total": len(groups), "succeeded": sum(item["status"] in {"completed", "content_readable"} for item in results),
              "failed": sum(item["status"] not in {"completed", "content_readable"} for item in results),
              "skipped": max(0, len(groups) - MAX_SOURCES), "results": results}
    if output["skipped"] or len(rows) < len(pending):
        output["status"] = BrowserStatus.PARTIAL
    if postprocess and total_new:
        output["postprocess"] = _postprocess(store, runtime_dir)
    return output


def sync_urls(source: Mapping[str, Any], urls: list[str], store: JsonlStore,
              runtime_dir: Path | str, *, driver: ChromeUseDriver | None = None,
              postprocess: bool = False, enrich_images: bool = False) -> dict[str, Any]:
    active_driver = driver or ChromeUseDriver()
    platform = str(source["platform"])
    source_id = str(source["source_id"])
    adapter = _adapter(platform, active_driver)
    state = SocialRuntime(runtime_dir).load(source_id, platform)
    state["last_attempt_at"] = now_utc()
    SocialRuntime(runtime_dir).save(state)
    new_count = duplicates = pages = attempted = 0
    item_results: list[dict[str, Any]] = []
    artifacts: set[str] = set()
    seen = set(state.get("last_seen_object_ids", []))
    statuses = []
    try:
        active_driver.adopt_tab(platform)
        for url in urls[:MAX_ITEMS_PER_SOURCE]:
            if pages >= MAX_PAGES:
                statuses.append(BrowserStatus.PARTIAL)
                break
            item_platform, canonical = normalize_social_url(url)
            if item_platform != platform:
                raise ValueError("social inbox platform changed during sync")
            pages += 1
            attempted += 1
            try:
                item = adapter.acquire(canonical)
            except ChromeUseError:
                raise
            except Exception:
                item = SocialItem(platform, _answer_id(canonical) if platform == "zhihu" else note_id(canonical),
                                  canonical, {}, BrowserStatus.DOM_CHANGED)
            statuses.append(item.status)
            if item.status != BrowserStatus.CONTENT_READABLE:
                item_results.append({"url": canonical, "status": item.status, "new_observation": False})
                break
            if enrich_images and platform == "xiaohongshu":
                item.record["image_artifact_candidates"] = _enrich_images_existing(item.record)
            appended, touched = _ingest(item, store)
            new_count += int(appended)
            duplicates += int(not appended)
            artifacts.update(touched)
            seen.add(item.object_id)
            item_results.append({"url": canonical, "status": BrowserStatus.COMPLETED,
                                 "new_observation": appended})
            state.update({"last_success_at": now_utc(), "last_seen_object_ids": sorted(seen)[-500:],
                          "consecutive_failures": 0, "last_status": BrowserStatus.COMPLETED,
                          "last_run": {"fetched": attempted, "new_observations": new_count,
                                       "duplicate_observations": duplicates,
                                       "artifacts_touched": len(artifacts), "pages": pages,
                                       "login_required": 0, "challenge_required": 0, "dom_changed": 0}})
            SocialRuntime(runtime_dir).save(state)
    except ChromeUseError as exc:
        state["last_status"] = exc.status
        state["consecutive_failures"] = int(state.get("consecutive_failures", 0)) + 1
    status = statuses[-1] if statuses else state.get("last_status", "never_synced")
    if status == BrowserStatus.CONTENT_READABLE:
        status = BrowserStatus.COMPLETED
    if statuses and all(item == BrowserStatus.CONTENT_READABLE for item in statuses):
        status = BrowserStatus.COMPLETED
    state["last_status"] = status
    state["last_attempt_at"] = now_utc()
    state["last_run"] = {"fetched": attempted, "new_observations": new_count,
                          "duplicate_observations": duplicates, "artifacts_touched": len(artifacts),
                          "pages": pages,
                          "login_required": int(BrowserStatus.LOGIN_REQUIRED in statuses),
                          "challenge_required": int(BrowserStatus.CHALLENGE_REQUIRED in statuses),
                          "dom_changed": int(BrowserStatus.DOM_CHANGED in statuses)}
    if status not in {BrowserStatus.COMPLETED, BrowserStatus.CONTENT_READABLE} and not state.get("consecutive_failures"):
        state["consecutive_failures"] = 1
    SocialRuntime(runtime_dir).save(state)
    result = _sync_result(source_id, platform, state)
    result["item_results"] = item_results
    if postprocess and new_count:
        result["postprocess"] = _postprocess(store, runtime_dir)
    return result


def _ingest(item, store: JsonlStore) -> tuple[bool, list[str]]:
    source, observation = (bridge_xhs(item.record) if item.platform == "xiaohongshu"
                           else bridge_zhihu(item.record))
    store.upsert_source(source)
    appended = store.append_observation(observation)
    touched = materialize_artifact_candidates(observation, store)
    return appended, touched


def _adapter(platform: str, driver: ChromeUseDriver):
    if platform == "xiaohongshu":
        return XiaohongshuAcquirer(driver)
    if platform == "zhihu":
        return ZhihuAcquirer(driver)
    raise ValueError("unsupported social platform")


def _sync_result(source_id: str, platform: str, checkpoint: Mapping[str, Any], *, status: str | None = None) -> dict[str, Any]:
    run = checkpoint.get("last_run") if isinstance(checkpoint.get("last_run"), Mapping) else {}
    return {"status": status or str(checkpoint.get("last_status") or "never_synced"),
            "source_id": source_id, "platform": platform,
            "fetched": int(run.get("fetched", 0)),
            "new_observations": int(run.get("new_observations", 0)),
            "duplicate_observations": int(run.get("duplicate_observations", 0)),
            "artifacts_touched": int(run.get("artifacts_touched", 0)),
            "pages": int(run.get("pages", 0)),
            "last_success_at": checkpoint.get("last_success_at")}


def _is_detail_url(platform: str, url: str) -> bool:
    return bool(canonical_xhs_url(url) and note_id(url)) if platform == "xiaohongshu" else bool(canonical_zhihu_url(url))


def _answer_id(url: str) -> str:
    match = re.search(r"/answer/(\d+)$", urlsplit(url).path)
    return match.group(1) if match else ""


def _canonical_zhihu_profile(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        if (parsed.scheme not in {"http", "https"} or
                (parsed.hostname or "").casefold() not in {"www.zhihu.com", "zhihu.com"}):
            return ""
        match = re.fullmatch(r"/people/([^/]+)(?:/answers)?/?", parsed.path)
        return f"https://www.zhihu.com/people/{match.group(1)}" if match else ""
    except ValueError:
        return ""


def _rsshub_base(environment: Mapping[str, str] | None) -> str:
    raw = (environment or {}).get("RSSHUB_BASE_URL") or os.environ.get("RSSHUB_BASE_URL", "")
    if not raw:
        env_file = REPO_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.lstrip().startswith("RSSHUB_BASE_URL="):
                    raw = line.split("=", 1)[1].strip().strip("\"'")
                    break
    try:
        parsed = urlsplit(str(raw).strip())
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment):
            return ""
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
    except ValueError:
        return ""


def _enrich_images_existing(note: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Opt-in bridge to the established local VLM process; never runs by default."""
    from scripts.tools.xhs_local_vlm_batch import enrich_social_note_images
    return enrich_social_note_images(dict(note))


def _postprocess(store: JsonlStore, runtime_dir: Path | str) -> dict[str, Any]:
    from ..graph.backfill import graph_backfill
    from ..feed.environment import feed_private_dir
    from ..feed.service import daily_feed
    from ..feed.storage import FeedRepository

    graph = graph_backfill(store, runtime_dir, now=now_utc())
    snapshot = build_snapshot(store)
    date = datetime.now(timezone.utc).date().isoformat()
    private = feed_private_dir()
    feed_repository = FeedRepository(private)
    current = feed_repository.current_run(date)
    viewed = False
    if current:
        run_ids = {str(current["feed_run_id"])}
        viewed = any((row.get("action") or row.get("event")) in {"impression", "open", "deep_read", "save", "useful"}
                     and (row.get("context") or {}).get("feed_run_id") in run_ids
                     for row in feed_repository.all_feedback())
    if viewed:
        path = Path(runtime_dir) / "social" / "feed_refresh_pending.json"
        from .storage import _atomic_write
        _atomic_write(path, json.dumps({"refresh_pending": True, "corpus_hash": snapshot.corpus_hash,
                                        "requested_at": now_utc()}, sort_keys=True) + "\n")
        feed_status = "refresh_pending"
    else:
        daily_feed(store.directory, Path(runtime_dir), private, date=date, refresh=current is not None,
                   snapshot=snapshot, dense_enabled=False)
        pending = Path(runtime_dir) / "social" / "feed_refresh_pending.json"
        if pending.exists():
            pending.unlink()
        feed_status = "revised" if current else "created"
    return {"graph": graph, "corpus_hash": snapshot.corpus_hash, "feed": feed_status}
