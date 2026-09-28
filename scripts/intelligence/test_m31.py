from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from .artifacts import materialize_artifact_candidates
from .aliases import ArtifactAliases
from .connectors.base import ConnectorContext
from .connectors.http import HttpResponse, SharedHttpClient
from .connectors.rss_atom import RssAtomConnector
from .entity_aliases import EntityAliases
from .graph.models import make_edge
from .graph.builders.observation_artifact import build_observation_artifact_edges
from .graph.store import GraphStore
from .ids import artifact_id
from .models import new_artifact, new_observation, new_source
from .providers.huggingface_metadata import HuggingFaceMetadataProvider, enrich_huggingface_metadata, select_huggingface_artifacts
from .retrieval.bm25 import BM25Retriever
from .retrieval.corpus import CorpusSnapshot, RetrievalDocument, build_snapshot, filter_documents
from .retrieval.dense import DenseRetriever, DeterministicFakeEmbedding
from .retrieval.engine import RetrievalEngine
from .retrieval.evaluation import blind_pool_candidates, evaluate_human_qrels, require_corpus_match
from .retrieval.graph import GraphRetriever
from .retrieval.registry import RetrieverRegistry
from .retrieval.request import make_request
from .retrieval.base import RetrievalResult, RetrieverSpec
from .runner import load_source_catalog
from .rss_migration import rematerialize_primary_artifacts
from .store import JsonlStore


NOW = "2026-09-28T12:00:00Z"


