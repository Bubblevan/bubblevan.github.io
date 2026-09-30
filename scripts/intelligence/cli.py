from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

from .bridge_capture import ingest_capture
from .bridge_xhs import ingest_xhs
from .entity_aliases import EntityAliases
from .store import JsonlStore
from .aliases import ArtifactAliases
from .connectors.base import ConnectorContext
from .connectors.registry import connector_registry
from .connectors.state import ConnectorStateStore
from .ids import artifact_id
from .connectors.http import SharedHttpClient
from .discovery.budget import ExpansionBudget
from .discovery.expand import SourceDiscovery
from .discovery.source_candidates import SourceCandidateStore
from .graph.backfill import graph_backfill, validate_graph_nodes
from .graph.enrichment import enrich_artifact, enrich_entity
from .graph.store import GraphStore
from .models import now_utc
from .resolver import SemanticScholarResolver, materialize_semantic_scholar_result
from .runner import load_merged_source_catalog, load_source_catalog, run_all_sources, run_source
from .retrieval.bm25 import BM25Retriever
from .retrieval.corpus import build_snapshot
from .retrieval.dense import DenseRetriever, SentenceTransformerBackend
from .retrieval.engine import RetrievalEngine, explain_candidate, infer_topic_ids, read_run
from .retrieval.graph import GraphRetriever
from .retrieval.manifest import dense_freshness, make_manifest
from .retrieval.registry import RetrieverRegistry
from .retrieval.request import make_request
from .retrieval.source import SourceRetriever
from .retrieval.topic import TopicRetriever
from .retrieval.expansion import expand_query
from .repositories.artifacts import ArtifactRepository


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORE = REPO_ROOT / "data" / "intelligence" / "events"
DEFAULT_RUNTIME = REPO_ROOT / "data" / "intelligence" / "runtime"
DEFAULT_PRIVATE = REPO_ROOT / "data" / "intelligence" / "private" / "feed"
DEFAULT_PRIVATE_ROOT = DEFAULT_PRIVATE.parent
_STORE_LOCKED_COMMANDS = {
    "ingest-xhs", "ingest-capture", "run-source", "run-all", "resolve-artifact",
    "graph-backfill", "graph-rebuild", "graph-enrich", "graph-enrich-pending", "graph-enrich-author",
    "repair-hf-identities", "rematerialize-primary-artifacts", "enrich-hf-metadata",
    "discover-sources", "approve-source-candidate", "reject-source-candidate", "reopen-source-candidate",
    "discover-rss-sources", "approve-source-proposal", "reject-source-proposal", "defer-source-proposal",
    "propose-openalex-topics", "approve-openalex-topic", "reject-openalex-topic",
    "social-sync", "social-sync-inbox", "retrieval-warm-dense",
}
_MUTATING_COMMANDS = {
    "ingest-xhs", "ingest-capture", "run-source", "run-all", "resolve-artifact", "smoke",
    "graph-backfill", "graph-rebuild", "graph-enrich", "graph-enrich-pending", "graph-enrich-author",
    "repair-hf-identities", "rematerialize-primary-artifacts", "enrich-hf-metadata", "discover-sources",
    "approve-source-candidate", "reject-source-candidate", "reopen-source-candidate",
    "retrieval-build", "retrieval-smoke", "search", "retrieval-label-pack", "eval-import-json",
    "eval-import-argilla", "eval-build-model-judge-pool", "eval-import-model-judgments", "eval-freeze", "eval-run",
    "social-sync", "social-sync-inbox", "retrieval-warm-dense",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline Personal Research Intelligence data layer.")
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("ingest-xhs", "ingest-capture"):
        command = commands.add_parser(name)
        command.add_argument("json_file", type=Path)
        command.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    inspect = commands.add_parser("inspect-artifact")
    inspect.add_argument("artifact_id")
    inspect.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    stats = commands.add_parser("stats")
    stats.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    artifact_stats = commands.add_parser("artifact-stats", help="show physical and canonical Artifact counts")
    artifact_stats.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    feedback_stats = commands.add_parser("feedback-stats", help="show privacy-safe aggregate feedback inventory")
    feedback_stats.add_argument("--mode", choices=["production", "smoke"], default=None)
    feedback_stats.add_argument("--private-dir", type=Path, default=None)
    feedback_stats.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    feed_profile = commands.add_parser("feed-profile", help="inspect or update the private personal feed profile")
    feed_profile.add_argument("--add-topic", action="append", default=[])
    feed_profile.add_argument("--remove-topic", action="append", default=[])
    feed_profile.add_argument("--follow-source", action="append", default=[])
    feed_profile.add_argument("--unfollow-source", action="append", default=[])
    feed_profile.add_argument("--block-topic", action="append", default=[])
    feed_profile.add_argument("--unblock-topic", action="append", default=[])
    feed_profile.add_argument("--block-source", action="append", default=[])
    feed_profile.add_argument("--unblock-source", action="append", default=[])
    feed_profile.add_argument("--mode", choices=["production", "smoke"], default=None)
    feed_profile.add_argument("--private-dir", type=Path, default=None)
    feed_profile.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    feed_daily = commands.add_parser("feed-daily", help="generate or read the immutable daily personal feed")
    feed_daily.add_argument("--date", default=None)
    feed_daily.add_argument("--refresh", action="store_true")
    feed_daily.add_argument("--lookback-days", type=int, default=7)
    feed_daily.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    feed_daily.add_argument("--revision")
    feed_daily.add_argument("--device")
    feed_daily.add_argument("--experimental-graph", action="store_true")
    feed_daily.add_argument("--no-dense", action="store_true", help="skip the optional local Dense route")
    feed_daily.add_argument("--mode", choices=["production", "smoke"], default=None)
    feed_daily.add_argument("--private-dir", type=Path, default=None)
    feed_daily.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    feed_daily.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    feed_feedback = commands.add_parser("feed-feedback", help="append one private v2 feedback event")
    feed_feedback.add_argument("feed_run_id")
    feed_feedback.add_argument("artifact_id")
    feed_feedback.add_argument("action")
    feed_feedback.add_argument("--target-id")
    feed_feedback.add_argument("--reason-code")
    feed_feedback.add_argument("--supersedes-feedback-id")
    feed_feedback.add_argument("--mode", choices=["production", "smoke"], default=None)
    feed_feedback.add_argument("--private-dir", type=Path, default=None)
    feed_feedback.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    feed_stats = commands.add_parser("feed-stats", help="show aggregate personal feed interaction metrics")
    feed_stats.add_argument("--mode", choices=["production", "smoke"], default=None)
    feed_stats.add_argument("--private-dir", type=Path, default=None)
    feed_stats.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    archive_smoke = commands.add_parser("feed-archive-smoke", help="archive M4 feed smoke data and copy profile preferences only")
    archive_smoke.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    archive_smoke.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    daily = commands.add_parser("intelligence-daily", help="run the one-shot daily Research Intelligence pipeline")
    daily.add_argument("--date", default=None)
    daily.add_argument("--mode", choices=["production", "smoke"], default="production")
    daily.add_argument("--attempt", type=int, default=None)
    daily.add_argument("--dense", action="store_true", help="attempt to warm the local Dense cache")
    daily.add_argument("--device", default=None)
    daily.add_argument("--enrich-limit", type=int, default=0)
    daily.add_argument("--enrich-provider", choices=["openalex", "semantic-scholar", "github"], default="openalex")
    daily.add_argument("--force", action="store_true")
    daily.add_argument("--scheduled", action="store_true", help=argparse.SUPPRESS)
    daily.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    daily.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    daily.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)

    ops = commands.add_parser("ops-status", help="show pipeline, source freshness, and feed status")
    ops.add_argument("--mode", choices=["production", "smoke"], default="production")
    ops.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    ops.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    commands.add_parser("connectors", help="list available connector ids and capabilities")
    commands.add_parser("sources", help="list seed sources and approved private subscriptions")
    local_sources = commands.add_parser("source-records", help="list locally materialized sources")
    local_sources.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    run = commands.add_parser("run-source", help="run one configured source once")
    run.add_argument("source_id")
    run.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    run.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    run_all = commands.add_parser("run-all", help="run each active source once")
    run_all.add_argument("--once", action="store_true", required=True)
    run_all.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    run_all.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    social_add = commands.add_parser("social-add-url", help="add a canonical public social URL to the private inbox")
    social_add.add_argument("url")
    social_add.add_argument("--source-id")
    social_add.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    social_inbox = commands.add_parser("social-inbox", help="list pending sanitized social URLs")
    social_inbox.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    social_sync = commands.add_parser("social-sync", help="interactively sync one approved browser source")
    social_sync.add_argument("--source", required=True)
    social_sync.add_argument("--limit", type=int, default=10)
    social_sync.add_argument("--postprocess", action="store_true")
    social_sync.add_argument("--enrich-images", action="store_true")
    social_sync.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    social_sync.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    social_sync_inbox = commands.add_parser("social-sync-inbox", help="interactively sync pending inbox URLs")
    social_sync_inbox.add_argument("--limit", type=int, default=10)
    social_sync_inbox.add_argument("--postprocess", action="store_true")
    social_sync_inbox.add_argument("--enrich-images", action="store_true")
    social_sync_inbox.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    social_sync_inbox.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    social_sync_inbox.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    social_rss = commands.add_parser("social-propose-zhihu-rss", help="probe the configured RSSHub Zhihu answer route")
    social_rss.add_argument("--profile-url", required=True)
    social_rss.add_argument("--store", type=Path, default=None)

    state = commands.add_parser("connector-state", help="show one local connector checkpoint")
    state.add_argument("source_id")
    state.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    smoke = commands.add_parser("smoke", help="explicitly run an optional live resolver smoke check")
    smoke.add_argument("provider", choices=["semantic-scholar"])
    smoke.add_argument("--arxiv", required=True)
    smoke.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    resolve = commands.add_parser("resolve-artifact", help="optionally reconcile an artifact with Semantic Scholar")
    resolve.add_argument("artifact_id")
    resolve.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    for name in ("graph-backfill", "graph-rebuild", "graph-stats"):
        command = commands.add_parser(name)
        command.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
        command.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    for name in ("repair-hf-identities", "audit-hf-identities"):
        command = commands.add_parser(name, help="repair or audit reserved Hugging Face URL identities")
        command.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    neighbors = commands.add_parser("graph-neighbors")
    neighbors.add_argument("node_id")
    neighbors.add_argument("--predicate")
    neighbors.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    path = commands.add_parser("graph-path")
    path.add_argument("from_id")
    path.add_argument("to_id")
    path.add_argument("--max-depth", type=int, default=3)
    path.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    enrich = commands.add_parser("graph-enrich")
    enrich.add_argument("--artifact", required=True)
    enrich.add_argument("--provider", choices=["openalex", "semantic-scholar", "github"], required=True)
    enrich.add_argument("--max-provider-requests", type=int, required=True)
    enrich.add_argument("--max-references", type=int, default=20)
    enrich.add_argument("--max-citations", type=int, default=20)
    enrich.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    enrich.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    pending = commands.add_parser("graph-enrich-pending")
    pending.add_argument("--provider", choices=["openalex", "semantic-scholar", "github"], required=True)
    pending.add_argument("--limit", type=int, required=True)
    pending.add_argument("--max-provider-requests", type=int, required=True)
    pending.add_argument("--max-references", type=int, default=20)
    pending.add_argument("--max-citations", type=int, default=20)
    pending.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    pending.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    enrich_author = commands.add_parser("graph-enrich-author")
    enrich_author.add_argument("--entity", required=True)
    enrich_author.add_argument("--provider", choices=["semantic-scholar"], required=True)
    enrich_author.add_argument("--limit", type=int, required=True)
    enrich_author.add_argument("--max-provider-requests", type=int, required=True)
    enrich_author.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    enrich_author.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    discover = commands.add_parser("discover-sources")
    discover.add_argument("--seed-source", required=True)
    discover.add_argument("--max-depth", type=int, default=2)
    discover.add_argument("--max-nodes", type=int, default=100)
    discover.add_argument("--max-edges", type=int, default=300)
    discover.add_argument("--max-candidates", type=int, default=50)
    discover.add_argument("--max-provider-requests", type=int, default=50)
    discover.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    candidates = commands.add_parser("source-candidates")
    candidates.add_argument("--status", choices=["pending", "approved", "rejected", "deferred"])
    candidates.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    candidate = commands.add_parser("source-candidate")
    candidate.add_argument("candidate_id")
    candidate.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    approve = commands.add_parser("approve-source-candidate")
    approve.add_argument("candidate_id")
    approve.add_argument("--reviewed-at", default=now_utc())
    approve.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    reject = commands.add_parser("reject-source-candidate")
    reject.add_argument("candidate_id")
    reject.add_argument("--reason-code", choices=["irrelevant", "low_signal", "duplicate", "too_broad", "not_a_source", "already_known", "other"], required=True)
    reject.add_argument("--reviewed-at", default=now_utc())
    reject.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    reopen = commands.add_parser("reopen-source-candidate")
    reopen.add_argument("candidate_id")
    reopen.add_argument("--reviewed-at", default=now_utc())
    reopen.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    export = commands.add_parser("export-source-template")
    export.add_argument("candidate_id")
    export.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    proposals = commands.add_parser("source-proposals", help="list discovered endpoint proposals for human review")
    proposals.add_argument("--status", choices=["pending", "approved", "rejected", "deferred"])
    proposals.add_argument("--store", type=Path, default=None)
    discover_rss = commands.add_parser("discover-rss-sources", help="propose standard RSS/Atom links from source candidates")
    discover_rss.add_argument("--limit", type=int, default=12)
    discover_rss.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    review_source = commands.add_parser("approve-source-proposal")
    review_source.add_argument("proposal_id")
    review_source.add_argument("--store", type=Path, default=None)
    reject_source = commands.add_parser("reject-source-proposal")
    reject_source.add_argument("proposal_id")
    reject_source.add_argument("--reason-code", default="not_a_source")
    reject_source.add_argument("--store", type=Path, default=None)
    defer_source = commands.add_parser("defer-source-proposal")
    defer_source.add_argument("proposal_id")
    defer_source.add_argument("--store", type=Path, default=None)
    probe_review = commands.add_parser("probe-openreview-source", help="probe one explicit OpenReview invitation and API version")
    probe_review.add_argument("--api-version", type=int, choices=[1, 2], required=True)
    probe_review.add_argument("--invitation", required=True)
    probe_review.add_argument("--decision-invitation")
    probe_source = commands.add_parser("probe-source", help="validate a source endpoint without persisting observations")
    probe_source.add_argument("provider", choices=["rss", "openreview", "huggingface-daily", "openalex"])
    probe_source.add_argument("--url")
    probe_source.add_argument("--api-version", type=int, choices=[1, 2])
    probe_source.add_argument("--invitation")
    probe_source.add_argument("--query", help="JSON exact-ID OpenAlex query object")
    topic_propose = commands.add_parser("propose-openalex-topics", help="search OpenAlex topics; proposal requires human approval")
    topic_propose.add_argument("internal_topic_id")
    topic_propose.add_argument("--store", type=Path, default=None)
    topic_proposals = commands.add_parser("openalex-topic-proposals")
    topic_proposals.add_argument("--status", choices=["pending", "approved", "rejected"])
    topic_proposals.add_argument("--store", type=Path, default=None)
    topic_approve = commands.add_parser("approve-openalex-topic")
    topic_approve.add_argument("proposal_id")
    topic_approve.add_argument("--reviewed-by", required=True)
    topic_approve.add_argument("--store", type=Path, default=None)
    topic_reject = commands.add_parser("reject-openalex-topic")
    topic_reject.add_argument("proposal_id")
    topic_reject.add_argument("--store", type=Path, default=None)
    coverage = commands.add_parser("source-coverage", help="report source contribution and overlap over a rolling window")
    coverage.add_argument("--days", type=int, default=7)
    coverage.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    coverage.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    retrieval_build = commands.add_parser("retrieval-build", help="build reproducible local retrieval indexes")
    retrieval_build.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    retrieval_build.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    retrieval_build.add_argument("--dense", action="store_true", help="build the live embedding index")
    retrieval_build.add_argument("--routes", nargs="+", choices=["bm25", "dense", "topic", "source", "graph"],
                                 help="build only the selected retrieval routes (for example: --routes dense)")
    retrieval_build.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    retrieval_build.add_argument("--revision")
    retrieval_build.add_argument("--device")
    retrieval_manifest = commands.add_parser("retrieval-manifest", help="show deterministic corpus/index manifests")
    retrieval_manifest.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    retrieval_manifest.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    retrieval_status = commands.add_parser("retrieval-status", help="compare current corpus and local Dense freshness")
    retrieval_status.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    retrieval_status.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    retrieval_warm = commands.add_parser("retrieval-warm-dense", help="warm the optional Dense index using the incremental embedding cache")
    retrieval_warm.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    retrieval_warm.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    retrieval_warm.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    retrieval_warm.add_argument("--revision")
    retrieval_warm.add_argument("--device")
    retrieval_smoke = commands.add_parser("retrieval-smoke", help="run ten fixed local multi-route smoke queries")
    retrieval_smoke.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    retrieval_smoke.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    retrieval_smoke.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    retrieval_smoke.add_argument("--revision")
    retrieval_smoke.add_argument("--device")

    research_start = commands.add_parser("research-start", help="start a private evidence-grounded research session")
    research_start.add_argument("--query", default="")
    research_start.add_argument("--artifact", action="append", default=[])
    research_start.add_argument("--real-case", action="store_true",
                                 help="apply real-corpus synthetic-evidence and first-party quality gates")
    research_start.add_argument("--feed-run-id")
    research_start.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    research_start.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    research_start.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    research_evidence = commands.add_parser("research-evidence", help="collect bounded local evidence for a research session")
    research_evidence.add_argument("session_id")
    research_evidence.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    research_evidence.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    research_evidence.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    research_evidence.add_argument("--paper-file", action="append", default=[], metavar="ARTIFACT_ID=PATH",
                                   help="optional explicitly supplied local paper full text; never downloads URLs")
    research_generate = commands.add_parser(
        "research-generate", aliases=["research-synthesize"],
        help="explicitly synthesize a research brief from frozen evidence")
    research_generate.add_argument("session_id")
    research_generate.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    research_generate.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    research_generate.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    research_show = commands.add_parser("research-show", help="show a private research session and latest draft")
    research_show.add_argument("session_id")
    research_show.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    research_show.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    research_show.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    research_review = commands.add_parser("research-review", help="record explicit human review of a research draft")
    research_review.add_argument("session_id")
    research_review.add_argument("--reviewer", required=True)
    research_review.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    research_review.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    research_review.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    research_approve = commands.add_parser("research-approve", help="explicitly approve a reviewed draft for Hugo")
    research_approve.add_argument("session_id")
    research_approve.add_argument("--approver", required=True)
    research_approve.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    research_approve.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    research_approve.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    research_preview = commands.add_parser("research-promotion-preview", help="create a private Hugo promotion preview")
    research_preview.add_argument("session_id")
    research_preview.add_argument("--target", required=True)
    research_preview.add_argument("--title")
    research_preview.add_argument("--topic", action="append", default=[])
    research_preview.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    research_preview.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    research_preview.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    research_promote = commands.add_parser("research-promote", help="write an explicitly approved brief to the selected Hugo target")
    research_promote.add_argument("session_id")
    research_promote.add_argument("--target", required=True)
    research_promote.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    research_promote.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    research_promote.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)

    search = commands.add_parser("search", help="run explainable multi-route retrieval")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--top-k", type=int, default=20)
    search.add_argument("--route-depth", type=int, default=50)
    search.add_argument("--corpus-profile", choices=["research-default", "all-artifacts", "models"], default="research-default")
    search.add_argument("--graph-expand", action="store_true", help="add query-seeded graph expansion from BM25/Dense results")
    search.add_argument("--topic", action="append", default=[])
    search.add_argument("--seed-artifact", action="append", default=[])
    search.add_argument("--negative-seed-artifact", action="append", default=[])
    search.add_argument("--source", action="append", default=[])
    search.add_argument("--as-of")
    search.add_argument("--artifact-type", action="append", default=[])
    search.add_argument("--language", action="append", default=[])
    search.add_argument("--routes", help="comma-separated route IDs")
    search.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    search.add_argument("--revision")
    search.add_argument("--device")
    search.add_argument("--no-dense", action="store_true")
    search.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    search.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    explain = commands.add_parser("explain-retrieval", help="explain one candidate from a stored retrieval run")
    explain.add_argument("request_id")
    explain.add_argument("artifact_id")
    explain.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    commands.add_parser("rematerialize-primary-artifacts", help="rebuild RSS primary Artifacts from local observations without network")
    enrich_hf = commands.add_parser("enrich-hf-metadata", help="enrich a bounded set of exact Hugging Face repo IDs")
    enrich_hf.add_argument("--limit", type=int, default=20)
    enrich_hf.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    enrich_hf.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    label_pack = commands.add_parser("retrieval-label-pack", help="build a blind DEV relevance judgment pool")
    label_pack.add_argument("--queries", type=Path, default=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1" / "queries-draft.json")
    label_pack.add_argument("--output-dir", type=Path, default=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1")
    label_pack.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    label_pack.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    label_pack.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    label_pack.add_argument("--revision")
    label_pack.add_argument("--device")
    eval_root = REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1"
    eval_pack = commands.add_parser("eval-export-json", help="export a blind portable annotation JSON")
    eval_pack.add_argument("--pack", type=Path, default=eval_root / "dev-v1-label-pack.json")
    eval_pack.add_argument("--output", type=Path, default=eval_root / "dev-v1-annotation-json.json")
    eval_pack.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    eval_argilla = commands.add_parser("eval-export-argilla", help="sync blind candidates to Argilla")
    eval_argilla.add_argument("--pack", type=Path, default=eval_root / "dev-v1-label-pack.json")
    eval_argilla.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    eval_import_json = commands.add_parser("eval-import-json", help="validate and import partial human or model JSON judgments")
    eval_import_json.add_argument("--pack", type=Path, default=eval_root / "dev-v1-label-pack.json")
    eval_import_json.add_argument("--input", type=Path, required=True)
    eval_import_json.add_argument("--qrels", type=Path, default=eval_root / "dev-v1-qrels.json")
    eval_import_json.add_argument("--reviewed-by")
    eval_import_json.add_argument("--reviewed-at")
    eval_import_json.add_argument("--judge-type", choices=["human", "model"], default="human")
    eval_import_json.add_argument("--judge-name")
    eval_import_json.add_argument("--judge-model")
    eval_import_argilla = commands.add_parser("eval-import-argilla", help="validate and import Argilla judgments")
    eval_import_argilla.add_argument("--pack", type=Path, default=eval_root / "dev-v1-label-pack.json")
    eval_import_argilla.add_argument("--dataset")
    eval_import_argilla.add_argument("--qrels", type=Path, default=eval_root / "dev-v1-qrels.json")
    eval_import_argilla.add_argument("--reviewed-by")
    eval_import_argilla.add_argument("--reviewed-at")
    eval_import_argilla.add_argument("--judge-type", choices=["human", "model"], default="human")
    eval_import_argilla.add_argument("--judge-name")
    eval_import_argilla.add_argument("--judge-model")
    eval_build_pool = commands.add_parser("eval-build-model-judge-pool", help="rerun B0–B4 and export only newly needed blind judgments")
    eval_build_pool.add_argument("--previous-benchmark", type=Path, default=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1" / "dev-v1.json")
    eval_build_pool.add_argument("--output-dir", type=Path, default=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1.1")
    eval_build_pool.add_argument("--prompt", type=Path, default=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "judges" / "gpt-6-luna-v1.md")
    eval_build_pool.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    eval_build_pool.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    eval_build_pool.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    eval_build_pool.add_argument("--revision")
    eval_build_pool.add_argument("--device")
    eval_import_model = commands.add_parser("eval-import-model-judgments", help="validate incremental blind model judgments and merge current-pool qrels")
    eval_import_model.add_argument("--pack", type=Path, default=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1.1" / "dev-v1.1-label-pack.json")
    eval_import_model.add_argument("--judge-input", type=Path, default=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1.1" / "dev-v1-1-judge-input.json")
    eval_import_model.add_argument("--judge-output", type=Path, default=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1.1" / "dev-v1-1-judge-output.json")
    eval_import_model.add_argument("--previous-benchmark", type=Path, default=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1" / "dev-v1.json")
    eval_import_model.add_argument("--output", type=Path, default=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1.1" / "dev-v1.1-qrels.json")
    eval_import_model.add_argument("--judged-at", default=now_utc())
    eval_freeze = commands.add_parser("eval-freeze", help="freeze a complete DEV benchmark with explicit judge provenance")
    eval_freeze.add_argument("--pack", type=Path, default=eval_root / "dev-v1-label-pack.json")
    eval_freeze.add_argument("--qrels", type=Path, default=eval_root / "dev-v1-qrels.json")
    eval_freeze.add_argument("--output", type=Path, default=eval_root / "dev-v1.json")
    eval_freeze.add_argument("--reviewed-by", required=True)
    eval_freeze.add_argument("--reviewed-at", required=True)
    eval_freeze.add_argument("--guideline-version", default="m3-2-v1")
    eval_freeze.add_argument("--judge-type", choices=["human", "model"], default="human")
    eval_freeze.add_argument("--judge-name")
    eval_freeze.add_argument("--judge-model")
    eval_freeze.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    eval_run = commands.add_parser("eval-run", help="run a frozen development benchmark with a B0–B4 coverage gate")
    eval_run.add_argument("--benchmark", type=Path, default=eval_root / "dev-v1.json")
    eval_run.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    eval_run.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    eval_run.add_argument("--output", type=Path, default=eval_root / "dev-v1-evaluation.json")
    eval_run.add_argument("--error-analysis", type=Path, default=REPO_ROOT / "content" / "docs" / "agent" / "search" / "research-intelligence" / "m3-2-1-error-analysis.md")
    eval_run.add_argument("--model", default="Qwen/Qwen3-Embedding-0.6B")
    eval_run.add_argument("--revision")
    eval_run.add_argument("--device")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in _STORE_LOCKED_COMMANDS:
        from .ops.locks import LockContended, store_writer_lock
        try:
            with store_writer_lock(getattr(args, "runtime_dir", DEFAULT_RUNTIME), timeout_seconds=5.0):
                return _dispatch(args)
        except LockContended:
            _print_json({"status": "lock_contended", "message": "another intelligence writer is active"})
            return 2
    return _dispatch(args)


def _dispatch(args: argparse.Namespace) -> int:
    try:
        if args.command.startswith("research-"):
            from .research import ResearchService
            service = ResearchService(args.store_dir, args.runtime_dir, args.private_root, repository_root=REPO_ROOT)
            if args.command == "research-start":
                result = service.start(args.query, artifact_ids=args.artifact,
                                       source_feed_run_id=args.feed_run_id, real_case=args.real_case)
            elif args.command == "research-evidence":
                paper_files = {}
                for item in args.paper_file:
                    artifact_id_value, separator, file_path = item.partition("=")
                    if not separator or not artifact_id_value.strip() or not file_path.strip():
                        raise ValueError("--paper-file must use ARTIFACT_ID=PATH")
                    paper_files[artifact_id_value.strip()] = Path(file_path.strip())
                result = service.collect_evidence(args.session_id, paper_files=paper_files or None)
            elif args.command in {"research-generate", "research-synthesize"}:
                result = service.generate(args.session_id)
            elif args.command == "research-show":
                session = service.get_session(args.session_id)
                try:
                    brief = service.get_brief(args.session_id)
                except ValueError:
                    brief = None
                evidence_count = 0
                if session.get("evidence_path"):
                    evidence_count = len(service.load_evidence(session))
                review_surface = None
                if brief is not None:
                    review_surface = service.review_surface(args.session_id)
                result = {"session": session, "evidence_count": evidence_count, "latest_brief": brief,
                          "review_surface": review_surface}
            elif args.command == "research-review":
                result = service.review(args.session_id, reviewer=args.reviewer)
            elif args.command == "research-approve":
                result = service.approve(args.session_id, approver=args.approver)
            elif args.command == "research-promotion-preview":
                result = service.promotion_preview(args.session_id, target=args.target,
                                                   title=args.title, topics=args.topic)
            else:
                result = service.promote(args.session_id, target=args.target)
            _print_json(result)
            return 0 if result.get("status") not in {"synthesis_unavailable", "preview_blocked",
                                                       "evidence_blocked"} else 1
        store = JsonlStore(getattr(args, "store_dir", DEFAULT_STORE))
        if args.command == "feed-profile":
            from .feed.models import profile_hash
            from .feed.environment import feed_private_dir
            from .feed.service import mutate_profile
            from .feed.storage import FeedRepository
            private_dir = args.private_dir or feed_private_dir(args.mode, private_root=DEFAULT_PRIVATE_ROOT)
            repository = FeedRepository(private_dir)
            changes_requested = any(getattr(args, name) for name in (
                "add_topic", "remove_topic", "follow_source", "unfollow_source",
                "block_topic", "unblock_topic", "block_source", "unblock_source"))
            if changes_requested:
                source_ids = {str(item["source_id"]) for item in load_merged_source_catalog()}
                source_ids.update(str(row["source_id"]) for row in store.iter_records("source"))
                requested = set(args.follow_source + args.unfollow_source + args.block_source + args.unblock_source)
                unknown = requested - source_ids
                if unknown:
                    raise ValueError(f"unknown source id(s): {sorted(unknown)}")
                profile = mutate_profile(repository, add={
                    "selected_topic_ids": _topic_ids(args.add_topic), "followed_source_ids": args.follow_source,
                    "blocked_topic_ids": _topic_ids(args.block_topic), "blocked_source_ids": args.block_source,
                }, remove={
                    "selected_topic_ids": _topic_ids(args.remove_topic), "followed_source_ids": args.unfollow_source,
                    "blocked_topic_ids": _topic_ids(args.unblock_topic), "blocked_source_ids": args.unblock_source,
                })
            else:
                profile = repository.load_profile()
            _print_json({"profile": profile, "profile_hash": profile_hash(profile)})
            return 0
        if args.command == "feed-daily":
            from datetime import date as _date
            from .feed.environment import feed_private_dir
            from .feed.service import daily_feed
            private_dir = args.private_dir or feed_private_dir(args.mode, private_root=DEFAULT_PRIVATE_ROOT)
            run = daily_feed(args.store_dir, args.runtime_dir, private_dir,
                             date=args.date or _date.today().isoformat(), refresh=args.refresh,
                             lookback_days=args.lookback_days, model=args.model,
                             revision=args.revision, device=args.device,
                             experimental_graph=args.experimental_graph,
                             dense_enabled=not args.no_dense, lock_timeout_seconds=5.0)
            _print_json({"status": "ready", "feed_run_id": run["feed_run_id"],
                         "feed_date": run["feed_date"], "revision": run["revision"],
                         "supersedes_feed_run_id": run["supersedes_feed_run_id"],
                         "corpus_hash": run["corpus_hash"], "profile_hash": run["profile_hash"],
                         "candidate_count": run["candidate_count"], "selected_count": len(run["items"]),
                         "metrics": run["metrics"], "retrieval_routes": run["retrieval_routes"]})
            return 0
        if args.command == "feed-feedback":
            from .feed.environment import feed_private_dir
            from .feed.service import apply_feedback
            from .feed.storage import FeedRepository
            private_dir = args.private_dir or feed_private_dir(args.mode, private_root=DEFAULT_PRIVATE_ROOT)
            result = apply_feedback(FeedRepository(private_dir), store,
                                    feed_run_id=args.feed_run_id, artifact_id=args.artifact_id,
                                    action=args.action, target_id=args.target_id,
                                    reason_code=args.reason_code,
                                    supersedes_feedback_id=args.supersedes_feedback_id)
            _print_json(result)
            return 0
        if args.command in {"feedback-stats", "feed-stats"}:
            from .feed.environment import feed_private_dir
            from .feed.service import feedback_stats
            from .feed.storage import FeedRepository
            private_dir = args.private_dir or feed_private_dir(args.mode, private_root=DEFAULT_PRIVATE_ROOT)
            _print_json(feedback_stats(store, FeedRepository(private_dir)))
            return 0
        if args.command == "feed-archive-smoke":
            from .feed.migration import archive_m4_smoke_state
            from .ops.locks import feed_writer_lock
            with feed_writer_lock(args.private_root / "feed", timeout_seconds=5.0):
                report = archive_m4_smoke_state(args.private_root, args.runtime_dir)
            _print_json(report)
            return 0
        if args.command == "intelligence-daily":
            from .ops.daily import run_daily_pipeline
            result = run_daily_pipeline(
                store_dir=args.store_dir, runtime_dir=args.runtime_dir,
                private_root=args.private_root, run_date=args.date, mode=args.mode,
                attempt=args.attempt, dense=args.dense, device=args.device,
                enrich_limit=args.enrich_limit, enrich_provider=args.enrich_provider, force=args.force,
                scheduled=args.scheduled,
            )
            _print_json(result)
            exit_code = int(result["exit_code"])
            return 0 if args.scheduled and exit_code == 2 else exit_code
        if args.command == "ops-status":
            from .ops.health import ops_status
            _print_json(ops_status(store_dir=args.store_dir, runtime_dir=args.runtime_dir,
                                   mode=args.mode))
            return 0
        if args.command == "audit-hf-identities":
            from .hf_identity import audit_huggingface_reserved_namespace_models
            result = audit_huggingface_reserved_namespace_models(store)
            _print_json(result)
            return 0 if result["passed"] else 1
        if args.command == "repair-hf-identities":
            from .rss_migration import repair_huggingface_blog_identities
            result = repair_huggingface_blog_identities(store)
            _print_json(result)
            return 0 if result["audit"]["passed"] else 1
        if args.command == "rematerialize-primary-artifacts":
            from .rss_migration import rematerialize_primary_artifacts
            result = rematerialize_primary_artifacts(store)
            _write_json(DEFAULT_RUNTIME / "retrieval" / "m3-1-rss-rematerialization.json", result)
            _print_json(result)
            return 0
        if args.command == "enrich-hf-metadata":
            from .providers.huggingface_metadata import HuggingFaceMetadataProvider, enrich_huggingface_metadata
            pack_path = REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "dev-v1-label-pack.json"
            pool = set()
            if pack_path.exists():
                pack = json.loads(pack_path.read_text(encoding="utf-8"))
                pool = {str(row.get("artifact_id")) for query in pack.get("queries", [])
                        for row in query.get("candidates", []) if row.get("artifact_id")}
            provider = HuggingFaceMetadataProvider(args.runtime_dir / "huggingface-metadata")
            result = enrich_huggingface_metadata(store, provider, limit=args.limit, benchmark_pool=pool)
            _write_json(args.runtime_dir / "retrieval" / "m3-1-hf-enrichment.json", result)
            _print_json(result)
            return 0
        if args.command == "retrieval-label-pack":
            from .retrieval.evaluation import build_blind_label_pack
            result = build_blind_label_pack(
                args.store_dir, args.runtime_dir, queries_path=args.queries, output_dir=args.output_dir,
                model=args.model, revision=args.revision, device=args.device,
            )
            _print_json(result)
            return 0
        if args.command == "artifact-stats":
            _print_json(_artifact_stats(store))
            return 0
        if args.command == "eval-export-json":
            from .evaluation.annotation.json_fallback import JsonFallbackAdapter
            pack = _read_json_object(args.pack)
            result = JsonFallbackAdapter().export(
                pack, args.output, display_fallbacks=_annotation_display_fallbacks(pack, store))
            _print_json(result)
            return 0
        if args.command == "eval-export-argilla":
            from .evaluation.annotation.argilla import ArgillaAdapter
            pack = _read_json_object(args.pack)
            fallbacks = _annotation_display_fallbacks(pack, store)
            _print_json(ArgillaAdapter().export(pack, fallbacks))
            return 0
        if args.command == "eval-import-json":
            from .evaluation.annotation.json_fallback import JsonFallbackAdapter
            pack = _read_json_object(args.pack)
            _print_json(JsonFallbackAdapter().import_labels(
                pack, args.input, args.qrels, reviewed_by=args.reviewed_by, reviewed_at=args.reviewed_at,
                judge_type=args.judge_type, judge_name=args.judge_name, judge_model=args.judge_model))
            return 0
        if args.command == "eval-import-argilla":
            from .evaluation.annotation.argilla import ArgillaAdapter
            pack = _read_json_object(args.pack)
            _print_json(ArgillaAdapter().import_labels(
                pack, args.dataset, args.qrels, reviewed_by=args.reviewed_by, reviewed_at=args.reviewed_at,
                judge_type=args.judge_type, judge_name=args.judge_name, judge_model=args.judge_model))
            return 0
        if args.command == "eval-build-model-judge-pool":
            from .evaluation.pool_builder import build_model_judge_pool
            _print_json(build_model_judge_pool(
                previous_benchmark_path=args.previous_benchmark, store=store,
                runtime_dir=args.runtime_dir, output_dir=args.output_dir,
                prompt_path=args.prompt, model=args.model, revision=args.revision,
                device=args.device))
            return 0
        if args.command == "eval-import-model-judgments":
            from .evaluation.model_judging import assemble_model_qrels, prompt_hash
            pack = _read_json_object(args.pack)
            judge_input = _read_json_object(args.judge_input)
            judge_output = _read_json_object(args.judge_output)
            previous = _read_json_object(args.previous_benchmark)
            prompt_path = REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "judges" / "gpt-6-luna-v1.md"
            if prompt_hash(prompt_path.read_bytes()) != judge_input.get("prompt_hash"):
                raise ValueError("frozen grading prompt hash does not match the judge input")
            qrels = assemble_model_qrels(current_pack=pack, judge_input=judge_input,
                                         judge_output=judge_output, previous_benchmark=previous,
                                         judged_at=args.judged_at)
            _write_json(args.output, qrels)
            _print_json({"status": "validated", "judgments": len(qrels["qrels"]),
                         "new_pairs_judged": qrels["provenance"]["new_pairs_judged"],
                         "qrels_hash": qrels["qrels_hash"], "path": str(args.output)})
            return 0
        if args.command == "eval-freeze":
            _print_json(_freeze_dev_qrels(args.pack, args.qrels, args.output,
                                          reviewed_by=args.reviewed_by, reviewed_at=args.reviewed_at,
                                          guideline_version=args.guideline_version, store_dir=args.store_dir,
                                          judge_type=args.judge_type, judge_name=args.judge_name,
                                          judge_model=args.judge_model))
            return 0
        if args.command == "eval-run":
            from .evaluation.m32_evaluation import run_frozen_dev, write_error_analysis
            benchmark = _read_json_object(args.benchmark)
            result = run_frozen_dev(benchmark, store, args.runtime_dir, model=args.model,
                                    revision=args.revision, device=args.device)
            write_error_analysis(result, benchmark, args.error_analysis)
            public = {key: value for key, value in result.items()
                      if key not in {"rankings", "topic_rankings"}}
            _write_json(args.output, public)
            _print_json({"status": result["status"], "benchmark_hash": result["benchmark_hash"],
                         "corpus_hash": result["corpus_hash"], "judged_pairs": result["judged_pairs"],
                         "comparison_eligibility": result["comparison_eligibility"],
                         "warnings": result["warnings"],
                         "output": str(args.output), "error_analysis": str(args.error_analysis)})
            return 0
        if args.command in {"retrieval-build", "retrieval-manifest", "retrieval-status",
                            "retrieval-warm-dense", "retrieval-smoke", "search", "explain-retrieval"}:
            if args.command == "explain-retrieval":
                run_path = args.runtime_dir / "retrieval" / "runs" / f"{args.request_id}.json"
                run_result = read_run(run_path)
                _print_json(explain_candidate(run_result, args.artifact_id))
                return 0
            snapshot = build_snapshot(store)
            if args.command == "retrieval-status":
                _print_json(dense_freshness(snapshot, args.runtime_dir))
                return 0
            if args.command == "retrieval-warm-dense":
                dense = DenseRetriever(SentenceTransformerBackend(
                    args.model, revision=args.revision, device=args.device,
                ))
                manifest = dense.build(snapshot, str(args.runtime_dir / "retrieval"))
                _print_json({key: value for key, value in manifest.items()
                             if key not in {"document_hashes", "document_order_hash"}})
                return 0
            if args.command == "retrieval-smoke":
                from .retrieval.live_smoke import run_live_smoke
                from .retrieval.m31_report import write_m31_report
                smoke_result = run_live_smoke(
                    args.store_dir, args.runtime_dir, model=args.model,
                    revision=args.revision, device=args.device,
                )
                after_snapshot = build_snapshot(store)
                migration_path = args.runtime_dir / "retrieval" / "m3-1-rss-rematerialization.json"
                hf_path = args.runtime_dir / "retrieval" / "m3-1-hf-enrichment.json"
                migration = json.loads(migration_path.read_text(encoding="utf-8")) if migration_path.exists() else {"status": "not-run"}
                hf_enrichment = json.loads(hf_path.read_text(encoding="utf-8")) if hf_path.exists() else {"status": "not-run"}
                live_source_path = args.runtime_dir / "retrieval" / "m3-1-live-source-smoke.json"
                live_source_smoke = json.loads(live_source_path.read_text(encoding="utf-8")) if live_source_path.exists() else {}
                report_path = REPO_ROOT / "content" / "docs" / "agent" / "search" / "research-intelligence" / "m3-1-retrieval-quality-report.md"
                report = write_m31_report(
                    store=store, snapshot=after_snapshot, smoke=smoke_result,
                    before_path=REPO_ROOT / "data" / "intelligence" / "eval" / "retrieval" / "m3-live-before.json",
                    migration=migration, hf_enrichment=hf_enrichment,
                    live_source_smoke=live_source_smoke, report_path=report_path,
                )
                _print_json({"corpus_hash": smoke_result["corpus_hash"],
                             "queries": [{"category": item["smoke_category"], "request_id": item["request"]["request_id"]}
                                         for item in smoke_result["queries"]],
                             "hardware": smoke_result["hardware"], "dense": smoke_result["dense"],
                             "report_path": str(report_path),
                             "runtime_smoke_path": str(args.runtime_dir / "retrieval" / "live-smoke-20260928.json")})
                return 0
            if args.command == "retrieval-manifest":
                manifests = {}
                for route in ("bm25", "dense"):
                    manifest_path = args.runtime_dir / "retrieval" / route / "manifest.json"
                    if manifest_path.exists():
                        value = json.loads(manifest_path.read_text(encoding="utf-8"))
                        manifests[route] = {key: item for key, item in value.items()
                                            if key not in {"document_hashes", "document_order_hash", "index_file_hashes"}}
                _print_json({"corpus": make_manifest(snapshot, retriever_versions={"normalization": snapshot.normalization_version}),
                             "indexes": manifests})
                return 0
            registry = _retriever_registry(store, args.store_dir, args.runtime_dir, dense=False)
            if args.command == "retrieval-build":
                selected_routes = list(args.routes) if args.routes else None
                if args.dense or (selected_routes and "dense" in selected_routes):
                    registry.register(DenseRetriever(SentenceTransformerBackend(
                        args.model, revision=args.revision, device=args.device,
                    )))
                engine = RetrievalEngine(snapshot, registry, store_dir=str(args.store_dir), runtime_dir=str(args.runtime_dir))
                result = engine.build(routes=selected_routes)
                result = {"corpus_hash": result["corpus_hash"],
                          "corpus": _corpus_counts(store, snapshot),
                          "indexes": {route: {key: value for key, value in manifest.items()
                                              if key not in {"document_hashes", "index_file_hashes"}}
                                      for route, manifest in result["routes"].items()},
                          "failed_routes": result["failed_routes"]}
                _write_json(args.runtime_dir / "retrieval" / "corpus_manifest.json",
                            make_manifest(snapshot, retriever_versions=registry.versions()))
                _print_json(result)
                return 1 if result.get("failed_routes") else 0
            if args.command == "search":
                if args.top_k < 1 or args.top_k > 500:
                    raise ValueError("--top-k must be between 1 and 500")
                topic_map = _topic_ids(args.topic)
                topic_ids = sorted(set(topic_map).union(infer_topic_ids(args.query)))
                expanded = expand_query(args.query, entity_names=[
                    str(item.get("name") or "") for item in store.iter_records("entity")
                ])
                request = make_request(
                    args.query, seed_artifact_ids=args.seed_artifact,
                    negative_seed_artifact_ids=args.negative_seed_artifact, topic_ids=topic_ids,
                    source_ids=args.source, as_of=args.as_of,
                filters={"artifact_types": args.artifact_type, "published_after": None,
                             "published_before": None, "languages": args.language,
                             "corpus_profile": args.corpus_profile},
                    top_k=args.top_k, expanded_terms=expanded,
                )
                if not args.no_dense:
                    registry.register(DenseRetriever(SentenceTransformerBackend(
                        args.model, revision=args.revision, device=args.device,
                    )))
                engine = RetrievalEngine(snapshot, registry, store_dir=str(args.store_dir), runtime_dir=str(args.runtime_dir))
                selected_routes = [item.strip() for item in args.routes.split(",") if item.strip()] if args.routes else None
                if args.graph_expand:
                    selected_routes = list(selected_routes or engine.eligible_routes(request))
                    if "graph-expand" not in selected_routes:
                        selected_routes.append("graph-expand")
                result = engine.search(request, routes=selected_routes, route_depth=args.route_depth)
                result["corpus"] = _corpus_counts(store, snapshot)
                result["items"] = [
                    {"artifact_id": item["artifact_id"], "title": (snapshot.by_id().get(item["artifact_id"]).title if snapshot.by_id().get(item["artifact_id"]) else ""),
                     "artifact_type": (snapshot.by_id().get(item["artifact_id"]).artifact_type if snapshot.by_id().get(item["artifact_id"]) else ""),
                     "score": item["fusion"]["score"], "routes": [route["route"] for route in item["routes"]]}
                    for item in result["candidates"]
                ]
                _print_json(result)
                return 0
        if args.command in {"ingest-xhs", "ingest-capture"}:
            payload = _read_json_object(args.json_file)
            if args.command == "ingest-xhs":
                source, observation, artifact_ids = ingest_xhs(payload, store)
                _print_json(
                    {
                        "source_id": source["source_id"],
                        "observation_id": observation["observation_id"],
                        "artifact_ids": artifact_ids,
                    }
                )
            else:
                source, observation = ingest_capture(payload, store)
                _print_json(
                    {"source_id": source["source_id"], "observation_id": observation["observation_id"]}
                )
            return 0
        if args.command == "inspect-artifact":
            artifact = ArtifactRepository(store).get(args.artifact_id)
            if artifact is None:
                raise ValueError(f"artifact not found: {args.artifact_id}")
            _print_json(artifact)
            return 0
        if args.command == "stats":
            stats_payload = store.stats()
            stats_payload["artifact"] = sum(1 for _ in ArtifactRepository(store).iter_canonical())
            _print_json(stats_payload)
            return 0
        if args.command == "connectors":
            _print_json([
                {
                    "connector_id": spec.connector_id,
                    "version": spec.version,
                    "modes": list(spec.modes),
                    "capabilities": sorted(spec.capabilities),
                    "requires_auth": spec.requires_auth,
                    "supports_incremental": spec.supports_incremental,
                }
                for spec in connector_registry().list()
            ])
            return 0
        if args.command == "sources":
            _print_json([
                {"source_id": source["source_id"], "name": source["name"],
                 "connector": source["acquisition"]["connector"], "status": source["status"],
                 "acquisition_mode": (source.get("operations") or {}).get("acquisition_mode", "scheduled")}
                for source in load_merged_source_catalog()
            ])
            return 0
        if args.command == "source-records":
            _print_json([
                {"source_id": source["source_id"], "name": source["name"], "platform": source["platform"],
                 "status": source["status"], "canonical_url": source["canonical_url"]}
                for source in store.iter_records("source")
            ])
            return 0
        if args.command in {"run-source", "run-all"}:
            sources = load_merged_source_catalog()
            if args.command == "run-source":
                source = next((item for item in sources if item["source_id"] == args.source_id), None)
                if source is None:
                    raise ValueError(f"source not found in catalog: {args.source_id}")
                if (source.get("operations") or {}).get("acquisition_mode") == "interactive":
                    raise ValueError("interactive source; use social-sync --source <source_id>")
                selected = [source]
            else:
                selected = [item for item in sources if item["status"] == "active"]
            states = ConnectorStateStore(args.runtime_dir)
            registry = connector_registry()
            if args.command == "run-source":
                result = run_source(selected[0], registry, states, store, ConnectorContext(store=store))
                _print_json({"status": "succeeded", **result})
                return 0
            summary = run_all_sources(selected, registry, states, store, ConnectorContext(store=store))
            _print_json(summary)
            return 1 if summary["failed"] else 0
        if args.command == "social-add-url":
            from .social.runner import add_social_url
            if args.source_id:
                source_ids = {str(row["source_id"]) for row in load_merged_source_catalog()}
                source_ids.update(str(row["source_id"]) for row in store.iter_records("source"))
                if args.source_id not in source_ids:
                    raise ValueError("social inbox source_id is not known locally")
            _print_json(add_social_url(args.url, private_root=args.private_root, source_id=args.source_id))
            return 0
        if args.command == "social-inbox":
            from .social.runner import DEFAULT_INBOX
            from .social.storage import SocialInbox
            root = args.private_root or DEFAULT_INBOX
            _print_json([row for row in SocialInbox(root).list() if row["status"] == "pending"])
            return 0
        if args.command == "social-sync":
            from .social.runner import sync_source
            source = next((row for row in load_merged_source_catalog()
                           if row["source_id"] == args.source and row["status"] == "active"), None)
            if source is None:
                raise ValueError("interactive source was not found or is not active")
            result = sync_source(source, store, args.runtime_dir, limit=args.limit,
                                 postprocess=args.postprocess, enrich_images=args.enrich_images)
            _print_json(result)
            return 0 if result["status"] in {"completed", "content_readable", "rss_proposal_pending_approval"} else 1
        if args.command == "social-sync-inbox":
            from .social.runner import sync_inbox
            result = sync_inbox(store, args.runtime_dir, args.private_root, limit=args.limit,
                                postprocess=args.postprocess, enrich_images=args.enrich_images)
            _print_json(result)
            return 0 if result["failed"] == 0 else 1
        if args.command == "social-propose-zhihu-rss":
            from .discovery.source_proposals import SourceProposalStore
            from .social.runner import propose_zhihu_rsshub
            result = propose_zhihu_rsshub(args.profile_url,
                                          proposals=SourceProposalStore(args.store) if args.store else None)
            _print_json(result)
            return 0 if result["status"] in {"valid", "unavailable", "deferred"} else 1
        if args.command == "source-proposals":
            from .discovery.source_proposals import PROPOSAL_PATH, SourceProposalStore
            rows = SourceProposalStore(args.store or PROPOSAL_PATH).list(status=args.status)
            _print_json(rows)
            return 0
        if args.command == "discover-rss-sources":
            from .discovery.source_proposals import PROPOSAL_PATH, SourceProposalStore, discover_rss_proposals
            proposals = SourceProposalStore(PROPOSAL_PATH)
            candidates = SourceCandidateStore(args.store_dir).iter_candidates()
            discovered = discover_rss_proposals(candidates, store.iter_records("entity"), proposals,
                                                max_candidates=args.limit)
            _print_json({"discovered": len(discovered), "proposals": discovered})
            return 0
        if args.command == "approve-source-proposal":
            from .discovery.source_proposals import (PROPOSAL_PATH, SUBSCRIPTION_PATH,
                                                      SourceProposalStore, SourceSubscriptionRegistry,
                                                      source_from_proposal)
            proposals = SourceProposalStore(args.store or PROPOSAL_PATH)
            proposal = next((row for row in proposals.list() if row["proposal_id"] == args.proposal_id), None)
            if proposal is None:
                raise ValueError("source proposal not found")
            source = source_from_proposal(proposal)
            subscriptions = SourceSubscriptionRegistry(SUBSCRIPTION_PATH)
            subscriptions.add(source)
            proposals.review(args.proposal_id, "approved")
            _print_json({"status": "approved", "source_id": source["source_id"], "name": source["name"]})
            return 0
        if args.command in {"reject-source-proposal", "defer-source-proposal"}:
            from .discovery.source_proposals import PROPOSAL_PATH, SourceProposalStore
            status = "rejected" if args.command == "reject-source-proposal" else "deferred"
            reason = args.reason_code if args.command == "reject-source-proposal" else None
            row = SourceProposalStore(args.store or PROPOSAL_PATH).review(
                args.proposal_id, status, reason_code=reason)
            _print_json(row)
            return 0
        if args.command == "probe-openreview-source":
            from .connectors.openreview_submissions import OpenReviewSubmissionsConnector
            from dataclasses import asdict
            result = OpenReviewSubmissionsConnector().probe(api_version=args.api_version,
                                                           invitation=args.invitation,
                                                           decision_invitation=args.decision_invitation)
            _print_json(asdict(result))
            return 0 if result.status == "valid" else 1
        if args.command == "probe-source":
            from dataclasses import asdict
            from .discovery.source_proposals import probe_rss_endpoint
            from .connectors.openreview_submissions import OpenReviewSubmissionsConnector
            if args.provider == "rss":
                if not args.url:
                    raise ValueError("RSS probe requires --url")
                result = probe_rss_endpoint(args.url)
            elif args.provider == "openreview":
                if not args.invitation or args.api_version not in {1, 2}:
                    raise ValueError("OpenReview probe requires --api-version and --invitation")
                result = OpenReviewSubmissionsConnector().probe(api_version=args.api_version,
                                                               invitation=args.invitation,
                                                               decision_invitation=None)
            elif args.provider == "huggingface-daily":
                from .connectors.huggingface_daily import probe_huggingface_daily
                result = probe_huggingface_daily()
            else:
                if not args.query:
                    raise ValueError("OpenAlex probe requires --query exact-ID JSON")
                query = json.loads(args.query)
                from .connectors.openalex_works import probe_openalex_query
                result = probe_openalex_query(query)
            _print_json(asdict(result))
            return 0 if result.status == "valid" else 1
        if args.command == "propose-openalex-topics":
            from .discovery.openalex_topics import TOPIC_PROPOSALS_PATH, OpenAlexTopicProposalStore
            rows = OpenAlexTopicProposalStore(args.store or TOPIC_PROPOSALS_PATH).propose(args.internal_topic_id)
            _print_json({"status": "pending_human_review", "internal_topic_id": args.internal_topic_id,
                         "candidates": rows})
            return 0
        if args.command == "openalex-topic-proposals":
            from .discovery.openalex_topics import TOPIC_PROPOSALS_PATH, OpenAlexTopicProposalStore
            _print_json(OpenAlexTopicProposalStore(args.store or TOPIC_PROPOSALS_PATH).list(status=args.status))
            return 0
        if args.command == "approve-openalex-topic":
            from .discovery.openalex_topics import TOPIC_PROPOSALS_PATH, OpenAlexTopicProposalStore
            row = OpenAlexTopicProposalStore(args.store or TOPIC_PROPOSALS_PATH).approve(
                args.proposal_id, reviewed_by=args.reviewed_by)
            _print_json({"status": row["status"], "internal_topic_id": row["internal_topic_id"],
                         "openalex_topic_id": row["openalex_topic_id"], "reviewed_by": row["reviewed_by"]})
            return 0
        if args.command == "reject-openalex-topic":
            from .discovery.openalex_topics import TOPIC_PROPOSALS_PATH, OpenAlexTopicProposalStore
            _print_json(OpenAlexTopicProposalStore(args.store or TOPIC_PROPOSALS_PATH).reject(args.proposal_id))
            return 0
        if args.command == "source-coverage":
            from .coverage import source_coverage
            _print_json(source_coverage(store, args.runtime_dir, load_merged_source_catalog(), days=args.days))
            return 0
        if args.command == "connector-state":
            state = ConnectorStateStore(args.runtime_dir).load(args.source_id)
            if state is None:
                raise ValueError(f"connector state not found: {args.source_id}")
            from dataclasses import asdict
            _print_json(asdict(state))
            return 0
        if args.command == "smoke":
            from .canonicalize import extract_arxiv_id
            arxiv = extract_arxiv_id(args.arxiv)
            if not arxiv:
                raise ValueError("smoke requires a valid arXiv identifier")
            with tempfile.TemporaryDirectory(prefix="ri-s2-smoke-") as temp:
                result = SemanticScholarResolver().resolve(
                    {"identifiers": {"arxiv": arxiv}, "title": ""},
                    artifact_id(f"arxiv:{arxiv}"), ArtifactAliases(temp), ConnectorContext(store=store),
                )
            _print_json(result)
            return 0
        if args.command == "resolve-artifact":
            aliases = ArtifactAliases(args.store_dir)
            canonical_id = ArtifactRepository(store).resolve_id(args.artifact_id)
            artifact = ArtifactRepository(store).get(canonical_id)
            if artifact is None:
                raise ValueError(f"artifact not found: {args.artifact_id}")
            result = SemanticScholarResolver().resolve(
                artifact, str(artifact["artifact_id"]), aliases, ConnectorContext(store=store),
            )
            resolved_artifact = materialize_semantic_scholar_result(result, artifact, store)
            if resolved_artifact:
                result["materialized_artifact"] = resolved_artifact
            _print_json(result)
            return 0
        if args.command == "graph-backfill":
            result = graph_backfill(store, args.runtime_dir, now=now_utc())
            _print_json(result)
            return 0
        if args.command == "graph-rebuild":
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            result = graph.rebuild_indexes(args.runtime_dir, entity_id_resolver=EntityAliases(args.store_dir))
            _print_json(result)
            return 0
        if args.command == "graph-neighbors":
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            aliases = EntityAliases(args.store_dir)
            _print_json({
                "node_id": args.node_id,
                "predicate": args.predicate,
                "edges": graph.neighbors(args.node_id, predicate=args.predicate, entity_id_resolver=aliases),
            })
            return 0
        if args.command == "graph-path":
            if args.max_depth < 1 or args.max_depth > 10:
                raise ValueError("graph path max-depth must be between 1 and 10")
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            result = _find_graph_path(
                args.from_id, args.to_id, graph, EntityAliases(args.store_dir), args.max_depth,
            )
            _print_json(result)
            return 0 if result["found"] else 1
        if args.command == "graph-stats":
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            edges = graph.iter_edges()
            _print_json({
                "nodes": {
                    "sources": len(list(store.iter_records("source"))),
                    "observations": len(list(store.iter_records("observation"))),
                    "artifacts": sum(1 for _ in ArtifactRepository(store).iter_canonical()),
                    "entities": len(list(store.iter_records("entity"))),
                    "topics": len(set(
                        endpoint for edge in edges for endpoint in (edge["subject_id"], edge["object_id"])
                        if endpoint.startswith("topic-")
                    )),
                },
                "edges": len(edges),
                "predicates": _count_by(edges, "predicate"),
                "providers": _count_edge_providers(edges),
                "source_candidates": len(SourceCandidateStore(args.store_dir).iter_candidates()),
            })
            return 0
        if args.command == "graph-enrich":
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            budget = _make_budget(
                args.max_provider_requests,
                max_references=args.max_references,
                max_citations=args.max_citations,
            )
            result = enrich_artifact(
                args.artifact, args.provider, store, graph, EntityAliases(args.store_dir),
                args.runtime_dir, budget=budget,
                context=ConnectorContext(store=store, http=SharedHttpClient(), now=now_utc),
            )
            validate_graph_nodes(store, graph)
            graph.rebuild_indexes(args.runtime_dir, entity_id_resolver=EntityAliases(args.store_dir))
            _print_json(result)
            return 1 if result.get("status") == "partial" else 0
        if args.command == "graph-enrich-author":
            if args.limit < 1 or args.limit > 10:
                raise ValueError("author recent-works limit must be between 1 and 10")
            budget = _make_budget(args.max_provider_requests, recent_works=args.limit)
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            result = enrich_entity(
                args.entity, args.provider, store, graph, EntityAliases(args.store_dir),
                args.runtime_dir, budget=budget,
                context=ConnectorContext(store=store, http=SharedHttpClient(), now=now_utc),
            )
            validate_graph_nodes(store, graph)
            graph.rebuild_indexes(args.runtime_dir, entity_id_resolver=EntityAliases(args.store_dir))
            _print_json(result)
            return 1 if result.get("status") == "partial" else 0
        if args.command == "graph-enrich-pending":
            if args.limit < 1 or args.limit > 20:
                raise ValueError("graph-enrich-pending limit must be between 1 and 20")
            budget = _make_budget(
                args.max_provider_requests,
                max_references=args.max_references,
                max_citations=args.max_citations,
            )
            artifacts = _pending_artifacts(store, args.provider)[:args.limit]
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            results = []
            for artifact in artifacts:
                if budget.provider_requests >= budget.max_provider_requests:
                    budget.exhausted = True
                    break
                results.append(enrich_artifact(
                    str(artifact["artifact_id"]), args.provider, store, graph,
                    EntityAliases(args.store_dir), args.runtime_dir, budget=budget,
                    context=ConnectorContext(store=store, http=SharedHttpClient(), now=now_utc),
                ))
            validate_graph_nodes(store, graph)
            graph.rebuild_indexes(args.runtime_dir, entity_id_resolver=EntityAliases(args.store_dir))
            _print_json({
                "provider": args.provider,
                "limit": args.limit,
                "items_selected": len(artifacts),
                "provider_requests": budget.provider_requests,
                "budget_exhausted": budget.exhausted,
                "results": results,
            })
            return 1 if any(result.get("status") == "partial" for result in results) else 0
        if args.command == "discover-sources":
            budget = ExpansionBudget(
                max_depth=args.max_depth, max_nodes=args.max_nodes, max_edges=args.max_edges,
                max_candidates=args.max_candidates, max_provider_requests=args.max_provider_requests,
            )
            graph = GraphStore(args.store_dir)
            validate_graph_nodes(store, graph)
            result = SourceDiscovery(
                store, graph, EntityAliases(args.store_dir),
                SourceCandidateStore(args.store_dir), now=now_utc(),
            ).discover(args.seed_source, budget)
            _print_json(result)
            return 0
        if args.command == "source-candidates":
            rows = SourceCandidateStore(args.store_dir).iter_candidates()
            if args.status:
                rows = [row for row in rows if row["status"] == args.status]
            _print_json(rows)
            return 0
        if args.command == "source-candidate":
            row = next((item for item in SourceCandidateStore(args.store_dir).iter_candidates()
                        if item["candidate_id"] == args.candidate_id), None)
            if row is None:
                raise ValueError("source candidate not found")
            _print_json(row)
            return 0
        if args.command == "approve-source-candidate":
            row = SourceCandidateStore(args.store_dir).review(
                args.candidate_id, "approved", reviewed_at=args.reviewed_at,
            )
            _print_json(row)
            return 0
        if args.command == "reject-source-candidate":
            row = SourceCandidateStore(args.store_dir).review(
                args.candidate_id, "rejected", reviewed_at=args.reviewed_at, reason_code=args.reason_code,
            )
            _print_json(row)
            return 0
        if args.command == "reopen-source-candidate":
            row = SourceCandidateStore(args.store_dir).review(
                args.candidate_id, "pending", reviewed_at=args.reviewed_at,
            )
            _print_json(row)
            return 0
        if args.command == "export-source-template":
            row = next((item for item in SourceCandidateStore(args.store_dir).iter_candidates()
                        if item["candidate_id"] == args.candidate_id), None)
            if row is None:
                raise ValueError("source candidate not found")
            _print_yaml(_source_template(row))
            return 0
        raise ValueError(f"unsupported command: {args.command}")
    except Exception as exc:
        from .evaluation.annotation.base import AnnotationImportError
        from .ops.locks import LockContended
        if isinstance(exc, LockContended):
            _print_json({"status": "lock_contended", "message": "another intelligence writer is active"})
            return 2
        if isinstance(exc, AnnotationImportError):
            _print_json({"status": "rejected", **exc.report})
            return 2
        if not isinstance(exc, (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError, RuntimeError)):
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input JSON must be one object")
    return payload


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _print_yaml(value: object) -> None:
    import yaml
    print(yaml.safe_dump(value, allow_unicode=True, sort_keys=False).rstrip())


def _retriever_registry(store: JsonlStore, store_dir: Path, runtime_dir: Path, *, dense: bool) -> RetrieverRegistry:
    from .retrieval.semantic_scholar_recommendations import SemanticScholarRecommendationsRetriever
    registry = RetrieverRegistry()
    registry.register(BM25Retriever())
    registry.register(GraphRetriever(str(store_dir)))
    registry.register(TopicRetriever())
    registry.register(SourceRetriever(str(store_dir)))
    registry.register(SemanticScholarRecommendationsRetriever(store, runtime_dir))
    if dense:
        registry.register(DenseRetriever(SentenceTransformerBackend()))
    return registry


def _topic_ids(values: list[str]) -> list[str]:
    from .topics import topic_aliases
    aliases = topic_aliases()
    result = []
    for value in values:
        if value.startswith("topic-"):
            if value not in set(aliases.values()):
                raise ValueError(f"unknown topic id: {value}")
            result.append(value)
            continue
        key = " ".join("".join(char if char.isalnum() else " " for char in value.casefold()).split())
        topic = aliases.get(key)
        if not topic:
            raise ValueError(f"unknown topic alias: {value}")
        result.append(topic)
    return sorted(set(result))


def _corpus_counts(store: JsonlStore, snapshot: Any) -> dict[str, Any]:
    artifacts = list(ArtifactRepository(store).iter_canonical())
    by_type: dict[str, int] = {}
    for artifact in artifacts:
        artifact_type = str(artifact.get("artifact_type") or "other")
        by_type[artifact_type] = by_type.get(artifact_type, 0) + 1
    missing_published = sum(not artifact.get("published_at") for artifact in artifacts)
    return {
        "artifacts_total": len(artifacts),
        "papers": by_type.get("paper", 0),
        "blogs": by_type.get("blog", 0),
        "repositories": by_type.get("repository", 0),
        "models": by_type.get("model", 0),
        "datasets": by_type.get("dataset", 0),
        "models_and_datasets": by_type.get("model", 0) + by_type.get("dataset", 0),
        "documents_indexed": len(snapshot.documents),
        "documents_skipped_or_canonicalized": max(0, len(artifacts) - len(snapshot.documents)),
        "missing_published_at": missing_published,
        "corpus_hash": snapshot.corpus_hash,
        "quality": dict(snapshot.quality),
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _make_budget(
    max_provider_requests: int,
    *,
    max_references: int = 20,
    max_citations: int = 20,
    recent_works: int = 10,
) -> ExpansionBudget:
    if max_provider_requests < 1 or max_provider_requests > 50:
        raise ValueError("max-provider-requests must be between 1 and 50")
    if max_references < 0 or max_references > 20 or max_citations < 0 or max_citations > 20:
        raise ValueError("reference and citation limits must be between 0 and 20")
    if recent_works < 0 or recent_works > 10:
        raise ValueError("recent-work limit must be between 0 and 10")
    return ExpansionBudget(
        max_provider_requests=max_provider_requests,
        max_references_per_artifact=max_references,
        max_citations_per_artifact=max_citations,
        max_recent_works_per_author=recent_works,
    )


def _pending_artifacts(store: JsonlStore, provider: str) -> list[dict[str, Any]]:
    selected = []
    for artifact in ArtifactRepository(store).iter_canonical():
        identifiers = artifact.get("identifiers") if isinstance(artifact.get("identifiers"), dict) else {}
        if provider == "github":
            eligible = artifact.get("artifact_type") == "repository" and bool(identifiers.get("github"))
        elif provider == "openalex":
            eligible = artifact.get("artifact_type") == "paper" and bool(
                identifiers.get("openalex") or identifiers.get("doi") or identifiers.get("arxiv")
            )
        else:
            eligible = artifact.get("artifact_type") == "paper" and bool(
                identifiers.get("semantic_scholar") or identifiers.get("doi") or identifiers.get("arxiv")
            )
        if eligible and artifact.get("status") == "candidate":
            selected.append(artifact)
    return sorted(selected, key=lambda item: str(item["artifact_id"]))


def _artifact_stats(store: JsonlStore) -> dict[str, Any]:
    repository = ArtifactRepository(store)
    physical = repository.raw_rows()
    redirects = repository.aliases.canonical_redirect_map()
    canonical = list(repository.iter_canonical())
    return {
        "physical_row_count": len(physical),
        "redirected_row_count": sum(str(row.get("artifact_id")) in redirects for row in physical),
        "canonical_count": len(canonical),
        "canonical_by_type": dict(sorted(Counter(str(row.get("artifact_type") or "other")
                                                   for row in canonical).items())),
    }


def _feedback_stats(store: JsonlStore) -> dict[str, Any]:
    rows = list(store.iter_records("feedback"))
    repository = ArtifactRepository(store)
    by_artifact: dict[str, dict[str, Any]] = {}
    actions: Counter[str] = Counter()
    surfaces: Counter[str] = Counter()
    times: list[str] = []
    for row in rows:
        artifact_id = repository.resolve_id(str(row.get("artifact_id") or ""))
        event = str(row.get("event") or "unknown")
        occurred = str(row.get("occurred_at") or "")
        actions[event] += 1
        surface = str((row.get("context") or {}).get("surface") or "unknown")
        surfaces[surface] += 1
        if occurred:
            times.append(occurred)
        item = by_artifact.setdefault(artifact_id, {"feedback_count": 0, "actions": Counter(),
                                                   "first_at": occurred, "last_at": occurred})
        item["feedback_count"] += 1
        item["actions"][event] += 1
        if occurred:
            item["first_at"] = min(filter(None, (item["first_at"], occurred)), default=occurred)
            item["last_at"] = max(item["last_at"], occurred)
    return {
        "total_feedback_events": len(rows),
        "unique_artifacts": len(by_artifact),
        "time_span": {"first_at": min(times) if times else None, "last_at": max(times) if times else None},
        "actions": dict(sorted(actions.items())),
        "surfaces": dict(sorted(surfaces.items())),
        "per_artifact": [
            {"artifact_id": artifact_id, "feedback_count": item["feedback_count"],
             "actions": dict(sorted(item["actions"].items())),
             "first_at": item["first_at"] or None, "last_at": item["last_at"] or None}
            for artifact_id, item in sorted(by_artifact.items())
        ],
    }


def _annotation_display_fallbacks(pack: dict[str, Any], store: JsonlStore) -> dict[str, dict[str, str]]:
    """Supply display-only context for blank HF Blog rows, without touching frozen data."""
    repository = ArtifactRepository(store)
    candidates = {str(candidate["artifact_id"])
                  for query in pack.get("queries", []) for candidate in query.get("candidates", [])}
    artifacts = {str(row["artifact_id"]): row for row in repository.iter_canonical()
                 if str(row.get("canonical_url") or "").casefold().startswith("https://huggingface.co/blog/")}
    needed = {artifact_id for artifact_id in candidates.intersection(artifacts)
              if not str(artifacts[artifact_id].get("summary") or "").strip()
              or not str(artifacts[artifact_id].get("title") or "").strip()}
    if not needed:
        return {}
    sources = {str(row["source_id"]): str(row.get("name") or row.get("canonical_url") or row["source_id"])
               for row in store.iter_records("source")}
    excerpts: dict[str, list[tuple[str, str, str]]] = {artifact_id: [] for artifact_id in needed}
    for observation in store.iter_records("observation"):
        source_name = sources.get(str(observation.get("source_id") or ""), "Hugging Face Blog")
        text = " ".join(str(value or "").strip() for value in
                        (observation.get("title"), observation.get("text")) if str(value or "").strip())
        if not text:
            continue
        text = " ".join(text.split())[:600]
        for candidate in observation.get("artifact_candidates", []):
            if not isinstance(candidate, dict):
                continue
            try:
                from .canonicalize import artifact_identity
                candidate_id = repository.resolve_id(artifact_id_from_candidate(candidate, artifact_identity))
            except (ValueError, TypeError):
                continue
            if candidate_id in needed:
                excerpts[candidate_id].append((str(observation.get("observed_at") or ""), source_name, text))
    result = {}
    for artifact_id in sorted(needed):
        artifact = artifacts[artifact_id]
        rows = sorted(excerpts[artifact_id], reverse=True)
        row = rows[0] if rows else None
        result[artifact_id] = {
            "canonical_url": str(artifact.get("canonical_url") or ""),
            "title": str(artifact.get("title") or (row[2].split(". ", 1)[0] if row else "")),
            "summary_excerpt": (f"Source: {row[1]}. Observation excerpt: {row[2]}" if row else ""),
        }
    return result


def artifact_id_from_candidate(candidate: dict[str, Any], identity_fn) -> str:
    from .ids import artifact_id as make_artifact_id
    return make_artifact_id(identity_fn(candidate))


def _freeze_dev_qrels(pack_path: Path, qrels_path: Path, output_path: Path, *, reviewed_by: str,
                      reviewed_at: str, guideline_version: str, store_dir: Path,
                      judge_type: str = "human", judge_name: str | None = None,
                      judge_model: str | None = None) -> dict[str, Any]:
    pack = _read_json_object(pack_path)
    qrels = _read_json_object(qrels_path)
    if output_path.exists():
        raise ValueError("frozen DEV file already exists; it is immutable")
    benchmark_hash = hashlib.sha256(json.dumps(
        {"benchmark_id": pack.get("benchmark_id"), "queries": pack.get("queries")},
        ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if benchmark_hash != pack.get("benchmark_hash"):
        raise ValueError("label pack benchmark hash is invalid")
    current_corpus_hash = build_snapshot(JsonlStore(store_dir)).corpus_hash
    if current_corpus_hash != pack.get("corpus_hash"):
        raise ValueError("label pack corpus hash does not match the current corpus")
    if len(pack.get("queries", [])) != 20:
        raise ValueError("DEV freeze requires exactly 20 reviewed queries")
    if qrels.get("benchmark_hash") != pack.get("benchmark_hash") or qrels.get("corpus_hash") != pack.get("corpus_hash"):
        raise ValueError("qrels hashes do not match the label pack")
    if judge_type not in {"human", "model"}:
        raise ValueError("judge_type must be human or model")
    fallback_judge = qrels.get("judge") if isinstance(qrels.get("judge"), dict) else {
        "type": judge_type, "name": judge_name or reviewed_by.strip(), "model": judge_model,
    }
    if fallback_judge.get("type") not in {"human", "model"}:
        fallback_judge = {"type": judge_type, "name": judge_name or reviewed_by.strip(), "model": judge_model}
    expected = {(str(query["query_id"]), str(candidate["artifact_id"]))
                for query in pack["queries"] for candidate in query.get("candidates", [])}
    actual: dict[tuple[str, str], int] = {}
    judge_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for item in qrels.get("qrels", []):
        identity = (str(item.get("query_id") or ""), str(item.get("artifact_id") or ""))
        grade = item.get("grade")
        if identity not in expected or identity in actual or isinstance(grade, bool) or grade not in (0, 1, 2):
            raise ValueError("qrels contain invalid, duplicate, or unknown judgments")
        actual[identity] = int(grade)
        item_judge = item.get("judge") if isinstance(item.get("judge"), dict) else fallback_judge
        if item_judge.get("type") not in {"human", "model"}:
            raise ValueError("qrels are missing explicit human or model judge provenance")
        judge_by_pair[identity] = dict(item_judge)
    if actual.keys() != expected:
        raise ValueError(f"DEV freeze blocked: {len(expected - actual.keys())} candidate judgments remain")
    quality_issues: dict[tuple[str, str], str] = {}
    allowed_issues = {"insufficient_metadata", "broken_url", "suspected_duplicate", "identity_problem", "none"}
    for item in qrels.get("quality_issues", []):
        identity = (str(item.get("query_id") or ""), str(item.get("artifact_id") or ""))
        issue = str(item.get("quality_issue") or "")
        if identity not in expected or issue not in allowed_issues:
            raise ValueError("qrels contain an invalid or unknown quality issue")
        if identity in quality_issues and quality_issues[identity] != issue:
            raise ValueError("qrels contain conflicting duplicate quality issues")
        quality_issues[identity] = issue
    if not str(reviewed_by).strip():
        raise ValueError("reviewed_by is required")
    from .evaluation.annotation.base import _timestamp
    normalized_reviewed_at = _timestamp(reviewed_at)
    root_judge = dict(fallback_judge)
    output = {
        "schema": "bubblevan/retrieval-frozen-benchmark/v1", "benchmark_id": str(pack.get("benchmark_id") or "dev-v1"), "status": "frozen",
        "corpus_hash": pack["corpus_hash"], "benchmark_hash": pack["benchmark_hash"],
        "reviewed_by": reviewed_by.strip(), "reviewed_at": normalized_reviewed_at,
        "guideline_version": guideline_version, "judge": root_judge,
        "retrieval_provenance": pack.get("retrieval_provenance"),
        "model_judgment_provenance": qrels.get("provenance"),
        "queries": pack["queries"],
        "qrels": [{"query_id": query_id, "artifact_id": artifact_id, "grade": grade,
                   "judge": judge_by_pair[(query_id, artifact_id)]}
                  for (query_id, artifact_id), grade in sorted(actual.items())],
        "quality_issues": [{"query_id": query_id, "artifact_id": artifact_id, "quality_issue": issue}
                           for (query_id, artifact_id), issue in sorted(quality_issues.items())],
        "qrels_hash": hashlib.sha256(json.dumps(sorted((query, artifact, grade)
                                                       for (query, artifact), grade in actual.items()),
                                                 separators=(",", ":")).encode()).hexdigest(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    output_path.chmod(0o444)
    return {"status": "frozen", "query_count": 20, "judgments": len(actual),
            "corpus_hash": output["corpus_hash"], "benchmark_hash": output["benchmark_hash"],
            "qrels_hash": output["qrels_hash"], "path": str(output_path)}


def _find_graph_path(from_id: str, to_id: str, graph: GraphStore, aliases: EntityAliases, max_depth: int) -> dict[str, Any]:
    from collections import deque

    def canonical(value: str) -> str:
        return aliases.resolve_entity_id(value) if value.startswith("ent-") else value

    start, target = canonical(from_id), canonical(to_id)
    outgoing: dict[str, list[dict[str, Any]]] = {}
    for edge in graph.iter_edges():
        subject, obj = canonical(str(edge["subject_id"])), canonical(str(edge["object_id"]))
        outgoing.setdefault(subject, []).append(dict(edge, _object=obj))
    for values in outgoing.values():
        values.sort(key=lambda item: (item["predicate"], item["_object"], item["edge_id"]))
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        node, path = queue.popleft()
        if node == target:
            return {"found": True, "from_id": from_id, "to_id": to_id, "depth": len(path), "steps": path}
        if len(path) >= max_depth:
            continue
        for edge in outgoing.get(node, []):
            next_node = str(edge["_object"])
            if next_node in visited:
                continue
            step = {
                "edge_id": edge["edge_id"],
                "subject_id": edge["subject_id"],
                "predicate": edge["predicate"],
                "object_id": edge["object_id"],
                "evidence": edge["evidence"],
            }
            visited.add(next_node)
            queue.append((next_node, path + [step]))
    return {"found": False, "from_id": from_id, "to_id": to_id, "max_depth": max_depth, "steps": []}


def _count_by(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for record in records:
        key = str(record.get(field) or "")
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def _count_edge_providers(edges: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for edge in edges:
        for provider in {str(item.get("provider")) for item in edge.get("evidence", []) if item.get("provider")}:
            result[provider] = result.get(provider, 0) + 1
    return dict(sorted(result.items()))


def _source_template(candidate: dict[str, Any]) -> dict[str, Any]:
    source_type = {
        "person": "author",
        "institution": "lab",
        "organization": "community",
        "repository": "repository",
    }[candidate["candidate_type"]]
    return {
        "identity": f"candidate|{candidate['candidate_id']}",
        "source_type": source_type,
        "platform": candidate["platform"],
        "name": candidate["name"],
        "canonical_url": candidate["canonical_url"],
        "external_ids": candidate["external_ids"],
        "topics": candidate["topics"],
        "acquisition": {"connector": "manual", "mode": "manual"},
        "status": "paused",
        "review_note": "Generated suggestion only; review the evidence path and choose a supported connector before activation.",
    }


if __name__ == "__main__":
    raise SystemExit(main())
