from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .aliases import ArtifactAliases
from .artifacts import materialize_artifact_candidates
from .connectors.base import ConnectorCheckpoint, ConnectorContext, ConnectorSpec, FetchResult
from .connectors.http import HttpResponse, HttpTransportError, SharedHttpClient, _CategorizedHTTPConnection
from .connectors.openalex_works import OpenAlexWorksConnector, probe_openalex_query
from .connectors.openreview_submissions import OpenReviewSubmissionsConnector
from .connectors.registry import ConnectorRegistry
from .connectors.state import ConnectorStateStore
from .coverage import source_coverage
from .discovery.openalex_topics import OpenAlexTopicProposalStore
from .discovery.source_proposals import (
    SourceProposalStore, SourceSubscriptionRegistry, discover_rss_proposals, probe_rss_endpoint,
    source_from_proposal,
)
from .graph.backfill import graph_backfill
from .graph.builders.observation_artifact import build_observation_artifact_edges
from .graph.store import GraphStore
from .ids import artifact_id
from .models import new_artifact, new_observation, new_source
from .ops.daily import _scheduled_transport_recovery, run_daily_pipeline
from .repositories.artifacts import ArtifactRepository
from .runner import load_merged_source_catalog, run_source
from .store import JsonlStore


ROOT = Path(__file__).resolve().parents[2]
NOW = "2026-09-29T08:00:00Z"


class FakeHttp:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, *, headers=None):
        self.urls.append((url, dict(headers or {})))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    @staticmethod
    def retry_after_seconds(_headers):
        return None


def _source(identity: str, name: str, *, connector: str = "fixture", config=None):
    return new_source(identity=identity, source_type="publication", platform="fixture", name=name,
                      canonical_url="https://example.org/", connector=connector, mode="api",
                      acquisition_config=config, created_at=NOW)


def _paper_observation(source_id_value: str, identity: str, doi: str, observed_at: str,
                       *, title: str | None = None, arxiv: str | None = None,
                       source_platform: str = "fixture"):
    canonical = f"https://doi.org/{doi}"
    identifiers = {"doi": doi}
    if arxiv:
        identifiers["arxiv"] = arxiv
    title = title or f"Research {doi}"
    candidate = {"artifact_type": "paper", "title": title, "canonical_url": canonical,
                 "identifiers": identifiers, "authors": ["Example Author"], "organizations": [],
                 "summary": "A structured paper abstract.", "published_at": observed_at,
                 "topics": ["topic-search-agent"],
                 "mention": {"role": "primary", "evidence_level": "api_metadata",
                             "origin": "fixture", "confidence": 1.0}}
    return new_observation(
        identity=identity, source_id=source_id_value, platform=source_platform,
        platform_object_id=identity, kind="indexed_work", title=title, text="A structured paper abstract.",
        urls=[canonical], media=[], published_at=observed_at, observed_at=observed_at,
        topics=["topic-search-agent"], authors=["Example Author"],
        provenance={"retrieval_mode": "fixture", "evidence_level": "api_metadata",
                    "source_url": "https://example.org/item", "collector": "fixture"},
        artifact_candidates=[candidate],
    )


