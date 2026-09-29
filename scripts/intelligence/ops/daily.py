from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import time
from typing import Any, Callable

from ..connectors.base import ConnectorContext
from ..connectors.http import SharedHttpClient
from ..connectors.registry import connector_registry
from ..connectors.state import ConnectorStateStore
from ..feed.environment import feed_private_dir, normalize_feed_mode
from ..feed.feedback_projection import project_feedback
from ..feed.generation import load_dense_resource
from ..feed.models import profile_hash
from ..feed.service import daily_feed
from ..feed.storage import FeedRepository
from ..graph.backfill import graph_backfill
from ..graph.enrichment import enrich_artifact
from ..graph.store import GraphStore
from ..entity_aliases import EntityAliases
from ..discovery.budget import ExpansionBudget
from ..models import now_utc
from ..repositories.artifacts import ArtifactRepository
from ..retrieval.corpus import build_snapshot
from ..runner import load_merged_source_catalog, run_all_sources
from ..schema_validator import SchemaValidationError
from ..store import JsonlStore, PrivateRecordError
from .health import source_health, write_health_manifest
from .locks import LockContended, store_writer_lock
from .models import make_stage, new_daily_run, parse_utc
from .storage import DailyRunStore


def run_daily_pipeline(*, store_dir: Path | str, runtime_dir: Path | str,
                       private_root: Path | str, run_date: str | None = None,
                       mode: str = "production", attempt: int | None = None,
                       dense: bool = False, device: str | None = None,
                       enrich_limit: int = 0, enrich_provider: str = "openalex", force: bool = False,
                       scheduled: bool = False, recovery_passes: int | None = None,
                       recovery_sleep: Callable[[float], None] = time.sleep,
                       lock_timeout_seconds: float = 60.0,
                       now: Callable[[], str] = now_utc,
                       source_loader: Callable[[], list[dict[str, Any]]] = load_merged_source_catalog,
                       acquisition_runner: Callable[..., dict[str, Any]] = run_all_sources,
                       backfill_runner: Callable[..., dict[str, Any]] = graph_backfill,
                       snapshot_builder: Callable[..., Any] = build_snapshot,
                       feed_runner: Callable[..., dict[str, Any]] = daily_feed,
                       dense_loader: Callable[..., tuple[Any, str]] = load_dense_resource) -> dict[str, Any]:
    selected_mode = normalize_feed_mode(mode)
    requested_date = date.fromisoformat(run_date or date.today().isoformat()).isoformat()
    if enrich_limit < 0 or enrich_limit > 20:
        raise ValueError("enrich-limit must be between 0 and 20")
    if enrich_provider not in {"openalex", "semantic-scholar", "github"}:
        raise ValueError("unsupported enrichment provider")
    passes = (1 if scheduled else 0) if recovery_passes is None else recovery_passes
    if passes not in {0, 1}:
        raise ValueError("recovery_passes must be 0 or 1")
    root = Path(private_root)
    private_dir = feed_private_dir(selected_mode, private_root=root)
    store = JsonlStore(store_dir)
    history = DailyRunStore(runtime_dir)
    previous_attempts = history.for_date(requested_date, mode=selected_mode)
    latest_for_day = previous_attempts[-1] if previous_attempts else None
    if attempt is None:
        if latest_for_day and latest_for_day["status"] == "completed" and not force:
            return {"status": "completed", "reused": True, "exit_code": 0, "run": latest_for_day}
        selected_attempt = int(latest_for_day["attempt"]) + 1 if latest_for_day else 1
    else:
        selected_attempt = int(attempt)
        if selected_attempt < 1:
            raise ValueError("attempt must be positive")
        matching = next((row for row in previous_attempts if int(row["attempt"]) == selected_attempt), None)
        if matching and matching["status"] == "completed" and not force:
            return {"status": "completed", "reused": True, "exit_code": 0, "run": matching}
        if matching:
            raise ValueError("DailyPipelineRun attempt already exists; use the next attempt number")

    run = new_daily_run(run_date=requested_date, attempt=selected_attempt, mode=selected_mode, started_at=now())
    stage_partial = False
    critical_failure = False
    warmed_dense = None
    snapshot = None
    source_rows: list[dict[str, Any]] = []
    feed_repo = FeedRepository(private_dir)
    store_summary: dict[str, Any] = {}

    before_started = time.perf_counter()
    before_at = now()
    try:
        with store_writer_lock(runtime_dir, timeout_seconds=lock_timeout_seconds):
            before_snapshot = snapshot_builder(store)
            run["corpus_hash_before"] = before_snapshot.corpus_hash
            artifact_count_before = sum(1 for _ in ArtifactRepository(store).iter_canonical())
            source_rows = source_loader()
            active_sources = [row for row in source_rows if row.get("status") == "active"]
            source_results = acquisition_runner(
                active_sources, connector_registry(), ConnectorStateStore(runtime_dir), store,
                ConnectorContext(store=store),
            )
            artifact_count_after = sum(1 for _ in ArtifactRepository(store).iter_canonical())
        source_results, recovered_artifacts = _scheduled_transport_recovery(
            source_results, active_sources, acquisition_runner, runtime_dir, store,
            enabled=passes == 1, recovery_sleep=recovery_sleep,
        )
        artifact_count_after = max(artifact_count_after, recovered_artifacts)
        finished = now()
        result_rows = [_safe_source_result(row) for row in source_results.get("results", [])]
        total = int(source_results.get("sources_total", len(active_sources)))
        succeeded = int(source_results.get("succeeded", 0))
        failed = int(source_results.get("failed", total - succeeded))
        deferred = sum(row.get("error_class") == "ConnectorDeferred" for row in result_rows)
        new_observations = sum(int(row.get("new_observations") or 0) for row in result_rows)
        fetched = sum(int(row.get("fetched") or 0) for row in result_rows)
        store_summary = {
            "sources_total": total, "sources_succeeded": succeeded,
            "sources_failed": failed, "sources_deferred": deferred,
            "new_observations": new_observations,
            "new_artifacts": max(0, artifact_count_after - artifact_count_before),
            "fetched": fetched,
            "results": result_rows,
        }
        run["source_summary"] = store_summary
        stage_status = "partial" if failed else "succeeded"
        stage_partial |= bool(failed)
        run["stages"].append(make_stage(
            stage="acquisition", status=stage_status, started_at=before_at, finished_at=finished,
            duration_ms=(time.perf_counter() - before_started) * 1000,
            metrics={key: store_summary[key] for key in (
                "sources_total", "sources_succeeded", "sources_failed", "sources_deferred",
                "new_observations", "new_artifacts", "fetched",
            )},
            error_class="SourceAcquisitionPartial" if failed else None,
            error="one or more sources failed; remaining sources continued" if failed else None,
        ))
    except Exception as exc:
        _append_failure(run, "acquisition", before_at, before_started, exc,
                        "another intelligence writer is active" if isinstance(exc, LockContended)
                        else "source acquisition failed")
        critical_failure = True

    if not critical_failure:
        started_at, tick = now(), time.perf_counter()
        try:
            with store_writer_lock(runtime_dir, timeout_seconds=lock_timeout_seconds):
                graph_metrics = backfill_runner(store, runtime_dir, now=now())
            if int(graph_metrics.get("network_requests", 0)) != 0:
                raise ValueError("graph-backfill must not make external network requests")
            run["stages"].append(make_stage(
                stage="graph_backfill", status="succeeded", started_at=started_at, finished_at=now(),
                duration_ms=(time.perf_counter() - tick) * 1000,
                metrics={key: graph_metrics.get(key, 0 if key == "network_requests" else None)
                         for key in ("sources", "observations", "artifacts", "entities", "edges_total", "network_requests")},
            ))
        except Exception as exc:
            if _is_critical_graph_error(exc):
                _append_failure(run, "graph_backfill", started_at, tick, exc,
                                "local graph backfill failed an integrity check")
                critical_failure = True
            else:
                stage_partial = True
                run["stages"].append(make_stage(
                    stage="graph_backfill", status="partial", started_at=started_at, finished_at=now(),
                    duration_ms=(time.perf_counter() - tick) * 1000,
                    metrics={"network_requests": 0}, error_class=type(exc).__name__,
                    error="optional local graph backfill was unavailable",
                ))

    if not critical_failure:
        if enrich_limit:
            started_at, tick = now(), time.perf_counter()
            try:
                with store_writer_lock(runtime_dir, timeout_seconds=lock_timeout_seconds):
                    graph = GraphStore(store.directory)
                    aliases = EntityAliases(store.directory)
                    budget = ExpansionBudget(
                        max_provider_requests=max(1, enrich_limit * 4),
                        max_references_per_artifact=10,
                        max_citations_per_artifact=10,
                    )
                    artifacts = _pending_artifacts(store, enrich_provider)[:enrich_limit]
                    context = ConnectorContext(store=store, http=SharedHttpClient(), now=now)
                    results = [enrich_artifact(
                        str(item["artifact_id"]), enrich_provider, store, graph, aliases,
                        runtime_dir, budget=budget, context=context,
                    ) for item in artifacts]
                    from ..graph.backfill import validate_graph_nodes
                    validate_graph_nodes(store, graph)
                    indexes = graph.rebuild_indexes(runtime_dir, entity_id_resolver=aliases)
                failures = sum(row.get("status") not in {"succeeded", "cached", "unresolved", "skipped"}
                               for row in results)
                if failures:
                    stage_partial = True
                run["stages"].append(make_stage(
                    stage="graph_enrichment", status="partial" if failures else "succeeded",
                    started_at=started_at, finished_at=now(),
                    duration_ms=(time.perf_counter() - tick) * 1000,
                    metrics={"provider": enrich_provider, "artifacts_selected": len(artifacts),
                             "artifacts_completed": len(results) - failures,
                             "provider_requests": budget.provider_requests,
                             "budget_exhausted": budget.exhausted,
                             "indexes": indexes},
                    error_class="GraphEnrichmentPartial" if failures else None,
                    error="optional scholarly graph enrichment was partial" if failures else None,
                ))
            except Exception as exc:
                if _is_critical_graph_error(exc):
                    _append_failure(run, "graph_enrichment", started_at, tick, exc,
                                    "graph enrichment failed an integrity check")
                    critical_failure = True
                else:
                    stage_partial = True
                    run["stages"].append(make_stage(
                        stage="graph_enrichment", status="partial", started_at=started_at,
                        finished_at=now(), duration_ms=(time.perf_counter() - tick) * 1000,
                        metrics={"provider": enrich_provider}, error_class=type(exc).__name__,
                        error="optional scholarly graph enrichment was unavailable",
                    ))
        else:
            stamp = now()
            run["stages"].append(make_stage(
                stage="graph_enrichment", status="skipped", started_at=stamp, finished_at=stamp,
                duration_ms=0, metrics={"limit": 0, "reason": "disabled"},
            ))

    if not critical_failure:
        started_at, tick = now(), time.perf_counter()
        try:
            snapshot = snapshot_builder(store)
            run["corpus_hash_after"] = snapshot.corpus_hash
            eligibility = {key: sum(doc.eligibility == key for doc in snapshot.documents)
                           for key in ("full_text", "metadata_only", "graph_only")}
            run["stages"].append(make_stage(
                stage="corpus_snapshot", status="succeeded", started_at=started_at, finished_at=now(),
                duration_ms=(time.perf_counter() - tick) * 1000,
                metrics={"canonical_artifacts": artifact_count_after, **eligibility,
                         "corpus_hash": snapshot.corpus_hash},
            ))
        except Exception as exc:
            _append_failure(run, "corpus_snapshot", started_at, tick, exc,
                            "corpus snapshot failed")
            critical_failure = True

    if not critical_failure and dense:
        started_at, tick = now(), time.perf_counter()
        try:
            warmed_dense, dense_status = dense_loader(
                snapshot, str(runtime_dir), "Qwen/Qwen3-Embedding-0.6B", None, device,
            )
            if warmed_dense is None:
                stage_partial = True
            run["stages"].append(make_stage(
                stage="dense_warming", status="succeeded" if warmed_dense is not None else "partial",
                started_at=started_at, finished_at=now(), duration_ms=(time.perf_counter() - tick) * 1000,
                metrics={"status": str(dense_status)[:100], "corpus_hash": snapshot.corpus_hash},
                error_class=None if warmed_dense is not None else "DenseUnavailable",
                error=None if warmed_dense is not None else "Dense index unavailable; feed will use local fallback routes",
            ))
        except Exception as exc:
            stage_partial = True
            run["stages"].append(make_stage(
                stage="dense_warming", status="partial", started_at=started_at, finished_at=now(),
                duration_ms=(time.perf_counter() - tick) * 1000,
                metrics={"corpus_hash": snapshot.corpus_hash}, error_class=type(exc).__name__,
                error="Dense index unavailable; feed will use local fallback routes",
            ))
            warmed_dense = None
    elif not critical_failure:
        stamp = now()
        run["stages"].append(make_stage(
            stage="dense_warming", status="skipped", started_at=stamp, finished_at=stamp,
            duration_ms=0, metrics={"reason": "disabled"},
        ))

    if not critical_failure:
        started_at, tick = now(), time.perf_counter()
        try:
            profile = feed_repo.load_profile()
            projection = project_feedback(feed_repo.all_feedback())
            current = feed_repo.current_run(requested_date)
            current_changed = bool(current and (
                current.get("corpus_hash") != snapshot.corpus_hash
                or current.get("profile_hash") != profile_hash(profile)
                or current.get("feedback_projection_hash") != projection["projection_hash"]
            ))
            viewed = bool(current and _active_impression_count(feed_repo, current["feed_run_id"]) > 0)
            pending = bool(current and current_changed and viewed)
            reused = bool(current and not current_changed)
            if current is None or (current_changed and not viewed):
                factory = None
                if dense:
                    def factory(_snapshot, _runtime, _model, _revision, _device):
                        return warmed_dense, ("available" if warmed_dense is not None else "unavailable:DenseUnavailable")
                else:
                    def factory(_snapshot, _runtime, _model, _revision, _device):
                        return None, "disabled"
                feed_run = feed_runner(
                    store_dir, runtime_dir, private_dir, date=requested_date,
                    refresh=current is not None, dense_resource_factory=factory,
                    snapshot=snapshot, dense_enabled=dense,
                    lock_timeout_seconds=lock_timeout_seconds,
                )
            else:
                feed_run = current
            run["feed_run_id"] = feed_run["feed_run_id"]
            run["feed_refresh_pending"] = pending
            run["feed_metrics"] = {
                "candidate_count": int(feed_run.get("candidate_count", 0)),
                "selected_count": len(feed_run.get("items", [])),
                "revision": int(feed_run.get("revision", 1)),
                "reused_existing": reused,
                "viewed_existing": viewed,
                "refresh_pending": pending,
                "requested_corpus_hash": snapshot.corpus_hash,
                "requested_profile_hash": profile_hash(profile),
                "requested_feedback_projection_hash": projection["projection_hash"],
            }
            if not run["corpus_hash_before"]:
                run["corpus_hash_before"] = snapshot.corpus_hash
            run["stages"].append(make_stage(
                stage="feed_preparation", status="pending" if pending else "reused" if reused else "succeeded",
                started_at=started_at, finished_at=now(), duration_ms=(time.perf_counter() - tick) * 1000,
                metrics=dict(run["feed_metrics"]),
                error_class="FeedRefreshPending" if pending else None,
                error="new corpus is ready; refresh this viewed feed from Today" if pending else None,
            ))
        except Exception as exc:
            _append_failure(run, "feed_preparation", started_at, tick, exc,
                            "private feed state is unavailable" if _is_critical_state_error(exc)
                            else "feed preparation failed")
            critical_failure = _is_critical_state_error(exc)
            stage_partial |= not critical_failure

    run["source_health"] = {}
    if not critical_failure:
        started_at, tick = now(), time.perf_counter()
        try:
            health = source_health(runtime_dir=runtime_dir, now=now(), sources=source_rows or None)
            run["source_health"] = {key: health[key] for key in (
                "active_sources", "healthy", "deferred", "stale", "failing", "never_run")}
            run["stages"].append(make_stage(
                stage="health", status="succeeded", started_at=started_at, finished_at=now(),
                duration_ms=(time.perf_counter() - tick) * 1000,
                metrics=run["source_health"],
            ))
        except Exception as exc:
            stage_partial = True
            run["stages"].append(make_stage(
                stage="health", status="partial", started_at=started_at, finished_at=now(),
                duration_ms=(time.perf_counter() - tick) * 1000,
                metrics={}, error_class=type(exc).__name__, error="source health could not be calculated",
            ))

    run["status"] = "failed" if critical_failure else "partial" if stage_partial else "completed"
    run["finished_at"] = now()
    health_manifest_failed = False
    persistence_error = None
    try:
        history.prune(today=requested_date, retain_days=90)
        status = {
            "run_id": run["run_id"], "run_date": run["run_date"], "mode": selected_mode,
            "status": run["status"], "finished_at": run["finished_at"],
            "latest_corpus_hash": run["corpus_hash_after"],
            "feed_run_id": run["feed_run_id"],
            "feed_refresh_pending": run["feed_refresh_pending"],
            "source_summary": run["source_summary"], "source_health": run["source_health"],
            "stages": run["stages"],
        }
        try:
            write_health_manifest(runtime_dir, status)
        except Exception:
            health_manifest_failed = True
            stage_partial = True
            run["status"] = "failed" if critical_failure else "partial"
            health_stage = next((row for row in reversed(run["stages"]) if row["stage"] == "health"), None)
            if health_stage:
                health_stage.update({"status": "partial", "error_class": "HealthManifestWriteFailed",
                                     "error": "health manifest could not be persisted"})
            status["status"] = run["status"]
            status["stages"] = run["stages"]
        history.save(run)
        if health_manifest_failed:
            try:
                write_health_manifest(runtime_dir, status)
            except Exception:
                pass
    except Exception:
        # Do not report a successful run when its immutable history could not be saved.
        run["status"] = "failed"
        run["finished_at"] = run.get("finished_at") or now()
        persistence_error = "daily run history could not be persisted"
        try:
            write_health_manifest(runtime_dir, {
                "run_id": run["run_id"], "run_date": run["run_date"], "mode": selected_mode,
                "status": run["status"], "finished_at": run["finished_at"],
                "latest_corpus_hash": run["corpus_hash_after"],
                "feed_run_id": run["feed_run_id"],
                "feed_refresh_pending": run["feed_refresh_pending"],
                "source_summary": run["source_summary"], "source_health": run["source_health"],
                "stages": run["stages"],
            })
        except Exception:
            pass
    return {"status": run["status"], "reused": False,
            "exit_code": 1 if run["status"] == "failed" else 2 if run["status"] == "partial" else 0,
            "run": run, **({"error": persistence_error} if persistence_error else {})}


