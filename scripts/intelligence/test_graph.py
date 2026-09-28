from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from .aliases import ArtifactAliases
from .cli import _find_graph_path, main
from .connectors.base import ConnectorContext
from .connectors.http import HttpResponse, SharedHttpClient
from .discovery.budget import ExpansionBudget
from .discovery.expand import SourceDiscovery
from .discovery.source_candidates import SourceCandidateStore
from .entity_aliases import EntityAliases, normalize_entity_alias
from .graph.backfill import graph_backfill, validate_graph_nodes
from .graph.builders.observation_artifact import build_observation_artifact_edges
from .graph.builders.scholarly import (
    build_openalex_edges,
    build_semantic_scholar_edges,
    materialize_exact_entity,
)
from .graph.enrichment import enrich_artifact
from .graph.models import make_edge
from .graph.store import GraphStore
from .ids import artifact_id
from .models import new_artifact, new_observation, new_source
from .providers.base import GraphProviderFailure, ProviderCache
from .providers.github_graph import GitHubGraphProvider
from .providers.openalex import OpenAlexGraphProvider
from .providers.semantic_scholar_graph import SemanticScholarGraphProvider
from .resolver import SemanticScholarResolver
from .store import JsonlStore


ROOT = Path(__file__).resolve().parents[2]
GRAPH_FIXTURES = Path(__file__).with_name("fixtures") / "graph"
NOW = "2026-09-28T12:00:00Z"


class SequenceTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def send(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": dict(headers), "timeout": timeout})
        if not self.responses:
            raise AssertionError("unexpected provider request")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def http_response(status: int, payload: object = None, headers: dict[str, str] | None = None) -> HttpResponse:
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    return HttpResponse(status, headers or {}, body)


def fixture(name: str) -> dict:
    return json.loads((GRAPH_FIXTURES / name).read_text(encoding="utf-8"))


def source(identity: str, name: str | None = None) -> dict:
    return new_source(
        identity=identity, source_type="curator", platform="fixture", name=name or identity,
        canonical_url=f"https://example.org/{identity.rsplit('|', 1)[-1]}",
        connector="manual", mode="manual", topics=["topic-search-agent"], created_at=NOW,
    )


def paper(identity: str, *, topics: list[str] | None = None, status: str = "candidate") -> dict:
    return new_artifact(
        identity=identity, artifact_type="paper", title="A synthetic research paper",
        canonical_url=f"https://papers.example/{identity.rsplit(':', 1)[-1]}",
        identifiers={"doi": identity.split(":", 1)[1] if identity.startswith("doi:") else None},
        topics=topics or ["topic-search-agent"], status=status,
    )


class GraphBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.events = self.root / "events"
        self.runtime = self.root / "runtime"
        self.store = JsonlStore(self.events)
        self.graph = GraphStore(self.events)
        self.entity_aliases = EntityAliases(self.events)

    def tearDown(self):
        self.temp.cleanup()

    def add_source_paper(
        self,
        source_record: dict,
        artifact: dict,
        *,
        observation_key: str,
        kind: str = "post",
        evidence_level: str = "rendered_link",
        origin: str = "url",
        observed_at: str = NOW,
    ) -> dict:
        self.store.upsert_source(source_record)
        self.store.upsert_artifact(artifact)
        identifiers = dict(artifact.get("identifiers") or {})
        candidate = {
            "artifact_type": "paper",
            "title": artifact["title"],
            "canonical_url": artifact["canonical_url"],
            "identifiers": identifiers,
            "authors": [],
            "organizations": [],
            "summary": "",
            "topics": artifact["topics"],
            "mention": {"evidence_level": evidence_level, "origin": origin, "confidence": 1.0},
        }
        observation = new_observation(
            identity=observation_key, source_id=source_record["source_id"], platform=source_record["platform"],
            platform_object_id=observation_key, kind=kind, title="Curated paper", text="A synthetic note.",
            urls=[artifact["canonical_url"]], media=[], published_at=None, observed_at=observed_at,
            topics=artifact["topics"], provenance={
                "retrieval_mode": "fixture", "evidence_level": "source_text",
                "source_url": source_record["canonical_url"], "collector": "test",
            },
            artifact_candidates=[candidate],
        )
        self.store.append_observation(observation)
        return observation

    def add_author(self, author_id: str = "S2AUTHOR123", name: str = "Researcher Example") -> dict:
        entity, _ = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="person", name=name,
            external_ids={"semantic_scholar_author": author_id},
            url=f"https://www.semanticscholar.org/author/{author_id}",
            provider="semantic-scholar", provider_record_id="S2PAPER123", now=NOW,
        )
        return entity

    def add_authorship_edge(self, artifact: dict, entity: dict) -> dict:
        edge = make_edge(
            artifact["artifact_id"], "authored_by", entity["entity_id"],
            {"evidence_type": "exact_provider_metadata", "provider": "semantic-scholar",
             "provider_record_id": "S2PAPER123", "observed_at": NOW},
        )
        return self.graph.add_edge(edge)


