from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from .feed.feedback_projection import project_feedback
from .feed.generation import _merge_route
from .feed.models import default_profile, new_feedback, profile_hash, update_profile
from .feed.policy import rank_and_select
from .feed.service import apply_feedback, daily_feed, feedback_stats
from .feed.storage import FeedRepository
from .ops.locks import feed_lock_path
from .ids import artifact_id, source_id
from .models import new_artifact, new_observation, new_source
from .retrieval.dense import DenseRetriever, DeterministicFakeEmbedding
from .store import JsonlStore


ROOT = Path(__file__).resolve().parents[2]


def _candidate(number: int, *, source: str = "src-a", topic: str = "topic-a",
               seen: bool = False, tier: int = 4) -> dict:
    return {"artifact_id": f"art-{number:024x}", "source_ids": [source], "topics": [topic],
            "published_at": "2026-09-28T00:00:00Z", "first_observed_at": None,
            "freshness_basis": "published_at", "previously_seen": seen, "interest_tier": tier,
            "selected_topic_matches": [], "useful_exemplar_matches": [], "topic_exact": False,
            "why": "近期新内容。"}


def _fake_dense(snapshot, runtime_dir, model, revision, device):
    retriever = DenseRetriever(DeterministicFakeEmbedding(dimension=64))
    retriever.build(snapshot, runtime_dir)
    return retriever, "available"


class FeedProjectionTests(unittest.TestCase):
    def test_profile_hash_is_stable_and_explicit_update_changes_version_and_hash(self):
        profile = default_profile(created_at="2026-09-29T00:00:00Z")
        self.assertEqual(profile_hash(profile), profile_hash(deepcopy(profile)))
        updated = update_profile(profile, add={"selected_topic_ids": ["topic-search-agent"]},
                                 updated_at="2026-09-29T01:00:00Z")
        self.assertEqual(updated["version"], 2)
        self.assertNotEqual(profile_hash(profile), profile_hash(updated))

    def test_route_union_deduplicates_by_canonical_artifact_id_and_keeps_best_ranks(self):
        artifact = "art-aaaaaaaaaaaaaaaaaaaaaaaa"
        row = {"artifact_id": artifact, "dense_best_rank": None, "bm25_best_rank": None,
               "evidence": [], "topic_exact": False}
        by_id = {artifact: row}
        _merge_route(by_id, [{"artifact_id": artifact, "rank": 8}, {"artifact_id": artifact, "rank": 3}], "dense_selected_topic")
        self.assertEqual(len(by_id), 1)
        self.assertEqual(by_id[artifact]["dense_best_rank"], 3)

    def test_hide_and_blocked_source_or_topic_are_hard_exclusions(self):
        candidates = [_candidate(1), _candidate(2, source="src-block"), _candidate(3, topic="topic-block")]
        profile = {"followed_source_ids": [], "selected_topic_ids": [], "blocked_source_ids": ["src-block"],
                   "blocked_topic_ids": ["topic-block"]}
        projection = {"hidden_artifact_ids": [candidates[0]["artifact_id"]], "impression_counts": {},
                      "blocked_source_ids": [], "blocked_topic_ids": []}
        selected, metrics = rank_and_select(candidates, profile=profile, projection=projection, feed_date="2026-09-29")
        self.assertEqual(selected, [])
        self.assertEqual(metrics["hidden_leak_count"], 0)

    def test_not_relevant_does_not_block_source_and_save_is_not_exemplar(self):
        events = [
            new_feedback(artifact_id="art-aaaaaaaaaaaaaaaaaaaaaaaa", action="not_relevant", feed_run_id="feed-aaaaaaaaaaaaaaaaaaaaaaaa", rank=1, occurred_at="2026-09-29T00:00:00Z", identity="not-relevant"),
            new_feedback(artifact_id="art-bbbbbbbbbbbbbbbbbbbbbbbb", action="save", feed_run_id="feed-aaaaaaaaaaaaaaaaaaaaaaaa", rank=2, occurred_at="2026-09-29T00:00:01Z", identity="save"),
        ]
        projection = project_feedback(events)
        self.assertEqual(projection["blocked_source_ids"], [])
        self.assertEqual(projection["useful_artifact_ids"], [])
        self.assertEqual(projection["saved_artifact_ids"], ["art-bbbbbbbbbbbbbbbbbbbbbbbb"])
        self.assertEqual(projection["not_relevant_artifact_ids"], ["art-aaaaaaaaaaaaaaaaaaaaaaaa"])

    def test_useful_becomes_exemplar_and_retract_removes_it(self):
        useful = new_feedback(artifact_id="art-aaaaaaaaaaaaaaaaaaaaaaaa", action="useful", feed_run_id="feed-aaaaaaaaaaaaaaaaaaaaaaaa", rank=1, occurred_at="2026-09-29T00:00:00Z", identity="useful")
        retract = new_feedback(artifact_id=useful["artifact_id"], action="retract", feed_run_id="feed-aaaaaaaaaaaaaaaaaaaaaaaa", rank=1, supersedes_feedback_id=useful["feedback_id"], occurred_at="2026-09-29T00:01:00Z", identity="retract")
        self.assertEqual(project_feedback([useful])["useful_artifact_ids"], [useful["artifact_id"]])
        self.assertEqual(project_feedback([useful, retract])["useful_artifact_ids"], [])

    def test_v1_feedback_is_readable_and_save_does_not_become_useful(self):
        row = json.loads((ROOT / "scripts/intelligence/fixtures/feedback.json").read_text(encoding="utf-8"))
        self.assertEqual(row["schema"], "bubblevan/intelligence-feedback/v1")
        self.assertEqual(project_feedback([row])["useful_artifact_ids"], [])

    def test_profile_hash_is_independent_of_timestamp_noise(self):
        first = default_profile(created_at="2026-09-29T00:00:00Z")
        second = dict(first, updated_at="2026-09-30T00:00:00Z")
        self.assertEqual(profile_hash(first), profile_hash(second))


