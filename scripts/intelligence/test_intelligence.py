from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import re
import tempfile
import unittest

from .bridge_capture import bridge_capture, ingest_capture
from .bridge_xhs import bridge_xhs, ingest_xhs
from .canonicalize import (
    artifact_identity,
    canonicalize_url,
    extract_arxiv_id,
    extract_artifact_candidates,
    extract_doi,
    extract_github_repo,
    extract_huggingface_repo,
)
from .cli import main as cli_main
from .ids import artifact_id, entity_id, feedback_id, observation_id, source_id, topic_id
from .models import new_artifact, new_feedback, new_observation, new_source
from .schema_validator import SchemaValidationError, validate_instance
from .store import JsonlStore


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).with_name("fixtures")
SCHEMAS = ROOT / "schemas" / "intelligence"


class IntelligenceDataLayerTests(unittest.TestCase):
    def test_all_current_synthetic_schema_fixtures_validate(self) -> None:
        schema_files = sorted(SCHEMAS.glob("*.schema.json"))
        self.assertEqual(
            {path.stem.removesuffix(".schema") for path in schema_files},
            {"source", "observation", "artifact", "entity", "feedback", "topic", "artifact_alias"},
        )
        for schema_path in schema_files:
            fixture_path = FIXTURES / f"{schema_path.stem.removesuffix('.schema')}.json"
            with self.subTest(schema=schema_path.name):
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
                validate_instance(fixture, schema)

    def test_deterministic_ids_use_namespace_and_normalized_identity(self) -> None:
        self.assertEqual(source_id(" XHS | Tabris "), source_id("xhs | tabris"))
        self.assertEqual(observation_id("XHS|note-1"), observation_id(" xhs|NOTE-1 "))
        self.assertEqual(artifact_id("arxiv:2606.11709"), artifact_id("arxiv:2606.11709"))
        self.assertEqual(entity_id("Person|Example"), entity_id("person|example"))
        self.assertEqual(feedback_id("art-1|save|time"), feedback_id("art-1|save|time"))
        self.assertEqual(topic_id("Agentic RL"), "topic-agentic-rl")

    def test_duplicate_observation_ingest_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            fixture = json.loads((FIXTURES / "observation.json").read_text(encoding="utf-8"))
            self.assertTrue(store.append_observation(fixture))
            self.assertFalse(store.append_observation(fixture))
            self.assertEqual(list(store.iter_records("observation")), [fixture])

    def test_xhs_and_github_observations_collapse_to_the_same_arxiv_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            xhs_note = {
                "ok": True,
                "note_id": "note-42",
                "url": "https://www.xiaohongshu.com/explore/note-42",
                "title": "A paper worth reading",
                "desc": "arXiv:2606.11709v1 introduces a synthetic method.",
                "author": {"nickname": "Synthetic Curator", "user_id": "public-id"},
                "tags": ["agents"],
                "images": [],
                "retrieval": {"mode": "saved_runtime_state"},
                "published_at": "2026-09-20T12:00:00Z",
            }
            _source, xhs_observation, xhs_artifact_ids = ingest_xhs(
                xhs_note, store, observed_at="2026-09-28T00:00:00Z"
            )
            self.assertEqual(len(xhs_artifact_ids), 1)

            github_source = new_source(
                identity="github|example/research-demo",
                source_type="repository",
                platform="github",
                name="research-demo",
                canonical_url="https://github.com/example/research-demo",
                connector="fixture",
                mode="manual",
                created_at="2026-09-28T00:00:00Z",
            )
            candidates = extract_artifact_candidates(
                "This implementation accompanies arXiv:2606.11709."
            )
            self.assertEqual(len(candidates), 1)
            github_observation = new_observation(
                identity="github|example/research-demo|readme",
                source_id=github_source["source_id"],
                platform="github",
                platform_object_id="example/research-demo",
                kind="discussion",
                title="Paper implementation",
                text="This implementation accompanies arXiv:2606.11709.",
                urls=["https://github.com/example/research-demo"],
                media=[],
                published_at=None,
                observed_at="2026-09-28T00:00:00Z",
                topics=[],
                provenance={
                    "retrieval_mode": "manual",
                    "evidence_level": "source_text",
                    "source_url": "https://github.com/example/research-demo",
                    "collector": "synthetic-fixture",
                },
                artifact_candidates=candidates,
            )
            artifact_candidate = candidates[0]
            github_artifact = new_artifact(
                identity=artifact_identity(artifact_candidate),
                artifact_type="paper",
                canonical_url=str(artifact_candidate["canonical_url"]),
                identifiers=dict(artifact_candidate["identifiers"]),
                observation_ids=[github_observation["observation_id"]],
            )
            self.assertEqual(xhs_artifact_ids[0], github_artifact["artifact_id"])
            store.append_observation(github_observation)
            store.upsert_artifact(github_artifact)

            artifacts = list(store.iter_records("artifact"))
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(
                artifacts[0]["observation_ids"],
                sorted([xhs_observation["observation_id"], github_observation["observation_id"]]),
            )

    def test_doi_precedes_url_in_artifact_identity(self) -> None:
        identity = artifact_identity(
            {
                "identifiers": {"doi": "https://doi.org/10.5555/Example.1"},
                "canonical_url": "https://example.org/landing-page?utm_source=feed",
                "title": "Example",
            }
        )
        self.assertEqual(identity, "doi:10.5555/example.1")

    def test_arxiv_versions_collapse_to_the_same_work_identity(self) -> None:
        self.assertEqual(extract_arxiv_id("arXiv:2606.11709v1"), "2606.11709")
        self.assertEqual(extract_arxiv_id("https://arxiv.org/abs/2606.11709v4"), "2606.11709")

    def test_github_and_huggingface_repository_normalization(self) -> None:
        github_url = "https://github.com/Example/Research-Demo/tree/main/src/file.py?utm_campaign=x"
        hf_url = "https://huggingface.co/datasets/Example/Data-Set/tree/main?fbclid=x"
        self.assertEqual(extract_github_repo(github_url), "example/research-demo")
        self.assertEqual(extract_huggingface_repo(hf_url), "example/data-set")
        self.assertEqual(
            artifact_identity({"canonical_url": github_url}),
            "github:example/research-demo",
        )
        self.assertEqual(artifact_identity({"canonical_url": hf_url}), "huggingface:dataset:example/data-set")

    def test_capture_bridge_only_accepts_link_and_bookmark_and_is_deterministic(self) -> None:
        capture = json.loads((FIXTURES / "capture.json").read_text(encoding="utf-8"))
        source_a, observation_a = bridge_capture(capture)
        source_b, observation_b = bridge_capture(capture)
        self.assertEqual(source_a["source_id"], source_b["source_id"])
        self.assertEqual(observation_a["observation_id"], observation_b["observation_id"])
        with self.assertRaisesRegex(ValueError, "only PKB link/bookmark"):
            bridge_capture({**capture, "type_hint": "task"})

        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            ingest_capture(capture, store)
            ingest_capture(capture, store)
            self.assertEqual(store.stats()["observation"], 1)
            self.assertEqual(store.stats()["artifact"], 1)

    def test_xhs_bridge_uses_sanitized_fields_and_deterministic_post_identity(self) -> None:
        note = _synthetic_xhs_note()
        source_a, observation_a = bridge_xhs(note, observed_at="2026-09-28T00:00:00Z")
        source_b, observation_b = bridge_xhs(note, observed_at="2026-09-28T12:00:00Z")
        self.assertEqual(source_a["source_id"], source_b["source_id"])
        self.assertEqual(observation_a["observation_id"], observation_b["observation_id"])
        self.assertEqual(observation_a["platform_object_id"], "xhs-note-1")
        self.assertEqual(observation_a["provenance"]["evidence_level"], "source_text")
        self.assertEqual(observation_a["artifact_candidates"][0]["identifiers"]["arxiv"], "2606.11709")
        self.assertNotIn("local_path", json.dumps(observation_a, ensure_ascii=False))
        self.assertNotIn("snapshot_path", json.dumps(observation_a, ensure_ascii=False))

    def test_xhs_bridge_accepts_explicit_image_index_candidates(self) -> None:
        note = _synthetic_xhs_note()
        note["images"][0]["artifact_candidates"] = [
            {
                "artifact_type": "repository",
                "title": "Synthetic implementation",
                "canonical_url": "https://github.com/example/agent-demo/tree/main/src",
                "identifiers": {},
                "authors": ["Example Researcher"],
                "organizations": [],
                "summary": "A visible image-source clue.",
                "topics": ["agent-harness"],
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            _source, observation, artifact_ids = ingest_xhs(
                note, store, observed_at="2026-09-28T00:00:00Z"
            )
            repository_candidates = [
                candidate
                for candidate in observation["artifact_candidates"]
                if candidate["artifact_type"] == "repository"
            ]
            self.assertEqual(len(repository_candidates), 1)
            self.assertEqual(len(artifact_ids), 2)
            self.assertEqual(store.stats()["artifact"], 2)
            self.assertEqual(observation["provenance"]["evidence_level"], "image_extract")

    def test_materialized_upsert_is_idempotent_sorted_and_advances_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            first = new_artifact(
                identity="doi:10.5555/materialized",
                artifact_type="paper",
                identifiers={"doi": "10.5555/materialized"},
                observation_ids=["obs-" + "b" * 24],
                status="candidate",
            )
            second = new_artifact(
                identity="doi:10.5555/materialized",
                artifact_type="paper",
                identifiers={"doi": "10.5555/materialized", "arxiv": "2606.11709"},
                observation_ids=["obs-" + "a" * 24],
                status="deep_read",
            )
            store.upsert_artifact(first)
            store.upsert_artifact(second)
            stored = list(store.iter_records("artifact"))
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]["status"], "deep_read")
            self.assertEqual(
                stored[0]["observation_ids"],
                ["obs-" + "a" * 24, "obs-" + "b" * 24],
            )
            self.assertEqual(stored[0]["identifiers"]["arxiv"], "2606.11709")
            self.assertEqual(list(Path(temp).glob("*.tmp")), [])

    def test_cli_ingest_and_stats_work_without_network_or_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            input_file = FIXTURES / "capture.json"
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    cli_main(["ingest-capture", str(input_file), "--store-dir", str(Path(temp) / "store")]),
                    0,
                )
                self.assertEqual(
                    cli_main(["stats", "--store-dir", str(Path(temp) / "store")]),
                    0,
                )

    def test_sensitive_token_never_persisted_and_store_rejects_unsafe_records(self) -> None:
        note = _synthetic_xhs_note()
        note.update(
            {
                "xsec_token": "synthetic-xsec-secret",
                "cookie": "synthetic-cookie-secret",
                "authorization": "Bearer synthetic-auth-secret",
                "session_token": "synthetic-session-secret",
                "token": "synthetic-generic-token-secret",
                "raw_runtime_state": {"session": "synthetic-runtime-secret"},
                "desc": (
                    "Read https://www.xiaohongshu.com/explore/xhs-note-1"
                    "?xsec_token=synthetic-xsec-secret and cookie=synthetic-cookie-secret"
                ),
            }
        )
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            ingest_xhs(note, store, observed_at="2026-09-28T00:00:00Z")
            serialized = "\n".join(path.read_text(encoding="utf-8") for path in Path(temp).glob("*.jsonl"))
            for secret in (
                "synthetic-xsec-secret",
                "synthetic-cookie-secret",
                "synthetic-auth-secret",
                "synthetic-session-secret",
                "synthetic-generic-token-secret",
                "synthetic-runtime-secret",
            ):
                self.assertNotIn(secret, serialized)
            self.assertNotIn("xsec_token", serialized)
            self.assertNotIn('"cookie"', serialized)
            with self.assertRaisesRegex(ValueError, "private field"):
                store.upsert_source(
                    {
                        **_synthetic_source(),
                        "external_ids": {"cookie": "should-never-persist"},
                    }
                )

    def test_url_normalization_covers_xhs_zhihu_and_common_tracking_params(self) -> None:
        self.assertEqual(
            canonicalize_url(
                "https://www.xiaohongshu.com/explore/abc?xsec_token=secret&xsec_source=pc_share&utm_source=x"
            ),
            "https://www.xiaohongshu.com/explore/abc",
        )
        self.assertEqual(
            canonicalize_url("https://www.zhihu.com/question/123/answer/456?utm_campaign=feed&fbclid=abc"),
            "https://www.zhihu.com/question/123/answer/456",
        )
        self.assertEqual(
            canonicalize_url("https://example.org/a?keep=1&gclid=abc#fragment"),
            "https://example.org/a?keep=1",
        )

    def test_feedback_append_preserves_research_value_events(self) -> None:
        feedback = new_feedback(
            artifact_id="art-" + "a" * 24,
            event="deep_read",
            occurred_at="2026-09-28T08:00:00Z",
            surface="daily_feed",
            rank=3,
            query="agent memory",
        )
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            self.assertTrue(store.append_feedback(feedback))
            self.assertFalse(store.append_feedback(feedback))
            stored = list(store.iter_records("feedback"))
            self.assertEqual(stored[0]["event"], "deep_read")
            self.assertEqual(stored[0]["context"]["rank"], 3)

    def test_topics_support_multiple_parents_and_all_seed_topics_exist(self) -> None:
        yaml_text = (ROOT / "data" / "intelligence" / "topics.yaml").read_text(encoding="utf-8")
        blocks = re.split(r"(?m)^  - topic_id: ", yaml_text)[1:]
        entries = []
        for block in blocks:
            topic_id_value = block.splitlines()[0].strip()
            name = re.search(r"(?m)^    name: (.+)$", block)
            parents = re.search(r"(?m)^    parents: \[(.*)\]$", block)
            entries.append((topic_id_value, name.group(1) if name else "", parents.group(1).strip() if parents else ""))
        self.assertEqual(len(entries), 22)
        self.assertEqual(sum(not parents for _topic, _name, parents in entries), 11)
        self.assertEqual(
            {name for _topic, name, parents in entries if not parents},
            {
                "Training Data and Scaling",
                "Model Architecture",
                "Post-training and Alignment",
                "Reasoning, Verification and Planning",
                "Knowledge, Retrieval, Long Context and Memory",
                "LLM Agents and Tool Use",
                "Multimodal Models and World Models",
                "Efficiency, Systems and Deployment",
                "Evaluation and Interpretability",
                "Safety, Privacy, Security and Governance",
                "Domain-specific LLMs and AI for Science",
            },
        )
        cross_cutting = {topic for topic, _name, parents in entries if parents}
        self.assertEqual(
            cross_cutting,
            {
                "topic-search-agent", "topic-agentic-rl", "topic-self-evolving-agent",
                "topic-agent-harness", "topic-memory", "topic-rag", "topic-opd",
                "topic-verifier", "topic-reward", "topic-multi-agent", "topic-inference-serving",
            },
        )
        self.assertGreaterEqual(len(entries[11][2].split(",")), 2)

    def test_malformed_record_fails_closed_and_unknown_artifact_stays_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            with self.assertRaisesRegex(ValueError, "requires observation_id"):
                store.append_observation({"schema": "bubblevan/intelligence-observation/v1"})
            with self.assertRaisesRegex(SchemaValidationError, "unexpected property"):
                store.upsert_source({**_synthetic_source(), "unexpected": "field"})
            (Path(temp) / "observations-2026-09.jsonl").write_text("{not json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "malformed JSONL"):
                store.get_by_id("observation", "obs-" + "0" * 24)

        unresolved = {
            "artifact_type": "other",
            "title": "An unidentified research item",
            "canonical_url": "",
            "identifiers": {},
        }
        self.assertEqual(artifact_identity(unresolved), "title:an unidentified research item")
        artifact = new_artifact(
            identity=artifact_identity(unresolved),
            artifact_type="other",
            title=unresolved["title"],
        )
        self.assertEqual(artifact["status"], "candidate")
        self.assertEqual(artifact["canonical_url"], "")
        self.assertFalse(any(artifact["identifiers"].values()))


def _synthetic_source() -> dict[str, object]:
    return new_source(
        identity="fixture|source",
        source_type="curator",
        platform="xiaohongshu",
        name="Synthetic Curator",
        canonical_url="https://www.xiaohongshu.com/user/profile/synthetic",
        connector="fixture",
        mode="manual",
        created_at="2026-09-28T00:00:00Z",
    )


def _synthetic_xhs_note() -> dict[str, object]:
    return {
        "ok": True,
        "note_id": "xhs-note-1",
        "url": "https://www.xiaohongshu.com/explore/xhs-note-1?xsec_token=synthetic",
        "title": "Synthetic research note",
        "desc": "Paper: arXiv:2606.11709.",
        "author": {"nickname": "Synthetic Curator", "user_id": "public-user-1"},
        "tags": ["agentic-rl", "memory"],
        "stats": {"likes": "1", "collects": "0", "comments": "0"},
        "images": [
            {
                "image_id": "fixture-image",
                "url": "https://cdn.example.org/image.jpg?session=synthetic",
                "preview_url": "",
                "local_path": "must-not-be-copied",
            }
        ],
        "comments_text": "",
        "published_at": "2026-09-20T12:00:00Z",
        "retrieval": {
            "mode": "saved_runtime_state",
            "logged_in": False,
            "used_user_profile": False,
            "snapshot_path": "must-not-be-copied",
        },
    }


if __name__ == "__main__":
    unittest.main()
