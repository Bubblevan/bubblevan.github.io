from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from .artifacts import materialize_artifact_candidates, upsert_artifact_record
from .connectors.base import ConnectorContext, ConnectorDeferred, ConnectorFailure, FetchResult
from .connectors.registry import ConnectorRegistry
from .connectors.state import ConnectorState, ConnectorStateStore
from .models import new_source
from .store import JsonlStore, PrivateRecordError


SOURCE_CATALOG = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "sources.yaml"
MAX_PAGES_PER_RUN = 100


def load_source_catalog(path: Path | str = SOURCE_CATALOG) -> list[dict[str, Any]]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise ValueError("source catalog must contain a sources array")
    result = []
    for config in payload["sources"]:
        if not isinstance(config, dict):
            raise ValueError("source catalog entries must be objects")
        identity = str(config.get("identity") or "").strip()
        acquisition = config.get("acquisition") if isinstance(config.get("acquisition"), dict) else {}
        artifact_policy = config.get("artifact_policy") or {}
        if (not isinstance(artifact_policy, dict)
                or set(artifact_policy) - {"primary_type"}
                or (artifact_policy and artifact_policy.get("primary_type") not in {"paper", "blog", "technical_report"})):
            raise ValueError("source catalog entry has an invalid artifact_policy")
        if not identity or not acquisition.get("connector"):
            raise ValueError("source catalog entry requires identity and acquisition.connector")
        result.append(new_source(
            identity=identity,
            source_type=str(config.get("source_type") or "feed"),
            platform=str(config.get("platform") or "unknown"),
            name=str(config.get("name") or "Unnamed source"),
            canonical_url=str(config.get("canonical_url") or ""),
            external_ids=dict(config.get("external_ids") or {}),
            topics=list(config.get("topics") or []),
            connector=str(acquisition["connector"]),
            mode=str(acquisition.get("mode") or "api"),
            artifact_policy=dict(artifact_policy),
            status=str(config.get("status") or "active"),
        ))
    ids = [item["source_id"] for item in result]
    if len(ids) != len(set(ids)):
        raise ValueError("source catalog has duplicate identities")
    return result


def run_source(
    source: dict[str, Any],
    registry: ConnectorRegistry,
    states: ConnectorStateStore,
    store: JsonlStore,
    context: ConnectorContext | None = None,
) -> dict[str, Any]:
    context = context or ConnectorContext(store=store)
    connector_id = str(source.get("acquisition", {}).get("connector") or "")
    connector = registry.get(connector_id)
    state = states.load(str(source["source_id"]))
    if state and state.connector_id != connector_id:
        raise ValueError("source connector changed; checkpoint requires explicit migration")
    if state and state.connector_version != connector.spec.version:
        raise ValueError("connector version changed; checkpoint requires explicit migration")
    if state is None:
        state = ConnectorState(source_id=str(source["source_id"]), connector_id=connector_id,
                               connector_version=connector.spec.version)
    now = context.now()
    if state.backoff_until and _datetime(state.backoff_until) > _datetime(now):
        raise ConnectorDeferred(retry_at=state.backoff_until)
    store.upsert_source(source)
    state.last_attempt_at = now
    states.save(state)
    checkpoint = _checkpoint(state)
    total_fetched = 0
    total_new = 0
    artifact_ids_touched: set[str] = set()
    pages = 0
    fetch_cycles = 0
    diagnostics: list[dict[str, Any]] = []
    try:
        while True:
            fetch_cycles += 1
            if fetch_cycles > MAX_PAGES_PER_RUN:
                raise RuntimeError("connector exceeded the per-run page limit")
            try:
                result: FetchResult = connector.fetch(source, checkpoint, context)
            except ConnectorFailure:
                raise
            except Exception as exc:
                # Provider exceptions can contain request URLs or response snippets.
                # Keep only the exception class; never persist or print its message.
                raise ConnectorFailure(cause_class=type(exc).__name__) from None
            reported_pages = result.diagnostics.get("pages", 1)
            pages += reported_pages if isinstance(reported_pages, int) and reported_pages > 0 else 1
            for imported_source in result.sources:
                store.upsert_source(imported_source)
            total_fetched += len(result.observations)
            for observation in result.observations:
                _inject(context, "before_observation_append")
                appended = store.append_observation(observation)
                _inject(context, "after_observation_append")
                artifact_ids_touched.update(materialize_artifact_candidates(observation, store))
                total_new += int(appended)
            for artifact in result.artifacts:
                stored = upsert_artifact_record(artifact, store, resolver="connector", resolver_id=connector_id,
                                                resolved_at=now)
                artifact_ids_touched.add(str(stored["artifact_id"]))
            diagnostics.append(result.diagnostics)
            _inject(context, "before_checkpoint_advance")
            _copy_checkpoint(state, result.next_checkpoint)
            state.last_success_at = result.next_checkpoint.last_success_at or context.now()
            state.consecutive_failures = 0
            state.backoff_until = None
            state.last_error_class = None
            states.save(state)
            _inject(context, "after_checkpoint_advance")
            checkpoint = _checkpoint(state)
            if result.exhausted:
                break
        return {
            "source_id": source["source_id"], "connector_id": connector_id,
            "fetched": total_fetched, "new_observations": total_new,
            "duplicate_observations": total_fetched - total_new,
            "artifacts_touched": len(artifact_ids_touched),
            "persisted": total_new,
            "pages": pages, "diagnostics": diagnostics,
        }
    except Exception as exc:
        state.consecutive_failures += 1
        state.last_error_class = exc.cause_class if isinstance(exc, ConnectorFailure) else type(exc).__name__
        if isinstance(exc, ConnectorDeferred) and exc.retry_at:
            state.backoff_until = _datetime(exc.retry_at).isoformat().replace("+00:00", "Z")
        else:
            delay_seconds = (
                max(0.0, exc.retry_after_seconds)
                if isinstance(exc, ConnectorDeferred) and exc.retry_after_seconds is not None
                else min(3600, 30 * (2 ** min(state.consecutive_failures - 1, 7)))
            )
            state.backoff_until = (_datetime(context.now()) + timedelta(seconds=delay_seconds)).isoformat().replace("+00:00", "Z")
        states.save(state)
        raise