class GraphEdgeAndStoreTests(GraphBase):
    def test_same_relation_merges_distinct_source_evidence_deterministically(self):
        edge_a = make_edge(
            "src-" + "a" * 24, "mentions", "art-" + "b" * 24,
            {"evidence_type": "explicit_source_link", "source_id": "src-" + "a" * 24,
             "observation_id": "obs-" + "1" * 24, "observed_at": "2026-09-27T12:00:00Z"},
        )
        edge_b = make_edge(
            "src-" + "a" * 24, "mentions", "art-" + "b" * 24,
            {"evidence_type": "explicit_source_link", "source_id": "src-" + "c" * 24,
             "observation_id": "obs-" + "2" * 24, "observed_at": NOW},
        )
        self.graph.add_edge(edge_a)
        merged = self.graph.add_edge(edge_b)
        self.assertEqual(edge_a["edge_id"], edge_b["edge_id"])
        self.assertEqual(len(merged["evidence"]), 2)
        self.assertEqual(merged["first_observed_at"], "2026-09-27T12:00:00Z")
        self.assertEqual(merged["last_observed_at"], NOW)
        self.assertEqual(len(self.graph.iter_edges()), 1)

    def test_repeated_provider_evidence_updates_observed_at_without_duplicate(self):
        first = make_edge(
            "art-" + "a" * 24, "authored_by", "ent-" + "b" * 24,
            {"evidence_type": "exact_provider_metadata", "provider": "openalex",
             "provider_record_id": "W123", "observed_at": "2026-09-27T12:00:00Z"},
        )
        later = make_edge(
            "art-" + "a" * 24, "authored_by", "ent-" + "b" * 24,
            {"evidence_type": "exact_provider_metadata", "provider": "openalex",
             "provider_record_id": "W123", "observed_at": NOW},
        )
        self.graph.add_edge(first)
        merged = self.graph.add_edge(later)
        self.assertEqual(len(merged["evidence"]), 1)
        self.assertEqual(merged["evidence"][0]["observed_at"], NOW)
        self.assertEqual(merged["last_observed_at"], NOW)

    def test_name_similarity_and_inference_cannot_write_canonical_edges(self):
        with self.assertRaisesRegex(ValueError, "evidence"):
            make_edge(
                "art-" + "a" * 24, "authored_by", "ent-" + "b" * 24,
                {"evidence_type": "inferred_candidate", "observed_at": NOW},
            )
        with self.assertRaisesRegex(ValueError, "predicate"):
            make_edge(
                "art-" + "a" * 24, "authored", "ent-" + "b" * 24,
                {"evidence_type": "exact_provider_metadata", "provider": "fixture", "observed_at": NOW},
            )

    def test_graph_corruption_fails_closed(self):
        self.events.mkdir(parents=True, exist_ok=True)
        (self.events / "graph_edges.jsonl").write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "corrupt graph edge store"):
            self.graph.iter_edges()

    def test_graph_index_rebuild_is_deterministic_after_delete(self):
        self.add_author()
        artifact = paper("doi:10.5555/graph.1")
        self.store.upsert_artifact(artifact)
        self.add_authorship_edge(artifact, list(self.store.iter_records("entity"))[0])
        first = self.graph.rebuild_indexes(self.runtime, entity_id_resolver=self.entity_aliases)
        before_out = (self.runtime / "graph" / "out_edges.json").read_bytes()
        before_in = (self.runtime / "graph" / "in_edges.json").read_bytes()
        (self.runtime / "graph" / "out_edges.json").unlink()
        (self.runtime / "graph" / "in_edges.json").unlink()
        second = self.graph.rebuild_indexes(self.runtime, entity_id_resolver=self.entity_aliases)
        self.assertEqual(first, second)
        self.assertEqual(before_out, (self.runtime / "graph" / "out_edges.json").read_bytes())
        self.assertEqual(before_in, (self.runtime / "graph" / "in_edges.json").read_bytes())

    def test_evidence_union_serialization_is_stable_across_insertion_order(self):
        first = make_edge(
            "art-" + "a" * 24, "authored_by", "ent-" + "b" * 24,
            {"evidence_type": "exact_provider_metadata", "provider": "openalex",
             "provider_record_id": "W1", "observed_at": NOW},
        )
        second = make_edge(
            "art-" + "a" * 24, "authored_by", "ent-" + "b" * 24,
            {"evidence_type": "exact_provider_metadata", "provider": "semantic-scholar",
             "provider_record_id": "S2P1", "observed_at": NOW},
        )
        self.graph.add_edge(first)
        self.graph.add_edge(second)
        bytes_forward = self.graph.path.read_bytes()
        reverse_dir = self.root / "reverse"
        reverse = GraphStore(reverse_dir)
        reverse.add_edge(second)
        reverse.add_edge(first)
        self.assertEqual(bytes_forward, reverse.path.read_bytes())

    def test_graph_query_resolves_old_entity_id_without_rewriting_historical_edge(self):
        canonical, _ = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="person", name="Author",
            external_ids={"openalex_author": "A123"}, url="", provider="openalex",
            provider_record_id="W1", now=NOW,
        )
        old_id = "ent-" + "f" * 24
        self.entity_aliases.add_redirect(
            old_id, canonical["entity_id"], provider="openalex",
            provider_record_id="A123", created_at=NOW,
        )
        artifact = paper("doi:10.5555/redirect.1")
        self.store.upsert_artifact(artifact)
        edge = make_edge(
            artifact["artifact_id"], "authored_by", old_id,
            {"evidence_type": "exact_provider_metadata", "provider": "openalex",
             "provider_record_id": "W1", "observed_at": NOW},
        )
        self.graph.add_edge(edge)
        query = self.graph.neighbors(canonical["entity_id"], predicate="authored_by",
                                     entity_id_resolver=self.entity_aliases)
        self.assertEqual(len(query), 1)
        self.assertEqual(self.graph.iter_edges()[0]["object_id"], old_id)