class TransportTaxonomyTests(unittest.TestCase):
    def test_transport_phase_categories_are_structured_and_private(self):
        with patch("http.client.HTTPConnection.connect", side_effect=OSError("private-host-secret")):
            connection = _CategorizedHTTPConnection("example.org")
            with self.assertRaises(HttpTransportError) as caught:
                connection.connect()
        self.assertEqual(caught.exception.category, "transport_other")
        self.assertEqual(str(caught.exception), "HTTP request failed")
        self.assertNotIn("private-host-secret", str(caught.exception))

        with patch("http.client.HTTPConnection.getresponse", side_effect=TimeoutError("url-token-secret")):
            connection = _CategorizedHTTPConnection("example.org")
            with self.assertRaises(HttpTransportError) as caught:
                connection.getresponse()
        self.assertEqual(caught.exception.category, "read_timeout")
        self.assertEqual(str(caught.exception), "HTTP request failed")
        self.assertNotIn("url-token-secret", str(caught.exception))

    def test_transport_taxonomy_keeps_dns_tls_and_connection_codes(self):
        import socket
        import ssl
        from .connectors.http import _transport_category
        self.assertEqual(_transport_category(socket.gaierror("token host")), "dns_error")
        self.assertEqual(_transport_category(ssl.SSLError("cookie")), "tls_error")
        self.assertEqual(_transport_category(ConnectionResetError("secret")), "connection_reset")

    def test_https_handler_uses_urllib_context_without_nonexistent_private_field(self):
        from urllib.request import Request
        from .connectors.http import _CategorizedHTTPSHandler

        handler = _CategorizedHTTPSHandler()
        with patch.object(handler, "do_open", return_value="ok") as do_open:
            self.assertEqual(handler.https_open(Request("https://example.org/feed")), "ok")
        self.assertEqual(do_open.call_args.kwargs["context"], handler._context)

    def test_official_openreview_client_transport_errors_are_safe(self):
        from .connectors.openreview_submissions import _official_request

        connection_error_type = type("ConnectionError", (RuntimeError,),
                                     {"__module__": "requests.exceptions"})
        with self.assertRaises(HttpTransportError) as caught:
            _official_request(lambda: (_ for _ in ()).throw(connection_error_type("token-secret")))
        self.assertEqual(caught.exception.category, "transport_other")
        self.assertNotIn("token-secret", str(caught.exception))


