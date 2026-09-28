from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from .evaluation.annotation.base import import_judgments
from .evaluation.model_judging import (
    JUDGE_INPUT_SCHEMA,
    MODEL_JUDGMENT_SCHEMA,
    ModelJudgmentError,
    assemble_model_qrels,
    build_judge_input,
    model_judgment_output,
    prompt_hash,
    validate_model_judgment_output,
)
from .evaluation.pool_coverage import (
    BASELINES,
    build_evaluation_pool,
    judgment_coverage,
    official_coverage_gate,
    pool_delta,
)
from .evaluation import pool_builder
from .evaluation.standard_metrics import evaluate_ir_measures


class M321PoolCoverageTests(unittest.TestCase):
    def test_official_gate_rejects_incomplete_judged_at_10(self) -> None:
        metrics = {baseline: {"Judged@10": 1.0, "Judged@20": 1.0} for baseline in BASELINES}
        metrics["B3"]["Judged@10"] = 0.95
        gate = official_coverage_gate(metrics)
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["status"], "incomplete_judgment_pool")
        self.assertIn("B3.Judged@10", gate["incomplete"])

    def test_official_gate_rejects_incomplete_judged_at_20(self) -> None:
        metrics = {baseline: {"Judged@10": 1.0, "Judged@20": 1.0} for baseline in BASELINES}
        metrics["B2"]["Judged@20"] = 0.99
        gate = official_coverage_gate(metrics)
        self.assertFalse(gate["passed"])
        self.assertIn("B2.Judged@20", gate["incomplete"])

    def test_reusable_pool_builder_keeps_query_context_and_exact_new_pair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous_path = root / "dev-v1.json"
            previous_path.write_text(json.dumps({
                "benchmark_id": "dev-v1", "benchmark_hash": "a" * 64,
                "corpus_hash": "c" * 64, "qrels": [],
                "queries": [{"query_id": "q1", "category": "AI", "specificity": "broad",
                             "query": "A query"}],
            }), encoding="utf-8")
            prompt_path = root / "prompt.md"
            prompt_path.write_text("judge only relevance", encoding="utf-8")
            document = SimpleNamespace(artifact_type="paper", title="A paper",
                                       body="A short abstract", published_at="2026-01-01")
            rankings = {baseline: {"q1": ["a1"]} for baseline in BASELINES}
            fake_snapshot = SimpleNamespace(corpus_hash="c" * 64, by_id=lambda: {"a1": document})

            class FakeArtifactRepository:
                def __init__(self, _store):
                    pass

                def iter_canonical(self):
                    return iter([{"artifact_id": "a1", "canonical_url": "https://example.test/a1"}])

            with (patch.object(pool_builder, "build_snapshot", return_value=fake_snapshot),
                  patch.object(pool_builder, "run_frozen_dev", return_value={
                      "schema": "bubblevan/retrieval-pool-rankings/v1", "status": "pool_built",
                      "benchmark_hash": "a" * 64, "corpus_hash": "c" * 64,
                      "query_count": 1, "retrieval_provenance": {}, "rankings": rankings,
                      "topic_rankings": {},
                  }),
                  patch.object(pool_builder, "ArtifactRepository", FakeArtifactRepository)):
                result = pool_builder.build_model_judge_pool(
                    previous_benchmark_path=previous_path, store=object(), runtime_dir=root / "runtime",
                    output_dir=root / "out", prompt_path=prompt_path,
                )

            output = root / "out" / "dev-v1-1-judge-input.json"
            judge_input = json.loads(output.read_text(encoding="utf-8"))
            pack = json.loads((root / "out" / "dev-v1.1-label-pack.json").read_text(encoding="utf-8"))
            self.assertEqual(result["new_judgments_required"], 1)
            self.assertEqual(judge_input["judgments"][0]["query_id"], "q1")
            self.assertEqual(pack["queries"][0]["query_id"], "q1")

    def test_current_b2_fixture_has_unjudged_top_20_and_legacy_point_75_is_preserved(self) -> None:
        root = Path(__file__).resolve().parents[2]
        rankings = json.loads((root / "data/intelligence/eval/retrieval/dev-v1.1/retrieval-pool-rankings.json")
                              .read_text(encoding="utf-8"))["rankings"]
        v1 = json.loads((root / "data/intelligence/eval/retrieval/dev-v1/dev-v1.json")
                        .read_text(encoding="utf-8"))
        old_eval = json.loads((root / "data/intelligence/eval/retrieval/dev-v1/dev-v1-evaluation.json")
                              .read_text(encoding="utf-8"))
        judged = {(row["query_id"], row["artifact_id"]) for row in v1["qrels"]}
        report = judgment_coverage(rankings, judged)
        self.assertEqual(old_eval["baselines"]["B2"]["aggregate"]["Judged@10"], 0.75)
        self.assertEqual(report["B2"]["cutoffs"]["10"]["Judged"], 1.0)
        self.assertLess(report["B2"]["cutoffs"]["20"]["Judged"], 1.0)
        self.assertGreater(report["B2"]["cutoffs"]["20"]["unjudged_count"], 0)

    def test_new_pool_is_exact_union_of_b0_to_b4_top_20(self) -> None:
        rankings = {baseline: {"q1": [f"{baseline}-{i}" for i in range(25)], "q2": ["shared"]}
                    for baseline in BASELINES}
        rankings["B4"]["q1"][3] = "B0-0"
        pool = build_evaluation_pool(rankings)
        expected = set().union(*(set(rankings[baseline]["q1"][:20]) for baseline in BASELINES))
        self.assertEqual(set(pool["q1"]), expected)
        self.assertEqual(pool["q2"], ["shared"])

    def test_already_judged_pairs_are_excluded_from_incremental_delta(self) -> None:
        pool = {"q1": ["old", "new"], "q2": ["new2"]}
        delta = pool_delta(pool, [{"query_id": "q1", "artifact_id": "old", "grade": 1},
                                  {"query_id": "q2", "artifact_id": "removed", "grade": 0}])
        self.assertEqual(delta["existing_judgments"], 1)
        self.assertEqual(delta["new_judgments_required"], 2)
        self.assertEqual(delta["removed_from_current_pool"], 1)
        self.assertEqual(delta["new_pairs"], [{"query_id": "q1", "artifact_id": "new"},
                                               {"query_id": "q2", "artifact_id": "new2"}])

    def test_completed_gate_requires_all_baselines_and_both_cutoffs(self) -> None:
        metrics = {baseline: {"Judged@10": 1.0, "Judged@20": 1.0} for baseline in BASELINES}
        self.assertTrue(official_coverage_gate(metrics)["passed"])