class FeedPolicyTests(unittest.TestCase):
    def test_previous_impressions_are_demoted_below_unseen_candidates(self):
        candidates = [_candidate(1, seen=True, tier=0), _candidate(2, seen=False, tier=4)]
        selected, _ = rank_and_select(candidates, profile={"selected_topic_ids": [], "followed_source_ids": [], "blocked_source_ids": [], "blocked_topic_ids": []},
                                      projection={"hidden_artifact_ids": [], "impression_counts": {candidates[0]["artifact_id"]: 1}}, feed_date="2026-09-29")
        self.assertEqual(selected[0]["artifact_id"], candidates[1]["artifact_id"])

    def test_selected_topic_and_followed_source_get_explicit_priority(self):
        candidate = _candidate(1, source="src-followed", topic="topic-selected")
        selected, _ = rank_and_select([candidate], profile={"selected_topic_ids": ["topic-selected"], "followed_source_ids": ["src-followed"], "blocked_source_ids": [], "blocked_topic_ids": []},
                                      projection={"hidden_artifact_ids": [], "impression_counts": {}}, feed_date="2026-09-29")
        self.assertEqual(selected[0]["interest_tier"], 0)
        self.assertIn("近期", selected[0]["why"])

    def test_source_diversity_cap_and_topic_diversity_cap_work(self):
        candidates = []
        for index in range(12):
            candidates.append(_candidate(index + 1, source=f"src-{index // 2}", topic=f"topic-{index // 4}"))
        selected, metrics = rank_and_select(candidates, profile={"selected_topic_ids": [], "followed_source_ids": [], "blocked_source_ids": [], "blocked_topic_ids": []},
                                            projection={"hidden_artifact_ids": [], "impression_counts": {}}, feed_date="2026-09-29")
        self.assertEqual(len(selected), 12)
        self.assertLessEqual(max(CounterLike(row["source_ids"][0] for row in selected).values()), 2)
        self.assertLessEqual(max(CounterLike(row["topics"][0] for row in selected).values()), 4)
        self.assertEqual(metrics["items_with_reason"], 12)

    def test_primary_artifact_is_preferred_with_other_features_equal(self):
        referenced = _candidate(1)
        referenced["mention_role"] = "referenced"
        primary = _candidate(2)
        primary["mention_role"] = "primary"
        selected, _ = rank_and_select([referenced, primary], profile={"selected_topic_ids": [], "followed_source_ids": [], "blocked_source_ids": [], "blocked_topic_ids": []},
                                      projection={"hidden_artifact_ids": [], "impression_counts": {}}, feed_date="2026-09-29")
        self.assertEqual(selected[0]["mention_role"], "primary")

    def test_not_relevant_is_excluded_as_an_exact_artifact_only(self):
        candidates = [_candidate(1, tier=0), _candidate(2, tier=4)]
        projection = {"hidden_artifact_ids": [], "impression_counts": {},
                      "not_relevant_artifact_ids": [candidates[0]["artifact_id"]]}
        selected, _ = rank_and_select(candidates, profile={"selected_topic_ids": [], "followed_source_ids": [], "blocked_source_ids": [], "blocked_topic_ids": []},
                                      projection=projection, feed_date="2026-09-29")
        self.assertEqual([row["artifact_id"] for row in selected], [candidates[1]["artifact_id"]])

    def test_diversity_caps_relax_when_pool_is_too_small(self):
        candidates = [_candidate(index + 1, source="src-only", topic="topic-only") for index in range(5)]
        selected, metrics = rank_and_select(candidates, profile={"selected_topic_ids": [], "followed_source_ids": [], "blocked_source_ids": [], "blocked_topic_ids": []},
                                            projection={"hidden_artifact_ids": [], "impression_counts": {}}, feed_date="2026-09-29")
        self.assertEqual(len(selected), 5)
        self.assertGreater(metrics["source_cap_used"], 2)
        self.assertGreater(metrics["topic_cap_used"], 4)

    def test_feed_stops_at_ten_if_filling_to_twelve_would_be_too_concentrated(self):
        candidates = [_candidate(index + 1,
                                 source="src-a" if index < 8 else "src-b" if index < 14 else "src-c",
                                 topic="topic-majority" if index < 13 else "topic-minority" if index < 15 else "topic-rare")
                      for index in range(16)]
        selected, metrics = rank_and_select(candidates,
            profile={"selected_topic_ids": [], "followed_source_ids": [], "blocked_source_ids": [], "blocked_topic_ids": []},
            projection={"hidden_artifact_ids": [], "impression_counts": {}}, feed_date="2026-09-29")
        self.assertEqual(len(selected), 10)
        self.assertGreater(metrics["source_cap_used"], 2)
        self.assertGreater(metrics["topic_cap_used"], 4)

    def test_every_selected_candidate_has_a_human_readable_reason(self):
        candidates = [_candidate(1), _candidate(2)]
        selected, metrics = rank_and_select(candidates, profile={"selected_topic_ids": [], "followed_source_ids": [], "blocked_source_ids": [], "blocked_topic_ids": []},
                                            projection={"hidden_artifact_ids": [], "impression_counts": {}}, feed_date="2026-09-29")
        self.assertTrue(all(row["why"] for row in selected))
        self.assertEqual(metrics["items_with_reason"], metrics["selected_count"])


class FeedServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store_dir = self.root / "events"
        self.runtime_dir = self.root / "runtime"
        self.private_dir = self.root / "private" / "feed"
        self.store = JsonlStore(self.store_dir)
        self.repository = FeedRepository(self.private_dir)
        self._add_corpus()

    def tearDown(self):
        self.temp.cleanup()

    def _add_corpus(self):
        source_ids = [source_id("feed-test|source-a"), source_id("feed-test|source-b")]
        topics = ["topic-search-agent", "topic-memory", "topic-agentic-rl"]
        for index, src in enumerate(source_ids):
            self.store.upsert_source(new_source(identity=f"feed-test|source-{'a' if index == 0 else 'b'}", source_type="feed", platform="test",
                                                name=f"Test Source {index}", topics=topics, connector="manual", mode="manual"))
        self.artifact_ids = []
        observed_at = (date.today() - timedelta(days=1)).isoformat() + "T12:00:00Z"
        published_at = (date.today() - timedelta(days=1)).isoformat() + "T00:00:00Z"
        for index in range(16):
            arxiv = f"2609.{index + 10000:05d}"
            identity = f"arxiv:{arxiv}"
            aid = artifact_id(identity)
            self.artifact_ids.append(aid)
            obs = new_observation(
                identity=f"feed-test|observation-{index}", source_id=source_ids[index % 2], platform="arxiv",
                platform_object_id=f"item-{index}", kind="paper_announcement", title=f"Agent memory system research {index}",
                text=(f"Research article number {index} describes agent memory and search methods with enough detail "
                      "to be eligible in the retrieval corpus and support lexical matching."),
                urls=[f"https://arxiv.org/abs/{arxiv}"], media=[], published_at=published_at, observed_at=observed_at,
                topics=[topics[index % 3]], provenance={"retrieval_mode": "manual", "evidence_level": "source_text",
                    "source_url": f"https://arxiv.org/abs/{arxiv}", "collector": "feed-test"},
                artifact_candidates=[{"artifact_type": "paper", "title": f"Agent memory system research {index}",
                    "canonical_url": f"https://arxiv.org/abs/{arxiv}",
                    "identifiers": {"doi": None, "arxiv": arxiv, "github": None, "huggingface": None},
                    "authors": [], "organizations": [], "summary": "Synthetic relevant research summary.",
                    "topics": [topics[index % 3]], "mention": {"role": "primary", "evidence_level": "source_text",
                        "origin": "title", "confidence": 1.0}}]
            )
            artifact = new_artifact(identity=identity, artifact_type="paper", title=f"Agent memory system research {index}",
                canonical_url=f"https://arxiv.org/abs/{arxiv}",
                identifiers={"doi": None, "arxiv": arxiv, "github": None, "huggingface": None},
                published_at=published_at, summary="Synthetic relevant research summary.", topics=[topics[index % 3]],
                observation_ids=[obs["observation_id"]], status="candidate")
            self.store.append_observation(obs)
            self.store.upsert_artifact(artifact)

    def _profile(self):
        profile = default_profile(created_at="2026-09-29T00:00:00Z")
        profile = update_profile(profile, add={"selected_topic_ids": ["topic-search-agent", "topic-memory", "topic-agentic-rl"],
                                               "followed_source_ids": [source_id("feed-test|source-a"), source_id("feed-test|source-b")]},
                                 updated_at="2026-09-29T00:00:00Z")
        self.repository.save_profile(profile)

    def test_daily_generation_uses_source_topic_dense_and_bm25_and_no_graph_or_impressions(self):
        self._profile()
        before = self.repository.all_feedback(self.store)
        run = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(), dense_resource_factory=_fake_dense)
        self.assertEqual(run["policy_version"], "feed-v0")
        self.assertEqual(run["metrics"]["hidden_leak_count"], 0)
        self.assertTrue(run["items"])
        self.assertTrue(all(item["why"] for item in run["items"]))
        self.assertGreater(run["retrieval_routes"]["source"]["candidates"], 0)
        self.assertGreater(run["retrieval_routes"]["topic"]["candidates"], 0)
        self.assertGreater(run["retrieval_routes"]["bm25"]["candidates"], 0)
        self.assertGreater(run["retrieval_routes"]["dense"]["candidates"], 0)
        self.assertNotIn("graph", run["retrieval_routes"])
        self.assertEqual(self.repository.all_feedback(self.store), before)

    def test_impression_is_idempotent_and_historical_feedback_stays_bound_after_refresh(self):
        run = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(), dense_resource_factory=_fake_dense)
        item = run["items"][0]
        first = apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"], artifact_id=item["artifact_id"], action="impression")
        second = apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"], artifact_id=item["artifact_id"], action="impression")
        self.assertEqual(first["status"], "recorded")
        self.assertEqual(second["status"], "already_recorded")
        self.assertEqual(self.repository.feedback_store.stats()["feedback"], 1)
        refresh = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=run["feed_date"], refresh=True, dense_resource_factory=_fake_dense)
        self.assertEqual(refresh["revision"], run["revision"] + 1)
        self.assertEqual(refresh["supersedes_feed_run_id"], run["feed_run_id"])
        event = self.repository.all_feedback(self.store)[0]
        self.assertEqual(event["context"]["feed_run_id"], run["feed_run_id"])

    def test_same_day_run_returns_existing_and_refresh_is_immutable_new_revision(self):
        first = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(), dense_resource_factory=_fake_dense)
        second = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(), dense_resource_factory=_fake_dense)
        self.assertEqual(first["feed_run_id"], second["feed_run_id"])
        third = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(), refresh=True, dense_resource_factory=_fake_dense)
        self.assertEqual(third["revision"], 2)
        self.assertNotEqual(first["feed_run_id"], third["feed_run_id"])
        self.assertEqual(len(self.repository.runs()), 2)

    def test_same_profile_corpus_feedback_and_date_reproduce_ids_order_and_reasons(self):
        date_value = date.today().isoformat()
        first = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date_value, dense_resource_factory=_fake_dense)
        second_private = self.root / "other-private" / "feed"
        second = daily_feed(self.store_dir, self.root / "other-runtime", second_private,
                            date=date_value, dense_resource_factory=_fake_dense)
        self.assertEqual(first["feed_run_id"], second["feed_run_id"])
        self.assertEqual(first["items"], second["items"])

    def test_dense_failure_falls_back_to_recent_lexical_source_and_topic(self):
        self._profile()
        run = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(),
                         dense_resource_factory=lambda *args: (None, "unavailable:RuntimeError"))
        self.assertTrue(run["items"])
        self.assertEqual(run["retrieval_routes"]["dense"]["status"], "unavailable:RuntimeError")
        self.assertGreater(run["retrieval_routes"]["topic"]["candidates"], 0)

    def test_useful_exemplar_is_used_by_dense_route_on_the_following_run(self):
        first = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(), dense_resource_factory=_fake_dense)
        item = first["items"][0]
        apply_feedback(self.repository, self.store, feed_run_id=first["feed_run_id"], artifact_id=item["artifact_id"], action="useful")
        second = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=first["feed_date"], refresh=True, dense_resource_factory=_fake_dense)
        self.assertGreater(second["retrieval_routes"]["dense"]["candidates"], 0)
        self.assertTrue(any(any(evidence["route"] == "dense_useful_exemplar" for evidence in row.get("evidence", []))
                            for row in second["items"]))

    def test_topic_feedback_blocks_only_matching_topic_and_restore_reopens_it(self):
        first = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(), dense_resource_factory=_fake_dense)
        item = next(row for row in first["items"] if row.get("topics"))
        topic = item["topics"][0]
        apply_feedback(self.repository, self.store, feed_run_id=first["feed_run_id"], artifact_id=item["artifact_id"],
                       action="show_less_of_topic", target_id=topic)
        second = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=first["feed_date"], refresh=True, dense_resource_factory=_fake_dense)
        self.assertFalse(any(topic in row["topics"] for row in second["items"]))
        other = next(row for row in first["items"] if topic in row.get("topics", []))
        apply_feedback(self.repository, self.store, feed_run_id=first["feed_run_id"], artifact_id=other["artifact_id"],
                       action="restore_topic", target_id=topic)
        third = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=first["feed_date"], refresh=True, dense_resource_factory=_fake_dense)
        self.assertTrue(any(topic in row["topics"] for row in third["items"]))

    def test_saved_projection_unsave_and_unhide_are_reversible_and_stats_are_aggregate(self):
        run = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(), dense_resource_factory=_fake_dense)
        item = run["items"][0]
        for action in ("save", "hide"):
            apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"], artifact_id=item["artifact_id"], action=action)
        apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"], artifact_id=item["artifact_id"], action="unsave")
        apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"], artifact_id=item["artifact_id"], action="unhide")
        projection = project_feedback(self.repository.all_feedback(self.store))
        self.assertNotIn(item["artifact_id"], projection["saved_artifact_ids"])
        self.assertNotIn(item["artifact_id"], projection["hidden_artifact_ids"])
        stats = feedback_stats(self.store, self.repository)
        self.assertIn("by_source", stats)
        self.assertNotIn("summary", json.dumps(stats))

    def test_feed_writer_uses_a_short_lived_portalocker_file(self):
        from .ops.locks import feed_writer_lock
        path = feed_lock_path(self.private_dir)
        with feed_writer_lock(self.private_dir, timeout_seconds=1.0):
            self.assertTrue(path.exists())
        self.assertFalse((self.private_dir.parent / ".ui-writer.json").exists())

    def test_private_profile_and_feed_paths_are_ignored_by_git_and_hugo(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        hugo = (ROOT / "hugo.toml").read_text(encoding="utf-8")
        self.assertIn("/data/intelligence/private/", ignore)
        self.assertIn("! intelligence/private/**", hugo)

    def test_hidden_source_and_topic_feedback_change_the_next_revision(self):
        self._profile()
        run = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(), dense_resource_factory=_fake_dense)
        item = run["items"][0]
        apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"], artifact_id=item["artifact_id"], action="hide")
        hidden_run = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=run["feed_date"], refresh=True, dense_resource_factory=_fake_dense)
        self.assertNotIn(item["artifact_id"], {row["artifact_id"] for row in hidden_run["items"]})
        next_item = hidden_run["items"][0]
        source = next(iter(next_item["source_ids"]))
        apply_feedback(self.repository, self.store, feed_run_id=hidden_run["feed_run_id"], artifact_id=next_item["artifact_id"], action="show_less_from_source", target_id=source)
        source_run = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=run["feed_date"], refresh=True, dense_resource_factory=_fake_dense)
        self.assertFalse(any(source in row["source_ids"] for row in source_run["items"]))

    def test_candidate_feedback_actions_retract_and_old_v1_are_compatible(self):
        run = daily_feed(self.store_dir, self.runtime_dir, self.private_dir, date=date.today().isoformat(), dense_resource_factory=_fake_dense)
        item = run["items"][0]
        event = apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"], artifact_id=item["artifact_id"], action="useful")
        self.assertIn(item["artifact_id"], project_feedback(self.repository.all_feedback(self.store))["useful_artifact_ids"])
        retract = apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"], artifact_id=item["artifact_id"], action="retract", supersedes_feedback_id=event["feedback_id"])
        self.assertEqual(retract["status"], "recorded")
        self.assertNotIn(item["artifact_id"], project_feedback(self.repository.all_feedback(self.store))["useful_artifact_ids"])

    def test_not_relevant_hides_only_exact_artifact_and_retract_restores_it(self):
        run = daily_feed(self.store_dir, self.runtime_dir, self.private_dir,
                         date=date.today().isoformat(), dense_resource_factory=_fake_dense)
        item = run["items"][0]
        marked = apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"],
                                artifact_id=item["artifact_id"], action="not_relevant")
        projection = project_feedback(self.repository.all_feedback())
        self.assertEqual(projection["not_relevant_artifact_ids"], [item["artifact_id"]])
        self.assertEqual(projection["hidden_artifact_ids"], [])
        self.assertEqual(projection["blocked_source_ids"], [])
        self.assertEqual(projection["blocked_topic_ids"], [])
        suppressed = daily_feed(self.store_dir, self.runtime_dir, self.private_dir,
                                date=run["feed_date"], refresh=True, dense_resource_factory=_fake_dense)
        self.assertNotIn(item["artifact_id"], {row["artifact_id"] for row in suppressed["items"]})

        apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"],
                       artifact_id=item["artifact_id"], action="retract",
                       supersedes_feedback_id=marked["feedback_id"])
        restored = daily_feed(self.store_dir, self.runtime_dir, self.private_dir,
                              date=run["feed_date"], refresh=True, dense_resource_factory=_fake_dense)
        self.assertIn(item["artifact_id"], {row["artifact_id"] for row in restored["items"]})

        hidden = apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"],
                                artifact_id=item["artifact_id"], action="hide")
        hidden_run = daily_feed(self.store_dir, self.runtime_dir, self.private_dir,
                                date=run["feed_date"], refresh=True, dense_resource_factory=_fake_dense)
        self.assertNotIn(item["artifact_id"], {row["artifact_id"] for row in hidden_run["items"]})
        self.assertIn(item["artifact_id"], project_feedback(self.repository.all_feedback())["hidden_artifact_ids"])
        self.assertNotIn(item["artifact_id"], project_feedback(self.repository.all_feedback())["not_relevant_artifact_ids"])
        apply_feedback(self.repository, self.store, feed_run_id=run["feed_run_id"],
                       artifact_id=item["artifact_id"], action="retract",
                       supersedes_feedback_id=hidden["feedback_id"])


class CounterLike(dict):
    def __init__(self, values):
        from collections import Counter
        super().__init__(Counter(values))


if __name__ == "__main__":
    unittest.main()
