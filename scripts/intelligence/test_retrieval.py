from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from .aliases import ArtifactAliases
from .discovery.source_candidates import SourceCandidateStore
from .entity_aliases import EntityAliases
from .graph.models import make_edge
from .graph.store import GraphStore
from .ids import entity_id
from .models import new_artifact, new_observation, new_source
from .retrieval.base import RetrievalResult, RetrieverSpec
from .retrieval.benchmark import freeze_benchmark, validate_benchmark
from .retrieval.corpus import CorpusSnapshot, RetrievalDocument, build_snapshot, filter_documents
from .retrieval.dense import DenseRetriever, DeterministicFakeEmbedding
from .retrieval.bm25 import BM25Retriever
from .retrieval.engine import RetrievalEngine
from .retrieval.expansion import expand_query
from .retrieval.fusion import reciprocal_rank_fusion
from .retrieval.metrics import evaluate_ranking, evaluate_routes, future_leak_count
from .retrieval.manifest import make_manifest
from .retrieval.registry import RetrieverRegistry
from .retrieval.request import make_request
from .retrieval.tokenization import tokenize
from .retrieval.graph import GraphRetriever
from .retrieval.topic import TopicRetriever
from .retrieval.source import SourceRetriever
from .retrieval.semantic_scholar_recommendations import SemanticScholarRecommendationsRetriever
from .retrieval.synthetic_fixture import (
    ARTIFACT_A, ARTIFACT_D, ARTIFACT_E, ARTIFACT_SEED, build_synthetic_snapshot, run_synthetic_evaluation,
)
from .store import JsonlStore


NOW = "2026-09-28T12:00:00Z"


class Fixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = JsonlStore(self.root / "events")
        self.graph = GraphStore(self.root / "events")
        self.aliases = ArtifactAliases(self.root / "events")
        self.source = new_source(identity="source|fixture", source_type="curator", platform="fixture",
                                 name="Fixture source", canonical_url="https://fixture.example/feed",
                                 connector="manual", mode="manual", created_at=NOW)
        self.store.upsert_source(self.source)
        self.artifacts = {}
        for key, title, published, topics in (
            ("search", "Search Agent reinforcement learning", "2026-09-01T00:00:00Z", ["topic-search-agent"]),
            ("memory", "Persistent memory for assistants", "2026-09-10T00:00:00Z", ["topic-memory"]),
            ("other", "Unrelated computer vision dataset", None, []),
        ):
            item = new_artifact(identity=f"url:https://papers.example/{key}", artifact_type="paper", title=title,
                                canonical_url=f"https://papers.example/{key}", published_at=published,
                                summary=f"Summary about {title}.", topics=topics,
                                field_provenance={"mention": {"mention_role": "primary"}})
            self.store.upsert_artifact(item)
            self.artifacts[key] = item
        for index in range(4):
            obs = new_observation(
                identity=f"fixture:{index}", source_id=self.source["source_id"], platform="fixture",
                platform_object_id=f"{index}", kind="capture", title=f"Excerpt {index}",
                text="Search agent memory evidence " + ("x" * 2100 if index == 0 else "short text"),
                urls=[self.artifacts["search"]["canonical_url"]], media=[], published_at=None,
                observed_at=f"2026-09-{index + 1:02d}T00:00:00Z", topics=["topic-search-agent"],
                provenance={"retrieval_mode": "fixture", "evidence_level": "source_text",
                            "source_url": "https://fixture.example/feed", "collector": "test"},
                artifact_candidates=([{
                    "artifact_type": "paper", "title": self.artifacts["search"]["title"],
                    "canonical_url": self.artifacts["search"]["canonical_url"],
                    "identifiers": {}, "authors": [], "organizations": [], "summary": "", "topics": [],
                    "mention": {"role": "primary", "origin": "entry_url", "evidence_level": "explicit_source_link", "confidence": 1.0},
                }] if index < 3 else []),
            )
            if index < 3:
                self.store.append_observation(obs)
                self.artifacts["search"]["observation_ids"].append(obs["observation_id"])
        self.store.upsert_artifact(self.artifacts["search"])
        self.entity = entity_id("fixture-author")
        self.graph.add_edges([
            make_edge(self.artifacts["search"]["artifact_id"], "cites", self.artifacts["memory"]["artifact_id"],
                      {"evidence_type": "exact_provider_metadata", "provider": "fixture", "provider_record_id": "cite-1", "observed_at": NOW}),
            make_edge(self.artifacts["search"]["artifact_id"], "authored_by", self.entity,
                      {"evidence_type": "exact_provider_metadata", "provider": "fixture", "provider_record_id": "author-a", "observed_at": NOW}),
            make_edge(self.artifacts["other"]["artifact_id"], "authored_by", self.entity,
                      {"evidence_type": "exact_provider_metadata", "provider": "fixture", "provider_record_id": "author-b", "observed_at": NOW}),
            make_edge(self.source["source_id"], "mentions", self.artifacts["search"]["artifact_id"],
                      {"evidence_type": "explicit_source_link", "source_id": self.source["source_id"], "observed_at": NOW}),
            make_edge(self.source["source_id"], "recommends", self.artifacts["other"]["artifact_id"],
                      {"evidence_type": "explicit_source_link", "source_id": self.source["source_id"], "observed_at": NOW}),
        ])

    def close(self):
        self.temp.cleanup()


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.close()

    def test_corpus_snapshot_is_deterministic_bounded_and_provenanced(self):
        first = build_snapshot(self.fx.store)
        second = build_snapshot(self.fx.store)
        self.assertEqual(first.corpus_hash, second.corpus_hash)
        self.assertEqual([item.artifact_id for item in first.documents], [item.artifact_id for item in second.documents])
        doc = first.by_id()[self.fx.artifacts["search"]["artifact_id"]]
        self.assertEqual(sum(item.artifact_id == doc.artifact_id for item in first.documents), 1)
        self.assertEqual(len(doc.observation_excerpts), 3)
        self.assertLessEqual(max(len(item["text"]) for item in doc.observation_excerpts), 2000)
        self.assertEqual(doc.observation_excerpts[0]["source_id"], self.fx.source["source_id"])

    def test_source_tree_hash_tracks_source_and_entity_records_separately_from_corpus(self):
        first = build_snapshot(self.fx.store)
        second_source = new_source(identity="source|fixture|second", source_type="curator", platform="fixture",
                                   name="Second fixture source", canonical_url="https://second.example/feed",
                                   connector="manual", mode="manual", created_at=NOW)
        self.fx.store.upsert_source(second_source)
        second = build_snapshot(self.fx.store)
        self.assertEqual(first.corpus_hash, second.corpus_hash)
        self.assertNotEqual(first.source_tree_hash, second.source_tree_hash)

    def test_artifact_redirect_collapses_before_indexing(self):
        other_id = "art-" + "a" * 24
        duplicate = dict(self.fx.artifacts["search"], artifact_id=other_id, title="Alias title")
        self.fx.store.upsert_artifact(duplicate)
        self.fx.aliases.add_redirect(other_id, self.fx.artifacts["search"]["artifact_id"])
        snapshot = build_snapshot(self.fx.store)
        self.assertEqual(sum(item.artifact_id == self.fx.artifacts["search"]["artifact_id"] for item in snapshot.documents), 1)

    def test_as_of_excludes_future_publication_and_observation_fallback(self):
        snapshot = build_snapshot(self.fx.store)
        request = make_request("memory", as_of="2026-09-05T00:00:00Z")
        filtered = filter_documents(snapshot, request)
        ids = {item.artifact_id for item in filtered}
        self.assertNotIn(self.fx.artifacts["memory"]["artifact_id"], ids)
        self.assertEqual(future_leak_count([item.artifact_id for item in filtered], snapshot.by_id(), request.as_of), 0)

    def test_as_of_excludes_future_first_observation_when_publication_time_is_missing(self):
        snapshot = build_snapshot(self.fx.store)
        document = snapshot.by_id()[self.fx.artifacts["other"]["artifact_id"]]
        future = replace(document, published_at=None, first_observed_at="2026-09-10T00:00:00Z")
        adjusted = CorpusSnapshot(tuple(future if item.artifact_id == future.artifact_id else item
                                        for item in snapshot.documents), snapshot.corpus_hash, snapshot.source_tree_hash)
        filtered = filter_documents(adjusted, make_request("future fallback", as_of="2026-09-05T00:00:00Z"))
        self.assertNotIn(future.artifact_id, {item.artifact_id for item in filtered})

    def test_bm25_route_ranks_only_temporally_eligible_results(self):
        future = RetrievalDocument("art-" + "1" * 24, "paper", "memorymarker", "", (), (), (),
                                   "2026-09-10T00:00:00Z", NOW, (), (), (), "en", "published_at")
        past = replace(future, artifact_id="art-" + "2" * 24, published_at="2026-09-01T00:00:00Z")
        snapshot = CorpusSnapshot((future, past), "c" * 64, "d" * 64)
        route = BM25Retriever()
        route.build(snapshot, str(self.fx.root / "temporal-runtime"))
        request = make_request("memorymarker", as_of="2026-09-05T00:00:00Z")
        eligible = filter_documents(snapshot, request)
        result = route.retrieve(request, documents=eligible, top_k=10)
        self.assertEqual([item["artifact_id"] for item in result.candidates], [past.artifact_id])
        self.assertEqual(result.candidates[0]["rank"], 1)

    def test_request_id_and_query_expansion_are_deterministic(self):
        one = make_request("搜索智能体 RAG", expanded_terms=expand_query("搜索智能体 RAG"))
        two = make_request("搜索智能体 RAG", expanded_terms=expand_query("搜索智能体 RAG"))
        self.assertEqual(one.request_id, two.request_id)
        self.assertIn("search agent", one.expanded_terms)
        self.assertIn("retrieval augmented generation", one.expanded_terms)
        self.assertGreaterEqual(len(tokenize("搜索智能体")), 2)

    def test_retrieval_manifest_semantic_hash_ignores_built_at(self):
        snapshot = build_snapshot(self.fx.store)
        first = make_manifest(snapshot, retriever_versions={"bm25": "v1"}, built_at="2026-09-28T00:00:00Z")
        second = make_manifest(snapshot, retriever_versions={"bm25": "v1"}, built_at="2026-09-29T00:00:00Z")
        self.assertEqual(first["manifest_hash"], second["manifest_hash"])
        self.assertNotEqual(first["built_at"], second["built_at"])

    def test_graph_citation_author_and_source_routes_are_exact_and_explainable(self):
        snapshot = build_snapshot(self.fx.store)
        seeds = [self.fx.artifacts["search"]["artifact_id"]]
        request = make_request("", seed_artifact_ids=seeds)
        graph = GraphRetriever(str(self.fx.root / "events"))
        graph.build(snapshot, str(self.fx.root / "runtime"))
        result = graph.retrieve(request, documents=snapshot.documents, top_k=20)
        by_id = {item["artifact_id"]: item for item in result.candidates}
        self.assertIn(self.fx.artifacts["memory"]["artifact_id"], by_id)
        self.assertIn("citation", {item["signal"] for item in by_id[self.fx.artifacts["memory"]["artifact_id"]]["explanation"]["graph_paths"]})
        self.assertIn(self.fx.artifacts["other"]["artifact_id"], by_id)
        self.assertGreater(by_id[self.fx.artifacts["other"]["artifact_id"]]["explanation"]["shared_author_count"], 0)
        other_paths = by_id[self.fx.artifacts["other"]["artifact_id"]]["explanation"]["graph_paths"]
        self.assertTrue(any(self.fx.source["source_id"] in path["source_ids"] for path in other_paths))
        source_request = make_request("", source_ids=[self.fx.source["source_id"]])
        source = SourceRetriever(str(self.fx.root / "events"))
        source.build(snapshot, str(self.fx.root / "runtime"))
        source_result = source.retrieve(source_request, documents=snapshot.documents, top_k=10)
        self.assertEqual({item["artifact_id"] for item in source_result.candidates},
                         {self.fx.artifacts["search"]["artifact_id"], self.fx.artifacts["other"]["artifact_id"]})
        other_source = next(item for item in source_result.candidates if item["artifact_id"] == self.fx.artifacts["other"]["artifact_id"])
        self.assertEqual(other_source["explanation"]["source_evidence"][0]["predicate"], "recommends")

    def test_entity_redirect_is_applied_during_graph_retrieval(self):
        old_person = entity_id("redirected-author-old")
        canonical_person = entity_id("redirected-author-canonical")
        self.fx.graph.add_edges([
            make_edge(self.fx.artifacts["search"]["artifact_id"], "authored_by", old_person,
                      {"evidence_type": "exact_provider_metadata", "provider": "fixture", "provider_record_id": "old-author", "observed_at": NOW}),
            make_edge(self.fx.artifacts["memory"]["artifact_id"], "authored_by", canonical_person,
                      {"evidence_type": "exact_provider_metadata", "provider": "fixture", "provider_record_id": "new-author", "observed_at": NOW}),
        ])
        EntityAliases(self.fx.root / "events").add_redirect(
            old_person, canonical_person, provider="fixture", provider_record_id="author-equivalence", created_at=NOW,
        )
        snapshot = build_snapshot(self.fx.store)
        route = GraphRetriever(str(self.fx.root / "events"))
        route.build(snapshot, str(self.fx.root / "runtime"))
        result = route.retrieve(make_request("", seed_artifact_ids=[self.fx.artifacts["search"]["artifact_id"]]),
                                documents=snapshot.documents, top_k=20)
        memory = next(item for item in result.candidates if item["artifact_id"] == self.fx.artifacts["memory"]["artifact_id"])
        self.assertGreater(memory["explanation"]["shared_author_count"], 0)
        self.assertTrue(any(path["signal"] == "author" for path in memory["explanation"]["graph_paths"]))
        self.assertTrue(any(canonical_person in path["entity_ids"] for path in memory["explanation"]["graph_paths"]))

    def test_graph_neighbor_budget_is_bounded(self):
        seed = "art-" + "a" * 24
        neighbors = ["art-" + f"{index:024x}" for index in range(1, 102)]
        docs = [RetrievalDocument(seed, "paper", "seed", "seed", (), (), (), None, NOW, (), (), (), "en", "observed_at_fallback")]
        docs.extend(RetrievalDocument(item, "paper", item, "neighbor", (), (), (), None, NOW, (), (), (), "en", "observed_at_fallback")
                    for item in neighbors)
        snapshot = CorpusSnapshot(tuple(sorted(docs, key=lambda item: item.artifact_id)), "a" * 64, "b" * 64)
        graph_dir = self.fx.root / "bounded-graph"
        graph = GraphStore(graph_dir)
        graph.add_edges([make_edge(seed, "cites", item,
                                   {"evidence_type": "exact_provider_metadata", "provider": "fixture", "provider_record_id": f"edge-{index}", "observed_at": NOW})
                         for index, item in enumerate(neighbors)])
        route = GraphRetriever(str(graph_dir))
        route.build(snapshot, str(self.fx.root / "runtime"))
        result = route.retrieve(make_request("", seed_artifact_ids=[seed]), documents=snapshot.documents, top_k=500)
        self.assertEqual(len(result.candidates), 100)

    def test_topic_route_uses_exact_ids_and_recency(self):
        snapshot = build_snapshot(self.fx.store)
        request = make_request("", topic_ids=["topic-memory"])
        route = TopicRetriever()
        route.build(snapshot, str(self.fx.root / "runtime"))
        result = route.retrieve(request, documents=snapshot.documents, top_k=10)
        self.assertEqual([item["artifact_id"] for item in result.candidates], [self.fx.artifacts["memory"]["artifact_id"]])
        no_alias_match = route.retrieve(make_request("", topic_ids=["topic-not-an-alias"]), documents=snapshot.documents, top_k=10)
        self.assertEqual(no_alias_match.candidates, [])

    def test_bm25_mature_index_is_deterministic_and_persisted(self):
        snapshot = build_snapshot(self.fx.store)
        runtime = self.fx.root / "runtime"
        first = BM25Retriever()
        manifest_one = first.build(snapshot, str(runtime))
        request = make_request("search agent reinforcement learning")
        result = first.retrieve(request, documents=snapshot.documents, top_k=3)
        self.assertEqual(result.candidates[0]["artifact_id"], self.fx.artifacts["search"]["artifact_id"])
        second = BM25Retriever()
        manifest_two = second.build(snapshot, str(runtime))
        self.assertEqual(manifest_one, manifest_two)
        result_two = second.retrieve(request, documents=snapshot.documents, top_k=3)
        self.assertEqual([item["artifact_id"] for item in result.candidates],
                         [item["artifact_id"] for item in result_two.candidates])

    def test_bm25_chinese_query_expansion_reaches_english_document(self):
        snapshot = build_snapshot(self.fx.store)
        route = BM25Retriever()
        route.build(snapshot, str(self.fx.root / "runtime"))
        terms = expand_query("搜索智能体")
        result = route.retrieve(make_request("搜索智能体", expanded_terms=terms), documents=snapshot.documents, top_k=10)
        self.assertEqual(result.candidates[0]["artifact_id"], self.fx.artifacts["search"]["artifact_id"])

    def test_dense_exact_cosine_and_incremental_embedding_cache(self):
        snapshot = build_snapshot(self.fx.store)
        backend = DeterministicFakeEmbedding(2, token_vectors={"query": [1, 0], "close": [0.9, 0.1], "far": [0, 1]})
        docs = tuple([
            RetrievalDocument("art-" + "1" * 24, "paper", "close", "close", (), (), (), None, NOW, (), (), (), "en", "observed_at_fallback"),
            RetrievalDocument("art-" + "2" * 24, "paper", "far", "far", (), (), (), None, NOW, (), (), (), "en", "observed_at_fallback"),
        ])
        custom = CorpusSnapshot(docs, "a" * 64, "b" * 64)
        dense = DenseRetriever(backend)
        runtime = self.fx.root / "runtime"
        dense.build(custom, str(runtime))
        request = make_request("query")
        result = dense.retrieve(request, documents=docs, top_k=2)
        self.assertEqual(result.candidates[0]["artifact_id"], docs[0].artifact_id)
        dense.build(custom, str(runtime))
        self.assertEqual(dense.cache_stats, {"reused": 2, "embedded": 0})
        changed = replace(docs[1], body="close")
        changed_snapshot = CorpusSnapshot((docs[0], changed), "c" * 64, "b" * 64)
        dense.build(changed_snapshot, str(runtime))
        self.assertEqual(dense.cache_stats, {"reused": 1, "embedded": 1})

    def test_synthetic_fixture_routes_are_complementary_and_fuse(self):
        result = run_synthetic_evaluation(self.fx.root / "synthetic-runtime")
        self.assertEqual(result["route_top1"], {"bm25": ARTIFACT_A, "dense": ARTIFACT_D, "graph": ARTIFACT_E})
        self.assertEqual(set(result["fused_ids"]), {ARTIFACT_A, ARTIFACT_D, ARTIFACT_E})
        self.assertEqual(result["route_metrics"]["unique_contribution"], {
            "bm25": [ARTIFACT_A], "dense": [ARTIFACT_D], "graph": [ARTIFACT_E],
        })
        self.assertEqual(result["route_metrics"]["future_leak_count"], 0)
        self.assertEqual(result["label_source"], "synthetic_fixture")

    def test_rrf_exact_rank_based_canonical_and_deduplicated(self):
        rows = {
            "bm25": [{"artifact_id": "alias-a", "rank": 1, "raw_score": 900},
                     {"artifact_id": "art-b", "rank": 2, "raw_score": 0.01}],
            "dense": [{"artifact_id": "art-a", "rank": 3, "raw_score": 0.2},
                      {"artifact_id": "art-a", "rank": 4, "raw_score": 200}],
        }
        fused = reciprocal_rank_fusion(rows, request_id="rq-" + "1" * 24, top_k=10, k=60,
                                       canonicalize=lambda value: "art-a" if value == "alias-a" else value)
        self.assertEqual(fused[0]["artifact_id"], "art-a")
        self.assertAlmostEqual(fused[0]["fusion"]["score"], 1 / 61 + 1 / 63)
        self.assertEqual(len(fused[0]["routes"]), 2)
        self.assertAlmostEqual(fused[1]["fusion"]["score"], 1 / 62)
        changed_scale = {route: [dict(row, raw_score=float(row["raw_score"]) * 1e8) for row in route_rows]
                         for route, route_rows in rows.items()}
        scaled = reciprocal_rank_fusion(changed_scale, request_id="rq-" + "1" * 24, top_k=10, k=60,
                                        canonicalize=lambda value: "art-a" if value == "alias-a" else value)
        self.assertEqual([item["fusion"]["score"] for item in fused], [item["fusion"]["score"] for item in scaled])
        self.assertEqual(len(reciprocal_rank_fusion(rows, request_id="rq-" + "1" * 24, top_k=1)), 1)

    def test_metrics_and_benchmark_freeze_validate_known_ids(self):
        scores = evaluate_ranking(["a", "b", "c"], {"b": 2, "c": 1})
        self.assertEqual(scores["Recall@5"], 1.0)
        self.assertEqual(scores["MRR@10"], 0.5)
        self.assertEqual(scores["Precision@10"], 0.2)
        routes = evaluate_routes({"bm25": ["a", "b"], "dense": ["c"]}, {"b": 1, "c": 2}, k=20)
        self.assertEqual(routes["union_recall"], 1.0)
        self.assertEqual(routes["unique_contribution"]["dense"], ["c"])
        self.assertEqual(evaluate_ranking(["b", "c", "a"], {"b": 2, "c": 1})["nDCG@10"], 1.0)
        query = {"query_id": "q-1", "query": "fixture", "as_of": None, "qrels": {"art-" + "1" * 24: 2},
                 "provenance": {"label_source": "synthetic_fixture", "reviewed_by": None, "reviewed_at": None}}
        benchmark = freeze_benchmark(version="fixture-v1", split="synthetic", corpus_hash="a" * 64, queries=[query])
        same = freeze_benchmark(version="fixture-v1", split="synthetic", corpus_hash="a" * 64, queries=[query])
        changed = freeze_benchmark(version="fixture-v2", split="synthetic", corpus_hash="a" * 64, queries=[query])
        self.assertEqual(benchmark["benchmark_hash"], same["benchmark_hash"])
        self.assertNotEqual(benchmark["benchmark_hash"], changed["benchmark_hash"])
        unreviewed_query = dict(query, provenance={"label_source": "human", "reviewed_by": None, "reviewed_at": None})
        with self.assertRaisesRegex(ValueError, "reviewer identity"):
            freeze_benchmark(version="dev-v1", split="dev", corpus_hash="a" * 64, queries=[unreviewed_query])
        reviewed_query = dict(query, provenance={"label_source": "human", "reviewed_by": "fixture reviewer",
                                                 "reviewed_at": NOW})
        dev = freeze_benchmark(version="dev-v1", split="dev", corpus_hash="a" * 64, queries=[reviewed_query])
        validate_benchmark(dev, ["art-" + "1" * 24])
        validate_benchmark(benchmark, ["art-" + "1" * 24])
        with self.assertRaisesRegex(ValueError, "unknown Artifact"):
            validate_benchmark(benchmark, ["art-" + "2" * 24])

    def test_semantic_scholar_requires_exact_seed_and_defers_without_stopping_local_route(self):
        artifact = dict(self.fx.artifacts["search"])
        artifact["identifiers"] = {"semantic_scholar": "S2-exact-123"}
        self.fx.store.upsert_artifact(artifact)
        snapshot = build_snapshot(self.fx.store)
        called = []

        def unavailable(positive, negative):
            called.append((positive, negative))
            raise TimeoutError("fixture offline")

        s2 = SemanticScholarRecommendationsRetriever(self.fx.store, self.fx.root / "runtime", transport=unavailable)
        s2.build(snapshot, str(self.fx.root / "runtime"))
        exact = make_request("related", seed_artifact_ids=[artifact["artifact_id"]])
        deferred = s2.retrieve(exact, documents=snapshot.documents, top_k=10)
        self.assertEqual(deferred.status, "deferred")
        self.assertEqual(called, [(["S2-exact-123"], [])])

        class LocalRoute:
            spec = RetrieverSpec("local", "fixture-local-v1")
            def build(self, snapshot, runtime_dir):
                return {"corpus_hash": snapshot.corpus_hash}
            def retrieve(self, request, *, documents, top_k):
                return RetrievalResult("local", [{"artifact_id": documents[0].artifact_id, "rank": 1,
                                                   "raw_score": 1.0, "explanation": {"fixture": True}}])

        registry = RetrieverRegistry()
        registry.register(s2)
        registry.register(LocalRoute())
        engine = RetrievalEngine(snapshot, registry, store_dir=str(self.fx.root / "events"),
                                 runtime_dir=str(self.fx.root / "runtime"))
        search = engine.search(exact, routes=["semantic-scholar", "local"], persist=False)
        self.assertEqual(search["routes_executed"], ["local"])
        self.assertEqual(search["routes_skipped"][0]["route"], "semantic-scholar")
        self.assertTrue(search["candidates"])
        self.assertEqual(len(called), 2)

        unresolved = s2.retrieve(make_request("related", seed_artifact_ids=[self.fx.artifacts["memory"]["artifact_id"]]),
                                 documents=snapshot.documents, top_k=10)
        self.assertEqual(unresolved.status, "skipped")
        self.assertEqual(len(called), 2)

    def test_route_failure_isolated_and_search_run_records_corpus_hash(self):
        snapshot = build_snapshot(self.fx.store)
        class Broken:
            spec = RetrieverSpec("dense", "test", optional=True)
            def build(self, snapshot, runtime_dir): raise RuntimeError("fake unavailable")
            def retrieve(self, request, *, documents, top_k): raise AssertionError("must not run")
        class Healthy:
            spec = RetrieverSpec("bm25", "test")
            def build(self, snapshot, runtime_dir): return {"corpus_hash": snapshot.corpus_hash}
            def retrieve(self, request, *, documents, top_k):
                return RetrievalResult("healthy", [{"artifact_id": self.artifact_id, "rank": 1, "raw_score": 1.0, "explanation": {}}])
            artifact_id = snapshot.documents[0].artifact_id
        registry = RetrieverRegistry()
        registry.register(Broken())
        registry.register(Healthy())
        engine = RetrievalEngine(snapshot, registry, store_dir=str(self.fx.root / "events"), runtime_dir=str(self.fx.root / "runtime"))
        result = engine.search(make_request("fixture"), routes=["dense", "bm25"])
        self.assertEqual(result["routes_executed"], ["bm25"])
        self.assertEqual(result["routes_failed"][0]["route"], "dense")
        self.assertEqual(result["corpus_hash"], snapshot.corpus_hash)
        self.assertEqual(result["source_tree_hash"], snapshot.source_tree_hash)
        self.assertTrue(Path(result["run_path"]).exists())

    def test_filters_are_applied_before_route_candidates_are_returned(self):
        snapshot = build_snapshot(self.fx.store)
        registry = RetrieverRegistry()
        registry.register(BM25Retriever())
        engine = RetrievalEngine(snapshot, registry, store_dir=str(self.fx.root / "events"),
                                 runtime_dir=str(self.fx.root / "runtime"))
        request = make_request("search agent", filters={"artifact_types": ["dataset"], "published_after": None,
                                                          "published_before": None, "languages": []})
        result = engine.search(request, routes=["bm25"], persist=False)
        self.assertEqual(result["route_candidates"]["bm25"], [])
        self.assertEqual(result["candidates"], [])


if __name__ == "__main__":
    unittest.main()