class EntityIdentityTests(GraphBase):
    def test_exact_orcid_and_openalex_aliases_resolve_to_one_person(self):
        first, _ = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="person", name="Same Name",
            external_ids={"semantic_scholar_author": "S2AUTHOR123"},
            url="https://www.semanticscholar.org/author/S2AUTHOR123",
            provider="semantic-scholar", provider_record_id="S2AUTHOR123", now=NOW,
        )
        second, created = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="person", name="Same Name",
            external_ids={"semantic_scholar_author": "S2AUTHOR123", "openalex_author": "A123",
                          "orcid": "https://orcid.org/0000-0002-1825-0097"},
            url="https://openalex.org/A123",
            provider="openalex", provider_record_id="W123", now=NOW,
        )
        self.assertFalse(created)
        self.assertEqual(first["entity_id"], second["entity_id"])
        self.assertEqual(self.entity_aliases.resolve_alias("openalex-author:https://openalex.org/A123"), first["entity_id"])
        self.assertEqual(self.entity_aliases.resolve_alias("orcid:0000000218250097"), first["entity_id"])

    def test_same_name_without_exact_id_does_not_merge(self):
        first, _ = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="person", name="Alex Example",
            external_ids={"openalex_author": "A111"}, url="", provider="openalex",
            provider_record_id="W1", now=NOW,
        )
        second, created = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="person", name="Alex Example",
            external_ids={"openalex_author": "A222"}, url="", provider="openalex",
            provider_record_id="W2", now=NOW,
        )
        self.assertTrue(created)
        self.assertNotEqual(first["entity_id"], second["entity_id"])
        name_only = __import__("scripts.intelligence.models", fromlist=["new_entity"]).new_entity(
            identity="name-only|alex example", entity_type="person", name="Alex Example",
            resolution_state="unresolved",
        )
        self.store.upsert_entity(name_only)
        self.assertEqual(name_only["resolution_state"], "unresolved")
        self.assertIsNone(self.entity_aliases.resolve_alias("openalex-author:A333"))

    def test_entity_alias_normalizes_only_exact_provider_identifiers(self):
        self.assertEqual(normalize_entity_alias("openalex-author:https://openalex.org/A123"), "openalex-author:A123")
        self.assertEqual(normalize_entity_alias("orcid:0000000218250097"), "orcid:0000-0002-1825-0097")
        self.assertEqual(normalize_entity_alias("ror:https://ror.org/03yrm5c26"), "ror:03yrm5c26")
        self.assertEqual(normalize_entity_alias("issn:1234567x"), "issn:1234-567X")
        self.assertEqual(normalize_entity_alias("issn:1234-567X"), "issn:1234-567X")
        with self.assertRaises(ValueError):
            normalize_entity_alias("person-name:alex-example")
        with self.assertRaises(ValueError):
            normalize_entity_alias("github-user:alex")

    def test_entity_redirect_path_compression_and_cycle_detection(self):
        old, middle, canonical = ("ent-" + char * 24 for char in "abc")
        self.entity_aliases.add_redirect(
            old, middle, provider="openalex", provider_record_id="A1", created_at=NOW,
        )
        self.entity_aliases.add_redirect(
            middle, canonical, provider="openalex", provider_record_id="A2", created_at=NOW,
        )
        self.assertEqual(self.entity_aliases.resolve_entity_id(old), canonical)
        redirects = [json.loads(line) for line in (self.events / "entity_redirects.jsonl").read_text().splitlines()]
        self.assertEqual(next(row for row in redirects if row["from_entity_id"] == old)["to_entity_id"], canonical)
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.entity_aliases.add_redirect(
                canonical, old, provider="openalex", provider_record_id="A3", created_at=NOW,
            )

    def test_entity_redirect_reader_rejects_unvisited_corrupt_cycle(self):
        first, second = ("ent-" + char * 24 for char in "ab")
        self.entity_aliases._atomic_jsonl(self.entity_aliases.redirect_path, [
            {"schema": "bubblevan/intelligence-entity-redirect/v1", "from_entity_id": first,
             "to_entity_id": second, "reason": "exact_provider_equivalence", "provider": "openalex",
             "provider_record_id": "A1", "created_at": NOW},
            {"schema": "bubblevan/intelligence-entity-redirect/v1", "from_entity_id": second,
             "to_entity_id": first, "reason": "exact_provider_equivalence", "provider": "openalex",
             "provider_record_id": "A2", "created_at": NOW},
        ])
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.entity_aliases.resolve_entity_id("ent-" + "c" * 24)

    def test_entity_alias_cooccurrence_is_exact_equivalence_evidence(self):
        first, _ = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="institution", name="Lab",
            external_ids={"openalex_institution": "I123"}, url="", provider="openalex",
            provider_record_id="W1", now=NOW,
        )
        second, _ = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="institution", name="Lab",
            external_ids={"ror": "03yrm5c26", "openalex_institution": "I123"}, url="",
            provider="openalex", provider_record_id="I123", now=NOW,
        )
        self.assertEqual(first["entity_id"], second["entity_id"])
        self.assertEqual(self.entity_aliases.resolve_alias("ror:03yrm5c26"), first["entity_id"])
        self.assertEqual(self.entity_aliases.resolve_alias("openalex-institution:I123"), first["entity_id"])