class StructuredConnectorTests(unittest.TestCase):
    def test_openreview_requires_explicit_version_and_only_ingests_public_submission_decision(self):
        calls = []
        invitations = {
            "venue/Submission": [
                {"id": "paper-1", "forum": "paper-1", "readers": ["everyone"],
                 "cdate": 1790000000000,
                 "content": {"title": {"value": "A paper"}, "abstract": {"value": "Abstract"},
                             "authors": {"value": ["A. Researcher"]}, "pdf": {"value": "/pdf/paper-1"}}},
                {"id": "private-submission", "forum": "private-submission", "readers": ["PC"],
                 "content": {"title": {"value": "private title"}, "abstract": {"value": "private"}}},
                {"id": "missing-readers", "forum": "missing-readers",
                 "content": {"title": {"value": "ambiguous title"}}},
            ],
            "venue/Decision": [
                {"id": "decision-1", "forum": "paper-1", "readers": ["everyone"],
                 "pdate": 1790000000000, "content": {"decision": {"value": "Accept"}}},
                {"id": "private-review", "forum": "paper-1", "readers": ["PC"],
                 "content": {"decision": {"value": "Reject"}}},
            ],
        }

        class Client:
            def get_invitation(self, *, id):
                return {"id": id}

            def get_all_notes(self, **_kwargs):
                raise AssertionError("the unbounded OpenReview method must not be used")

            def get_notes(self, *, invitation, limit):
                calls.append((invitation, limit))
                return invitations[invitation]

        connector = OpenReviewSubmissionsConnector(client_factory=lambda version: Client())
        source = _source("openreview|venue", "Venue",
                         connector="openreview-submissions",
                         config={"venue": {"api_version": 2, "invitation": "venue/Submission",
                                            "decision_invitation": "venue/Decision", "max_backfill": 100}})
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = JsonlStore(Path(temp.name) / "events")
        result = run_source(source, ConnectorRegistry([connector]),
                            ConnectorStateStore(store.directory.parent / "runtime"), store,
                            ConnectorContext(store=store, now=lambda: NOW))
        observations = list(store.iter_records("observation"))
        artifacts = list(ArtifactRepository(store).iter_canonical())
        self.assertEqual([row["kind"] for row in observations], ["paper_submission", "decision"])
        self.assertEqual(artifacts.__len__(), 1)
        self.assertEqual(artifacts[0]["identifiers"]["openreview"], "paper-1")
        self.assertEqual(observations[1]["metadata"]["decision_visibility"], "public")
        self.assertNotIn("private", json.dumps(observations))
        self.assertEqual(calls, [("venue/Submission", 101), ("venue/Decision", 101)])
        self.assertEqual(result["artifacts_touched"], 1)
        probe = connector.probe(api_version=2, invitation="venue/Submission", decision_invitation="venue/Decision")
        self.assertEqual(probe.status, "valid")
        with self.assertRaises(ValueError):
            connector.fetch({**source, "acquisition": {"connector": "openreview-submissions",
                                                          "mode": "api", "venue": {
                                                              "api_version": True, "invitation": "x"}}},
                            None, ConnectorContext(store=store, now=lambda: NOW))

    def test_huggingface_daily_structured_overlap_dedupes_arxiv_and_keeps_votes_out_of_artifact(self):
        from .connectors.huggingface_daily import HuggingFaceDailyPapersConnector

        item = {"paper": {"id": "2609.12345", "title": "A paper from HF Daily",
                           "summary": "Short abstract", "authors": [{"name": "A. Researcher"}],
                           "publishedAt": "2026-09-28T00:00:00Z", "projectUrl": "https://example.org/project"},
                "upvotes": 123, "submittedBy": {"name": "Curator Example"}}
        client = FakeHttp([HttpResponse(200, {}, json.dumps({"results": [item]}).encode()),
                           HttpResponse(200, {}, json.dumps({"results": [item]}).encode())])
        source = _source("huggingface|daily", "Hugging Face Daily Papers",
                         connector="huggingface-daily-papers")
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            arxiv_source = _source("arxiv|seed", "arXiv")
            store.upsert_source(arxiv_source)
            arxiv_observation = _paper_observation(arxiv_source["source_id"], "arxiv|paper|1",
                                                   "10.5555/hf-daily.1", NOW, arxiv="2609.12345",
                                                   title="A paper from HF Daily", source_platform="arxiv")
            store.append_observation(arxiv_observation)
            materialize_artifact_candidates(arxiv_observation, store)
            result = run_source(source, ConnectorRegistry([HuggingFaceDailyPapersConnector()]),
                                ConnectorStateStore(Path(temp) / "runtime"), store,
                                ConnectorContext(store=store, http=client, now=lambda: NOW))
            observations = [row for row in store.iter_records("observation")
                            if row["source_id"] == source["source_id"]]
            artifacts = list(ArtifactRepository(store).iter_canonical())
            self.assertEqual(len(observations), 2)
            self.assertTrue(all(row["kind"] == "recommendation" for row in observations))
            self.assertTrue(all(row["metadata"]["upvotes"] == 123 for row in observations))
            self.assertEqual(len(artifacts), 1)
            self.assertNotIn("upvotes", artifacts[0])
            self.assertNotIn("Curator Example", json.dumps(artifacts[0]))
            self.assertEqual(result["new_observations"], 2)
            state = ConnectorStateStore(Path(temp) / "runtime").load(source["source_id"])
            self.assertEqual(state.last_successful_date, "2026-09-29")
            self.assertEqual([url.split("date=")[1].split("&")[0] for url, _ in client.urls],
                             ["2026-09-29", "2026-09-28"])
            graph_backfill(store, Path(temp) / "runtime", now=NOW)
            recommendation_edges = [edge for edge in GraphStore(store.directory).iter_edges()
                                    if edge["subject_id"] == source["source_id"]
                                    and edge["predicate"] == "recommends"]
            self.assertEqual(len(recommendation_edges), 1)
            self.assertEqual(recommendation_edges[0]["object_id"], artifacts[0]["artifact_id"])

    def test_openalex_exact_topic_poll_uses_seven_day_window_and_replays_without_duplication(self):
        payload = {"results": [{"id": "https://openalex.org/W123", "doi": "https://doi.org/10.5555/openalex.1",
                               "title": "OpenAlex exact query result", "type": "article",
                               "publication_date": "2026-09-28", "authorships": [], "primary_topic": None,
                               "topics": [], "primary_location": None, "best_oa_location": None,
                               "ids": {"openalex": "https://openalex.org/W123"}}],
                   "meta": {"next_cursor": None}}
        body = json.dumps(payload).encode()
        client = FakeHttp([HttpResponse(200, {}, body), HttpResponse(200, {}, body)])
        query = {"topic_ids": ["T123"]}
        source = _source("openalex|topic", "OpenAlex exact topic",
                         connector="openalex-works", config={"query": query})
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            states = ConnectorStateStore(Path(temp) / "runtime")
            registry = ConnectorRegistry([OpenAlexWorksConnector()])
            first = run_source(source, registry, states, store,
                               ConnectorContext(store=store, http=client, now=lambda: NOW))
            second = run_source(source, registry, states, store,
                                ConnectorContext(store=store, http=client, now=lambda: NOW))
            first_url = client.urls[0][0]
            self.assertIn("from_publication_date%3A2026-09-22", first_url)
            self.assertIn("to_publication_date%3A2026-09-29", first_url)
            self.assertIn("topics.id%3AT123", first_url)
            self.assertEqual(first["new_observations"], 1)
            self.assertEqual(second["new_observations"], 0)
            self.assertEqual(store.stats()["observation"], 1)
            self.assertEqual(store.stats()["artifact"], 1)
            self.assertEqual(states.load(source["source_id"]).last_window_end, "2026-09-29")
            self.assertEqual(probe_openalex_query(query, http=FakeHttp([HttpResponse(200, {}, body)]), now=NOW).status,
                             "valid")
            graph_backfill(store, Path(temp) / "runtime", now=NOW)
            self.assertTrue(any(edge["subject_id"] == source["source_id"]
                                and edge["object_id"] == next(iter(ArtifactRepository(store).iter_canonical()))["artifact_id"]
                                and edge["predicate"] == "mentions"
                                for edge in GraphStore(store.directory).iter_edges()))
            with self.assertRaises(ValueError):
                OpenAlexWorksConnector().fetch(source, ConnectorCheckpoint(cursor="not-json"),
                                                ConnectorContext(store=store, http=client, now=lambda: NOW))