def _safe_source_result(row: dict[str, Any]) -> dict[str, Any]:
    allowed = ("status", "source_id", "connector_id", "error_class", "error", "retry_at",
               "retry_after_seconds", "error_category", "attempt_count", "initial_error_category",
               "final_status", "fetched", "new_observations", "duplicate_observations",
               "artifacts_touched", "pages")
    return {key: row[key] for key in allowed if key in row}


_TRANSIENT_TRANSPORT_CATEGORIES = {
    "dns_error", "connect_timeout", "read_timeout", "connection_reset", "network_unreachable",
}


def _scheduled_transport_recovery(source_results: dict[str, Any], active_sources: list[dict[str, Any]],
                                 acquisition_runner: Callable[..., dict[str, Any]], runtime_dir: Path | str,
                                 store: JsonlStore, *, enabled: bool,
                                 recovery_sleep: Callable[[float], None]) -> tuple[dict[str, Any], int]:
    rows = [dict(row) for row in source_results.get("results", [])]
    by_id = {str(row.get("source_id") or ""): row for row in rows}
    retry_ids = {
        source_id for source_id, row in by_id.items()
        if row.get("status") == "failed"
        and row.get("error_class") == "HttpTransportError"
        and row.get("error_category") in _TRANSIENT_TRANSPORT_CATEGORIES
    } if enabled else set()
    for row in rows:
        row["attempt_count"] = 1
        row["final_status"] = row.get("status", "failed")
        if row.get("error_category"):
            row["initial_error_category"] = row["error_category"]
    if not retry_ids:
        return {**source_results, "results": rows}, 0

    # The first pass is complete before waiting; retry only the failed source IDs.
    recovery_sleep(30.0)
    retry_sources = [source for source in active_sources if str(source.get("source_id")) in retry_ids]
    with store_writer_lock(runtime_dir, timeout_seconds=60.0):
        artifact_count_before = sum(1 for _ in ArtifactRepository(store).iter_canonical())
        retry_results = acquisition_runner(
            retry_sources, connector_registry(), ConnectorStateStore(runtime_dir), store,
            ConnectorContext(store=store),
        )
        artifact_count_after = sum(1 for _ in ArtifactRepository(store).iter_canonical())
    retry_by_id = {str(row.get("source_id") or ""): row for row in retry_results.get("results", [])}
    for source_id in sorted(retry_ids):
        initial = by_id[source_id]
        retry = dict(retry_by_id.get(source_id) or {
            "status": "failed", "source_id": source_id,
            "error_class": "ConnectorFailure", "error": "transport recovery attempt failed",
        })
        retry["attempt_count"] = 2
        retry["initial_error_category"] = initial.get("error_category")
        if retry.get("status") == "succeeded":
            retry["status"] = "succeeded_after_retry"
            retry["final_status"] = "succeeded_after_retry"
            retry["succeeded_after_retry"] = True
        else:
            retry["final_status"] = retry.get("status", "failed")
            retry["succeeded_after_retry"] = False
            retry["error_category"] = retry.get("error_category") or initial.get("error_category")
        by_id[source_id] = retry
    results = [by_id.get(str(row.get("source_id") or ""), row) for row in rows]
    succeeded = sum(row.get("status") in {"succeeded", "succeeded_after_retry"} for row in results)
    return ({"sources_total": len(results), "succeeded": succeeded,
             "failed": len(results) - succeeded, "results": results}, artifact_count_after)