class LocalGraphAndDiscoveryTests(GraphBase):
    def _seed_graph(self, source_count: int = 1, observations_per_source: int = 1):
        artifact = paper("doi:10.5555/discovery.1")
        self.store.upsert_artifact(artifact)
        seed_sources = []
        for source_index in range(source_count):
            src = source(f"curator|{source_index}", f"Curator {source_index}")
            seed_sources.append(src)
            for observation_index in range(observations_per_source):
                self.add_source_paper(
                    src, artifact, observation_key=f"seed-{source_index}-{observation_index}",
                    observed_at=f"2026-09-{27 + source_index:02d}T12:00:00Z",
                )
        author = self.add_author()
        self.add_authorship_edge(artifact, author)
        return seed_sources, artifact, author

    def test_source_artifact_edges_require_explicit_links_and_recommendation_semantics(self):
        src = source("curator|a")
        art = paper("doi:10.5555/link.1")
        self.add_source_paper(src, art, observation_key="linked")
        other = paper("doi:10.5555/inferred.1")
        self.store.upsert_artifact(other)
        self.add_source_paper(src, other, observation_key="inferred", evidence_level="image_extract", origin="ocr")
        rec = paper("doi:10.5555/recommended.1")
        self.store.upsert_artifact(rec)
        self.add_source_paper(src, rec, observation_key="recommendation", kind="recommendation")
        result = build_observation_artifact_edges(
            self.store, self.graph, ArtifactAliases(self.events), self.entity_aliases, now=NOW,
        )
        predicates = {(edge["object_id"], edge["predicate"]) for edge in self.graph.iter_edges()}
        self.assertIn((art["artifact_id"], "mentions"), predicates)
        self.assertIn((rec["artifact_id"], "recommends"), predicates)
        self.assertNotIn((other["artifact_id"], "mentions"), predicates)
        self.assertEqual(result["unlinked_candidates_skipped"], 1)

    def test_github_release_repository_metadata_is_an_exact_source_edge(self):
        src = source("github|stanford-oval/storm", "STORM releases")
        repository = new_artifact(
            identity="github:stanford-oval/storm", artifact_type="repository",
            title="STORM releases", canonical_url="https://github.com/stanford-oval/storm",
            identifiers={"github": "stanford-oval/storm"},
        )
        observation = self.add_source_paper(
            src, repository, observation_key="storm-release", evidence_level="api_metadata", origin="repository",
        )
        build_observation_artifact_edges(
            self.store, self.graph, ArtifactAliases(self.events), self.entity_aliases, now=NOW,
        )
        repository_edge = next(edge for edge in self.graph.iter_edges() if edge["subject_id"] == src["source_id"])
        evidence = repository_edge["evidence"][0]
        self.assertEqual(repository_edge["object_id"], repository["artifact_id"])
        self.assertEqual(evidence["evidence_type"], "exact_provider_metadata")
        self.assertEqual(evidence["provider"], "github")
        self.assertEqual(evidence["provider_record_id"], "stanford-oval/storm")
        self.assertEqual(evidence["observation_id"], observation["observation_id"])

    def test_discovery_reaches_github_owner_from_repository_seed_source(self):
        src = source("github|stanford-oval/storm", "STORM releases")
        repository = new_artifact(
            identity="github:stanford-oval/storm", artifact_type="repository",
            title="STORM releases", canonical_url="https://github.com/stanford-oval/storm",
            identifiers={"github": "stanford-oval/storm"},
        )
        self.add_source_paper(
            src, repository, observation_key="storm-release", evidence_level="api_metadata", origin="repository",
        )
        graph_backfill(self.store, self.runtime, now=NOW)
        from .graph.builders.github import build_github_owner_edge
        build_github_owner_edge(
            repository,
            {"provider": "github", "status": "succeeded",
             "repository": {"id": 918273645, "full_name": "stanford-oval/storm", "topics": ["agent"]},
             "owner": {"id": 112233, "login": "stanford-oval", "type": "Organization",
                       "html_url": "https://github.com/stanford-oval"}},
            self.store, self.graph, self.entity_aliases, now=NOW,
        )
        result = SourceDiscovery(
            self.store, self.graph, self.entity_aliases, SourceCandidateStore(self.events), now=NOW,
        ).discover(src["source_id"], ExpansionBudget(max_depth=2))
        candidates = SourceCandidateStore(self.events).iter_candidates()
        self.assertEqual(result["candidates_generated"], 1)
        self.assertEqual(candidates[0]["candidate_type"], "organization")
        self.assertEqual(candidates[0]["signals"]["independent_source_count"], 1)
        self.assertEqual(candidates[0]["evidence_paths"][0]["depth"], 2)

    def test_backfill_is_offline_and_replay_adds_no_duplicate_edges(self):
        sources, _, _ = self._seed_graph(source_count=1, observations_per_source=2)
        calls = []
        first = graph_backfill(self.store, self.runtime, now=NOW)
        edge_count = len(self.graph.iter_edges())
        second = graph_backfill(self.store, self.runtime, now=NOW)
        self.assertEqual(first["network_requests"], 0)
        self.assertEqual(second["observation_artifact"]["edges_added"], 0)
        self.assertEqual(len(self.graph.iter_edges()), edge_count)
        self.assertEqual(self.graph.neighbors(sources[0]["source_id"], predicate="mentions")[0]["predicate"], "mentions")
        self.assertEqual(calls, [])
        validate_graph_nodes(self.store, self.graph)

    def test_discovery_counts_independent_sources_not_observations(self):
        sources, _, author = self._seed_graph(source_count=1, observations_per_source=10)
        graph_backfill(self.store, self.runtime, now=NOW)
        result = SourceDiscovery(
            self.store, self.graph, self.entity_aliases, SourceCandidateStore(self.events), now=NOW,
        ).discover(sources[0]["source_id"], ExpansionBudget(max_depth=2))
        candidate = SourceCandidateStore(self.events).iter_candidates()[0]
        self.assertEqual(candidate["entity_id"], author["entity_id"])
        self.assertEqual(candidate["signals"]["supporting_artifact_count"], 1)
        self.assertEqual(candidate["signals"]["independent_source_count"], 1)
        self.assertEqual(candidate["signals"]["min_path_depth"], 2)
        self.assertEqual(candidate["evidence_paths"][0]["depth"], 2)
        self.assertEqual(len(candidate["evidence_paths"][0]["steps"]), 2)
        self.assertEqual(result["provider_requests"], 0)

    def test_two_independent_curators_support_same_exact_person(self):
        sources, _, _ = self._seed_graph(source_count=2, observations_per_source=3)
        graph_backfill(self.store, self.runtime, now=NOW)
        result = SourceDiscovery(
            self.store, self.graph, self.entity_aliases, SourceCandidateStore(self.events), now=NOW,
        ).discover(sources[0]["source_id"], ExpansionBudget(max_depth=2))
        candidate = SourceCandidateStore(self.events).iter_candidates()[0]
        self.assertEqual(candidate["signals"]["independent_source_count"], 2)
        self.assertEqual(set(candidate["signals"]["supporting_source_ids"]), {item["source_id"] for item in sources})
        self.assertEqual(len(result["candidate_ids"]), 1)

    def test_discovery_honors_depth_node_edge_and_candidate_budgets(self):
        sources, _, _ = self._seed_graph()
        graph_backfill(self.store, self.runtime, now=NOW)
        shallow = SourceDiscovery(
            self.store, self.graph, self.entity_aliases, SourceCandidateStore(self.events), now=NOW,
        ).discover(sources[0]["source_id"], ExpansionBudget(max_depth=1))
        self.assertEqual(shallow["candidates_generated"], 0)
        limited = SourceDiscovery(
            self.store, self.graph, self.entity_aliases, SourceCandidateStore(self.events), now=NOW,
        ).discover(sources[0]["source_id"], ExpansionBudget(max_depth=2, max_nodes=2, max_edges=1))
        self.assertLessEqual(limited["nodes_visited"], 2)
        self.assertLessEqual(limited["edges_traversed"], 1)
        self.assertTrue(limited["budget_exhausted"])
        with self.assertRaisesRegex(ValueError, "non-negative"):
            ExpansionBudget(max_depth=-1)

    def test_candidate_rejection_survives_repeated_discovery_and_new_evidence(self):
        sources, _, _ = self._seed_graph(source_count=1)
        graph_backfill(self.store, self.runtime, now=NOW)
        candidates = SourceCandidateStore(self.events)
        discovery = SourceDiscovery(self.store, self.graph, self.entity_aliases, candidates, now=NOW)
        discovery.discover(sources[0]["source_id"], ExpansionBudget(max_depth=2))
        candidate = candidates.iter_candidates()[0]
        rejected = candidates.review(candidate["candidate_id"], "rejected", reviewed_at=NOW, reason_code="low_signal")
        self.assertEqual(rejected["status"], "rejected")
        self.add_source_paper(source("curator|second"), list(self.store.iter_records("artifact"))[0], observation_key="later")
        build_observation_artifact_edges(self.store, self.graph, ArtifactAliases(self.events), self.entity_aliases, now=NOW)
        discovery.discover(sources[0]["source_id"], ExpansionBudget(max_depth=2))
        updated = candidates.iter_candidates()[0]
        self.assertEqual(updated["status"], "rejected")
        self.assertEqual(updated["reason_code"], "low_signal")

    def test_approval_is_not_source_activation_and_yaml_catalog_stays_unchanged(self):
        sources, _, _ = self._seed_graph()
        graph_backfill(self.store, self.runtime, now=NOW)
        candidates = SourceCandidateStore(self.events)
        SourceDiscovery(self.store, self.graph, self.entity_aliases, candidates, now=NOW).discover(
            sources[0]["source_id"], ExpansionBudget(max_depth=2),
        )
        candidate = candidates.iter_candidates()[0]
        catalog = (ROOT / "data" / "intelligence" / "sources.yaml").read_bytes()
        approved = candidates.review(candidate["candidate_id"], "approved", reviewed_at=NOW)
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(catalog, (ROOT / "data" / "intelligence" / "sources.yaml").read_bytes())
        self.assertFalse((self.events / "sources.jsonl").read_text(encoding="utf-8").count(candidate["candidate_id"]))

    def test_candidate_can_be_explicitly_reopened(self):
        sources, _, _ = self._seed_graph()
        graph_backfill(self.store, self.runtime, now=NOW)
        candidates = SourceCandidateStore(self.events)
        SourceDiscovery(self.store, self.graph, self.entity_aliases, candidates, now=NOW).discover(
            sources[0]["source_id"], ExpansionBudget(max_depth=2),
        )
        candidate = candidates.iter_candidates()[0]
        candidates.review(candidate["candidate_id"], "rejected", reviewed_at=NOW, reason_code="duplicate")
        reopened = candidates.review(candidate["candidate_id"], "pending", reviewed_at=NOW)
        self.assertEqual(reopened["status"], "pending")
        self.assertIsNone(reopened["reason_code"])

    def test_candidate_exact_entity_redirect_coalesces_review_memory(self):
        sources, _, old_entity = self._seed_graph()
        graph_backfill(self.store, self.runtime, now=NOW)
        candidates = SourceCandidateStore(self.events)
        discovery = SourceDiscovery(self.store, self.graph, self.entity_aliases, candidates, now=NOW)
        discovery.discover(sources[0]["source_id"], ExpansionBudget(max_depth=2))
        old_candidate = candidates.iter_candidates()[0]
        candidates.review(old_candidate["candidate_id"], "rejected", reviewed_at=NOW, reason_code="duplicate")
        from .models import new_entity
        canonical = new_entity(
            identity="semantic-scholar-author|S2AUTHOR-CANONICAL", entity_type="person",
            name="Canonical author", external_ids={"semantic_scholar_author": "S2AUTHOR-CANONICAL"},
        )
        self.store.upsert_entity(canonical)
        self.entity_aliases.add_redirect(
            old_entity["entity_id"], canonical["entity_id"], provider="semantic-scholar",
            provider_record_id="S2AUTHOR-CANONICAL", created_at=NOW,
        )
        discovery.discover(sources[0]["source_id"], ExpansionBudget(max_depth=2))
        rows = candidates.iter_candidates()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["entity_id"], canonical["entity_id"])
        self.assertEqual(rows[0]["status"], "rejected")
        self.assertEqual(rows[0]["reason_code"], "duplicate")

    def test_evidence_paths_are_directed_and_queryable(self):
        sources, _, author = self._seed_graph()
        graph_backfill(self.store, self.runtime, now=NOW)
        result = _find_graph_path(
            sources[0]["source_id"], author["entity_id"], self.graph, self.entity_aliases, 2,
        )
        self.assertTrue(result["found"])
        self.assertEqual([step["predicate"] for step in result["steps"]], ["mentions", "authored_by"])
        self.assertTrue(all(step["evidence"] for step in result["steps"]))

    def test_provider_verification_is_not_counted_as_independent_source(self):
        sources, _, _ = self._seed_graph()
        graph_backfill(self.store, self.runtime, now=NOW)
        SourceDiscovery(
            self.store, self.graph, self.entity_aliases, SourceCandidateStore(self.events), now=NOW,
        ).discover(sources[0]["source_id"], ExpansionBudget(max_depth=2))
        candidate = SourceCandidateStore(self.events).iter_candidates()[0]
        self.assertEqual(candidate["signals"]["independent_source_count"], 1)
        self.assertEqual(candidate["signals"]["provider_count"], 1)

    def test_replay_keeps_candidate_id_and_path_order_stable(self):
        sources, _, _ = self._seed_graph(source_count=2, observations_per_source=2)
        graph_backfill(self.store, self.runtime, now=NOW)
        candidates = SourceCandidateStore(self.events)
        discovery = SourceDiscovery(self.store, self.graph, self.entity_aliases, candidates, now=NOW)
        discovery.discover(sources[0]["source_id"], ExpansionBudget(max_depth=2))
        first = candidates.iter_candidates()[0]
        discovery.discover(sources[0]["source_id"], ExpansionBudget(max_depth=2))
        second = candidates.iter_candidates()[0]
        self.assertEqual(first["candidate_id"], second["candidate_id"])
        self.assertEqual(first["evidence_paths"], second["evidence_paths"])
        self.assertEqual(len(candidates.iter_candidates()), 1)

    def test_synthetic_seed_store_reaches_author_and_institution_with_cross_source_support(self):
        fixture_path = Path(__file__).with_name("fixtures") / "graph" / "graph_seed_store" / "seed.json"
        seed = json.loads(fixture_path.read_text(encoding="utf-8"))
        source_rows = {item["key"]: source(f"fixture|{item['key']}", item["name"]) for item in seed["curators"]}
        for src in source_rows.values():
            self.store.upsert_source(src)
        authors = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="person", name="Author X",
            external_ids={"semantic_scholar_author": "S2AUTHOR-X"},
            url="https://www.semanticscholar.org/author/S2AUTHOR-X",
            provider="semantic-scholar", provider_record_id="S2AUTHOR-X", now=NOW,
        )[0]
        authors, _ = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="person", name="Author X",
            external_ids={"semantic_scholar_author": "S2AUTHOR-X", "openalex_author": "A900",
                          "orcid": "0000-0002-1825-0097"},
            url="https://openalex.org/A900", provider="openalex", provider_record_id="W900", now=NOW,
        )
        institution, _ = materialize_exact_entity(
            self.store, self.entity_aliases, entity_type="institution", name="Institution I",
            external_ids={"openalex_institution": "I900", "ror": "03yrm5c26"},
            url="https://openalex.org/I900", provider="openalex", provider_record_id="A900", now=NOW,
        )
        for index, row in enumerate(seed["papers"]):
            artifact = new_artifact(
                identity=f"doi:{row['doi']}", artifact_type="paper", title=row["title"],
                canonical_url=f"https://papers.example/{row['key']}",
                identifiers={"doi": row["doi"]}, topics=["topic-search-agent"],
            )
            src_key = "curator-a" if index < 2 else "curator-b"
            self.add_source_paper(source_rows[src_key], artifact, observation_key=f"fixture-{row['key']}")
            self.graph.add_edge(make_edge(
                artifact["artifact_id"], "authored_by", authors["entity_id"],
                {"evidence_type": "exact_provider_metadata", "provider": "openalex",
                 "provider_record_id": "W900", "observed_at": NOW},
            ))
        self.graph.add_edge(make_edge(
            authors["entity_id"], "affiliated_with", institution["entity_id"],
            {"evidence_type": "exact_provider_metadata", "provider": "openalex",
             "provider_record_id": "A900", "observed_at": NOW},
        ))
        graph_backfill(self.store, self.runtime, now=NOW)
        result = SourceDiscovery(
            self.store, self.graph, self.entity_aliases, SourceCandidateStore(self.events), now=NOW,
        ).discover(source_rows["curator-a"]["source_id"], ExpansionBudget(max_depth=3))
        candidates = SourceCandidateStore(self.events).iter_candidates()
        author_candidate = next(item for item in candidates if item["entity_id"] == authors["entity_id"])
        institution_candidate = next(item for item in candidates if item["entity_id"] == institution["entity_id"])
        expected = seed["expected"]["author_candidate"]
        self.assertEqual(author_candidate["signals"]["supporting_artifact_count"], expected["supporting_artifact_count"])
        self.assertEqual(author_candidate["signals"]["independent_source_count"], expected["independent_source_count"])
        self.assertEqual(author_candidate["signals"]["min_path_depth"], expected["min_path_depth"])
        self.assertEqual(institution_candidate["signals"]["min_path_depth"], 3)
        self.assertEqual(result["provider_requests"], 0)


