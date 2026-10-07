from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from .connectors.state import ConnectorState, ConnectorStateStore
from .feed.environment import feed_private_dir
from .feed.migration import archive_m4_smoke_state
from .feed.models import default_profile, new_feedback, update_profile
from .feed.service import apply_feedback, daily_feed, feedback_stats
from .feed.storage import FeedRepository
from .ids import artifact_id, source_id
from .models import new_source, new_feedback as new_legacy_feedback
from .ops import daily as daily_ops
from .ops.daily import run_daily_pipeline
from .ops.health import ops_status, source_health
from .ops.locks import (LockContended, feed_lock_path, feed_writer_lock,
                        store_lock_path, store_writer_lock)
from .ops.models import new_daily_run
from .ops.storage import DailyRunStore
from .retrieval.corpus import CorpusSnapshot
from .store import JsonlStore


ROOT = Path(__file__).resolve().parents[2]
FIXED = "2026-09-29T08:00:00Z"


class OperationsEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.private_root = self.root / "private"
        self.runtime = self.root / "runtime"
        self.store = JsonlStore(self.root / "events")
        self.date = "2026-09-29"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _run_record(self, run_id: str, feed_date: str | None = None) -> dict:
        return {
            "schema": "bubblevan/feed-run/v1", "feed_run_id": run_id,
            "feed_date": feed_date or self.date, "revision": 1, "generated_at": FIXED,
            "corpus_hash": "fixture-corpus", "profile_hash": "fixture-profile",
            "feedback_projection_hash": "fixture-feedback", "policy_version": "feed-v0",
            "lookback_days": 7, "candidate_count": 1, "items": [],
            "supersedes_feed_run_id": None, "metrics": {}, "retrieval_routes": {},
            "experimental_graph": False,
        }

    def test_m4_state_is_archived_and_only_profile_is_copied(self) -> None:
        legacy = FeedRepository(self.private_root / "feed")
        profile = update_profile(default_profile(created_at=FIXED), add={
            "selected_topic_ids": [f"topic-{index}" for index in range(4)],
            "followed_source_ids": [f"src-{index}" for index in range(3)],
        }, updated_at=FIXED)
        legacy.save_profile(profile)
        run_id = "feed-" + "a" * 24
        legacy.save_run(self._run_record(run_id))
        event = new_feedback(artifact_id="art-" + "b" * 24, action="useful",
                             feed_run_id=run_id, rank=1, occurred_at=FIXED)
        legacy.append_feedback(event)

        report = archive_m4_smoke_state(self.private_root, self.runtime,
                                        now=datetime(2026, 9, 29, tzinfo=timezone.utc))

        self.assertEqual(report["archived_m4_feed_runs"], 1)
        self.assertEqual(report["archived_m4_feedback_events"], 1)
        self.assertTrue(Path(report["archived_directory"]).exists())
        production = FeedRepository(feed_private_dir("production", private_root=self.private_root))
        smoke_archive = FeedRepository(Path(report["archived_directory"]))
        self.assertEqual(production.load_profile()["selected_topic_ids"], profile["selected_topic_ids"])
        self.assertEqual(production.load_profile()["followed_source_ids"], profile["followed_source_ids"])
        self.assertEqual(production.runs(), [])
        self.assertEqual(production.all_feedback(), [])
        self.assertEqual(len(smoke_archive.runs()), 1)
        self.assertEqual(len(smoke_archive.all_feedback()), 1)

    def test_smoke_useful_events_never_enter_production_projection_or_stats(self) -> None:
        from .feed.feedback_projection import project_feedback

        production = FeedRepository(feed_private_dir("production", private_root=self.private_root))
        smoke = FeedRepository(feed_private_dir("smoke", private_root=self.private_root))
        run_id = "feed-" + "c" * 24
        event = new_feedback(artifact_id="art-" + "d" * 24, action="useful",
                             feed_run_id=run_id, rank=1, occurred_at=FIXED)
        smoke.append_feedback(event)
        self.assertIn(event["artifact_id"], project_feedback(smoke.all_feedback())["useful_artifact_ids"])
        self.assertEqual(project_feedback(production.all_feedback())["useful_artifact_ids"], [])
        self.assertEqual(feedback_stats(self.store, production)["environment"], "production")
        self.assertEqual(feedback_stats(self.store, production)["useful"], 0)
        self.assertEqual(feedback_stats(self.store, smoke)["environment"], "smoke")
        self.assertEqual(feedback_stats(self.store, smoke)["useful"], 1)

    def test_private_feed_stats_never_union_legacy_store_feedback(self) -> None:
        production = FeedRepository(feed_private_dir("production", private_root=self.private_root))
        self.store.append_feedback(new_legacy_feedback(
            artifact_id="art-" + "f" * 24, event="save", occurred_at=FIXED))
        self.assertEqual(production.all_feedback(self.store), [])
        self.assertEqual(feedback_stats(self.store, production)["feedback_events"], 0)

    def test_feed_modes_resolve_to_disjoint_directories(self) -> None:
        self.assertNotEqual(feed_private_dir("production", private_root=self.private_root),
                            feed_private_dir("smoke", private_root=self.private_root))
        with self.assertRaises(ValueError):
            feed_private_dir("both", private_root=self.private_root)


class WriterLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.private = self.root / "private" / "feed-production"
        self.runtime = self.root / "runtime"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _competing_writer(self, lock_path: Path) -> str:
        code = (
            "import sys; from scripts.intelligence.ops.locks import writer_lock, LockContended; "
            "p=sys.argv[1]; "
            "\ntry:\n with writer_lock(p, timeout_seconds=0.15, purpose='test'): print('acquired')"
            "\nexcept LockContended: print('lock_contended')"
        )
        result = subprocess.run([sys.executable, "-c", code, str(lock_path)], cwd=ROOT,
                                capture_output=True, text=True, timeout=5, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_portalocker_serializes_two_processes_for_store_and_feed(self) -> None:
        with store_writer_lock(self.runtime, timeout_seconds=1.0):
            self.assertEqual(self._competing_writer(store_lock_path(self.runtime)), "lock_contended")
        with feed_writer_lock(self.private, timeout_seconds=1.0):
            self.assertEqual(self._competing_writer(feed_lock_path(self.private)), "lock_contended")

    def test_locks_release_even_if_the_mutation_raises(self) -> None:
        for lock in (store_writer_lock(self.runtime, timeout_seconds=1.0),
                     feed_writer_lock(self.private, timeout_seconds=1.0)):
            with self.assertRaises(RuntimeError):
                with lock:
                    raise RuntimeError("fixture")
        with store_writer_lock(self.runtime, timeout_seconds=0.2):
            pass
        with feed_writer_lock(self.private, timeout_seconds=0.2):
            pass

    def test_streamlit_module_does_not_acquire_a_process_lifetime_lock(self) -> None:
        app = (ROOT / "apps" / "research_intelligence_feed.py").read_text(encoding="utf-8")
        self.assertNotIn("acquire_ui_writer", app)
        self.assertNotIn(".ui-writer.json", app)


class DailyPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store_dir = self.root / "events"
        self.runtime = self.root / "runtime"
        self.private_root = self.root / "private"
        self.store = JsonlStore(self.store_dir)
        self.hash_value = "a" * 64
        self.calls: list[str] = []

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _snapshot(self, _store: JsonlStore) -> CorpusSnapshot:
        return CorpusSnapshot((), self.hash_value, "source-tree")

    def _acquire(self, sources, registry, states, store, context):
        self.calls.append("acquisition")
        return {"sources_total": len(sources), "succeeded": len(sources), "failed": 0, "results": []}

    def _backfill(self, store, runtime_dir, *, now):
        self.calls.append("graph_backfill")
        return {"sources": 0, "observations": 0, "artifacts": 0, "entities": 0,
                "edges_total": 0, "network_requests": 0}

    def _run(self, **overrides):
        values = {
            "store_dir": self.store_dir, "runtime_dir": self.runtime,
            "private_root": self.private_root, "run_date": "2026-09-29",
            "mode": "production", "source_loader": lambda: [],
            "acquisition_runner": self._acquire, "backfill_runner": self._backfill,
            "snapshot_builder": self._snapshot, "now": lambda: FIXED,
        }
        values.update(overrides)
        return run_daily_pipeline(**values)

    def test_completed_run_is_reused_and_force_creates_next_attempt(self) -> None:
        first = self._run()
        self.assertEqual(first["run"]["attempt"], 1)
        calls_after_first = list(self.calls)
        replay = self._run()
        self.assertTrue(replay["reused"])
        self.assertEqual(self.calls, calls_after_first)
        forced = self._run(force=True)
        self.assertEqual(forced["run"]["attempt"], 2)
        self.assertNotEqual(first["run"]["run_id"], forced["run"]["run_id"])

    def test_pipeline_runs_acquisition_then_local_backfill_and_records_no_enrichment(self) -> None:
        run = self._run()["run"]
        self.assertEqual(self.calls[:2], ["acquisition", "graph_backfill"])
        self.assertEqual(run["stages"][1]["metrics"]["network_requests"], 0)
        enrichment = next(stage for stage in run["stages"] if stage["stage"] == "graph_enrichment")
        self.assertEqual(enrichment["status"], "skipped")
        self.assertEqual(enrichment["metrics"]["limit"], 0)

    def test_one_failed_source_keeps_feed_usable_and_returns_partial(self) -> None:
        def partial(sources, registry, states, store, context):
            return {"sources_total": 2, "succeeded": 1, "failed": 1, "results": [
                {"status": "succeeded", "source_id": "src-" + "1" * 24,
                 "fetched": 1, "new_observations": 1, "new_artifacts": 1},
                {"status": "failed", "source_id": "src-" + "2" * 24,
                 "error_class": "ConnectorFailure", "error": "connector fetch failed"},
            ]}
        result = self._run(source_loader=lambda: [
            {"source_id": "src-" + "1" * 24, "status": "active"},
            {"source_id": "src-" + "2" * 24, "status": "active"}], acquisition_runner=partial)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["exit_code"], 2)
        self.assertIsNotNone(result["run"]["feed_run_id"])
        self.assertEqual(result["run"]["source_summary"]["sources_failed"], 1)

    def test_global_store_corruption_fails_and_stops_later_stages(self) -> None:
        def broken(*_args, **_kwargs):
            raise ValueError("corrupt JSONL at https://feed.invalid?token=do-not-store")
        result = self._run(acquisition_runner=broken)
        serialized = json.dumps(result["run"], ensure_ascii=False)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("token=do-not-store", serialized)
        self.assertEqual([stage["stage"] for stage in result["run"]["stages"]], ["acquisition"])

    def test_dense_unavailable_is_partial_but_still_creates_feed(self) -> None:
        def broken_dense(*_args):
            raise RuntimeError("offline model cache missing")
        result = self._run(dense=True, dense_loader=broken_dense)
        self.assertEqual(result["status"], "partial")
        self.assertIsNotNone(result["run"]["feed_run_id"])
        dense_stage = next(stage for stage in result["run"]["stages"] if stage["stage"] == "dense_warming")
        self.assertEqual(dense_stage["status"], "partial")

    def test_unseen_existing_feed_auto_refreshes_on_corpus_change(self) -> None:
        first = self._run()["run"]
        self.hash_value = "b" * 64
        second = self._run(force=True)["run"]
        self.assertEqual(second["feed_metrics"]["revision"], 2)
        self.assertEqual(second["corpus_hash_after"], "b" * 64)
        self.assertNotEqual(second["feed_run_id"], first["feed_run_id"])
        self.assertFalse(second["feed_refresh_pending"])

    def test_viewed_feed_is_not_replaced_and_sets_refresh_pending(self) -> None:
        first = self._run()["run"]
        repository = FeedRepository(feed_private_dir("production", private_root=self.private_root))
        artifact = "art-" + "e" * 24
        impression = new_feedback(artifact_id=artifact, action="impression",
                                  feed_run_id=first["feed_run_id"], rank=1, occurred_at=FIXED)
        repository.append_feedback(impression)
        self.hash_value = "c" * 64
        second = self._run(force=True)["run"]
        self.assertTrue(second["feed_refresh_pending"])
        self.assertEqual(second["feed_run_id"], first["feed_run_id"])
        self.assertEqual(second["feed_metrics"]["revision"], 1)

    def test_daily_run_manifest_has_no_raw_secret_values(self) -> None:
        def raises_with_secret(*_args, **_kwargs):
            raise RuntimeError("Authorization: bearer top-secret")
        result = self._run(acquisition_runner=raises_with_secret)
        contents = json.dumps(result["run"])
        self.assertNotIn("top-secret", contents)
        self.assertNotIn("Authorization", contents)

    def test_health_manifest_write_failure_is_persisted_as_partial(self) -> None:
        with patch.object(daily_ops, "write_health_manifest",
                          side_effect=OSError("private path details")):
            result = self._run()
        stored = DailyRunStore(self.runtime).latest(mode="production")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["exit_code"], 2)
        self.assertEqual(stored["status"], "partial")
        health_stage = next(row for row in stored["stages"] if row["stage"] == "health")
        self.assertEqual(health_stage["status"], "partial")
        self.assertEqual(health_stage["error_class"], "HealthManifestWriteFailed")
        self.assertNotIn("private path details", json.dumps(stored))

    def test_scheduler_script_uses_absolute_paths_without_password(self) -> None:
        script = (ROOT / "scripts/intelligence/ops/windows/install-task.ps1").read_text(encoding="utf-8")
        self.assertIn("Resolve-Path", script)
        self.assertIn("-Execute $PythonPath", script)
        self.assertIn("-WorkingDirectory $repoRoot", script)
        self.assertIn("scripts.intelligence.ops.scheduled --mode production", script)
        self.assertIn("--hermes-path", script)
        self.assertIn("--target weixin", script)
        self.assertIn("-StartWhenAvailable", script)
        self.assertIn("-RunOnlyIfNetworkAvailable", script)
        self.assertIn("-MultipleInstances IgnoreNew", script)
        self.assertIn("-ExecutionTimeLimit (New-TimeSpan -Hours 2)", script)
        self.assertNotIn("-Password", script)
        self.assertNotIn("Password =", script)

    def test_pipeline_run_store_prunes_after_ninety_days(self) -> None:
        runs = DailyRunStore(self.runtime)
        old = new_daily_run(run_date="2026-05-01", attempt=1, mode="production", started_at=FIXED)
        old.update({"finished_at": FIXED, "status": "completed"})
        runs.save(old)
        recent = new_daily_run(run_date="2026-09-29", attempt=1, mode="production", started_at=FIXED)
        recent.update({"finished_at": FIXED, "status": "completed"})
        runs.save(recent)
        self.assertEqual(runs.prune(today="2026-09-29", retain_days=90), 1)
        self.assertEqual([row["run_date"] for row in runs.all()], ["2026-09-29"])


class SourceHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = Path(self.temp.name) / "runtime"
        self.source = new_source(identity="health|fixture", source_type="feed", platform="test",
                                 name="Health fixture", connector="rss-atom", mode="rss")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_source_health_healthy_stale_deferred_and_never_run(self) -> None:
        states = ConnectorStateStore(self.runtime)
        healthy = ConnectorState(source_id=self.source["source_id"], connector_id="rss-atom",
                                 last_success_at="2026-09-29T07:00:00Z")
        states.save(healthy)
        self.assertEqual(source_health(runtime_dir=self.runtime, now=FIXED,
                                       sources=[self.source])["sources"][0]["status"], "healthy")
        self.assertEqual(source_health(runtime_dir=self.runtime, now="2026-10-01T00:00:00Z",
                                       sources=[self.source])["sources"][0]["status"], "stale")
        healthy.backoff_until = "2026-09-29T09:00:00Z"
        states.save(healthy)
        self.assertEqual(source_health(runtime_dir=self.runtime, now=FIXED,
                                       sources=[self.source])["sources"][0]["status"], "deferred")
        self.assertEqual(source_health(runtime_dir=self.runtime, now=FIXED,
                                       sources=[new_source(identity="health|never", source_type="feed", platform="test",
                                                           name="Never", connector="rss-atom", mode="rss")])["sources"][0]["status"], "never_run")

    def test_poll_sla_is_read_from_source_catalog_metadata(self) -> None:
        source = dict(self.source)
        source["operations"] = {"poll_sla_hours": 12}
        states = ConnectorStateStore(self.runtime)
        states.save(ConnectorState(source_id=source["source_id"], connector_id="rss-atom",
                                   last_success_at="2026-09-28T12:00:00Z"))
        result = source_health(runtime_dir=self.runtime, now=FIXED, sources=[source])
        self.assertEqual(result["sources"][0]["poll_sla_hours"], 12)
        self.assertEqual(result["sources"][0]["status"], "stale")

    def test_ops_status_is_deterministic_and_reports_latest_values(self) -> None:
        runtime = Path(self.temp.name) / "ops-runtime"
        run_store = DailyRunStore(runtime)
        row = new_daily_run(run_date="2026-09-29", attempt=1, mode="production", started_at=FIXED)
        row.update({"finished_at": FIXED, "status": "completed", "corpus_hash_after": "a" * 64})
        run_store.save(row)
        first = ops_status(store_dir=self.temp.name, runtime_dir=runtime,
                           mode="production", now=FIXED, private_root=self.root / "private")
        second = ops_status(store_dir=self.temp.name, runtime_dir=runtime,
                            mode="production", now=FIXED, private_root=self.root / "private")
        self.assertEqual(first, second)
        self.assertEqual(first["latest_corpus_hash"], "a" * 64)
        self.assertEqual(first["last_successful_pipeline"]["run_id"], row["run_id"])

    def test_source_catalog_accepts_optional_poll_sla_and_rejects_invalid_values(self) -> None:
        from .runner import load_source_catalog
        catalog = Path(self.temp.name) / "sources.yaml"
        catalog.write_text("""schema: bubblevan/intelligence-source-catalog/v1
sources:
  - identity: 'ops|sla-fixture'
    source_type: feed
    platform: test
    name: SLA fixture
    canonical_url: https://example.org/feed.xml
    acquisition: {connector: rss-atom, mode: rss}
    operations: {poll_sla_hours: 12}
    status: active
""", encoding="utf-8")
        self.assertEqual(load_source_catalog(catalog)[0]["operations"]["poll_sla_hours"], 12)
        catalog.write_text(catalog.read_text(encoding="utf-8").replace("poll_sla_hours: 12", "poll_sla_hours: 0"),
                           encoding="utf-8")
        with self.assertRaises(ValueError):
            load_source_catalog(catalog)


if __name__ == "__main__":
    unittest.main()
