from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Callable

import yaml

from .artifacts import materialize_artifact_candidates, upsert_artifact_record
from .aliases import ArtifactAliases
from .connectors.base import ConnectorContext, ConnectorDeferred, ConnectorFailure, FetchResult
from .connectors.http import HttpTransportError
from .connectors.registry import ConnectorRegistry
from .connectors.state import ConnectorState, ConnectorStateStore
from .models import new_source
from .store import JsonlStore, PrivateRecordError


SOURCE_CATALOG = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "sources.yaml"
PRIVATE_SUBSCRIPTIONS = SOURCE_CATALOG.parent / "private" / "sources" / "subscriptions.jsonl"
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
        acquisition_config = {key: value for key, value in acquisition.items()
                              if key not in {"connector", "mode", "artifact_policy"}}
        artifact_policy = config.get("artifact_policy") or {}
        operations = config.get("operations") or {}
        if (not isinstance(artifact_policy, dict)
                or set(artifact_policy) - {"primary_type"}
                or (artifact_policy and artifact_policy.get("primary_type") not in {"paper", "blog", "technical_report"})):
            raise ValueError("source catalog entry has an invalid artifact_policy")
        if (not isinstance(operations, dict) or set(operations) - {"poll_sla_hours", "acquisition_mode"}
                or ("poll_sla_hours" in operations and (
                    isinstance(operations["poll_sla_hours"], bool)
                    or not isinstance(operations["poll_sla_hours"], (int, float))
                    or operations["poll_sla_hours"] < 1
                    or operations["poll_sla_hours"] > 8760
                ))
                or ("acquisition_mode" in operations
                    and operations["acquisition_mode"] not in {"scheduled", "interactive", "manual"})):
            raise ValueError("source catalog entry has invalid operations settings")
        if not identity or not acquisition.get("connector"):
            raise ValueError("source catalog entry requires identity and acquisition.connector")
        _validate_acquisition_config(str(acquisition["connector"]), acquisition_config)
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
            operations={"acquisition_mode": "scheduled", **operations},
            acquisition_config=acquisition_config,
            status=str(config.get("status") or "active"),
        ))
    ids = [item["source_id"] for item in result]
    if len(ids) != len(set(ids)):
        raise ValueError("source catalog has duplicate identities")
    return result


def load_merged_source_catalog(path: Path | str = SOURCE_CATALOG,
                              subscriptions_path: Path | str = PRIVATE_SUBSCRIPTIONS) -> list[dict[str, Any]]:
    """Merge tracked seed sources and locally approved subscriptions deterministically."""
    from .schema_validator import validate_record

    seed = load_source_catalog(path)
    subscriptions = _read_subscriptions(Path(subscriptions_path))
    rows: dict[str, dict[str, Any]] = {}
    for row in [*seed, *subscriptions]:
        source_id_value = str(row.get("source_id") or "")
        if not source_id_value or source_id_value in rows:
            raise ValueError("merged source catalog has duplicate or empty source_id")
        validate_record("source", row)
        connector = str(row.get("acquisition", {}).get("connector") or "")
        config = {key: value for key, value in row.get("acquisition", {}).items()
                  if key not in {"connector", "mode", "artifact_policy"}}
        _validate_acquisition_config(connector, config)
        rows[source_id_value] = row
    return [rows[key] for key in sorted(rows)]