class GraphBuilderTests(GraphBase):
    def test_openalex_builds_exact_author_and_institution_edges(self):
        artifact = paper("doi:10.5555/graph.1")
        self.store.upsert_artifact(artifact)
        provider = OpenAlexGraphProvider(ProviderCache(self.runtime / "provider-cache"))
        expansion = {
            "provider": "openalex",
            "status": "succeeded",
            "work": {
                "id": "W123",
                "authors": [{
                    "id": "A123",
                    "name": "Researcher Example",
                    "orcid": "https://orcid.org/0000-0002-1825-0097",
                    "institutions": [{"id": "I123", "name": "Example Research Lab", "ror": "03yrm5c26"}],
                }],
                "venue": {"id": "S123", "name": "Example Journal", "issn_l": "1234-567X"},
                "referenced_works": ["W456"],
            },
        }
        result = build_openalex_edges(artifact, expansion, self.store, self.graph, self.entity_aliases, now=NOW)
        self.assertEqual(result["entities_added"], 3)
        relations = {(edge["predicate"], edge["subject_id"], edge["object_id"]) for edge in self.graph.iter_edges()}
        author = self.entity_aliases.resolve_alias("openalex-author:A123")
        institution = self.entity_aliases.resolve_alias("ror:03yrm5c26")
        venue = self.entity_aliases.resolve_alias("openalex-source:S123")
        self.assertIn(("authored_by", artifact["artifact_id"], author), relations)
        self.assertIn(("affiliated_with", author, institution), relations)
        self.assertIn(("published_in", artifact["artifact_id"], venue), relations)
        self.assertEqual(result["citations_added"], 0)

    def test_semantic_scholar_citations_materialize_candidate_artifact_metadata(self):
        artifact = new_artifact(
            identity="semantic-scholar:S2PAPER123", artifact_type="paper", title="Known paper",
            identifiers={"semantic_scholar": "S2PAPER123"},
        )
        self.store.upsert_artifact(artifact)
        expansion = {
            "provider": "semantic-scholar",
            "status": "succeeded",
            "paper": {"paperId": "S2PAPER123", "authors": []},
            "references": [fixture("s2_references.json")["data"][0]["citedPaper"]],
            "citations": [fixture("s2_citations.json")["data"][0]["citingPaper"]],
        }
        result = build_semantic_scholar_edges(
            artifact, expansion, self.store, self.graph, self.entity_aliases, now=NOW,
            max_references=1, max_citations=1,
        )
        self.assertEqual(result["citations_added"], 2)
        cites = [edge for edge in self.graph.iter_edges() if edge["predicate"] == "cites"]
        self.assertEqual(len(cites), 2)
        other_artifacts = [item for item in self.store.iter_records("artifact") if item["artifact_id"] != artifact["artifact_id"]]
        self.assertEqual(len(other_artifacts), 2)
        self.assertTrue(all(item["status"] == "candidate" and item["title"] for item in other_artifacts))
        self.assertTrue(all(item["identifiers"].get("semantic_scholar") for item in other_artifacts))

    def test_github_owner_is_a_first_class_exact_entity_edge(self):
        artifact = new_artifact(
            identity="github:example/graph-fixture", artifact_type="repository",
            title="graph-fixture", canonical_url="https://github.com/example/graph-fixture",
            identifiers={"github": "example/graph-fixture"},
        )
        self.store.upsert_artifact(artifact)
        result = build_github = __import__(
            "scripts.intelligence.graph.builders.github", fromlist=["build_github_owner_edge"],
        ).build_github_owner_edge(
            artifact,
            {"provider": "github", "status": "succeeded",
             "repository": {"full_name": "example/graph-fixture"},
             "owner": {"id": 123456, "login": "example", "type": "Organization",
                       "html_url": "https://github.com/example"}},
            self.store, self.graph, self.entity_aliases, now=NOW,
        )
        self.assertEqual(result["entities_added"], 1)
        organization_id = self.entity_aliases.resolve_alias("github-org:123456")
        edge = self.graph.iter_edges()[0]
        self.assertEqual((edge["subject_id"], edge["predicate"], edge["object_id"]),
                         (artifact["artifact_id"], "owned_by", organization_id))
        self.assertEqual(edge["evidence"][0]["evidence_type"], "exact_provider_metadata")


