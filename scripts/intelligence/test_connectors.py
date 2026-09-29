from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from .aliases import ArtifactAliases
from .artifacts import upsert_artifact_record
from .bridge_xhs import bridge_xhs
from .canonicalize import artifact_identity, candidate_from_url
from .connectors.base import ConnectorCheckpoint, ConnectorContext, ConnectorDeferred, ConnectorFailure, ConnectorSpec, FetchResult
from .connectors.github_releases import GitHubReleasesConnector
from .connectors.http import HttpResponse, SharedHttpClient
from .connectors.registry import ConnectorRegistry, connector_registry
from .connectors.rss_atom import RssAtomConnector
from .connectors.state import ConnectorState, ConnectorStateStore
from .ids import artifact_id
from .models import new_artifact, new_observation, new_source
from .resolver import SemanticScholarResolver, materialize_semantic_scholar_result
from .runner import load_source_catalog, run_all_sources, run_source
from .store import JsonlStore, PrivateRecordError
from .topics import map_topics


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).with_name("fixtures") / "connectors"
NOW = "2026-09-28T12:00:00Z"


class SequenceTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def send(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": dict(headers), "timeout": timeout})
        if not self.responses:
            raise AssertionError("unexpected HTTP request")
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


class InjectedCrash(BaseException):
    pass


def response(status: int, body: bytes = b"", headers: dict[str, str] | None = None) -> HttpResponse:
    return HttpResponse(status, headers or {}, body)


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def feed_source() -> dict:
    return new_source(identity="fixture|rss|ai", source_type="feed", platform="rss", name="Fixture feed",
                      canonical_url="https://feed.example.org/feed.xml", connector="rss-atom", mode="rss",
                      created_at=NOW)


def github_source() -> dict:
    return new_source(identity="github|example/retrieval-agent", source_type="repository", platform="github",
                      name="Fixture releases", canonical_url="https://github.com/example/retrieval-agent",
                      external_ids={"github_repo": "example/retrieval-agent"}, connector="github-releases",
                      mode="api", created_at=NOW)


def test_observation(source_id: str) -> dict:
    candidate = candidate_from_url("https://github.com/example/connector-demo")
    return new_observation(
        identity="fixture|connector-observation-1", source_id=source_id, platform="fixture",
        platform_object_id="fixture-1", kind="post", title="Connector fixture", text="A fixture record.",
        urls=["https://github.com/example/connector-demo"], media=[], published_at=None, observed_at=NOW,
        topics=[], native_tags=[], provenance={"retrieval_mode": "manual", "evidence_level": "source_text",
        "source_url": "https://example.org/source", "collector": "fixture"}, artifact_candidates=[candidate],
    )


class StaticConnector:
    spec = ConnectorSpec("fixture", "1", ("manual",), frozenset({"pull", "incremental"}), supports_incremental=True)

    def fetch(self, source, checkpoint, context):
        return FetchResult([test_observation(source["source_id"])], ConnectorCheckpoint(high_watermark="done"), True)


class ConnectorRuntimeTests(unittest.TestCase):
    def test_xhs_missing_author_does_not_become_tabris_and_uses_stable_note_identity(self):
        note = {"note_id": "anonymous-1", "url": "https://www.xiaohongshu.com/explore/anonymous-1",
                "title": "An anonymous note", "desc": "No public author", "tags": [], "images": []}
        first, _ = bridge_xhs(note)
        second, _ = bridge_xhs(note)
        self.assertNotEqual(first["name"].casefold(), "tabris")
        self.assertEqual(first["name"], "Unknown Xiaohongshu source")
        self.assertEqual(first["source_id"], second["source_id"])
        self.assertTrue(first["source_id"].startswith("src-"))

    def test_huggingface_repo_type_identity_and_canonical_url_are_distinct(self):
        candidates = [candidate_from_url(url) for url in (
            "https://huggingface.co/org/foo", "https://huggingface.co/datasets/org/foo",
            "https://huggingface.co/spaces/org/foo",
        )]
        identities = [artifact_identity(item) for item in candidates]
        self.assertEqual(identities, ["huggingface:model:org/foo", "huggingface:dataset:org/foo", "huggingface:space:org/foo"])
        self.assertEqual([item["canonical_url"] for item in candidates], [
            "https://huggingface.co/org/foo", "https://huggingface.co/datasets/org/foo",
            "https://huggingface.co/spaces/org/foo",
        ])
        self.assertEqual(candidates[1]["identifiers"]["huggingface"], {"repo_type": "dataset", "repo_id": "org/foo"})

    def test_native_xhs_tags_are_separate_and_only_exact_aliases_become_topics(self):
        note = {"note_id": "tags-1", "url": "https://www.xiaohongshu.com/explore/tags-1",
                "title": "Research", "desc": "", "author": {"nickname": "A"},
                "tags": ["#Memory", "科研学习", "search agent"], "images": []}
        _source, obs = bridge_xhs(note)
        self.assertEqual(obs["native_tags"], sorted(["#Memory", "科研学习", "search agent"]))
        self.assertEqual(obs["topics"], ["topic-memory", "topic-search-agent"])
        self.assertEqual(map_topics(["RAG", "unknown topic"]), ["topic-rag"])

    def test_mixed_xhs_mention_evidence_survives_for_each_candidate(self):
        note = {"note_id": "evidence-1", "url": "https://www.xiaohongshu.com/explore/evidence-1",
                "title": "Paper", "desc": "arXiv:2609.12345", "comments_text": "Also arXiv:2609.12345",
                "author": {"nickname": "A"}, "tags": [], "images": [{"artifact_candidates": [
                    {"artifact_type": "paper", "title": "Paper", "canonical_url": "https://arxiv.org/abs/2609.12345",
                     "identifiers": {"arxiv": "2609.12345"}}
                ]}]}
        _source, obs = bridge_xhs(note)
        mentions = {item["mention"]["evidence_level"] for item in obs["artifact_candidates"]}
        self.assertEqual(mentions, {"source_text", "comment", "image_extract"})

    def test_registry_introspection_and_unknown_connector_fail_closed(self):
        registry = connector_registry()
        listed = {spec.connector_id: spec for spec in registry.list()}
        self.assertEqual(set(listed), {"rss-atom", "github-releases", "xhs-import", "pkb-import"})
        self.assertTrue({"pull", "incremental", "etag", "last_modified"} <= listed["rss-atom"].capabilities)
        self.assertIn("auth_optional", listed["github-releases"].capabilities)
        with self.assertRaisesRegex(ValueError, "unknown connector"):
            registry.get("not-a-connector")

    def test_source_catalog_has_four_feeds_and_three_repositories(self):
        sources = load_source_catalog()
        feeds = [source for source in sources if source["acquisition"]["connector"] == "rss-atom"]
        repos = [source for source in sources if source["acquisition"]["connector"] == "github-releases"]
        self.assertEqual((len(feeds), len(repos)), (4, 3))

    def test_rss_first_304_and_one_new_guid_are_incremental_and_conditional(self):
        transport = SequenceTransport([
            response(200, fixture("rss_first.xml"), {"ETag": '"v1"', "Last-Modified": "Mon, 28 Sep 2026 08:00:00 GMT"}),
            response(304, headers={"ETag": '"v1"'}),
            response(200, fixture("rss_updated.xml"), {"ETag": '"v2"'}),
        ])
        client = SharedHttpClient(transport, sleep=lambda _seconds: None)
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            states = ConnectorStateStore(Path(temp) / "runtime")
            source = feed_source()
            registry = ConnectorRegistry([RssAtomConnector()])
            first = run_source(source, registry, states, store, ConnectorContext(store=store, http=client, now=lambda: NOW))
            second = run_source(source, registry, states, store, ConnectorContext(store=store, http=client, now=lambda: NOW))
            third = run_source(source, registry, states, store, ConnectorContext(store=store, http=client, now=lambda: NOW))
            self.assertEqual((first["fetched"], first["persisted"]), (3, 3))
            self.assertEqual((second["fetched"], second["persisted"]), (0, 0))
            self.assertEqual((third["fetched"], third["persisted"]), (2, 1))
            self.assertEqual((third["new_observations"], third["duplicate_observations"]), (1, 1))
            self.assertEqual(first["artifacts_touched"], 3)
            self.assertEqual(second["pages"], 1)
            self.assertEqual(store.stats()["observation"], 4)
            self.assertEqual(transport.calls[1]["headers"]["If-None-Match"], '"v1"')
            self.assertEqual(transport.calls[1]["headers"]["If-Modified-Since"], "Mon, 28 Sep 2026 08:00:00 GMT")
            stored = list(store.iter_records("observation"))
            self.assertTrue(any(item["authors"] == ["A. Researcher"] for item in stored))
            self.assertNotIn("discard-me", json.dumps(stored))

    def test_rss_high_watermark_skips_older_entries_but_counts_provider_fetches(self):
        xml = b'''<rss version="2.0"><channel><title>Incremental feed</title>
          <item><guid>old-entry</guid><title>Old story</title>
            <link>https://example.org/old</link><pubDate>Tue, 22 Sep 2026 08:00:00 GMT</pubDate></item>
          <item><guid>new-entry</guid><title>New story</title>
            <link>https://example.org/new</link><pubDate>Sun, 27 Sep 2026 08:00:00 GMT</pubDate></item>
        </channel></rss>'''
        source = feed_source()
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            states = ConnectorStateStore(Path(temp) / "runtime")
            states.save(ConnectorState(
                source_id=source["source_id"], connector_id="rss-atom", connector_version="1",
                high_watermark="2026-09-24T00:00:00Z", last_success_at=NOW,
            ))
            result = run_source(
                source, ConnectorRegistry([RssAtomConnector()]), states, store,
                ConnectorContext(store=store, http=SharedHttpClient(SequenceTransport([response(200, xml)])),
                                 now=lambda: NOW),
            )
        self.assertEqual((result["fetched"], result["new_observations"],
                          result["duplicate_observations"]), (2, 1, 1))
        self.assertEqual(result["artifacts_touched"], 1)
        self.assertEqual(result["diagnostics"][0]["entries_skipped_before_high_watermark"], 1)

    def test_rss_atom_feed_is_supported_and_author_is_kept(self):
        transport = SequenceTransport([response(200, fixture("rss_atom.xml"))])
        source = feed_source()
        result = RssAtomConnector().fetch(source, None, ConnectorContext(http=SharedHttpClient(transport), now=lambda: NOW))
        self.assertEqual(len(result.observations), 1)
        self.assertEqual(result.observations[0]["authors"], ["Atom Author"])
        self.assertIn("An abstract with HTML.", result.observations[0]["text"])

    def test_rss_missing_guid_falls_back_to_canonical_link_then_content_hash(self):
        transport = SequenceTransport([response(200, b'''<rss version="2.0"><channel><title>x</title>
          <item><title>Linked</title><link>https://example.org/item</link></item>
          <item><title>No link</title><description>stable text</description></item></channel></rss>''')])
        items = RssAtomConnector().fetch(feed_source(), None, ConnectorContext(http=SharedHttpClient(transport), now=lambda: NOW)).observations
        self.assertEqual(len(items), 2)
        self.assertNotEqual(items[0]["observation_id"], items[1]["observation_id"])

    def test_rss_redacts_private_url_parameters_before_persisting_feed_text(self):
        secret = "must-not-persist-this-value"
        xml = f'''<rss version="2.0"><channel><title>Safe</title><item>
          <guid>private-query-1</guid><title>Release https://example.org/start?access_token={secret}&amp;view=compact</title>
          <description>More at https://example.org/docs?xsec_token={secret}</description>
          </item></channel></rss>'''.encode()
        source = feed_source()
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            states = ConnectorStateStore(Path(temp) / "runtime")
            result = run_source(source, ConnectorRegistry([RssAtomConnector()]), states, store,
                                ConnectorContext(store=store, http=SharedHttpClient(SequenceTransport([
                                    response(200, xml, {"ETag": '"redacted"'}),
                                ])), now=lambda: NOW))
            serialized = json.dumps(list(store.iter_records("observation")))
            self.assertEqual(result["new_observations"], 1)
            self.assertNotIn(secret, serialized)
            self.assertNotIn("access_token", serialized)
            self.assertNotIn("xsec_token", serialized)
            self.assertIn("view=compact", serialized)

    def test_rss_redacts_provider_token_like_query_keys(self):
        xml = b'''<rss version="2.0"><channel><title>Safe</title><item>
          <guid>token-query-1</guid><title>Read https://example.org/?tokenizer=private&amp;view=compact</title>
          </item></channel></rss>'''
        source = feed_source()
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            run_source(source, ConnectorRegistry([RssAtomConnector()]), ConnectorStateStore(Path(temp) / "runtime"),
                       store, ConnectorContext(http=SharedHttpClient(SequenceTransport([response(200, xml)])),
                                               now=lambda: NOW))
            serialized = json.dumps(list(store.iter_records("observation")))
            self.assertNotIn("tokenizer", serialized)
            self.assertNotIn("private", serialized)
            self.assertIn("view=compact", serialized)

    def test_rss_question_title_with_tokens_is_not_mistaken_for_url_query(self):
        xml = b'''<rss version="2.0"><channel><title>Safe</title><item>
          <guid>ordinary-question-1</guid><title>What Can We Do with Fewer Tokens?</title>
          </item></channel></rss>'''
        source = feed_source()
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            result = run_source(source, ConnectorRegistry([RssAtomConnector()]), ConnectorStateStore(Path(temp) / "runtime"),
                                store, ConnectorContext(http=SharedHttpClient(SequenceTransport([response(200, xml)])),
                                                        now=lambda: NOW))
            observation = next(store.iter_records("observation"))
            self.assertEqual(result["new_observations"], 1)
            self.assertEqual(observation["title"], "What Can We Do with Fewer Tokens?")

    def test_github_releases_200_304_then_new_release_and_token_never_persists(self):
        secret = "github-test-token-never-persist"
        transport = SequenceTransport([
            response(200, fixture("github_releases_page1.json"), {"ETag": '"gh1"', "X-RateLimit-Remaining": "4999"}),
            response(304, headers={"ETag": '"gh1"', "X-RateLimit-Remaining": "4998"}),
            response(200, fixture("github_releases_updated.json"), {"ETag": '"gh2"', "X-RateLimit-Remaining": "4997"}),
        ])
        client = SharedHttpClient(transport, sleep=lambda _seconds: None)
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            states = ConnectorStateStore(Path(temp) / "runtime")
            source = github_source()
            registry = ConnectorRegistry([GitHubReleasesConnector()])
            context = ConnectorContext(store=store, http=client, environment={"GITHUB_TOKEN": secret}, now=lambda: NOW)
            first = run_source(source, registry, states, store, context)
            second = run_source(source, registry, states, store, context)
            third = run_source(source, registry, states, store, context)
            self.assertEqual((first["fetched"], first["persisted"]), (2, 2))
            self.assertEqual((second["fetched"], second["persisted"]), (0, 0))
            self.assertEqual((third["fetched"], third["persisted"]), (3, 1))
            self.assertEqual(store.stats()["observation"], 3)
            self.assertEqual(transport.calls[1]["headers"]["If-None-Match"], '"gh1"')
            self.assertTrue(all(call["headers"].get("Authorization") == f"Bearer {secret}" for call in transport.calls))
            rows = list(store.iter_records("observation"))
            self.assertTrue(any(item["metadata"].get("prerelease") is True for item in rows))
            serialized = "\n".join(path.read_text(encoding="utf-8") for path in Path(temp).rglob("*") if path.is_file())
            self.assertNotIn(secret, serialized)

    def test_github_release_body_is_redacted_before_private_record_validation(self):
        secrets = ("body-token-secret", "header-bearer-secret", "url-token-secret",
                   "prefixed-token-secret")
        payload = [{
            "id": 991, "tag_name": "v1.0.0", "name": "Release v1.0.0",
            "published_at": "2026-09-27T10:00:00Z",
            "html_url": "https://github.com/example/retrieval-agent/releases/tag/v1.0.0",
            "body": (f"token={secrets[0]}\nmy_token={secrets[3]}\nAuthorization: Bearer {secrets[1]}\n"
                     f"See https://example.org/docs?access_token={secrets[2]}&view=compact"),
            "author": {"login": "release-bot"},
        }]
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            source = github_source()
            run_source(
                source, ConnectorRegistry([GitHubReleasesConnector()]),
                ConnectorStateStore(Path(temp) / "runtime"), store,
                ConnectorContext(store=store, http=SharedHttpClient(SequenceTransport([
                    response(200, json.dumps(payload).encode("utf-8"), {"ETag": '"safe"'}),
                ])), now=lambda: NOW),
            )
            serialized = "\n".join(path.read_text(encoding="utf-8")
                                     for path in Path(temp).rglob("*") if path.is_file())
        for secret in secrets:
            self.assertNotIn(secret, serialized)
        self.assertIn("token=[REDACTED]", serialized)
        self.assertIn("my_token=[REDACTED]", serialized)
        self.assertIn("Authorization:[REDACTED]", serialized)
        self.assertIn("view=compact", serialized)

    def test_github_pagination_stays_inside_connector_and_validates_next_url(self):
        first = response(200, b"[]", {"Link": '<https://api.github.com/repos/example/retrieval-agent/releases?per_page=100&page=2>; rel="next"', "ETag": "x"})
        second = response(200, b"[]")
        transport = SequenceTransport([first, second])
        result = GitHubReleasesConnector().fetch(github_source(), None, ConnectorContext(http=SharedHttpClient(transport), now=lambda: NOW))
        self.assertEqual(result.diagnostics["pages"], 2)
        self.assertIn("page=2", transport.calls[1]["url"])
        numeric_repo_first = response(200, b"[]", {"Link": '<https://api.github.com/repositories/155220641/releases?per_page=100&page=2>; rel="next"'})
        numeric_repo_transport = SequenceTransport([numeric_repo_first, response(200, b"[]")])
        numeric_repo_result = GitHubReleasesConnector().fetch(
            github_source(), None,
            ConnectorContext(http=SharedHttpClient(numeric_repo_transport), now=lambda: NOW),
        )
        self.assertEqual(numeric_repo_result.diagnostics["pages"], 2)
        self.assertIn("/repositories/155220641/releases?per_page=100&page=2", numeric_repo_transport.calls[1]["url"])
        bad = response(200, b"[]", {"Link": '<https://evil.example/next>; rel="next"'})
        with self.assertRaisesRegex(ValueError, "unexpected URL"):
            GitHubReleasesConnector().fetch(github_source(), None, ConnectorContext(http=SharedHttpClient(SequenceTransport([bad])), now=lambda: NOW))
        secret_query = response(200, b"[]", {"Link": '<https://api.github.com/repositories/155220641/releases?access_token=secret&page=2>; rel="next"'})
        with self.assertRaisesRegex(ValueError, "unexpected URL"):
            GitHubReleasesConnector().fetch(github_source(), None, ConnectorContext(http=SharedHttpClient(SequenceTransport([secret_query])), now=lambda: NOW))

    def test_repository_artifact_materializes_even_when_no_release_exists(self):
        transport = SequenceTransport([response(200, b"[]", {"ETag": '"empty"'})])
        source = github_source()
        registry = ConnectorRegistry([GitHubReleasesConnector()])
        with tempfile.TemporaryDirectory() as temp:
            store, states = JsonlStore(Path(temp) / "events"), ConnectorStateStore(Path(temp) / "runtime")
            run_source(source, registry, states, store,
                       ConnectorContext(store=store, http=SharedHttpClient(transport), now=lambda: NOW))
            artifacts = list(store.iter_records("artifact"))
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0]["artifact_type"], "repository")
            self.assertEqual(artifacts[0]["identifiers"]["github"], "example/retrieval-agent")

    def test_http_429_obeys_retry_after(self):
        delays = []
        transport = SequenceTransport([response(429, headers={"Retry-After": "2"}), response(200, b"ok")])
        client = SharedHttpClient(transport, sleep=delays.append)
        self.assertEqual(client.get("https://example.org").status, 200)
        self.assertEqual(delays, [2.0])
        self.assertEqual(len(transport.calls), 2)

    def test_http_retry_after_long_wait_defers_instead_of_retrying_early(self):
        delays = []
        transport = SequenceTransport([response(429, headers={"Retry-After": "3600"}), response(200)])
        result = SharedHttpClient(transport, max_retry_wait=10, sleep=delays.append).get("https://example.org")
        self.assertEqual(result.status, 429)
        self.assertEqual(delays, [])
        self.assertEqual(len(transport.calls), 1)

    def test_rss_retry_after_is_saved_as_provider_directed_backoff(self):
        transport = SequenceTransport([response(429, headers={"Retry-After": "3600"})])
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            states = ConnectorStateStore(Path(temp) / "runtime")
            source = feed_source()
            with self.assertRaises(ConnectorDeferred):
                run_source(source, ConnectorRegistry([RssAtomConnector()]), states, store,
                           ConnectorContext(store=store, http=SharedHttpClient(transport), now=lambda: NOW))
            state = states.load(source["source_id"])
            expected = datetime.fromisoformat(NOW.replace("Z", "+00:00")) + timedelta(seconds=3600)
            self.assertGreaterEqual(datetime.fromisoformat(state.backoff_until.replace("Z", "+00:00")), expected)
            self.assertIsNone(state.last_success_at)

    def test_github_exhausted_rate_limit_uses_reset_timestamp(self):
        now = datetime.fromisoformat(NOW.replace("Z", "+00:00"))
        reset_epoch = int((now + timedelta(hours=2)).timestamp())
        reset_at = datetime.fromtimestamp(reset_epoch, timezone.utc)
        transport = SequenceTransport([response(403, headers={
            "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset_epoch),
        })])
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            states = ConnectorStateStore(Path(temp) / "runtime")
            source = github_source()
            with self.assertRaises(ConnectorDeferred):
                run_source(source, ConnectorRegistry([GitHubReleasesConnector()]), states, store,
                           ConnectorContext(store=store, http=SharedHttpClient(transport), now=lambda: NOW))
            state = states.load(source["source_id"])
            self.assertEqual(datetime.fromisoformat(state.backoff_until.replace("Z", "+00:00")), reset_at)

    def test_run_all_isolates_a_broken_source_and_continues_to_third(self):
        order = []

        class GoodConnector:
            spec = ConnectorSpec("good", "1", ("api",), frozenset({"pull"}))

            def fetch(self, source, checkpoint, context):
                order.append(source["name"])
                obs = new_observation(
                    identity=f"good|{source['source_id']}", source_id=source["source_id"],
                    platform="fixture", platform_object_id=source["source_id"], kind="post",
                    title=source["name"], text="ok", urls=[], media=[], published_at=None,
                    observed_at=context.now(), topics=[], native_tags=[], provenance={
                        "retrieval_mode": "api", "evidence_level": "source_text",
                        "source_url": "https://fixture.example/item", "collector": "fixture",
                    }, artifact_candidates=[],
                )
                return FetchResult([obs], ConnectorCheckpoint(last_success_at=context.now()))

        class BrokenConnector:
            spec = ConnectorSpec("broken", "1", ("api",), frozenset({"pull"}))

            def fetch(self, source, checkpoint, context):
                order.append(source["name"])
                raise RuntimeError("failed https://fixture.invalid/path?token=do-not-leak")

        sources = [
            new_source(identity=f"fixture|{name}", source_type="feed", platform="fixture", name=name,
                       connector=connector, mode="api", created_at=NOW)
            for name, connector in (("good-1", "good"), ("broken", "broken"), ("good-2", "good"))
        ]
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            states = ConnectorStateStore(Path(temp) / "runtime")
            summary = run_all_sources(sources, ConnectorRegistry([GoodConnector(), BrokenConnector()]),
                                      states, store, ConnectorContext(store=store, now=lambda: NOW))
            self.assertEqual(order, ["good-1", "broken", "good-2"])
            self.assertEqual((summary["sources_total"], summary["succeeded"], summary["failed"]), (3, 2, 1))
            self.assertEqual([row["status"] for row in summary["results"]], ["succeeded", "failed", "succeeded"])
            self.assertNotIn("do-not-leak", json.dumps(summary))
            self.assertNotIn("fixture.invalid", json.dumps(summary))
            self.assertEqual(summary["results"][2]["new_observations"], 1)

    def test_run_all_isolates_private_source_record_rejection(self):
        class UnsafeConnector:
            spec = ConnectorSpec("unsafe", "1", ("api",), frozenset({"pull"}))

            def fetch(self, source, checkpoint, context):
                obs = new_observation(
                    identity="unsafe-record", source_id=source["source_id"], platform="fixture",
                    platform_object_id="unsafe-1", kind="post", title="unsafe",
                    text="https://fixture.invalid/?authorization=must-not-persist", urls=[], media=[],
                    published_at=None, observed_at=context.now(), topics=[], native_tags=[],
                    provenance={"retrieval_mode": "api", "evidence_level": "source_text",
                    "source_url": "https://fixture.example/source", "collector": "fixture"},
                    artifact_candidates=[],
                )
                return FetchResult([obs], ConnectorCheckpoint(last_success_at=context.now()))

        class GoodAfterUnsafe(StaticConnector):
            spec = ConnectorSpec("good-after-unsafe", "1", ("api",), frozenset({"pull"}))

            def fetch(self, source, checkpoint, context):
                obs = test_observation(source["source_id"])
                obs["observation_id"] = "obs-" + "d" * 24
                return FetchResult([obs], ConnectorCheckpoint(last_success_at=context.now()))

        sources = [
            new_source(identity="fixture|unsafe", source_type="feed", platform="fixture", name="Unsafe",
                       connector="unsafe", mode="api", created_at=NOW),
            new_source(identity="fixture|good-after-unsafe", source_type="feed", platform="fixture", name="Good",
                       connector="good-after-unsafe", mode="api", created_at=NOW),
        ]
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            summary = run_all_sources(sources, ConnectorRegistry([UnsafeConnector(), GoodAfterUnsafe()]),
                                      ConnectorStateStore(Path(temp) / "runtime"), store,
                                      ConnectorContext(store=store, now=lambda: NOW))
            self.assertEqual((summary["succeeded"], summary["failed"]), (1, 1))
            self.assertEqual(summary["results"][0]["error_class"], PrivateRecordError.__name__)
            self.assertEqual(summary["results"][1]["status"], "succeeded")
            self.assertNotIn("must-not-persist", json.dumps(summary))
            self.assertEqual(store.stats()["observation"], 1)

    def test_duplicate_observation_keeps_first_observed_at_and_advances_poll_times(self):
        class RepeatedObservationConnector:
            spec = ConnectorSpec("repeated", "1", ("api",), frozenset({"pull"}))

            def fetch(self, source, checkpoint, context):
                obs = new_observation(
                    identity="stable-publication", source_id=source["source_id"], platform="fixture",
                    platform_object_id="stable-1", kind="post", title="Stable", text="same item", urls=[],
                    media=[], published_at="2026-09-01T00:00:00Z", observed_at=context.now(), topics=[],
                    native_tags=[], provenance={"retrieval_mode": "api", "evidence_level": "source_text",
                    "source_url": "https://fixture.example/stable", "collector": "fixture"}, artifact_candidates=[],
                )
                return FetchResult([obs], ConnectorCheckpoint(last_success_at=context.now()))

        source = new_source(identity="fixture|temporal", source_type="feed", platform="fixture", name="Temporal",
                            connector="repeated", mode="api", created_at=NOW)
        current = ["2026-09-28T10:00:00Z"]
        context = ConnectorContext(now=lambda: current[0])
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            states = ConnectorStateStore(Path(temp) / "runtime")
            registry = ConnectorRegistry([RepeatedObservationConnector()])
            first = run_source(source, registry, states, store, context)
            current[0] = "2026-09-28T11:00:00Z"
            second = run_source(source, registry, states, store, context)
            observation = next(store.iter_records("observation"))
            state = states.load(source["source_id"])
            self.assertEqual(observation["published_at"], "2026-09-01T00:00:00Z")
            self.assertEqual(observation["observed_at"], "2026-09-28T10:00:00Z")
            self.assertEqual((first["new_observations"], second["new_observations"]), (1, 0))
            self.assertEqual(second["duplicate_observations"], 1)
            self.assertEqual(state.last_attempt_at, current[0])
            self.assertEqual(state.last_success_at, current[0])

    def test_http_5xx_retry_is_bounded_and_403_does_not_retry(self):
        delays = []
        transport = SequenceTransport([response(503), response(502), response(200)])
        self.assertEqual(SharedHttpClient(transport, sleep=delays.append).get("https://example.org").status, 200)
        self.assertEqual(len(transport.calls), 3)
        self.assertEqual(delays, [1, 2])
        denied = SequenceTransport([response(403), response(200)])
        self.assertEqual(SharedHttpClient(denied, sleep=lambda _seconds: None).get("https://example.org").status, 403)
        self.assertEqual(len(denied.calls), 1)

    def test_timeout_retry_is_bounded(self):
        transport = SequenceTransport([TimeoutError(), TimeoutError(), TimeoutError(), response(200)])
        sleeps = []
        client = SharedHttpClient(transport, max_attempts=3, sleep=sleeps.append)
        with self.assertRaisesRegex(RuntimeError, "HTTP request failed"):
            client.get("https://example.org")
        self.assertEqual(len(transport.calls), 3)
        self.assertEqual(sleeps, [1, 2])

    def test_checkpoint_save_is_atomic_and_corrupt_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            states = ConnectorStateStore(temp)
            source = feed_source()
            state = ConnectorState(source_id=source["source_id"], connector_id="rss-atom", etag="etag")
            states.save(state)
            self.assertEqual(states.load(source["source_id"]).etag, "etag")
            self.assertEqual(list(Path(temp).rglob("*.tmp")), [])
            path = states.path_for(source["source_id"])
            path.write_text(json.dumps({"source_id": source["source_id"], "connector_id": "rss-atom",
                                        "consecutive_failures": "invalid"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "corrupt connector checkpoint"):
                states.load(source["source_id"])
            path.write_text("{bad json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "corrupt connector checkpoint"):
                states.load(source["source_id"])

    def test_crash_at_each_commit_boundary_replays_without_silent_loss(self):
        source = new_source(identity="fixture|source", source_type="feed", platform="fixture", name="Fixture",
                            connector="fixture", mode="manual", created_at=NOW)
        registry = ConnectorRegistry([StaticConnector()])
        for crash_stage in ("before_observation_append", "after_observation_append", "before_checkpoint_advance", "after_checkpoint_advance"):
            with self.subTest(stage=crash_stage), tempfile.TemporaryDirectory() as temp:
                store = JsonlStore(Path(temp) / "events")
                states = ConnectorStateStore(Path(temp) / "runtime")
                def inject(stage):
                    if stage == crash_stage:
                        raise InjectedCrash(stage)
                context = ConnectorContext(store=store, now=lambda: NOW, fault_injector=inject)
                with self.assertRaises(InjectedCrash):
                    run_source(source, registry, states, store, context)
                replay = run_source(source, registry, states, store, ConnectorContext(store=store, now=lambda: NOW))
                self.assertEqual(store.stats()["observation"], 1)
                self.assertEqual(store.stats()["artifact"], 1)
                self.assertEqual(replay["persisted"], 0 if crash_stage != "before_observation_append" else 1)
                self.assertEqual(states.load(source["source_id"]).high_watermark, "done")

    def test_runner_backoff_prevents_a_retry_storm(self):
        class BrokenConnector(StaticConnector):
            spec = ConnectorSpec("broken", "1", ("api",), frozenset({"pull"}))
            def fetch(self, source, checkpoint, context):
                raise RuntimeError("fixture failure")
        source = new_source(identity="fixture|broken", source_type="feed", platform="fixture", name="Broken",
                            connector="broken", mode="api", created_at=NOW)
        with tempfile.TemporaryDirectory() as temp:
            store, states = JsonlStore(Path(temp) / "events"), ConnectorStateStore(Path(temp) / "runtime")
            registry = ConnectorRegistry([BrokenConnector()])
            context = ConnectorContext(store=store, now=lambda: NOW)
            with self.assertRaises(ConnectorFailure):
                run_source(source, registry, states, store, context)
            state = states.load(source["source_id"])
            self.assertEqual(state.consecutive_failures, 1)
            with self.assertRaisesRegex(ConnectorDeferred, "connector deferred"):
                run_source(source, registry, states, store, context)

    def test_scholarly_resolver_unifies_arxiv_and_doi_and_redirects_old_artifact(self):
        arxiv_id = artifact_id("arxiv:2609.12345")
        doi_id = artifact_id("doi:10.5555/ri.2026.1")
        transport = SequenceTransport([response(200, fixture("s2_arxiv.json"))])
        with tempfile.TemporaryDirectory() as temp:
            aliases = ArtifactAliases(temp)
            result = SemanticScholarResolver().resolve({"identifiers": {"arxiv": "2609.12345"}}, arxiv_id,
                                                       aliases, ConnectorContext(http=SharedHttpClient(transport), now=lambda: NOW))
            self.assertEqual(result["classification"], "provider_equivalence")
            self.assertEqual(result["canonical_artifact_id"], arxiv_id)
            self.assertEqual(aliases.resolve_alias("doi:10.5555/RI.2026.1"), arxiv_id)
            self.assertEqual(aliases.resolve_alias("semantic-scholar:S2PAPER001"), arxiv_id)
            exact = SemanticScholarResolver().resolve({"identifiers": {"doi": "10.5555/ri.2026.1"}}, doi_id,
                                                      aliases, ConnectorContext(now=lambda: NOW))
            self.assertEqual(exact["classification"], "exact_identifier")
            self.assertEqual(exact["canonical_artifact_id"], arxiv_id)
            self.assertEqual(aliases.resolve_artifact_id(doi_id), arxiv_id)
            self.assertEqual(len({aliases.resolve_artifact_id(value) for value in (arxiv_id, doi_id)}), 1)

    def test_doi_only_s2_lookup_can_reconcile_a_preexisting_arxiv_artifact(self):
        arxiv_id = artifact_id("arxiv:2609.12345")
        doi_id = artifact_id("doi:10.5555/ri.2026.1")
        with tempfile.TemporaryDirectory() as temp:
            aliases = ArtifactAliases(temp)
            aliases.register_alias("arxiv:2609.12345", arxiv_id, resolver="fixture", resolver_id="local", resolved_at=NOW)
            transport = SequenceTransport([response(200, fixture("s2_doi_same_paper.json"))])
            result = SemanticScholarResolver().resolve({"identifiers": {"doi": "10.5555/ri.2026.1"}}, doi_id,
                                                       aliases, ConnectorContext(http=SharedHttpClient(transport), now=lambda: NOW))
            self.assertEqual(result["classification"], "provider_equivalence")
            self.assertEqual(aliases.resolve_artifact_id(doi_id), arxiv_id)
            self.assertEqual(aliases.resolve_alias("doi:10.5555/ri.2026.1"), arxiv_id)

    def test_scholarly_title_only_produces_candidate_and_makes_no_request(self):
        transport = SequenceTransport([])
        with tempfile.TemporaryDirectory() as temp:
            result = SemanticScholarResolver().resolve({"title": "A similar paper", "identifiers": {}},
                                                       artifact_id("title:a similar paper"), ArtifactAliases(temp),
                                                       ConnectorContext(http=SharedHttpClient(transport)))
        self.assertEqual(result["classification"], "title_candidate")
        self.assertEqual(transport.calls, [])

    def test_scholarly_explicit_identifier_conflict_is_not_merged(self):
        transport = SequenceTransport([response(200, fixture("s2_conflict.json"))])
        with tempfile.TemporaryDirectory() as temp:
            aliases = ArtifactAliases(temp)
            result = SemanticScholarResolver().resolve({"identifiers": {"arxiv": "2609.12345"}},
                                                       artifact_id("arxiv:2609.12345"), aliases,
                                                       ConnectorContext(http=SharedHttpClient(transport), now=lambda: NOW))
            self.assertEqual(result["classification"], "conflict")
            self.assertIsNone(aliases.resolve_alias("arxiv:2609.12345"))

    def test_scholarly_metadata_is_materialized_with_conflicts(self):
        arxiv_id = artifact_id("arxiv:2609.12345")
        original = new_artifact(identity="arxiv:2609.12345", artifact_type="paper", title="Prior longer title",
                                identifiers={"arxiv": "2609.12345"},
                                field_provenance={"title": {"source": "xiaohongshu", "observation_id": "obs-" + "a" * 24}})
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            store.upsert_artifact(original)
            aliases = ArtifactAliases(temp)
            transport = SequenceTransport([response(200, fixture("s2_arxiv.json"))])
            result = SemanticScholarResolver().resolve({"identifiers": {"arxiv": "2609.12345"}}, arxiv_id,
                                                       aliases, ConnectorContext(http=SharedHttpClient(transport), now=lambda: NOW))
            materialized = materialize_semantic_scholar_result(result, original, store)
            self.assertEqual(materialized["identifiers"]["semantic_scholar"], "S2PAPER001")
            self.assertEqual(materialized["identifiers"]["doi"], "10.5555/ri.2026.1")
            self.assertIn("title", {item["field"] for item in materialized["field_conflicts"]})

    def test_artifact_alias_types_keep_huggingface_scopes_separate(self):
        first = artifact_id("huggingface:model:org/foo")
        second = artifact_id("huggingface:dataset:org/foo")
        with tempfile.TemporaryDirectory() as temp:
            aliases = ArtifactAliases(temp)
            aliases.register_alias("huggingface:model:org/foo", first, resolver="fixture", resolver_id="x", resolved_at=NOW)
            aliases.register_alias("huggingface:dataset:org/foo", second, resolver="fixture", resolver_id="x", resolved_at=NOW)
            self.assertNotEqual(aliases.resolve_alias("huggingface:model:org/foo"), aliases.resolve_alias("huggingface:dataset:org/foo"))

    def test_local_exact_aliases_attach_later_identifier_to_existing_artifact(self):
        arxiv_id = artifact_id("arxiv:2609.12345")
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            aliases = ArtifactAliases(temp)
            arxiv = new_artifact(identity="arxiv:2609.12345", artifact_type="paper",
                                 identifiers={"arxiv": "2609.12345"})
            upsert_artifact_record(arxiv, store, resolver_id="obs-" + "a" * 24, resolved_at=NOW)
            doi = new_artifact(identity="doi:10.5555/ri.2026.1", artifact_type="paper",
                               identifiers={"doi": "10.5555/ri.2026.1", "arxiv": "2609.12345"})
            merged = upsert_artifact_record(doi, store, resolver_id="obs-" + "b" * 24, resolved_at=NOW)
            self.assertEqual(merged["artifact_id"], arxiv_id)
            self.assertEqual(store.stats()["artifact"], 1)
            self.assertEqual(aliases.resolve_alias("doi:10.5555/ri.2026.1"), arxiv_id)
            self.assertEqual(aliases.resolve_artifact_id(artifact_id("doi:10.5555/ri.2026.1")), arxiv_id)

    def test_artifact_field_conflicts_are_preserved_with_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(temp)
            first = new_artifact(identity="doi:10.5555/stable", artifact_type="paper", title="Short title",
                                 identifiers={"doi": "10.5555/first"}, field_provenance={"title": {"source": "rss", "observation_id": None},
                                 "identifiers": {"doi": {"source": "rss", "observation_id": None}}})
            second = new_artifact(identity="doi:10.5555/stable", artifact_type="paper", title="A competing title",
                                  identifiers={"doi": "10.5555/second"}, field_provenance={"title": {"source": "github", "observation_id": "obs-" + "a" * 24},
                                  "identifiers": {"doi": {"source": "github", "observation_id": "obs-" + "a" * 24}}})
            store.upsert_artifact(first)
            merged = store.upsert_artifact(second)
            conflicts = {item["field"]: item for item in merged["field_conflicts"]}
            self.assertEqual({item["value"] for item in conflicts["title"]["values"]}, {"Short title", "A competing title"})
            self.assertEqual({item["value"] for item in conflicts["identifiers.doi"]["values"]}, {"10.5555/first", "10.5555/second"})
            self.assertEqual({item["source"] for item in conflicts["title"]["values"]}, {"rss", "github"})

    def test_redirect_path_compresses_and_cycles_fail_closed(self):
        a, b, c = ["art-" + character * 24 for character in "abc"]
        with tempfile.TemporaryDirectory() as temp:
            aliases = ArtifactAliases(temp)
            aliases.add_redirect(a, b)
            aliases.add_redirect(b, c)
            self.assertEqual(aliases.resolve_artifact_id(a), c)
            rows = [json.loads(line) for line in aliases.redirect_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(next(row["to_artifact_id"] for row in rows if row["from_artifact_id"] == a), c)
            with self.assertRaisesRegex(ValueError, "cycle|redundant"):
                aliases.add_redirect(c, a)
            with self.assertRaisesRegex(ValueError, "self-redirect"):
                aliases.add_redirect(c, c)

    def test_token_never_enters_http_diagnostics_or_runtime_state(self):
        secret = "never-print-this-token"
        transport = SequenceTransport([response(200, fixture("github_releases_page1.json"), {"X-RateLimit-Remaining": "1"})])
        client = SharedHttpClient(transport)
        diagnostics = client.diagnostics(response(200, headers={"X-RateLimit-Remaining": "1"}))
        self.assertNotIn(secret, json.dumps(diagnostics))
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            states = ConnectorStateStore(Path(temp) / "runtime")
            source = github_source()
            run_source(source, ConnectorRegistry([GitHubReleasesConnector()]), states, store,
                       ConnectorContext(store=store, http=client, environment={"GITHUB_TOKEN": secret}, now=lambda: NOW))
            serialized = "\n".join(path.read_text(encoding="utf-8") for path in Path(temp).rglob("*") if path.is_file())
            self.assertNotIn(secret, serialized)

    def test_manual_import_connectors_are_registered_but_require_explicit_payload(self):
        registry = connector_registry()
        xhs = registry.get("xhs-import")
        self.assertIn("manual_import", xhs.spec.capabilities)
        with self.assertRaisesRegex(ValueError, "explicit sanitized"):
            xhs.fetch({}, None, ConnectorContext())


if __name__ == "__main__":
    unittest.main()
