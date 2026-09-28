from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from .aliases import ArtifactAliases, REDIRECT_SCHEMA
from .cli import _annotation_display_fallbacks, _artifact_stats, _feedback_stats, _freeze_dev_qrels
from .entity_aliases import EntityAliases, REDIRECT_SCHEMA as ENTITY_REDIRECT_SCHEMA
from .evaluation.annotation.argilla import ArgillaAdapter
from .evaluation.annotation.base import AnnotationImportError, annotation_records, import_judgments
from .evaluation.annotation.json_fallback import JsonFallbackAdapter
from .evaluation.standard_metrics import evaluate_ir_measures
from .ids import entity_id
from .models import new_artifact, new_feedback
from .repositories.artifacts import ArtifactRepository
from .retrieval.corpus import build_snapshot
from .retrieval.metrics import evaluate_ranking
from .evaluation.m32_evaluation import _require_frozen_pack
from .store import JsonlStore


class M32CanonicalRepositoryTests(unittest.TestCase):
    def test_repository_resolves_flattened_redirect_groups_and_keeps_raw_rows_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            first = new_artifact(identity="redirect:first", artifact_type="other", title="Old alias")
            second = new_artifact(identity="redirect:second", artifact_type="other", title="Intermediate")
            canonical = new_artifact(identity="redirect:canonical", artifact_type="blog", title="Canonical")
            for artifact in (first, second, canonical):
                store.upsert_artifact(artifact)
            alias_path = Path(temp) / "artifact_redirects.jsonl"
            alias_path.write_text("".join(json.dumps({
                "schema": REDIRECT_SCHEMA, "from_artifact_id": source, "to_artifact_id": target,
                "reason": "fixture", "created_at": "2026-09-28T00:00:00Z",
            }, sort_keys=True) + "\n" for source, target in
                ((first["artifact_id"], second["artifact_id"]),
                 (second["artifact_id"], canonical["artifact_id"]))), encoding="utf-8")
            repository = ArtifactRepository(store)
            self.assertEqual(repository.resolve_id(first["artifact_id"]), canonical["artifact_id"])
            self.assertEqual(repository.get(first["artifact_id"])["title"], "Canonical")
            self.assertEqual([item["artifact_id"] for item in repository.iter_canonical()], [canonical["artifact_id"]])
            self.assertEqual(len(repository.raw_rows()), 3)
            counts = _artifact_stats(store)
            self.assertEqual(counts["physical_row_count"], 3)
            self.assertEqual(counts["redirected_row_count"], 2)
            self.assertEqual(counts["canonical_count"], 1)
            redirect_map = repository.aliases.canonical_redirect_map()
            self.assertEqual(redirect_map[first["artifact_id"]], canonical["artifact_id"])
            with self.assertRaises(TypeError):
                redirect_map[first["artifact_id"]] = second["artifact_id"]

    def test_artifact_redirect_map_is_read_only_and_does_not_compress_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ids = [new_artifact(identity=f"readonly:{i}", artifact_type="other")["artifact_id"] for i in range(3)]
            path = Path(temp) / "artifact_redirects.jsonl"
            path.write_text("".join(json.dumps({"schema": REDIRECT_SCHEMA, "from_artifact_id": a,
                                                 "to_artifact_id": b, "reason": "fixture",
                                                 "created_at": "2026-09-28T00:00:00Z"}, sort_keys=True) + "\n"
                                            for a, b in ((ids[0], ids[1]), (ids[1], ids[2]))), encoding="utf-8")
            before = path.read_bytes()
            redirects = ArtifactAliases(temp).canonical_redirect_map()
            self.assertEqual(redirects[ids[0]], ids[2])
            self.assertEqual(path.read_bytes(), before)
            with self.assertRaises(TypeError):
                redirects[ids[0]] = ids[1]

    def test_redirect_cycles_fail_closed_in_public_maps(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ids = [new_artifact(identity=f"cycle:{i}", artifact_type="other")["artifact_id"] for i in range(2)]
            (Path(temp) / "artifact_redirects.jsonl").write_text("".join(json.dumps({
                "schema": REDIRECT_SCHEMA, "from_artifact_id": a, "to_artifact_id": b,
                "reason": "fixture", "created_at": "2026-09-28T00:00:00Z"}, sort_keys=True) + "\n"
                for a, b in ((ids[0], ids[1]), (ids[1], ids[0]))), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cycle"):
                ArtifactAliases(temp).canonical_redirect_map()
            eids = [entity_id(f"cycle-entity-{index}") for index in range(2)]
            (Path(temp) / "entity_redirects.jsonl").write_text("".join(json.dumps({
                "schema": ENTITY_REDIRECT_SCHEMA, "from_entity_id": a, "to_entity_id": b,
                "reason": "exact_provider_equivalence", "provider": "fixture", "provider_record_id": "x",
                "created_at": "2026-09-28T00:00:00Z"}, sort_keys=True) + "\n"
                for a, b in ((eids[0], eids[1]), (eids[1], eids[0]))), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cycle"):
                EntityAliases(temp).canonical_redirect_map()

    def test_repository_maps_a_redirect_without_physical_target_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            old = new_artifact(identity="missing-root:old", artifact_type="blog", title="Old row")
            root = new_artifact(identity="missing-root:new", artifact_type="blog", title="Old row")
            store.upsert_artifact(old)
            ArtifactAliases(temp).add_redirect(old["artifact_id"], root["artifact_id"], created_at="2026-09-28T00:00:00Z")
            resolved = list(ArtifactRepository(store).iter_canonical())
            self.assertEqual(len(resolved), 1)
            self.assertEqual(resolved[0]["artifact_id"], root["artifact_id"])
            self.assertEqual(ArtifactRepository(store).get(old["artifact_id"])["artifact_id"], root["artifact_id"])

    def test_entity_redirect_map_is_flattened_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ids = [entity_id(f"m32-entity-{index}") for index in range(3)]
            rows = ((ids[0], ids[1]), (ids[1], ids[2]))
            path = Path(temp) / "entity_redirects.jsonl"
            path.write_text("".join(json.dumps({
                "schema": ENTITY_REDIRECT_SCHEMA, "from_entity_id": source, "to_entity_id": target,
                "reason": "exact_provider_equivalence", "provider": "fixture",
                "provider_record_id": "fixture-id", "created_at": "2026-09-28T00:00:00Z",
            }, sort_keys=True) + "\n" for source, target in rows), encoding="utf-8")
            aliases = EntityAliases(temp)
            before = path.read_bytes()
            redirects = aliases.canonical_redirect_map()
            self.assertEqual(redirects[ids[0]], ids[2])
            with self.assertRaises(TypeError):
                redirects[ids[0]] = ids[1]
            self.assertEqual(path.read_bytes(), before)


class M32AnnotationTests(unittest.TestCase):
    @staticmethod
    def pack(candidate_count: int = 2) -> dict:
        candidates = [{"artifact_id": f"art-{index:024x}", "artifact_type": "paper", "title": f"Paper {index}",
                       "canonical_url": f"https://example.test/{index}", "published_at": None,
                       "summary_excerpt": "" if index == 0 else "Public abstract excerpt."}
                      for index in range(candidate_count)]
        queries = [{"query_id": "q1", "category": "Research", "specificity": "specific", "query": "Find research evidence.",
                    "query_provenance": "fixture", "label_source": None, "reviewed_by": None,
                    "reviewed_at": None, "candidates": candidates}]
        digest = hashlib.sha256(json.dumps({"benchmark_id": "dev-v1", "queries": queries}, ensure_ascii=False,
                                           sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {"schema": "bubblevan/retrieval-blind-label-pack/v1", "benchmark_id": "dev-v1", "status": "draft",
                "corpus_hash": "c" * 64, "benchmark_hash": digest, "queries": queries}

    def test_blind_records_are_stable_and_exclude_route_information(self) -> None:
        pack = self.pack()
        records = annotation_records(pack, display_fallbacks={pack["queries"][0]["candidates"][0]["artifact_id"]:
                                                              {"summary_excerpt": "Source excerpt"}})
        self.assertEqual(records, annotation_records(pack, display_fallbacks={pack["queries"][0]["candidates"][0]["artifact_id"]:
                                                                             {"summary_excerpt": "Source excerpt"}}))
        self.assertEqual(len({row["external_id"] for row in records}), 2)
        self.assertIn("Source excerpt", records[0]["fields"]["summary_excerpt"])
        payload = json.dumps(records)
        for secret_name in ("route", "rank", "score", "retriever", "fusion"):
            self.assertNotIn(f'"{secret_name}"', payload)

    def test_blind_validator_rejects_derived_rank_and_route_fields(self) -> None:
        pack = self.pack()
        pack["queries"][0]["candidates"][0]["bm25_rank"] = 2
        with self.assertRaisesRegex(ValueError, "retrieval metadata"):
            annotation_records(pack)

    def test_partial_json_import_resumes_and_conflicts_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pack = self.pack()
            adapter = JsonFallbackAdapter()
            annotation_path = Path(temp) / "annotations.json"
            qrels_path = Path(temp) / "qrels.json"
            adapter.export(pack, annotation_path)
            payload = json.loads(annotation_path.read_text(encoding="utf-8"))
            payload["records"][0]["responses"]["relevance"] = "2"
            annotation_path.write_text(json.dumps(payload), encoding="utf-8")
            resumed = adapter.export(pack, annotation_path)
            self.assertEqual((resumed["records_added"], resumed["preserved_existing"], resumed["duplicates"]),
                             (0, 2, 0))
            payload = json.loads(annotation_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["records"][0]["responses"]["relevance"], "2")
            partial = adapter.import_labels(pack, annotation_path, qrels_path, reviewed_by="reviewer")
            self.assertEqual((partial["total"], partial["annotated"], partial["remaining"], partial["invalid"]),
                             (2, 1, 1, 0))
            payload = json.loads(annotation_path.read_text(encoding="utf-8"))
            payload["records"][1]["responses"]["relevance"] = 0
            annotation_path.write_text(json.dumps(payload), encoding="utf-8")
            complete = adapter.import_labels(pack, annotation_path, qrels_path)
            self.assertEqual((complete["annotated"], complete["remaining"]), (2, 0))
            saved = json.loads(qrels_path.read_text(encoding="utf-8"))
            self.assertEqual([item["grade"] for item in saved["qrels"]], [2, 0])
            payload["records"][0]["responses"]["relevance"] = 1
            annotation_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflicts"):
                adapter.import_labels(pack, annotation_path, qrels_path)

    def test_unknown_identity_and_wrong_hash_rejected_without_qrels_write(self) -> None:
        pack = self.pack()
        rows = [{"benchmark_hash": "x", "corpus_hash": pack["corpus_hash"], "query_id": "q1",
                 "artifact_id": pack["queries"][0]["candidates"][0]["artifact_id"], "grade": 1}]
        with self.assertRaises(AnnotationImportError) as raised:
            import_judgments(pack, rows)
        self.assertEqual(raised.exception.report["invalid"], 1)
        self.assertEqual(raised.exception.report["invalid_reasons"], {"hash_mismatch": 1})

    def test_wrong_corpus_hash_is_rejected(self) -> None:
        pack = self.pack()
        candidate_id = pack["queries"][0]["candidates"][0]["artifact_id"]
        with self.assertRaises(AnnotationImportError) as raised:
            import_judgments(pack, [{"benchmark_hash": pack["benchmark_hash"], "corpus_hash": "wrong",
                                     "query_id": "q1", "artifact_id": candidate_id, "grade": 1}])
        self.assertEqual(raised.exception.report["invalid_reasons"], {"hash_mismatch": 1})

    def test_invalid_grade_and_quality_label_are_rejected(self) -> None:
        pack = self.pack()
        candidate_id = pack["queries"][0]["candidates"][0]["artifact_id"]
        with self.assertRaises(AnnotationImportError) as grade_error:
            import_judgments(pack, [{"benchmark_hash": pack["benchmark_hash"], "corpus_hash": pack["corpus_hash"],
                                     "query_id": "q1", "artifact_id": candidate_id, "grade": 3}])
        self.assertEqual(grade_error.exception.report["invalid_reasons"], {"invalid_grade": 1})
        with self.assertRaises(AnnotationImportError) as issue_error:
            import_judgments(pack, [{"benchmark_hash": pack["benchmark_hash"], "corpus_hash": pack["corpus_hash"],
                                     "query_id": "q1", "artifact_id": candidate_id,
                                     "quality_issue": "made_up_issue"}])
        self.assertEqual(issue_error.exception.report["invalid_reasons"], {"invalid_quality_issue": 1})

    def test_conflicting_duplicate_grades_fail_closed(self) -> None:
        pack = self.pack()
        candidate_id = pack["queries"][0]["candidates"][0]["artifact_id"]
        row = {"benchmark_hash": pack["benchmark_hash"], "corpus_hash": pack["corpus_hash"],
               "query_id": "q1", "artifact_id": candidate_id}
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            import_judgments(pack, [{**row, "grade": 1}, {**row, "grade": 2}])

    def test_quality_issue_is_stored_separately_from_relevance(self) -> None:
        pack = self.pack()
        candidate_id = pack["queries"][0]["candidates"][0]["artifact_id"]
        qrels, report = import_judgments(pack, [{"benchmark_hash": pack["benchmark_hash"],
                                                 "corpus_hash": pack["corpus_hash"], "query_id": "q1",
                                                 "artifact_id": candidate_id, "quality_issue": "identity_problem"}])
        self.assertEqual(qrels["qrels"], [])
        self.assertEqual(qrels["quality_issues"][0]["quality_issue"], "identity_problem")
        self.assertEqual(report["annotated"], 0)

    def test_exported_external_record_id_is_validated_on_import(self) -> None:
        pack = self.pack()
        candidate_id = pack["queries"][0]["candidates"][0]["artifact_id"]
        with self.assertRaises(AnnotationImportError) as raised:
            import_judgments(pack, [{"benchmark_hash": pack["benchmark_hash"], "corpus_hash": pack["corpus_hash"],
                                     "query_id": "q1", "artifact_id": candidate_id,
                                     "external_id": "forged", "grade": 1}])
        self.assertEqual(raised.exception.report["invalid_reasons"], {"unknown_record_id": 1})

    def test_actual_633_record_export_has_no_route_rank_or_score_fields(self) -> None:
        root = Path(__file__).resolve().parents[2]
        source = root / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1" / "dev-v1-label-pack.json"
        pack = json.loads(source.read_text(encoding="utf-8"))
        rows = annotation_records(pack)
        self.assertEqual(len(rows), 633)
        self.assertEqual(len({row["external_id"] for row in rows}), 633)
        self.assertFalse(any({"route", "routes", "rank", "score", "retriever", "fusion"}.intersection(row["fields"])
                             for row in rows))

    def test_display_fallback_does_not_mutate_pack_identity_or_candidate(self) -> None:
        pack = self.pack()
        before = json.dumps(pack, ensure_ascii=False, sort_keys=True)
        candidate = pack["queries"][0]["candidates"][0]
        rows = annotation_records(pack, display_fallbacks={candidate["artifact_id"]:
                                                             {"canonical_url": candidate["canonical_url"],
                                                              "summary_excerpt": "Display-only excerpt"}})
        self.assertEqual(json.dumps(pack, ensure_ascii=False, sort_keys=True), before)
        self.assertIn("Display-only excerpt", rows[0]["fields"]["summary_excerpt"])

    def test_argilla_adapter_requires_env_credentials_without_echoing_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "ARGILLA_API_URL and ARGILLA_API_KEY"):
                ArgillaAdapter._argilla()

    def test_frozen_runner_rejects_draft_pack(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires a frozen"):
            _require_frozen_pack({"status": "draft"}, "x")

    def test_argilla_adapter_is_resume_safe_with_same_record_ids(self) -> None:
        state: dict[str, Any] = {}

        class FakeRecord:
            def __init__(self, id=None, fields=None, metadata=None, responses=None):
                self.id, self.fields, self.metadata = id, fields or {}, metadata or {}
                self.responses = responses or {}

        class FakeRecordManager:
            def __init__(self, dataset): self.dataset = dataset
            def __call__(self, **kwargs): return iter(self.dataset.rows.values())
            def log(self, records):
                for record in records:
                    self.dataset.rows.setdefault(record.id, record)

        class FakeDataset:
            def __init__(self, name=None, **kwargs):
                self.name, self.rows, self.records = name, state.get(name, {}), None
                self.records = FakeRecordManager(self)
            def get(self):
                if self.name not in state: raise ValueError("not found")
                self.rows = state[self.name]
                return self
            def create(self):
                state[self.name] = self.rows
                return self

        fake = SimpleNamespace(
            Record=FakeRecord, Dataset=FakeDataset,
            Settings=lambda **kwargs: kwargs, TextField=lambda **kwargs: kwargs,
            LabelQuestion=lambda **kwargs: kwargs,
        )
        pack = self.pack()
        adapter = ArgillaAdapter()
        with patch.object(ArgillaAdapter, "_argilla", staticmethod(lambda: (fake, object()))):
            first = adapter.export(pack)
            rows = list(state[first["dataset"]].values())
            rows[0].responses = {"relevance": {"value": "2"}}
            second = adapter.export(pack)
            self.assertEqual(first["records_added"], 2)
            self.assertEqual(second["records_added"], 0)
            self.assertEqual(second["duplicates"], 0)
            self.assertEqual(rows[0].responses["relevance"]["value"], "2")
            with tempfile.TemporaryDirectory() as temp:
                qrels_path = Path(temp) / "qrels.json"
                report = adapter.import_labels(pack, first["dataset"], qrels_path)
                self.assertEqual((report["annotated"], report["remaining"]), (1, 1))

    def test_freeze_requires_complete_hashed_pack_and_writes_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store_path = Path(temp) / "events"
            store = JsonlStore(store_path)
            corpus_hash = build_snapshot(store).corpus_hash
            queries = []
            judgments = []
            for index in range(20):
                query_id = f"q{index}"
                candidate_id = f"art-{index:024x}"
                queries.append({"query_id": query_id, "category": "Research", "specificity": "broad",
                                "query": f"query {index}", "query_provenance": "fixture", "label_source": None,
                                "reviewed_by": None, "reviewed_at": None,
                                "candidates": [{"artifact_id": candidate_id, "artifact_type": "paper", "title": "x",
                                                "canonical_url": "https://example.test/x", "published_at": None,
                                                "summary_excerpt": "x"}]})
                judgments.append({"query_id": query_id, "artifact_id": candidate_id, "grade": 0})
            benchmark_hash = hashlib.sha256(json.dumps({"benchmark_id": "dev-v1", "queries": queries},
                                                       ensure_ascii=False, sort_keys=True,
                                                       separators=(",", ":")).encode()).hexdigest()
            pack = {"benchmark_id": "dev-v1", "benchmark_hash": benchmark_hash, "corpus_hash": corpus_hash,
                    "queries": queries}
            qrels = {"benchmark_hash": benchmark_hash, "corpus_hash": corpus_hash, "qrels": judgments,
                     "quality_issues": [{"query_id": "q0", "artifact_id": "art-000000000000000000000000",
                                         "quality_issue": "insufficient_metadata"}]}
            pack_path, qrels_path, output = Path(temp) / "pack.json", Path(temp) / "qrels.json", Path(temp) / "dev.json"
            pack_path.write_text(json.dumps(pack), encoding="utf-8")
            qrels_path.write_text(json.dumps(qrels), encoding="utf-8")
            result = _freeze_dev_qrels(pack_path, qrels_path, output, reviewed_by="reviewer",
                                       reviewed_at="2026-09-28T10:00:00Z", guideline_version="m3-2-v1",
                                       store_dir=store_path)
            self.assertEqual(result["judgments"], 20)
            frozen = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(frozen["quality_issues"][0]["quality_issue"], "insufficient_metadata")
            with self.assertRaisesRegex(ValueError, "already exists"):
                _freeze_dev_qrels(pack_path, qrels_path, output, reviewed_by="reviewer",
                                  reviewed_at="2026-09-28T10:00:00Z", guideline_version="m3-2-v1",
                                  store_dir=store_path)


class M32MetricsAndFeedbackTests(unittest.TestCase):
    def test_ir_measures_parity_with_custom_metric_fixture(self) -> None:
        qrels = {f"d{index}": (2 if index in {0, 4} else 1 if index in {2, 6, 8} else 0)
                 for index in range(12)}
        ranking = [f"d{index}" for index in (4, 1, 6, 0, 11, 8, 3, 2, 7, 9, 5, 10)]
        custom = evaluate_ranking(ranking, qrels)
        official = evaluate_ir_measures(ranking, qrels)
        pairs = (("Recall@5", "Recall@5"), ("Recall@10", "Recall@10"), ("Recall@20", "Recall@20"),
                 ("MRR@10", "RR@10"), ("nDCG@10", "nDCG@10"), ("Precision@10", "P@10"))
        for local_name, official_name in pairs:
            self.assertAlmostEqual(custom[local_name], official[official_name], delta=1e-9)

    def test_feedback_inventory_omits_query_and_raw_event_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            artifact = new_artifact(identity="feedback:paper", artifact_type="paper", title="Safe title")
            store.upsert_artifact(artifact)
            store.append_feedback(new_feedback(artifact_id=artifact["artifact_id"], event="deep_read",
                                               occurred_at="2026-09-28T00:00:00Z", query="PRIVATE QUERY TEXT"))
            report = _feedback_stats(store)
            encoded = json.dumps(report)
            self.assertEqual(report["unique_artifacts"], 1)
            self.assertEqual(report["actions"], {"deep_read": 1})
            self.assertNotIn("PRIVATE QUERY TEXT", encoded)

    def test_feedback_stats_canonicalizes_alias_ids_and_reports_time_span(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            canonical = new_artifact(identity="feedback:canonical", artifact_type="paper", title="Canonical")
            alias = new_artifact(identity="feedback:alias", artifact_type="paper", title="Alias")
            store.upsert_artifact(canonical)
            store.upsert_artifact(alias)
            ArtifactAliases(temp).add_redirect(alias["artifact_id"], canonical["artifact_id"], created_at="2026-09-28T00:00:00Z")
            store.append_feedback(new_feedback(artifact_id=alias["artifact_id"], event="open",
                                               occurred_at="2026-09-28T01:00:00Z"))
            store.append_feedback(new_feedback(artifact_id=canonical["artifact_id"], event="deep_read",
                                               occurred_at="2026-09-28T02:00:00Z"))
            report = _feedback_stats(store)
            self.assertEqual(report["unique_artifacts"], 1)
            self.assertEqual(report["time_span"], {"first_at": "2026-09-28T01:00:00Z",
                                                     "last_at": "2026-09-28T02:00:00Z"})
            self.assertEqual(report["per_artifact"][0]["artifact_id"], canonical["artifact_id"])

    def test_ir_measures_empty_relevant_qrels_return_zero(self) -> None:
        result = evaluate_ir_measures(["a"], {"a": 0, "b": 0})
        self.assertTrue(all(value == 0.0 for value in result.values()))

    def test_ranx_metrics_and_rrf_match_the_reference_fixture(self) -> None:
        os.environ.setdefault("IR_DATASETS_HOME", str(Path(tempfile.gettempdir()) / "ri-ir-datasets"))
        os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ri-mpl-cache"))
        from ranx import Run, fuse
        from .evaluation.standard_metrics import ranx_metrics
        from .retrieval.fusion import reciprocal_rank_fusion
        qrels = {"q": {"a": 2, "b": 1, "c": 0}}
        rankings = {"q": ["a", "b", "c"]}
        report = ranx_metrics(rankings, qrels)
        self.assertIn("mrr@10", report["aggregate"])
        route_ids = {"bm25": ["a", "b", "c"], "dense": ["c", "a", "d"]}
        local = reciprocal_rank_fusion({name: [{"artifact_id": artifact_id, "rank": index + 1}
                                                for index, artifact_id in enumerate(ids)]
                                         for name, ids in route_ids.items()},
                                        request_id="fixture", top_k=20)
        ranx_runs = [Run({"q": {artifact_id: float(len(ids) - index)
                                 for index, artifact_id in enumerate(ids)}})
                     for ids in route_ids.values()]
        reference = fuse(runs=ranx_runs, method="rrf", params={"k": 60})
        reference_ids = [artifact_id for artifact_id, _ in sorted(reference.run["q"].items(),
                                                                    key=lambda item: (-item[1], item[0]))]
        self.assertEqual([item["artifact_id"] for item in local], reference_ids)


if __name__ == "__main__":
    unittest.main()