def _active_impression_count(repository: FeedRepository, run_id: str) -> int:
    events = repository.all_feedback()
    retracted = {str(row.get("supersedes_feedback_id")) for row in events
                 if row.get("action") == "retract" and row.get("supersedes_feedback_id")}
    return sum(1 for row in events if row.get("feedback_id") not in retracted
               and row.get("action") == "impression"
               and (row.get("context") or {}).get("feed_run_id") == run_id)


def _pending_artifacts(store: JsonlStore, provider: str) -> list[dict[str, Any]]:
    selected = []
    for artifact in ArtifactRepository(store).iter_canonical():
        identifiers = artifact.get("identifiers") if isinstance(artifact.get("identifiers"), dict) else {}
        if provider == "github":
            eligible = artifact.get("artifact_type") == "repository" and bool(identifiers.get("github"))
        elif provider == "openalex":
            eligible = artifact.get("artifact_type") == "paper" and bool(
                identifiers.get("openalex") or identifiers.get("doi") or identifiers.get("arxiv"))
        else:
            eligible = artifact.get("artifact_type") == "paper" and bool(
                identifiers.get("semantic_scholar") or identifiers.get("doi") or identifiers.get("arxiv"))
        if eligible and artifact.get("status") == "candidate":
            selected.append(artifact)
    return sorted(selected, key=lambda item: str(item["artifact_id"]))


def _append_failure(run: dict[str, Any], stage: str, started_at: str, tick: float,
                    exc: Exception, safe_error: str) -> None:
    run["stages"].append(make_stage(
        stage=stage, status="failed", started_at=started_at, finished_at=now_utc(),
        duration_ms=(time.perf_counter() - tick) * 1000, metrics={},
        error_class=type(exc).__name__, error=safe_error,
    ))


def _is_critical_graph_error(exc: Exception) -> bool:
    return _is_critical_state_error(exc)


def _is_critical_state_error(exc: Exception) -> bool:
    if isinstance(exc, (LockContended, PrivateRecordError, SchemaValidationError,
                        json.JSONDecodeError, ValueError)):
        return True
    message = str(exc).lower()
    return "corrupt" in message or "identity invariant" in message or "schema" in message