class ProposalAndCoverageTests(unittest.TestCase):
    def test_rss_autodiscovery_creates_proposal_only_and_rejection_is_sticky(self):
        homepage = HttpResponse(200, {}, b'<html><head><link rel="alternate" type="application/rss+xml" href="/feed.xml"></head></html>')
        feed = HttpResponse(200, {"Content-Type": "application/rss+xml"},
                            b'<rss version="2.0"><channel><title>Feed</title><item><guid>x</guid><title>One</title><link>https://lab.example.org/one</link></item></channel></rss>')
        client = FakeHttp([homepage, feed])
        with tempfile.TemporaryDirectory() as temp:
            proposal_store = SourceProposalStore(Path(temp) / "proposals.jsonl")
            subscriptions = SourceSubscriptionRegistry(Path(temp) / "subscriptions.jsonl")
            candidate = {"candidate_id": "sc-0123456789abcdef01234567", "candidate_type": "organization",
                         "name": "Example Lab", "canonical_url": "https://lab.example.org",
                         "status": "pending", "topics": ["topic-search-agent"],
                         "evidence_paths": [{"depth": 2, "supporting_artifact_ids": ["art-" + "a" * 24]}]}
            rows = discover_rss_proposals([candidate], [], proposal_store, http=client, now=NOW)
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["probe_status"], "valid")
            self.assertEqual(row["status"], "pending")
            self.assertEqual(row["canonical_url"], "https://lab.example.org/feed.xml")
            self.assertEqual(subscriptions.list(), [])
            self.assertEqual(probe_rss_endpoint("https://lab.example.org/feed.xml", http=FakeHttp([feed])).status,
                             "valid")
            proposal_store.review(row["proposal_id"], "rejected", reason_code="human_rejected")
            replay = discover_rss_proposals([candidate], [], proposal_store, http=FakeHttp([homepage, feed]), now=NOW)
            self.assertEqual(replay[0]["status"], "rejected")
            self.assertEqual(subscriptions.list(), [])

    def test_approved_subscription_merges_deterministically_and_duplicate_ids_fail_closed(self):
        source = new_source(identity="rss|approved|feed", source_type="feed", platform="rss", name="Approved",
                            canonical_url="https://example.org/feed.xml", connector="rss-atom", mode="rss",
                            created_at=NOW)
        with tempfile.TemporaryDirectory() as temp:
            seed = Path(temp) / "sources.yaml"
            seed.write_text("schema: bubblevan/intelligence-source-catalog/v1\nsources: []\n", encoding="utf-8")
            registry = Path(temp) / "subscriptions.jsonl"
            SourceSubscriptionRegistry(registry).add(source)
            first = load_merged_source_catalog(seed, registry)
            second = load_merged_source_catalog(seed, registry)
            self.assertEqual(first, second)
            self.assertEqual(first[0]["source_id"], source["source_id"])
            registry.write_text(json.dumps(source) + "\n" + json.dumps(source) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "corrupt"):
                load_merged_source_catalog(seed, registry)

    def test_private_source_registry_is_git_ignored_and_hugo_excluded(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        hugo_config = (ROOT / "hugo.toml").read_text(encoding="utf-8")
        self.assertIn("/data/intelligence/private/", gitignore)
        self.assertIn("! intelligence/private/**", hugo_config)

    def test_source_coverage_counts_first_source_unique_contribution_and_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            left = new_source(identity="coverage|left", source_type="feed", platform="test", name="Left",
                              connector="fixture", mode="api", created_at=NOW)
            right = new_source(identity="coverage|right", source_type="feed", platform="test", name="Right",
                               connector="fixture", mode="api", created_at=NOW)
            store.upsert_source(left); store.upsert_source(right)
            for source, when, doi in (
                (left, "2026-09-28T08:00:00Z", "10.5555/shared.1"),
                (right, "2026-09-29T07:00:00Z", "10.5555/shared.1"),
                (left, "2026-09-29T08:00:00Z", "10.5555/left.1"),
                (right, "2026-09-29T08:00:00Z", "10.5555/right.1"),
            ):
                observation = _paper_observation(source["source_id"], f"coverage|{source['name']}|{doi}", doi, when)
                store.append_observation(observation)
                materialize_artifact_candidates(observation, store)
            from .connectors.state import ConnectorState, ConnectorStateStore
            ConnectorStateStore(Path(temp) / "runtime").save(ConnectorState(
                source_id=left["source_id"], connector_id="fixture", last_attempt_at=NOW,
                last_success_at=NOW,
            ))
            report = source_coverage(store, Path(temp) / "runtime", [left, right], days=7, today="2026-09-29")
            rows = {row["source_id"]: row for row in report["sources"]}
            self.assertEqual(rows[left["source_id"]]["unique_contribution"], 2)
            self.assertEqual(rows[right["source_id"]]["unique_contribution"], 1)
            self.assertEqual(rows[right["source_id"]]["duplicate_canonical_artifacts"], 1)
            self.assertEqual(rows[left["source_id"]]["polls"], 0)
            self.assertEqual(rows[left["source_id"]]["health"], "healthy")
            self.assertEqual(rows[left["source_id"]]["checkpoint_last_attempt_at"], NOW)
            self.assertEqual(report["pairwise_overlap"][0]["shared_canonical_artifacts"], 1)

    def test_openalex_topic_proposals_do_not_write_mapping_until_human_approval(self):
        response = HttpResponse(200, {}, json.dumps({"results": [{"id": "https://openalex.org/T42",
            "display_name": "Research Agents", "description": "Agent systems and tool use.",
            "works_count": 42}]}).encode())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "topic-proposals.jsonl"
            topic_map = Path(temp) / "topic-map.yaml"
            with patch(f"{__package__}.discovery.openalex_topics.TOPIC_MAP_PATH", topic_map):
                proposals = OpenAlexTopicProposalStore(path)
                rows = proposals.propose("topic-search-agent", http=FakeHttp([response]), now=NOW)
                self.assertEqual(len(rows), 1)
                self.assertFalse(topic_map.exists())
                approved = proposals.approve(rows[0]["proposal_id"], reviewed_by="test-reviewer", reviewed_at=NOW)
                self.assertEqual(approved["status"], "approved")
                self.assertIn("T42", topic_map.read_text(encoding="utf-8"))


class ScalingRegressionTests(unittest.TestCase):
    def test_scale_benchmark_smoke_reports_all_three_phases(self):
        from .benchmarks.store_scale import benchmark_size

        result = benchmark_size(2, now=NOW)
        self.assertEqual(result["observations"], 2)
        self.assertEqual(result["artifacts"], 2)
        for phase in ("ingest_replay", "graph_backfill", "corpus_snapshot"):
            self.assertGreaterEqual(result[phase]["seconds"], 0)

    def test_openalex_topic_alias_fallback_preserves_search_term_for_review(self):
        from .discovery.openalex_topics import OpenAlexTopicProposalStore

        planning = {"id": "https://openalex.org/T10906", "display_name": "AI-based Problem Solving and Planning",
                    "description": "AI problem solving and planning", "works_count": 50000}
        client = FakeHttp([
            HttpResponse(200, {}, json.dumps({"results": []}).encode()),
            HttpResponse(200, {}, json.dumps({"results": [planning]}).encode()),
            HttpResponse(200, {}, json.dumps({"results": []}).encode()),
        ])
        with tempfile.TemporaryDirectory() as temp:
            rows = OpenAlexTopicProposalStore(Path(temp) / "topics.jsonl").propose(
                "topic-reasoning-verification-and-planning", http=client, now=NOW)
            match = next(row for row in rows if row["openalex_topic_id"] == "T10906")
            self.assertEqual(match["matched_search_terms"], ["planning"])
            self.assertEqual(len(client.urls), 3)

    def test_scheduled_transport_recovery_retries_one_source_after_thirty_seconds(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            source_id = "src-" + "a" * 24
            waits = []
            calls = []

            def acquire(sources, *_args):
                calls.append([row["source_id"] for row in sources])
                return {"sources_total": 1, "succeeded": 1, "failed": 0,
                        "results": [{"status": "succeeded", "source_id": source_id,
                                     "fetched": 1, "new_observations": 1}]}

            result, artifact_count = _scheduled_transport_recovery(
                {"sources_total": 1, "succeeded": 0, "failed": 1, "results": [{
                    "status": "failed", "source_id": source_id, "error_class": "HttpTransportError",
                    "error_category": "connection_reset"}]},
                [{"source_id": source_id}], acquire, Path(temp) / "runtime", store,
                enabled=True, recovery_sleep=waits.append,
            )
            row = result["results"][0]
            self.assertEqual(waits, [30.0])
            self.assertEqual(calls, [[source_id]])
            self.assertEqual(artifact_count, 0)
            self.assertEqual(row["attempt_count"], 2)
            self.assertEqual(row["initial_error_category"], "connection_reset")
            self.assertEqual(row["final_status"], "succeeded_after_retry")
            self.assertTrue(row["succeeded_after_retry"])
            self.assertEqual(result["succeeded"], 1)

    def test_manual_and_provider_deferred_sources_do_not_trigger_transport_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            calls = []

            def forbidden_retry(*_args):
                calls.append("retried")
                raise AssertionError("unexpected retry")

            sources = [{"source_id": "src-" + "b" * 24}, {"source_id": "src-" + "c" * 24}]
            initial = {"sources_total": 2, "succeeded": 0, "failed": 2, "results": [
                {"status": "failed", "source_id": sources[0]["source_id"],
                 "error_class": "HttpTransportError", "error_category": "read_timeout"},
                {"status": "failed", "source_id": sources[1]["source_id"],
                 "error_class": "ConnectorDeferred", "retry_after_seconds": 3600},
            ]}
            result, _ = _scheduled_transport_recovery(
                initial, sources, forbidden_retry, Path(temp) / "runtime", store,
                enabled=False, recovery_sleep=lambda _seconds: calls.append("waited"),
            )
            self.assertEqual(calls, [])
            self.assertEqual([row["attempt_count"] for row in result["results"]], [1, 1])
            self.assertEqual([row["final_status"] for row in result["results"]], ["failed", "failed"])

    def test_graph_builder_materializes_primary_observation_map_in_one_artifact_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            source = _source("graph|scale", "Graph scale")
            store.upsert_source(source)
            observation = _paper_observation(source["source_id"], "graph|observation", "10.5555/graph.1", NOW)
            store.append_observation(observation)
            materialize_artifact_candidates(observation, store)
            aliases = ArtifactAliases(store.directory)
            graph = GraphStore(store.directory)
            with patch.object(ArtifactRepository, "iter_canonical", autospec=True,
                              wraps=ArtifactRepository.iter_canonical) as iter_artifacts:
                build_observation_artifact_edges(store, graph, aliases, __import__(
                    "scripts.intelligence.entity_aliases", fromlist=["EntityAliases"]).EntityAliases(store.directory),
                    now=NOW)
            self.assertEqual(iter_artifacts.call_count, 1)

    def test_graph_backfill_commits_one_snapshot_and_replays_identically(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            source = _source("graph|snapshot", "Graph snapshot")
            store.upsert_source(source)
            for index in range(3):
                observation = _paper_observation(source["source_id"], f"graph|snapshot|{index}",
                                                 f"10.5555/graph.{index}", NOW)
                store.append_observation(observation)
                materialize_artifact_candidates(observation, store)
            original_write = GraphStore._atomic_write
            calls = []

            def counted_write(instance, edges):
                calls.append(1)
                return original_write(instance, edges)

            with patch.object(GraphStore, "_atomic_write", new=counted_write):
                graph_backfill(store, Path(temp) / "runtime", now=NOW)
                self.assertEqual(len(calls), 1)
            first = GraphStore(store.directory).iter_edges()
            graph_backfill(store, Path(temp) / "runtime", now=NOW)
            self.assertEqual(GraphStore(store.directory).iter_edges(), first)

    def test_event_id_index_scans_existing_observations_once_per_process(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            source = _source("event-index|source", "Event index")
            store.upsert_source(source)
            original_iter = store.iter_records
            calls = []

            def counted(kind):
                if kind == "observation":
                    calls.append(kind)
                return original_iter(kind)

            with patch.object(store, "iter_records", side_effect=counted):
                for index in range(20):
                    observation = _paper_observation(source["source_id"], f"event-index|{index}",
                                                     f"10.5555/event.{index}", NOW)
                    self.assertTrue(store.append_observation(observation))
                self.assertFalse(store.append_observation(observation))
            self.assertEqual(len(calls), 1)

    def test_materialized_batch_rewrites_artifact_index_once(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            with patch.object(JsonlStore, "_atomic_write", wraps=JsonlStore._atomic_write) as writer:
                with store.bulk_materialized():
                    for index in range(20):
                        store.upsert_artifact(new_artifact(identity=f"doi:10.5555/bulk.{index}",
                            artifact_type="paper", title=f"Bulk {index}",
                            canonical_url=f"https://doi.org/10.5555/bulk.{index}",
                            identifiers={"doi": f"10.5555/bulk.{index}"}))
                self.assertEqual(writer.call_count, 1)
            self.assertEqual(store.stats()["artifact"], 20)


if __name__ == "__main__":
    unittest.main()