class M321ModelJudgmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prompt = "frozen prompt"
        self.digest = prompt_hash(self.prompt)
        self.query = {"query_id": "q1", "category": "Research", "specificity": "specific",
                      "query": "A query"}
        self.document = SimpleNamespace(artifact_type="paper", title="A title", body="A short abstract",
                                        published_at="2026-01-01T00:00:00Z")
        self.artifact = {"canonical_url": "https://example.test/paper"}
        self.judge_input = build_judge_input(
            benchmark_id="dev-v1.1", benchmark_hash="b" * 64, corpus_hash="c" * 64,
            pairs=[("q1", "a1")], queries=[self.query], documents={"a1": self.document},
            artifacts={"a1": self.artifact}, grading_prompt_hash=self.digest,
        )

    def test_model_judgment_schema_records_model_identity(self) -> None:
        output = model_judgment_output(self.judge_input, [{"query_id": "q1", "artifact_id": "a1",
                                                           "grade": 1, "quality_issue": "none"}])
        self.assertEqual(output["schema"], MODEL_JUDGMENT_SCHEMA)
        self.assertEqual(output["schema"], "bubblevan/retrieval-model-judgment/v1")
        self.assertEqual(self.judge_input["schema"], JUDGE_INPUT_SCHEMA)

    def test_prompt_hash_is_deterministic(self) -> None:
        self.assertEqual(prompt_hash(self.prompt), self.digest)
        self.assertEqual(prompt_hash(self.prompt.encode("utf-8")), self.digest)

    def test_blind_payload_has_no_route_rank_or_score_fields(self) -> None:
        encoded = json.dumps(self.judge_input, ensure_ascii=False).casefold()
        for field in ('"route"', '"rank"', '"score"', '"baseline"', '"retriever"', '"fusion"'):
            self.assertNotIn(field, encoded)
        self.assertEqual(set(self.judge_input["judgments"][0]), {
            "query_id", "artifact_id", "query", "category", "specificity", "artifact_type",
            "title", "summary_excerpt", "canonical_url", "published_at",
        })

    def test_invalid_luna_grade_fails_closed(self) -> None:
        output = model_judgment_output(self.judge_input, [{"query_id": "q1", "artifact_id": "a1",
                                                           "grade": 3, "quality_issue": "none"}])
        with self.assertRaisesRegex(ModelJudgmentError, "grade"):
            validate_model_judgment_output(self.judge_input, output)

    def test_unknown_model_pair_fails_closed(self) -> None:
        output = model_judgment_output(self.judge_input, [{"query_id": "q1", "artifact_id": "unknown",
                                                           "grade": 0, "quality_issue": "none"}])
        with self.assertRaisesRegex(ModelJudgmentError, "unknown"):
            validate_model_judgment_output(self.judge_input, output)

    def test_metadata_quality_is_independent_from_zero_relevance(self) -> None:
        output = model_judgment_output(self.judge_input, [{"query_id": "q1", "artifact_id": "a1",
                                                           "grade": 0, "quality_issue": "insufficient_metadata"}])
        judged = validate_model_judgment_output(self.judge_input, output)
        self.assertEqual(judged[0]["grade"], 0)
        self.assertEqual(judged[0]["quality_issue"], "insufficient_metadata")

    def test_incremental_qrels_preserve_prior_judgment_and_attach_provenance(self) -> None:
        current_pack = {"benchmark_id": "dev-v1.1", "benchmark_hash": "b" * 64,
                        "corpus_hash": "c" * 64, "queries": [{**self.query, "candidates": [
                            {"artifact_id": "a0"}, {"artifact_id": "a1"}]}]}
        judge_input = {**self.judge_input, "judgments": [
            {"query_id": "q1", "artifact_id": "a1", "query": "A query", "category": "Research",
             "specificity": "specific", "artifact_type": "paper", "title": "A title",
             "summary_excerpt": "A short abstract", "canonical_url": "https://example.test/paper",
             "published_at": "2026-01-01T00:00:00Z"}]}
        judge_output = model_judgment_output(judge_input, [{"query_id": "q1", "artifact_id": "a1",
                                                           "grade": 2, "quality_issue": "none"}])
        previous = {"corpus_hash": "c" * 64, "reviewed_at": "2026-09-28T10:00:00Z",
                    "guideline_version": "m3-2-v1-gpt-6-luna",
                    "qrels": [{"query_id": "q1", "artifact_id": "a0", "grade": 1}],
                    "quality_issues": [{"query_id": "q1", "artifact_id": "a0",
                                        "quality_issue": "insufficient_metadata"}]}
        qrels = assemble_model_qrels(current_pack=current_pack, judge_input=judge_input,
                                     judge_output=judge_output, previous_benchmark=previous,
                                     judged_at="2026-09-29T00:00:00Z")
        self.assertEqual(qrels["schema"], "bubblevan/retrieval-qrels/v2")
        self.assertEqual(qrels["provenance"]["new_pairs_judged"], 1)
        self.assertEqual(qrels["qrels"][0]["judge"]["type"], "model")
        self.assertIsNone(qrels["qrels"][0]["judge"]["prompt_hash"])
        self.assertEqual(qrels["qrels"][1]["judge"]["prompt_hash"], self.digest)
        self.assertEqual(qrels["quality_issues"][0]["quality_issue"], "insufficient_metadata")

    def test_same_corpus_hash_is_required(self) -> None:
        current_pack = {"benchmark_id": "dev-v1.1", "benchmark_hash": "b" * 64,
                        "corpus_hash": "different", "queries": [{**self.query,
                            "candidates": [{"artifact_id": "a1"}]}]}
        output = model_judgment_output(self.judge_input, [{"query_id": "q1", "artifact_id": "a1",
                                                           "grade": 1, "quality_issue": "none"}])
        with self.assertRaisesRegex(ModelJudgmentError, "corpus hash"):
            assemble_model_qrels(current_pack=current_pack, judge_input=self.judge_input,
                                 judge_output=output, previous_benchmark={"corpus_hash": "c" * 64},
                                 judged_at="2026-09-29T00:00:00Z")

    def test_dev_v1_frozen_files_remain_byte_identical(self) -> None:
        root = Path(__file__).resolve().parents[2]
        expected = {
            "dev-v1.json": "1dd3f5ab4edee63c062337a5333cb025558e87176943728c2747e555f89765a5",
            "dev-v1-evaluation.json": "fef51d8d906a3e1919a0aba017e076ee384e0172db0f68b2d57569825b243042",
        }
        for name, digest in expected.items():
            data = (root / "data/intelligence/eval/retrieval/dev-v1" / name).read_bytes()
            canonical_text_bytes = data.replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(canonical_text_bytes).hexdigest(), digest)

    def test_dev_v1_1_is_new_benchmark_with_complete_provenance_and_coverage(self) -> None:
        root = Path(__file__).resolve().parents[2] / "data/intelligence/eval/retrieval"
        v1 = json.loads((root / "dev-v1/dev-v1.json").read_text(encoding="utf-8"))
        v1_1 = json.loads((root / "dev-v1.1/dev-v1.1.json").read_text(encoding="utf-8"))
        evaluation = json.loads((root / "dev-v1.1/dev-v1.1-evaluation.json").read_text(encoding="utf-8"))
        qrels = json.loads((root / "dev-v1.1/dev-v1.1-qrels.json").read_text(encoding="utf-8"))
        self.assertEqual(v1_1["corpus_hash"], v1["corpus_hash"])
        self.assertNotEqual(v1_1["benchmark_hash"], v1["benchmark_hash"])
        self.assertEqual(evaluation["comparison_eligibility"], "official")
        for baseline in BASELINES:
            self.assertEqual(evaluation["baselines"][baseline]["aggregate"]["Judged@10"], 1.0)
            self.assertEqual(evaluation["baselines"][baseline]["aggregate"]["Judged@20"], 1.0)
        judge_types = {row["judge"]["type"] for row in qrels["qrels"]}
        self.assertTrue(judge_types <= {"human", "model"})
        self.assertIn("model", judge_types)
        self.assertEqual(len(qrels["qrels"]), 997)