def _read_subscriptions(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        rows = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError
                rows.append(value)
        ids = [str(row.get("source_id") or "") for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError
        return sorted(rows, key=lambda row: str(row.get("source_id") or ""))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("private source subscription registry is corrupt") from exc


def _validate_acquisition_config(connector: str, config: dict[str, Any]) -> None:
    if connector == "openreview-submissions":
        venue = config.get("venue")
        if (set(config) != {"venue"} or not isinstance(venue, dict)
                or set(venue) - {"api_version", "invitation", "decision_invitation", "max_backfill"}
                or type(venue.get("api_version")) is not int or venue.get("api_version") not in {1, 2}
                or not isinstance(venue.get("invitation"), str) or not venue["invitation"].strip()
                or ("decision_invitation" in venue
                    and (not isinstance(venue["decision_invitation"], str)
                         or not venue["decision_invitation"].strip()))):
            raise ValueError("OpenReview source requires an explicit API version and invitation")
        cap = venue.get("max_backfill", 100)
        if isinstance(cap, bool) or not isinstance(cap, int) or not 1 <= cap <= 100:
            raise ValueError("OpenReview max_backfill must be between 1 and 100")
    elif connector == "openalex-works":
        query = config.get("query")
        fields = {"topic_ids", "author_ids", "institution_ids", "source_ids"}
        if set(config) != {"query"} or not isinstance(query, dict) or set(query) - fields:
            raise ValueError("OpenAlex source requires exact-ID query fields only")
        selected = 0
        for key in fields:
            values = query.get(key, [])
            if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError("OpenAlex query IDs must be nonempty strings")
            if len(values) > 20 or len(values) != len(set(values)):
                raise ValueError("OpenAlex query IDs must be unique and bounded to 20 per field")
            prefixes = {"topic_ids": "T", "author_ids": "A", "institution_ids": "I", "source_ids": "S"}
            import re
            if any(not re.fullmatch(prefixes[key] + r"[A-Za-z0-9]+", value.removeprefix("https://openalex.org/"))
                   for value in values):
                raise ValueError("OpenAlex source query contains a mismatched exact ID")
            selected += len(values)
        if not selected:
            raise ValueError("OpenAlex source requires at least one exact identifier")
    elif connector == "rss-atom":
        if config not in ({}, {"via": "rsshub"}):
            raise ValueError("rss-atom accepts only the optional RSSHub provenance marker")
    elif connector in {"huggingface-daily-papers", "github-releases"}:
        if config:
            raise ValueError(f"{connector} does not accept acquisition-specific configuration")
    elif config:
        raise ValueError("unsupported connector acquisition configuration")


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
            except HttpTransportError as exc:
                raise ConnectorFailure(cause_class=type(exc).__name__, error_category=exc.category) from None
            except Exception as exc:
                # Provider exceptions can contain request URLs or response snippets.
                # Keep only the exception class; never persist or print its message.
                raise ConnectorFailure(cause_class=type(exc).__name__) from None
            reported_pages = result.diagnostics.get("pages", 1)
            pages += reported_pages if isinstance(reported_pages, int) and reported_pages > 0 else 1
            for imported_source in result.sources:
                store.upsert_source(imported_source)
            reported_fetched = result.diagnostics.get("entries_fetched")
            fetched_count = (max(len(result.observations), reported_fetched)
                             if isinstance(reported_fetched, int) and not isinstance(reported_fetched, bool)
                             else len(result.observations))
            total_fetched += fetched_count
            aliases = ArtifactAliases(store.directory)
            with store.bulk_materialized(), aliases.bulk_update():
                for observation in result.observations:
                    _inject(context, "before_observation_append")
                    appended = store.append_observation(observation)
                    _inject(context, "after_observation_append")
                    artifact_ids_touched.update(materialize_artifact_candidates(observation, store, aliases=aliases))
                    total_new += int(appended)
                for artifact in result.artifacts:
                    stored = upsert_artifact_record(artifact, store, resolver="connector", resolver_id=connector_id,
                                                    resolved_at=now, aliases=aliases)
                    artifact_ids_touched.add(str(stored["artifact_id"]))
            diagnostics.append(result.diagnostics)
            _inject(context, "before_checkpoint_advance")
            _copy_checkpoint(state, result.next_checkpoint)
            state.last_success_at = result.next_checkpoint.last_success_at or context.now()
            state.consecutive_failures = 0
            state.backoff_until = None
            state.last_error_class = None
            state.last_error_category = None
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
        state.last_error_category = exc.error_category if isinstance(exc, ConnectorFailure) else None
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
    failed = 0
    skipped = 0
    for source in sources:
        operations = source.get("operations") if isinstance(source.get("operations"), dict) else {}
        if operations.get("acquisition_mode") == "interactive":
            skipped += 1
            results.append({
                "status": "skipped",
                "source_id": str(source.get("source_id") or ""),
                "connector_id": str(source.get("acquisition", {}).get("connector") or ""),
                "reason": "interactive_source_requires_user_session",
            })
            continue
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
            if isinstance(exc, ConnectorFailure) and exc.error_category:
                failure["error_category"] = exc.error_category
            if isinstance(exc, ConnectorDeferred):
                if exc.retry_at:
                    failure["retry_at"] = exc.retry_at
                if exc.retry_after_seconds is not None:
                    failure["retry_after_seconds"] = exc.retry_after_seconds
            results.append(failure)
            failed += 1
            continue
        succeeded += 1
        results.append({"status": "succeeded", **result})
    return {
        "sources_total": len(sources), "succeeded": succeeded,
        "failed": failed, "skipped": skipped, "results": results,
    }


def _inject(context: ConnectorContext, stage: str) -> None:
    if context.fault_injector:
        context.fault_injector(stage)


def _checkpoint(state: ConnectorState):
    from .connectors.base import ConnectorCheckpoint
    return ConnectorCheckpoint(
        cursor=state.cursor, etag=state.etag, last_modified=state.last_modified,
        high_watermark=state.high_watermark, last_successful_date=state.last_successful_date,
        last_window_end=state.last_window_end, last_success_at=state.last_success_at,
    )


def _copy_checkpoint(state: ConnectorState, checkpoint: Any) -> None:
    for field in ("cursor", "etag", "last_modified", "high_watermark", "last_successful_date",
                  "last_window_end", "last_success_at"):
        setattr(state, field, getattr(checkpoint, field))


def _datetime(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid connector runtime timestamp") from exc
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