class ProviderTests(GraphBase):
    def test_exact_provider_lookup_runs_when_local_arxiv_alias_already_exists(self):
        artifact = new_artifact(
            identity="arxiv:2609.12345", artifact_type="paper", title="A synthetic research paper",
            identifiers={"arxiv": "2609.12345"},
        )
        self.store.upsert_artifact(artifact)
        artifact_aliases = ArtifactAliases(self.events)
        artifact_aliases.register_alias(
            "arxiv:2609.12345", artifact["artifact_id"], resolver="local", resolver_id="observation",
            resolved_at=NOW,
        )
        transport = SequenceTransport([http_response(200, json.loads(
            (Path(__file__).with_name("fixtures") / "connectors" / "s2_arxiv.json").read_text(encoding="utf-8")
        ))])
        result = SemanticScholarResolver().resolve(
            artifact, artifact["artifact_id"], artifact_aliases,
            self.context(transport), force_provider_lookup=True,
        )
        self.assertEqual(result["classification"], "provider_equivalence")
        self.assertEqual(artifact_aliases.resolve_alias("semantic-scholar:S2PAPER001"), artifact["artifact_id"])
        self.assertEqual(len(transport.calls), 1)

    def test_openalex_exact_arxiv_enrichment_counts_resolver_and_provider_requests(self):
        artifact = new_artifact(
            identity="arxiv:2609.12345", artifact_type="paper", title="A synthetic research paper",
            identifiers={"arxiv": "2609.12345"},
        )
        self.store.upsert_artifact(artifact)
        ArtifactAliases(self.events).register_alias(
            "arxiv:2609.12345", artifact["artifact_id"], resolver="local", resolver_id="observation",
            resolved_at=NOW,
        )
        openalex_response = fixture("openalex_work.json")
        openalex_response["doi"] = "https://doi.org/10.5555/ri.2026.1"
        transport = SequenceTransport([
            http_response(200, json.loads(
                (Path(__file__).with_name("fixtures") / "connectors" / "s2_arxiv.json").read_text(encoding="utf-8")
            )),
            http_response(200, openalex_response),
        ])
        result = enrich_artifact(
            artifact["artifact_id"], "openalex", self.store, self.graph, self.entity_aliases, self.runtime,
            budget=ExpansionBudget(max_provider_requests=2, max_references_per_artifact=0,
                                   max_citations_per_artifact=0),
            context=self.context(transport),
        )
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["provider_requests"], 2)
        self.assertEqual(len(transport.calls), 2)

    def test_exact_identifier_transport_failure_is_safe_and_sets_retry_state(self):
        artifact = new_artifact(
            identity="arxiv:2609.12345", artifact_type="paper", title="A synthetic research paper",
            identifiers={"arxiv": "2609.12345"},
        )
        self.store.upsert_artifact(artifact)
        ArtifactAliases(self.events).register_alias(
            "arxiv:2609.12345", artifact["artifact_id"], resolver="local", resolver_id="observation",
            resolved_at=NOW,
        )
        secret_url = "https://api.example.invalid/path?token=provider-secret"
        transport = SequenceTransport([RuntimeError(secret_url)])
        result = enrich_artifact(
            artifact["artifact_id"], "openalex", self.store, self.graph, self.entity_aliases, self.runtime,
            budget=ExpansionBudget(max_provider_requests=2, max_references_per_artifact=0,
                                   max_citations_per_artifact=0),
            context=self.context(transport),
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["error_class"], "RuntimeError")
        self.assertNotIn("provider-secret", json.dumps(result))
        state = json.loads((self.runtime / "graph" / "providers" / "openalex.json").read_text())
        self.assertIsNone(state["backoff_until"])

    def context(self, transport, environment=None):
        return ConnectorContext(
            store=self.store,
            http=SharedHttpClient(transport, now=lambda: datetime.fromisoformat(NOW.replace("Z", "+00:00"))),
            environment=environment or {},
            now=lambda: NOW,
        )

    def test_openalex_uses_exact_work_identity_and_selected_fields(self):
        transport = SequenceTransport([http_response(200, fixture("openalex_work.json"), {"ETag": '"oa1"'})])
        provider = OpenAlexGraphProvider(ProviderCache(self.runtime / "cache"))
        result = provider.expand_artifact(
            paper("doi:10.5555/graph.1"), self.context(transport), ExpansionBudget(max_provider_requests=5),
        )
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["work"]["id"], "W123")
        self.assertEqual(result["work"]["authors"][0]["institutions"][0]["id"], "I123")
        self.assertEqual(len(result["work"]["referenced_works"]), 2)
        self.assertIn("select=", transport.calls[0]["url"])
        self.assertIn("authorships", transport.calls[0]["url"])
        self.assertNotIn("Authorization", transport.calls[0]["headers"])

    def test_semantic_scholar_reference_and_citation_fanout_are_hard_bounded(self):
        transport = SequenceTransport([
            http_response(200, fixture("s2_paper_graph.json")),
            http_response(200, fixture("s2_references.json")),
            http_response(200, fixture("s2_citations.json")),
        ])
        provider = SemanticScholarGraphProvider(ProviderCache(self.runtime / "cache"))
        artifact = new_artifact(
            identity="semantic-scholar:S2PAPER123", artifact_type="paper",
            identifiers={"semantic_scholar": "S2PAPER123"},
        )
        budget = ExpansionBudget(max_provider_requests=5, max_references_per_artifact=99, max_citations_per_artifact=99)
        result = provider.expand_artifact(artifact, self.context(transport), budget)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(budget.max_references_per_artifact, 20)
        self.assertEqual(budget.max_citations_per_artifact, 20)
        self.assertEqual(len(result["references"]), 1)
        self.assertEqual(len(result["citations"]), 1)
        self.assertTrue(all(parse_qs(urlsplit(call["url"]).query).get("limit", [""])[0] == "20"
                            for call in transport.calls[1:]))

    def test_provider_request_budget_prevents_additional_network_calls(self):
        transport = SequenceTransport([http_response(200, fixture("s2_paper_graph.json"))])
        provider = SemanticScholarGraphProvider(ProviderCache(self.runtime / "cache"))
        artifact = new_artifact(
            identity="semantic-scholar:S2PAPER123", artifact_type="paper",
            identifiers={"semantic_scholar": "S2PAPER123"},
        )
        budget = ExpansionBudget(max_provider_requests=1)
        result = provider.expand_artifact(artifact, self.context(transport), budget)
        self.assertEqual(len(transport.calls), 1)
        self.assertTrue(budget.exhausted)
        self.assertTrue(result["budget_exhausted"])
        self.assertEqual(result["status"], "partial")

    def test_semantic_scholar_author_recent_work_limit_is_at_most_ten(self):
        transport = SequenceTransport([http_response(200, fixture("s2_author_papers.json"))])
        provider = SemanticScholarGraphProvider(ProviderCache(self.runtime / "cache"))
        entity = {"entity_id": "ent-" + "1" * 24, "external_ids": {"semantic_scholar_author": "S2AUTHOR123"}}
        budget = ExpansionBudget(max_provider_requests=2, max_recent_works_per_author=100)
        result = provider.expand_entity(entity, self.context(transport), budget)
        self.assertEqual(len(result["recent_works"]), 1)
        self.assertEqual(budget.max_recent_works_per_author, 10)
        self.assertEqual(parse_qs(urlsplit(transport.calls[0]["url"]).query)["limit"], ["10"])

    def test_github_provider_persists_only_allowlisted_metadata(self):
        transport = SequenceTransport([http_response(200, fixture("github_repo.json"), {"ETag": '"gh1"'})])
        provider = GitHubGraphProvider(ProviderCache(self.runtime / "cache"))
        artifact = new_artifact(
            identity="github:example/graph-fixture", artifact_type="repository",
            identifiers={"github": "example/graph-fixture"},
        )
        result = provider.expand_artifact(artifact, self.context(transport), ExpansionBudget(max_provider_requests=1))
        self.assertEqual(result["repository"]["id"], 321654987)
        self.assertEqual(result["owner"]["id"], 123456)
        cache_text = "\n".join(path.read_text(encoding="utf-8") for path in (self.runtime / "cache").rglob("*.json"))
        self.assertNotIn("stargazers_count", cache_text)
        self.assertNotIn("private", cache_text)

    def test_provider_cache_identity_and_ttl_reuse_selected_response(self):
        transport = SequenceTransport([http_response(200, fixture("github_repo.json"))])
        provider = GitHubGraphProvider(ProviderCache(self.runtime / "cache"))
        artifact = new_artifact(
            identity="github:example/graph-fixture", artifact_type="repository",
            identifiers={"github": "example/graph-fixture"},
        )
        first = provider.expand_artifact(artifact, self.context(transport), ExpansionBudget(max_provider_requests=2))
        second = provider.expand_artifact(artifact, self.context(transport), ExpansionBudget(max_provider_requests=2))
        self.assertEqual(first["repository"], second["repository"])
        self.assertEqual(len(transport.calls), 1)

    def test_github_exhausted_rate_limit_propagates_reset_timestamp(self):
        reset = int(datetime(2026, 9, 28, 14, 0, tzinfo=timezone.utc).timestamp())
        transport = SequenceTransport([http_response(
            403, {}, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)},
        )])
        provider = GitHubGraphProvider(ProviderCache(self.runtime / "cache"))
        artifact = new_artifact(
            identity="github:example/graph-fixture", artifact_type="repository",
            identifiers={"github": "example/graph-fixture"},
        )
        with self.assertRaises(GraphProviderFailure) as caught:
            provider.expand_artifact(artifact, self.context(transport), ExpansionBudget(max_provider_requests=1))
        self.assertEqual(caught.exception.status, 403)
        self.assertEqual(caught.exception.retry_after_seconds, 7200)
        self.assertEqual(caught.exception.retry_at, "2026-09-28T14:00:00Z")

    def test_semantic_scholar_rate_limit_keeps_partial_graph_and_safe_retry_state(self):
        transport = SequenceTransport([
            http_response(200, fixture("s2_paper_graph.json")),
            http_response(200, fixture("s2_references.json")),
            http_response(429, {}, {"Retry-After": "3600"}),
        ])
        artifact = new_artifact(
            identity="semantic-scholar:S2PAPER123", artifact_type="paper", title="Known paper",
            identifiers={"semantic_scholar": "S2PAPER123"},
        )
        self.store.upsert_artifact(artifact)
        existing = make_edge(
            "src-" + "a" * 24, "mentions", artifact["artifact_id"],
            {"evidence_type": "explicit_source_link", "source_id": "src-" + "a" * 24,
             "observation_id": "obs-" + "b" * 24, "observed_at": NOW},
        )
        self.graph.add_edge(existing)
        result = enrich_artifact(
            artifact["artifact_id"], "semantic-scholar", self.store, self.graph,
            self.entity_aliases, self.runtime,
            budget=ExpansionBudget(max_provider_requests=5, max_references_per_artifact=1, max_citations_per_artifact=1),
            context=self.context(transport),
        )
        self.assertEqual(result["status"], "partial")
        predicates = {edge["predicate"] for edge in self.graph.iter_edges()}
        self.assertIn("mentions", predicates)
        self.assertIn("authored_by", predicates)
        self.assertIn("cites", predicates)
        state = json.loads((self.runtime / "graph" / "providers" / "semantic-scholar.json").read_text())
        self.assertEqual(state["retry_after_seconds"], 3600)
        self.assertEqual(state["backoff_until"], "2026-09-28T13:00:00Z")
        self.assertEqual(len(transport.calls), 3)

    def test_graph_provider_never_persists_api_key_value(self):
        secret = "s2-secret-value-fixture"
        transport = SequenceTransport([http_response(200, fixture("s2_paper_graph.json"))])
        provider = SemanticScholarGraphProvider(ProviderCache(self.runtime / "cache"))
        artifact = new_artifact(
            identity="semantic-scholar:S2PAPER123", artifact_type="paper",
            identifiers={"semantic_scholar": "S2PAPER123"},
        )
        provider.expand_artifact(
            artifact, self.context(transport, {"SEMANTIC_SCHOLAR_API_KEY": secret}),
            ExpansionBudget(max_provider_requests=1, max_references_per_artifact=0, max_citations_per_artifact=0),
        )
        self.assertEqual(transport.calls[0]["headers"]["x-api-key"], secret)
        stored = "\n".join(
            path.read_text(encoding="utf-8") for path in self.root.rglob("*")
            if path.is_file() and path.name != "sources.yaml"
        )
        self.assertNotIn(secret, stored)