def run_all_sources(
    sources: list[dict[str, Any]],
    registry: ConnectorRegistry,
    states: ConnectorStateStore,
    store: JsonlStore,
    context: ConnectorContext | None = None,
) -> dict[str, Any]:
    """Run sources independently while allowing store/schema failures to abort globally."""
    results: list[dict[str, Any]] = []
    succeeded = 0
    for source in sources:
        try:
            result = run_source(source, registry, states, store, context)
        except (ConnectorFailure, PrivateRecordError) as exc:
            private_rejection = isinstance(exc, PrivateRecordError)
            failure: dict[str, Any] = {
                "status": "failed",
                "source_id": str(source.get("source_id") or ""),
                "connector_id": str(source.get("acquisition", {}).get("connector") or ""),
                "error_class": type(exc).__name__ if private_rejection else exc.cause_class,
                "error": (
                    "source record rejected by privacy validation" if private_rejection else
                    "connector deferred by provider" if isinstance(exc, ConnectorDeferred) else
                    "connector fetch failed"
                ),
            }
            if isinstance(exc, ConnectorDeferred):
                if exc.retry_at:
                    failure["retry_at"] = exc.retry_at
                if exc.retry_after_seconds is not None:
                    failure["retry_after_seconds"] = exc.retry_after_seconds
            results.append(failure)
            continue
        succeeded += 1
        results.append({"status": "succeeded", **result})
    return {
        "sources_total": len(sources), "succeeded": succeeded,
        "failed": len(sources) - succeeded, "results": results,
    }


def _inject(context: ConnectorContext, stage: str) -> None:
    if context.fault_injector:
        context.fault_injector(stage)


def _checkpoint(state: ConnectorState):
    from .connectors.base import ConnectorCheckpoint
    return ConnectorCheckpoint(
        cursor=state.cursor, etag=state.etag, last_modified=state.last_modified,
        high_watermark=state.high_watermark, last_success_at=state.last_success_at,
    )


def _copy_checkpoint(state: ConnectorState, checkpoint: Any) -> None:
    for field in ("cursor", "etag", "last_modified", "high_watermark", "last_success_at"):
        setattr(state, field, getattr(checkpoint, field))


def _datetime(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid connector runtime timestamp") from exc
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