class QueueTransport:
    def __init__(self, response: HttpResponse):
        self.response = response
        self.calls = []

    def send(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": dict(headers), "timeout": timeout})
        return self.response


def _document(artifact_id: str, title: str, body: str, *, kind: str = "paper", topics=(), eligibility="full_text"):
    return RetrievalDocument(artifact_id, kind, title, body, (), (), tuple(topics), None, NOW, (), (), (),
                             "en" if title or body else "und", "observed_at_fallback", "referenced", eligibility)


class M31ArtifactSemanticsTests(unittest.TestCase):
    def test_rss_entry_has_primary_and_referenced_roles_and_only_primary_inherits_time_topics(self):
        source = new_source(identity="fixture|m31|rss", source_type="feed", platform="huggingface",
                            name="Fixture RSS", canonical_url="https://feed.example/rss.xml", connector="rss-atom",
                            mode="rss", artifact_policy={"primary_type": "blog"}, topics=["topic-rag"], created_at=NOW)
        xml = b'''<rss version="2.0"><channel><title>Feed</title><item>
          <guid>m31-one</guid><title>A primary research entry</title><link>https://feed.example/blog/entry</link>
          <pubDate>Mon, 28 Sep 2026 08:00:00 GMT</pubDate><author>Researcher</author><category>memory</category>
          <description>Read https://huggingface.co/org/model and https://arxiv.org/abs/2609.12345.</description>
          </item></channel></rss>'''
        response = HttpResponse(200, {}, xml)
        observation = RssAtomConnector().fetch(
            source, None, ConnectorContext(http=SharedHttpClient(QueueTransport(response)), now=lambda: NOW),
        ).observations[0]
        primary = next(item for item in observation["artifact_candidates"] if item["mention"]["role"] == "primary")
        referenced = [item for item in observation["artifact_candidates"] if item["mention"]["role"] == "referenced"]
        self.assertEqual(primary["artifact_type"], "blog")
        self.assertEqual(primary["title"], observation["title"])
        self.assertEqual(primary["published_at"], observation["published_at"])
        self.assertEqual({item["artifact_type"] for item in referenced}, {"model", "paper"})
        self.assertTrue(all("published_at" not in item for item in referenced))

        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            store.upsert_source(source)
            store.append_observation(observation)
            ids = materialize_artifact_candidates(observation, store)
            rows = {item["artifact_id"]: item for item in store.iter_records("artifact")}
            primary_id = next(aid for aid in ids if rows[aid]["artifact_type"] == "blog")
            primary_row = rows[primary_id]
            self.assertEqual(primary_row["published_at"], observation["published_at"])
            self.assertLessEqual(len(primary_row["summary"]), 4000)
            self.assertEqual(primary_row["topics"], ["topic-memory", "topic-rag"])
            self.assertEqual(primary_row["field_provenance"]["mention"]["connector"], "rss-atom")
            referenced_ids = [aid for aid in ids if aid != primary_id]
            self.assertTrue(all(rows[aid]["published_at"] is None for aid in referenced_ids))
            self.assertTrue(all(rows[aid]["topics"] == [] for aid in referenced_ids))

            graph = GraphStore(store.directory)
            build_observation_artifact_edges(store, graph, ArtifactAliases(store.directory), EntityAliases(store.directory), now=NOW)
            refs = [edge for edge in graph.iter_edges() if edge["predicate"] == "references"]
            self.assertEqual(len(refs), 2)
            self.assertEqual({edge["subject_id"] for edge in refs}, {primary_id})
            snapshot = build_snapshot(store, graph=graph)
            referenced_docs = [item for item in snapshot.documents if item.artifact_id in referenced_ids]
            self.assertEqual(len(referenced_docs), 2)
            route = GraphRetriever(str(store.directory))
            route.build(snapshot, str(Path(temp) / "runtime"))
            result = route.retrieve(make_request("", seed_artifact_ids=[primary_id]), documents=snapshot.documents, top_k=10)
            self.assertEqual({item["artifact_id"] for item in result.candidates}, set(referenced_ids))

    def test_source_catalog_declares_primary_types_and_unknown_rss_defaults_to_blog(self):
        sources = {item["name"]: item for item in load_source_catalog()}
        self.assertEqual(sources["arXiv cs.AI"]["acquisition"]["artifact_policy"]["primary_type"], "paper")
        self.assertEqual(sources["arXiv cs.LG"]["acquisition"]["artifact_policy"]["primary_type"], "paper")
        self.assertEqual(sources["Hugging Face Blog"]["acquisition"]["artifact_policy"]["primary_type"], "blog")
        self.assertEqual(sources["OpenAI News"]["acquisition"]["artifact_policy"]["primary_type"], "blog")
        source = new_source(identity="fixture|rss-default", source_type="feed", platform="rss", name="Unknown",
                            canonical_url="https://example.org/feed.xml", connector="rss-atom", mode="rss", created_at=NOW)
        response = HttpResponse(200, {}, b'<rss version="2.0"><channel><item><title>Unknown feed item</title><link>https://example.org/post</link></item></channel></rss>')
        result = RssAtomConnector().fetch(source, None, ConnectorContext(http=SharedHttpClient(QueueTransport(response)), now=lambda: NOW))
        self.assertEqual(result.observations[0]["artifact_candidates"][-1]["artifact_type"], "blog")

    def test_arxiv_rss_entry_materializes_as_primary_paper_with_publication_time(self):
        source = next(item for item in load_source_catalog() if item["name"] == "arXiv cs.AI")["acquisition"]
        source = {**source, "source_id": "fixture-arxiv-cs-ai", "name": "arXiv cs.AI",
                  "canonical_url": "https://rss.arxiv.org/rss/cs.AI", "platform": "arxiv",
                  "topics": ["topic-reasoning-verification-and-planning"]}
        payload = b'''<rss version="2.0"><channel><item>
          <guid>arxiv:2609.12345</guid><title>A synthetic arXiv paper</title>
          <link>https://arxiv.org/abs/2609.12345</link>
          <pubDate>Mon, 28 Sep 2026 08:00:00 GMT</pubDate>
          <description>A synthetic paper abstract for the offline RSS semantics test.</description>
          </item></channel></rss>'''
        result = RssAtomConnector().fetch(
            source, None, ConnectorContext(http=SharedHttpClient(QueueTransport(HttpResponse(200, {}, payload))),
                                           now=lambda: NOW),
        )
        observation = result.observations[0]
        primary = next(item for item in observation["artifact_candidates"]
                       if item["mention"].get("role") == "primary")
        self.assertEqual(primary["artifact_type"], "paper")
        self.assertEqual(primary["canonical_url"], "https://arxiv.org/abs/2609.12345")
        self.assertEqual(primary["published_at"], "2026-09-28T08:00:00Z")
        self.assertEqual(primary["mention"]["evidence_level"], "explicit_source_link")

    def test_huggingface_blog_urls_are_not_parsed_as_model_repo_ids(self):
        from .canonicalize import artifact_identity, candidate_from_url
        candidate = candidate_from_url("https://huggingface.co/blog/org/some-article")
        self.assertEqual(candidate["artifact_type"], "other")
        self.assertEqual(artifact_identity(candidate), "url:https://huggingface.co/blog/org/some-article")

    def test_legacy_candidate_without_role_defaults_to_referenced_and_incidental_is_not_materialized(self):
        source = new_source(identity="fixture|legacy-role", source_type="feed", platform="fixture", name="Legacy",
                            connector="manual", mode="manual", created_at=NOW)
        primary = {"artifact_type": "paper", "title": "Primary paper with enough searchable text to qualify fully",
                   "canonical_url": "https://papers.example/primary", "identifiers": {}, "authors": [],
                   "organizations": [], "summary": "A detailed primary description with adequate searchable body content.",
                   "topics": [], "mention": {"role": "primary", "origin": "entry_url",
                   "evidence_level": "rendered_link", "confidence": 1.0}}
        legacy = {"artifact_type": "model", "title": "", "canonical_url": "https://huggingface.co/org/model",
                  "identifiers": {"huggingface": {"repo_type": "model", "repo_id": "org/model"}},
                  "authors": [], "organizations": [], "summary": "", "topics": [],
                  "mention": {"origin": "url", "evidence_level": "rendered_link", "confidence": 1.0}}
        incidental = {**legacy, "canonical_url": "https://example.org/", "mention": {
            "role": "incidental", "origin": "url", "evidence_level": "rendered_link", "confidence": 1.0}}
        obs = new_observation(identity="fixture|legacy-observation", source_id=source["source_id"], platform="fixture",
                              platform_object_id="legacy", kind="post", title="Primary", text="body", urls=[], media=[],
                              published_at=NOW, observed_at=NOW, topics=["topic-rag"], native_tags=[], authors=[],
                              provenance={"retrieval_mode": "manual", "evidence_level": "source_text",
                                          "source_url": "https://example.org", "collector": "test"},
                              artifact_candidates=[primary, legacy, incidental])
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            store.upsert_source(source)
            ids = materialize_artifact_candidates(obs, store)
            rows = list(store.iter_records("artifact"))
            self.assertEqual(len(rows), 2)
            model = next(item for item in rows if item["artifact_type"] == "model")
            self.assertEqual(model["published_at"], None)
            self.assertEqual(model["topics"], [])
            self.assertIn(model["artifact_id"], ids)

    def test_primary_mention_upgrades_existing_referenced_role_without_later_downgrade(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            source = new_source(identity="fixture|role-upgrade", source_type="feed", platform="fixture",
                                name="Role Upgrade", connector="rss-atom", mode="rss", created_at=NOW)
            store.upsert_source(source)
            url = "https://example.org/research-entry"

            def observation(identity, role):
                candidate = {"artifact_type": "blog", "title": "Research entry",
                             "canonical_url": url, "identifiers": {}, "authors": [],
                             "organizations": [], "summary": "", "topics": [],
                             "mention": {"role": role, "origin": "entry_url" if role == "primary" else "url",
                                         "evidence_level": "explicit_source_link", "confidence": 1.0}}
                return new_observation(
                    identity=identity, source_id=source["source_id"], platform="fixture",
                    platform_object_id=identity, kind="post", title="Research entry", text="Entry text",
                    urls=[url], media=[], published_at=NOW, observed_at=NOW, topics=[], native_tags=[],
                    authors=[], provenance={"retrieval_mode": "fixture", "evidence_level": "source_text",
                                            "source_url": url, "collector": "test"},
                    artifact_candidates=[candidate],
                )

            first = observation("fixture|role-upgrade|reference", "referenced")
            store.append_observation(first)
            old_ids = materialize_artifact_candidates(first, store)
            primary = observation("fixture|role-upgrade|primary", "primary")
            store.append_observation(primary)
            primary_ids = materialize_artifact_candidates(primary, store)
            later_reference = observation("fixture|role-upgrade|later-reference", "referenced")
            store.append_observation(later_reference)
            materialize_artifact_candidates(later_reference, store)
            artifact = store.get_by_id("artifact", old_ids[0])
            self.assertEqual(old_ids, primary_ids)
            self.assertEqual(artifact["artifact_type"], "blog")
            self.assertEqual(artifact["field_provenance"]["mention"]["mention_role"], "primary")


class M31RetrievalQualityTests(unittest.TestCase):
    def test_route_depth_fusion_and_graph_expand_preserve_seed_provenance(self):
        docs = tuple(_document("art-" + f"{index:024x}", f"Searchable document {index}",
                               f"A sufficiently useful body about retrieval item {index}.")
                     for index in range(1, 8))
        seed = docs[0].artifact_id
        target = docs[-1].artifact_id
        snapshot = CorpusSnapshot(docs, "c" * 64, "d" * 64)

        class FixedRetriever:
            def __init__(self, route, candidates):
                self.spec = RetrieverSpec(route, "fixed-v1")
                self.candidates = candidates
                self.requested_depths = []

            def build(self, _snapshot, _runtime):
                return {"route": self.spec.route, "version": self.spec.version}

            def retrieve(self, _request, *, documents, top_k):
                self.requested_depths.append(top_k)
                eligible = {item.artifact_id for item in documents}
                return RetrievalResult(self.spec.route, [row for row in self.candidates
                                                         if row["artifact_id"] in eligible][:top_k])

        bm25_rows = [{"artifact_id": item.artifact_id, "rank": rank, "raw_score": 100 - rank,
                      "explanation": {}}
                     for rank, item in enumerate(docs[:5], 1)]
        dense_rows = [{"artifact_id": item.artifact_id, "rank": rank, "raw_score": 1 / rank,
                       "explanation": {}}
                      for rank, item in enumerate((docs[0], docs[2], docs[3], docs[4], docs[1]), 1)]

        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            graph_store = GraphStore(store.directory)
            graph_store.add_edges([make_edge(seed, "references", target,
                                             {"evidence_type": "explicit_source_link", "observed_at": NOW})])
            bm25 = FixedRetriever("bm25", bm25_rows)
            dense = FixedRetriever("dense", dense_rows)
            graph = GraphRetriever(str(store.directory))
            registry = RetrieverRegistry()
            for route in (bm25, dense, graph):
                registry.register(route)
            engine = RetrievalEngine(snapshot, registry, store_dir=str(store.directory),
                                     runtime_dir=str(Path(temp) / "runtime"))
            engine.build(routes=["bm25", "dense", "graph"])
            result = engine.search(make_request("retrieval", top_k=2),
                                   routes=["bm25", "dense", "graph-expand"],
                                   route_depth=5, persist=False)

            self.assertEqual(bm25.requested_depths, [5])
            self.assertEqual(dense.requested_depths, [5])
            self.assertEqual(len(result["route_candidates"]["bm25"]), 5)
            self.assertEqual(len(result["route_candidates"]["dense"]), 5)
            self.assertEqual(len(result["candidates"]), 2)
            self.assertEqual(result["reproducibility"]["config"]["route_depth"], 5)
            self.assertEqual(result["reproducibility"]["config"]["final_top_k"], 2)
            graph_rows = result["route_candidates"]["graph-expand"]
            self.assertEqual([row["artifact_id"] for row in graph_rows], [target])
            path = graph_rows[0]["explanation"]["graph_paths"][0]
            self.assertEqual(path["seed_source_route"], "bm25")
            self.assertEqual(path["seed_rank"], 1)
            self.assertEqual(graph_rows[0]["explanation"]["seed_sources"][0]["seed_id"], seed)

    def test_empty_document_is_not_indexed_but_graph_only_node_remains_addressable(self):
        seed = "art-" + "1" * 24
        blank = "art-" + "2" * 24
        docs = (_document(seed, "A searchable seed about memory and research", "Useful body content about memory."),
                _document(blank, "", "", eligibility="graph_only"))
        snapshot = CorpusSnapshot(docs, "a" * 64, "b" * 64)
        with tempfile.TemporaryDirectory() as temp:
            bm25 = BM25Retriever()
            bm25.build(snapshot, str(Path(temp) / "runtime"))
            dense = DenseRetriever(DeterministicFakeEmbedding(2))
            dense.build(snapshot, str(Path(temp) / "runtime"))
            self.assertNotIn(blank, bm25.document_ids)
            self.assertNotIn(blank, dense.document_ids)
            graph = GraphStore(Path(temp) / "events")
            graph.add_edges([__import__("scripts.intelligence.graph.models", fromlist=["make_edge"]).make_edge(
                seed, "references", blank, {"evidence_type": "explicit_source_link", "observed_at": NOW})])
            route = GraphRetriever(str(Path(temp) / "events"))
            route.build(snapshot, str(Path(temp) / "runtime"))
            request = make_request("memory", seed_artifact_ids=[seed])
            graph_result = route.retrieve(request, documents=filter_documents(snapshot, request, include_graph_only=True), top_k=5)
            self.assertEqual([item["artifact_id"] for item in graph_result.candidates], [blank])

    def test_metadata_only_hf_uses_repo_display_title_and_profiles(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            artifact = new_artifact(identity="huggingface:model:org/example-embedding", artifact_type="model",
                                    canonical_url="https://huggingface.co/org/example-embedding",
                                    identifiers={"huggingface": {"repo_type": "model", "repo_id": "org/example-embedding"}})
            store.upsert_artifact(artifact)
            snapshot = build_snapshot(store)
            document = snapshot.by_id()[artifact["artifact_id"]]
            self.assertEqual(document.title, "org/example-embedding")
            self.assertEqual(document.eligibility, "metadata_only")
            default = filter_documents(snapshot, make_request("example", filters={"corpus_profile": "research-default"}))
            models = filter_documents(snapshot, make_request("example", filters={"corpus_profile": "models"}))
            self.assertEqual(default, ())
            self.assertEqual([item.artifact_id for item in models], [artifact["artifact_id"]])

    def test_hf_metadata_enrichment_is_exact_bounded_cached_and_not_a_publication_time(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            artifact = new_artifact(identity="huggingface:model:org/embedder", artifact_type="model",
                                    canonical_url="https://huggingface.co/org/embedder",
                                    identifiers={"huggingface": {"repo_type": "model", "repo_id": "org/embedder"}})
            store.upsert_artifact(artifact)
            calls = []
            def transport(url):
                calls.append(url)
                return {"id": "org/embedder", "author": "org", "createdAt": "2025-01-01T00:00:00Z",
                        "lastModified": "2026-01-01T00:00:00Z", "pipeline_tag": "memory", "tags": ["embedding"],
                        "downloads": 999999, "likes": 999, "cardData": {}}
            provider = HuggingFaceMetadataProvider(Path(temp) / "cache", transport=transport)
            result = enrich_huggingface_metadata(store, provider, limit=1)
            metadata = provider.get("model", "org/embedder")
            self.assertEqual(result["api_requests"], 1)
            self.assertEqual(provider.cache_hits, 1)
            self.assertEqual(len(calls), 1)
            self.assertIn("expand%5B%5D=cardData", calls[0])
            self.assertNotIn("downloads", metadata)
            self.assertNotIn("likes", metadata)
            enriched = store.get_by_id("artifact", artifact["artifact_id"])
            self.assertIsNone(enriched["published_at"])
            self.assertEqual(enriched["provider_metadata"]["huggingface"]["created_at"], "2025-01-01T00:00:00Z")
            cache_text = "\n".join(path.read_text(encoding="utf-8") for path in Path(temp).rglob("*.json"))
            self.assertNotIn("authorization", cache_text.casefold())
            with self.assertRaisesRegex(ValueError, "between 1 and 20"):
                enrich_huggingface_metadata(store, provider, limit=21)

    def test_blind_label_pool_contains_no_route_rank_or_score_fields(self):
        doc = _document("art-" + "a" * 24, "Useful Paper", "A bounded summary.   ")
        candidate = {"artifact_id": doc.artifact_id, "rank": 1, "raw_score": 9.0, "route": "dense"}
        pool = blind_pool_candidates("q", {"dense": [candidate]}, [candidate], {doc.artifact_id: doc},
                                     {doc.artifact_id: {"canonical_url": "https://papers.example/a"}})
        self.assertEqual(len(pool), 1)
        self.assertNotIn("route", pool[0])
        self.assertNotIn("rank", pool[0])
        self.assertNotIn("raw_score", pool[0])
        self.assertNotIn("score", pool[0])
        self.assertEqual(pool[0]["summary_excerpt"], "A bounded summary.")

    def test_evaluation_requires_human_qrels_corpus_match_and_reports_empty_and_type_slices(self):
        with self.assertRaisesRegex(ValueError, "corpus hash"):
            require_corpus_match({"corpus_hash": "a" * 64}, "b" * 64)
        qrels = {"q1": {"art-" + "a" * 24: 2}}
        metrics = evaluate_human_qrels({"q1": {"bm25": []}}, qrels,
                                       {"art-" + "a" * 24: "paper"},
                                       benchmark_corpus_hash="a" * 64, current_corpus_hash="a" * 64)
        self.assertEqual(metrics["routes"]["bm25"]["q1"]["EmptyResult@10"], 1)
        self.assertEqual(metrics["type_slices"]["bm25"]["paper"]["by_query"]["q1"]["N"], 1)
        with self.assertRaisesRegex(ValueError, "human qrels"):
            evaluate_human_qrels({"q1": {}}, {}, {})

    def test_rss_rematerialization_is_zero_network_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            source = next(item for item in load_source_catalog() if item["name"] == "Hugging Face Blog")
            store.upsert_source(source)
            observation = new_observation(
                identity="fixture|rematerialize|rss", source_id=source["source_id"], platform="rss",
                platform_object_id="rematerialize", kind="post", title="A feed entry with stable title",
                text="A bounded public feed summary for this item.", urls=[],
                media=[], published_at="2026-09-01T00:00:00Z", observed_at=NOW,
                topics=["topic-memory"], native_tags=[], authors=["Author"],
                provenance={"retrieval_mode": "rss", "evidence_level": "rendered_page",
                            "source_url": "https://huggingface.co/blog/feed.xml", "collector": "rss-atom"},
                metadata={"entry_url": "https://huggingface.co/blog/stable-entry"},
                artifact_candidates=[{
                    "artifact_type": "model", "title": "", "canonical_url": "https://huggingface.co/blog/stable-entry",
                    "identifiers": {}, "authors": [], "organizations": [], "summary": "", "topics": [],
                    "mention": {"role": "referenced", "origin": "url", "evidence_level": "rendered_link", "confidence": 1.0},
                }],
            )
            store.append_observation(observation)
            first = rematerialize_primary_artifacts(store)
            count = len(list(store.iter_records("artifact")))
            second = rematerialize_primary_artifacts(store)
            self.assertEqual(first["network_requests"], 0)
            self.assertEqual(first["counts"]["new_artifacts"], 1)
            self.assertEqual(second["artifacts_touched"], 0)
            self.assertEqual(second["counts"]["already_materialized"], 1)
            self.assertEqual(len(list(store.iter_records("artifact"))), count)

    def test_arxiv_rematerialization_uses_nested_source_policy_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            source = next(item for item in load_source_catalog() if item["name"] == "arXiv cs.AI")
            store.upsert_source(source)
            url = "https://arxiv.org/abs/2609.12345"
            observation = new_observation(
                identity="fixture|m31|arxiv-rematerialize", source_id=source["source_id"], platform="rss",
                platform_object_id="arxiv:2609.12345", kind="post", title="A synthetic arXiv paper",
                text="A synthetic arXiv abstract used to verify source-policy migration.", urls=[url], media=[],
                published_at=NOW, observed_at=NOW, topics=[], native_tags=[], authors=[],
                provenance={"retrieval_mode": "rss", "evidence_level": "rendered_page",
                            "source_url": source["canonical_url"], "collector": "rss-atom"},
                metadata={"entry_url": url}, artifact_candidates=[],
            )
            store.append_observation(observation)

            first = rematerialize_primary_artifacts(store)
            artifacts = list(store.iter_records("artifact"))
            second = rematerialize_primary_artifacts(store)

            self.assertEqual(first["network_requests"], 0)
            self.assertEqual(first["counts"]["primary_type:paper"], 1)
            self.assertEqual(first["counts"]["new_artifacts"], 1)
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0]["artifact_type"], "paper")
            self.assertEqual(artifacts[0]["identifiers"]["arxiv"], "2609.12345")
            self.assertEqual(artifacts[0]["published_at"], NOW)
            self.assertEqual(second["artifacts_touched"], 0)

    def test_truncated_hf_blog_path_is_repaired_once_and_keeps_old_artifact_id(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            source = next(item for item in load_source_catalog() if item["name"] == "Hugging Face Blog")
            store.upsert_source(source)
            truncated = "https://huggingface.co/blog/org"
            full = "https://huggingface.co/blog/org/story"
            observation = new_observation(
                identity="fixture|truncated-hf-blog", source_id=source["source_id"], platform="rss",
                platform_object_id="truncated", kind="post", title="A primary blog story",
                text="A public story summary.", urls=[], media=[], published_at="2026-09-01T00:00:00Z",
                observed_at=NOW, topics=[], native_tags=[], authors=[],
                provenance={"retrieval_mode": "rss", "evidence_level": "rendered_page",
                            "source_url": "https://huggingface.co/blog/feed.xml", "collector": "rss-atom"},
                metadata={"entry_url": full}, artifact_candidates=[{
                    "artifact_type": "model", "title": "", "canonical_url": truncated,
                    "identifiers": {}, "authors": [], "organizations": [], "summary": "", "topics": [],
                    "mention": {"role": "referenced", "origin": "url", "evidence_level": "rendered_link", "confidence": 1.0},
                }],
            )
            store.append_observation(observation)
            old = new_artifact(
                identity=f"url:{truncated}", artifact_type="blog", canonical_url=truncated,
                title="Legacy truncated primary", observation_ids=[observation["observation_id"]],
                field_provenance={"mention": {"mention_role": "primary",
                                               "observation_id": observation["observation_id"]}},
            )
            store.upsert_artifact(old)
            aliases = ArtifactAliases(store.directory)
            intended_id = artifact_id(f"url:{full}")
            aliases.register_alias(f"url:{full}", intended_id, resolver="fixture",
                                   resolver_id=observation["observation_id"], resolved_at=NOW)
            aliases.add_redirect(intended_id, old["artifact_id"], reason="legacy_url_misclassification", created_at=NOW)

            first = rematerialize_primary_artifacts(store)
            repaired = store.get_by_id("artifact", old["artifact_id"])
            primary = next(item for item in store.iter_records("artifact")
                           if item.get("canonical_url") == full and item.get("artifact_type") == "blog")
            second = rematerialize_primary_artifacts(store)

            self.assertEqual(first["repaired_truncated_hf_blog_artifacts"], 1)
            self.assertEqual(repaired["artifact_type"], "model")
            self.assertEqual(repaired["artifact_id"], old["artifact_id"])
            self.assertEqual(primary["field_provenance"]["mention"]["mention_role"], "primary")
            self.assertEqual(aliases.resolve_alias(f"url:{full}"), primary["artifact_id"])
            self.assertEqual(aliases.resolve_artifact_id(intended_id), primary["artifact_id"])
            self.assertEqual(second["repaired_truncated_hf_blog_artifacts"], 0)
            self.assertEqual(second["artifacts_touched"], 0)

    def test_old_hf_blog_model_identity_is_preserved_separately_from_primary_blog(self):
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            source = next(item for item in load_source_catalog() if item["name"] == "Hugging Face Blog")
            store.upsert_source(source)
            full = "https://huggingface.co/blog/org/story"
            repo_id = "org/story"
            observation = new_observation(
                identity="fixture|old-hf-blog-model", source_id=source["source_id"], platform="rss",
                platform_object_id="old-hf-blog-model", kind="post", title="A primary blog story",
                text="A bounded feed summary for the blog story.", urls=[], media=[],
                published_at="2026-09-01T00:00:00Z", observed_at=NOW, topics=["topic-memory"],
                native_tags=[], authors=["Feed Author"],
                provenance={"retrieval_mode": "rss", "evidence_level": "rendered_page",
                            "source_url": "https://huggingface.co/blog/feed.xml", "collector": "rss-atom"},
                metadata={"entry_url": full}, artifact_candidates=[{
                    "artifact_type": "model", "title": "org/story", "canonical_url": full,
                    "identifiers": {"huggingface": {"repo_type": "model", "repo_id": repo_id}},
                    "authors": [], "organizations": [], "summary": "", "topics": [],
                    "mention": {"origin": "url", "evidence_level": "rendered_link", "confidence": 1.0},
                }],
            )
            store.append_observation(observation)
            old = new_artifact(
                identity=f"huggingface:model:{repo_id}", artifact_type="blog", canonical_url=full,
                identifiers={"huggingface": {"repo_type": "model", "repo_id": repo_id}},
                title="A primary blog story", summary=observation["text"], authors=["Feed Author"],
                published_at=observation["published_at"], topics=["topic-memory"],
                observation_ids=[observation["observation_id"]],
                field_provenance={"mention": {"mention_role": "primary",
                                               "observation_id": observation["observation_id"],
                                               "source_id": source["source_id"]}},
            )
            store.upsert_artifact(old)
            aliases = ArtifactAliases(store.directory)
            aliases.register_alias(f"huggingface:model:{repo_id}", old["artifact_id"], resolver="fixture",
                                   resolver_id=observation["observation_id"], resolved_at=NOW)
            url_id = artifact_id(f"url:{full}")
            aliases.register_alias(f"url:{full}", url_id, resolver="fixture",
                                   resolver_id=observation["observation_id"], resolved_at=NOW)
            aliases.add_redirect(url_id, old["artifact_id"], reason="legacy_hf_url_parse", created_at=NOW)

            result = rematerialize_primary_artifacts(store)
            restored = store.get_by_id("artifact", old["artifact_id"])
            primary = store.get_by_id("artifact", url_id)
            snapshot = build_snapshot(store)
            model_doc = snapshot.by_id()[old["artifact_id"]]
            self.assertEqual(result["restored_legacy_hf_model_ids"], 1)
            self.assertEqual(restored["artifact_type"], "model")
            self.assertEqual(restored["title"], repo_id)
            self.assertIsNone(restored["published_at"])
            self.assertEqual(restored["field_provenance"]["mention"]["mention_role"], "referenced")
            self.assertEqual(primary["artifact_type"], "blog")
            self.assertEqual(primary["artifact_id"], url_id)
            self.assertEqual(model_doc.eligibility, "metadata_only")
            self.assertEqual(filter_documents(snapshot, make_request(
                "org story", filters={"artifact_types": ["model"]})), ())
            self.assertEqual([item.artifact_id for item in filter_documents(
                snapshot, make_request("org story", filters={"artifact_types": ["model"], "corpus_profile": "models"}))], [old["artifact_id"]])
            self.assertEqual(select_huggingface_artifacts(store, limit=20), [])


if __name__ == "__main__":
    unittest.main()