class M321QrelsCompatibilityTests(unittest.TestCase):
    def _pack(self) -> dict:
        queries = [{"query_id": "q1", "category": "R", "specificity": "broad", "query": "q",
                    "candidates": [{"artifact_id": "a1", "title": "one"},
                                   {"artifact_id": "a2", "title": "two"}]}]
        digest = hashlib.sha256(json.dumps({"benchmark_id": "dev-v1", "queries": queries}, ensure_ascii=False,
                                           sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {"benchmark_id": "dev-v1", "benchmark_hash": digest, "corpus_hash": "c" * 64,
                "queries": queries}

    def test_old_human_qrels_schema_remains_readable(self) -> None:
        pack = self._pack()
        old = {"schema": "bubblevan/retrieval-human-qrels/v1", "benchmark_hash": pack["benchmark_hash"],
               "corpus_hash": pack["corpus_hash"], "reviewed_by": "Old reviewer",
               "qrels": [{"query_id": "q1", "artifact_id": "a1", "grade": 2}],
               "quality_issues": []}
        qrels, _ = import_judgments(pack, [{"benchmark_hash": pack["benchmark_hash"],
                                            "corpus_hash": pack["corpus_hash"], "query_id": "q1",
                                            "artifact_id": "a2", "grade": 1}],
                                    existing_qrels=old, reviewed_by="Next reviewer")
        self.assertEqual(qrels["schema"], "bubblevan/retrieval-qrels/v2")
        self.assertEqual(qrels["qrels"][0]["judge"]["type"], "human")
        self.assertEqual(qrels["qrels"][1]["judge"]["type"], "human")

    def test_generic_qrels_v2_supports_human_and_model(self) -> None:
        pack = self._pack()
        for kind, model in (("human", None), ("model", "GPT-6 Luna")):
            rows = [{"benchmark_hash": pack["benchmark_hash"], "corpus_hash": pack["corpus_hash"],
                     "query_id": "q1", "artifact_id": "a1", "grade": 1}]
            qrels, _ = import_judgments(pack, rows, reviewed_by="Judge", judge_type=kind,
                                        judge_name="Judge", judge_model=model)
            self.assertEqual(qrels["schema"], "bubblevan/retrieval-qrels/v2")
            self.assertEqual(qrels["judge"]["type"], kind)
            self.assertEqual(qrels["qrels"][0]["judge"]["type"], kind)

    def test_architecture_no_longer_prohibits_model_qrels(self) -> None:
        root = Path(__file__).resolve().parents[2]
        architecture = (root / "content/docs/agent/search/research-intelligence/architecture.md")
        text = architecture.read_text(encoding="utf-8").casefold()
        for obsolete in ("模型输出不能自标为 ground truth", "模型输出不能", "必须经人工确认后才能报告真实"):
            self.assertNotIn(obsolete.casefold(), text)
        self.assertIn("model-judged", text)


if __name__ == "__main__":
    unittest.main()