class GraphCliTests(GraphBase):
    def test_graph_enrich_requires_an_explicit_provider_request_budget(self):
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                main(["graph-enrich", "--artifact", "art-" + "a" * 24, "--provider", "openalex"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("--max-provider-requests", stderr.getvalue())

    def test_cli_candidate_template_never_changes_seed_catalog(self):
        sources, _, _ = LocalGraphAndDiscoveryTests._seed_graph(self)
        graph_backfill(self.store, self.runtime, now=NOW)
        SourceDiscovery(
            self.store, self.graph, self.entity_aliases, SourceCandidateStore(self.events), now=NOW,
        ).discover(sources[0]["source_id"], ExpansionBudget(max_depth=2))
        candidate = SourceCandidateStore(self.events).iter_candidates()[0]
        catalog_before = (ROOT / "data" / "intelligence" / "sources.yaml").read_bytes()
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["export-source-template", candidate["candidate_id"], "--store-dir", str(self.events)])
        self.assertEqual(code, 0)
        self.assertIn("status: paused", output.getvalue())
        self.assertIn("connector: manual", output.getvalue())
        self.assertEqual(catalog_before, (ROOT / "data" / "intelligence" / "sources.yaml").read_bytes())

    def test_cli_graph_path_shows_edge_evidence(self):
        sources, _, author = LocalGraphAndDiscoveryTests._seed_graph(self)
        graph_backfill(self.store, self.runtime, now=NOW)
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([
                "graph-path", sources[0]["source_id"], author["entity_id"], "--max-depth", "2",
                "--store-dir", str(self.events),
            ])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["found"])
        self.assertTrue(all(step["evidence"] for step in payload["steps"]))
