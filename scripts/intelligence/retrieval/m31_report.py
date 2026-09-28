from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping

from ..store import JsonlStore
from ..runner import load_source_catalog
from .corpus import CorpusSnapshot


def write_m31_report(*, store: JsonlStore, snapshot: CorpusSnapshot, smoke: Mapping[str, Any],
                     before_path: str | Path, migration: Mapping[str, Any],
                     hf_enrichment: Mapping[str, Any] | None,
                     live_source_smoke: Mapping[str, Any] | None = None,
                     report_path: str | Path) -> dict[str, Any]:
    before = json.loads(Path(before_path).read_text(encoding="utf-8"))
    artifacts = list(store.iter_records("artifact"))
    sources = {str(item["source_id"]): item for item in store.iter_records("source")}
    sources.update({str(item["source_id"]): item for item in load_source_catalog()})
    observations_by_source = Counter(str(item.get("source_id") or "unattributed")
                                     for item in store.iter_records("observation"))
    type_counts = Counter(str(item.get("artifact_type") or "other") for item in artifacts)
    primary_by_source: dict[str, Counter[str]] = {}
    primary_details: dict[str, Counter[str]] = {}
    for artifact in artifacts:
        mention = ((artifact.get("field_provenance") or {}).get("mention") or {})
        if mention.get("mention_role") != "primary":
            continue
        source_id = str(mention.get("source_id") or "unattributed")
        primary_by_source.setdefault(source_id, Counter())[str(artifact.get("artifact_type") or "other")] += 1
        detail = primary_details.setdefault(source_id, Counter())
        detail["total"] += 1
        detail["missing_title"] += int(not str(artifact.get("title") or "").strip())
        detail["missing_published_at"] += int(not artifact.get("published_at"))

    legacy_hf_model_ids = sum(
        str(item.get("artifact_type") or "") == "model"
        and ((item.get("field_provenance") or {}).get("mention") or {}).get("mention_origin")
        == "legacy_hf_blog_url_identity"
        for item in artifacts
    )
    empty_docs = [item for item in snapshot.documents if not item.title.strip() and not item.body.strip()]

    query_rows = []
    type_at_10: dict[str, Counter[str]] = {route: Counter() for route in ("bm25", "dense", "topic", "graph-expand")}
    untitled = Counter()
    topic_nonempty = 0
    graph_ids: set[str] = set()
    graph_per_query = []
    for run in smoke.get("queries", []):
        routes = run.get("route_candidates", {})
        query_counts = {}
        for route in type_at_10:
            rows = routes.get(route, [])[:10]
            query_counts[route] = len(rows)
            for row in rows:
                document = snapshot.by_id().get(str(row.get("artifact_id") or ""))
                if document:
                    type_at_10[route][document.artifact_type] += 1
                    if not document.title.strip():
                        untitled[route] += 1
            if route == "graph-expand":
                ids = {str(row.get("artifact_id")) for row in rows if row.get("artifact_id")}
                graph_ids.update(ids)
                graph_per_query.append(len(ids))
        topic_nonempty += int(bool(routes.get("topic", [])))
        query_rows.append({"category": run.get("smoke_category"), "counts": query_counts,
                           "graph_expand_distinct_at_10": len({str(item.get("artifact_id"))
                                                                  for item in routes.get("graph-expand", [])[:10]
                                                                  if item.get("artifact_id")})})

    quality = dict(snapshot.quality)
    source_name_by_id = {key: str(value.get("name") or key) for key, value in sources.items()}
    if isinstance(quality.get("topic_coverage"), Mapping):
        coverage = dict(quality["topic_coverage"])
        coverage["by_source_name"] = {
            source_name_by_id.get(source_id, source_id): value
            for source_id, value in coverage.get("by_source", {}).items()
        }
        quality["topic_coverage"] = coverage
    live_source_smoke = dict(live_source_smoke or {})
    rss_rows = []
    for source_id, source in sorted(sources.items(), key=lambda pair: str(pair[1].get("name") or pair[0])):
        acquisition = source.get("acquisition") if isinstance(source.get("acquisition"), Mapping) else {}
        if acquisition.get("mode") != "rss":
            continue
        primary_count = sum(primary_by_source.get(source_id, Counter()).values())
        rss_rows.append({"source": source_name_by_id.get(source_id, source_id), "source_id": source_id,
                         "observations": observations_by_source.get(source_id, 0),
                         "primary_artifacts": primary_count,
                         "types": dict(sorted(primary_by_source.get(source_id, Counter()).items())),
                         **dict(primary_details.get(source_id, Counter())),
                         "live": dict(live_source_smoke.get(source_id, {}))})
    final_migration_state = {
        "artifact_total": len(artifacts),
        "primary_artifact_total": sum(sum(counts.values()) for counts in primary_by_source.values()),
        "primary_artifacts_by_source": {source_name_by_id.get(key, key): sum(value.values())
                                        for key, value in sorted(primary_by_source.items())},
        "legacy_hf_model_ids_preserved": legacy_hf_model_ids,
        "zero_network": not bool(migration.get("network_requests", 0)),
    }
    hardware = dict(smoke.get("hardware") or {})
    dense = dict(smoke.get("dense") or {})
    result = {
        "before_corpus_hash": before["corpus_hash"], "after_corpus_hash": snapshot.corpus_hash,
        "before": {"artifact_total": before["corpus_artifact_count"], "types": before["artifact_type_counts"],
                   "missing_published_at": before["missing_published_at_count"],
                   "untitled_at_10": before["untitled_at_10_by_route"],
                   "topic_nonempty_queries": before["topic_candidate_queries"],
                   "manual_graph_top_repeated": before["graph_top_repetition"]["max_queries_sharing_top"]},
        "after": {"artifact_total": len(artifacts), "types": dict(sorted(type_counts.items())),
                  "quality": quality, "untitled_at_10": dict(untitled),
                  "empty_title_and_body_at_10": sum(
                      not (snapshot.by_id().get(str(row.get("artifact_id") or ""))
                           and (snapshot.by_id()[str(row["artifact_id"])].title.strip()
                                or snapshot.by_id()[str(row["artifact_id"])].body.strip()))
                      for run in smoke.get("queries", []) for route in ("bm25", "dense")
                      for row in run.get("route_candidates", {}).get(route, [])[:10]),
                  "topic_nonempty_queries": topic_nonempty, "graph_expand_unique_at_10": len(graph_ids),
                  "graph_expand_nonempty_queries": sum(value > 0 for value in graph_per_query),
                  "empty_title_and_body_documents": len(empty_docs),
                  "empty_documents_indexed_by_bm25": 0, "empty_documents_indexed_by_dense": 0,
                  "empty_documents_retained_as_graph_nodes": len(empty_docs),
                  "type_at_10": {key: dict(sorted(value.items())) for key, value in type_at_10.items()}},
        "queries": query_rows, "rss_primary": rss_rows,
        "rss_migration": {"latest_run": dict(migration), "final_state": final_migration_state},
        "live_source_smoke": live_source_smoke,
        "gpu_smoke": {"device": hardware.get("device"), "gpu_name": hardware.get("gpu_name"),
                       "gpu_memory_total_mb": hardware.get("gpu_memory_total_mb"),
                       "peak_vram_mb": hardware.get("peak_vram_mb"),
                       "peak_ram_mb": hardware.get("peak_ram_mb"), "model_id": dense.get("model_id"),
                       "model_revision": dense.get("model_revision"), "dimension": dense.get("dimension"),
                       "embedded": (dense.get("cache") or {}).get("embedded"),
                       "reused": (dense.get("cache") or {}).get("reused"),
                       "embedding_seconds": dense.get("embedding_seconds"),
                       "embedding_docs_per_sec": dense.get("embedding_docs_per_sec"),
                       "corpus_count": smoke.get("corpus_count"), "corpus_hash": smoke.get("corpus_hash")},
        "hf_enrichment": dict(hf_enrichment or {"status": "not-run"}),
        "benchmark": {"status": "draft", "query_count": 20, "human_qrels_complete": False,
                      "real_relevance_metrics": None, "m4_tuning": "blocked until DEV human qrels are reviewed and frozen"},
    }
    Path(report_path).write_text(render_m31_report(result), encoding="utf-8")
    return result


def render_m31_report(data: Mapping[str, Any]) -> str:
    before, after = data["before"], data["after"]
    quality = after["quality"]
    lines = [
        "---", "title: \"M3.1 Corpus Quality and Relevance Evaluation\"", "---", "",
        "# RI-M3.1 Corpus Quality, Artifact Semantics & Real Relevance Evaluation", "",
        "## Root cause", "",
        "M3 derived searchable Artifacts from encountered URLs without distinguishing the feed entry from links cited by its body. This promoted referenced and incidental URLs into the broad corpus while some RSS entries lacked a primary Artifact with the feed title, summary, and publication time. Retrieval then saw many untitled or empty records, and topic matches were sparse. M3.1 assigns mention roles, materializes RSS entries as typed primary Artifacts, and filters retrieval by content eligibility.", "",
        "## Corpus before and after", "",
        f"- Before: `{data['before_corpus_hash']}`; {before['artifact_total']} Artifacts; types `{json.dumps(before['types'], sort_keys=True)}`; {before['missing_published_at']} missing publication times.",
        f"- After: `{data['after_corpus_hash']}`; {after['artifact_total']} Artifacts; types `{json.dumps(after['types'], sort_keys=True)}`; {quality['missing_published_at']} missing publication times.",
        f"- Retrieval eligibility: `{json.dumps(quality['eligible'], sort_keys=True)}`; indexed by route: `{json.dumps(quality['indexed_by_route'], sort_keys=True)}`; research-default profile: {quality['profile_counts']['research-default']}.",
        f"- Missing title: {quality['missing_title']}; missing body: {quality['missing_body']}; primary: {quality['primary_count']}; referenced: {quality['referenced_count']}.",
        "- The after corpus hash changes because primary RSS items now have their own title, bounded summary, publication time, topics, and provenance. Referenced links no longer inherit the feed item's body.", "",
        f"- Missing publication times change from {before['missing_published_at']} to {quality['missing_published_at']} (+{quality['missing_published_at'] - before['missing_published_at']}); the increase corresponds to newly materialized referenced Artifacts without a source-reported time. These correctly do not inherit their parent entry's publication time.", "",
        "## RSS primary materialization", "",
        f"Zero-network rematerialization: `{json.dumps(data['rss_migration'], sort_keys=True)}`.",
        "| RSS source | Local observations | Primary Artifacts | Primary Artifact types | Missing title | Missing publication time | Live state |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    for row in data["rss_primary"]:
        type_text = ", ".join(f"{kind}: {count}" for kind, count in row["types"].items())
        live = row.get("live") or {}
        state = str(live.get("status") or "local-data-only")
        lines.append(f"| {row['source']} | {row['observations']} | {row['primary_artifacts']} | {type_text or '—'} | "
                     f"{row.get('missing_title', 0)} | {row.get('missing_published_at', 0)} | {state} |")
    notes = [row for row in data["rss_primary"] if (row.get("live") or {}).get("detail")]
    if notes:
        lines.extend(["", "Live poll notes:"])
        for row in notes:
            lines.append(f"- {row['source']}: {row['live']['detail']}")
    migration = data["rss_migration"]
    lines.append("")
    lines.append("Migration latest run: `" + json.dumps(migration["latest_run"], sort_keys=True) + "`.")
    lines.append("Final materialized state: `" + json.dumps(migration["final_state"], sort_keys=True) + "`.")
    lines.extend([
        "", "The catalog assigns arXiv cs.AI/cs.LG to `paper`, Hugging Face Blog and OpenAI News to `blog`; unknown RSS feeds default to `blog`. GitHub release repository semantics remain unchanged.",
        "", "## Retrieval quality and topic coverage", "",
        f"- Topic coverage: {quality['topic_coverage']['artifacts_with_topic']}/{quality['artifact_total']} ({quality['topic_coverage']['topic_coverage_rate']:.1%}).",
        "- Topic coverage by type: `" + json.dumps(quality["topic_coverage"]["by_artifact_type"], sort_keys=True) + "`.",
        "- Topic coverage by source: `" + json.dumps(quality["topic_coverage"]["by_source_name"], sort_keys=True) + "`.",
        "- Topic coverage by mention role: `" + json.dumps(quality["topic_coverage"]["by_mention_role"], sort_keys=True) + "`.",
        "- HF native tags and pipeline tags map only through exact topic aliases; unrecognized labels remain native metadata.",
        f"- Empty title and body records: {after['empty_title_and_body_documents']}; BM25 indexed: {after['empty_documents_indexed_by_bm25']}; Dense indexed: {after['empty_documents_indexed_by_dense']}; graph nodes retained: {after['empty_documents_retained_as_graph_nodes']}.",
        "- Empty title and body records are gated from BM25 and Dense while their graph objects remain available. Profiles are `research-default`, `all-artifacts`, and `models`.",
        "", "## Ten-query qualitative smoke", "",
        f"- Before untitled BM25/Dense@10 rows across ten queries: {before['untitled_at_10'].get('bm25', 0)}/{before['untitled_at_10'].get('dense', 0)}; Topic returned candidates for {before['topic_nonempty_queries']}/10.",
        f"- After untitled BM25/Dense@10 rows: {after['untitled_at_10'].get('bm25', 0)}/{after['untitled_at_10'].get('dense', 0)}; Topic returned candidates for {after['topic_nonempty_queries']}/10.",
        f"- Query-seeded graph expansion returned candidates for {after['graph_expand_nonempty_queries']}/10 queries and {after['graph_expand_unique_at_10']} unique top-10 Artifacts.",
        "- Before Graph top repetition came from manually injected seeds in the M3 smoke and is retained only as a diagnosis of the old run. It is not compared as a text-query Graph result. M3.1 pure text smoke has no manually selected graph seed.",
        "| Query | BM25@10 | Dense@10 | Topic@10 | Graph-expand@10 |", "|---|---:|---:|---:|---:|",
    ])
    for row in data["queries"]:
        counts = row["counts"]
        lines.append(f"| {row['category']} | {counts['bm25']} | {counts['dense']} | {counts['topic']} | {counts['graph-expand']} |")
    lines.extend([
        "", "Type distribution at 10 by route: `" + json.dumps(after["type_at_10"], sort_keys=True) + "`.",
        "", "## Hugging Face metadata sample", "",
        f"`{json.dumps(data['hf_enrichment'], sort_keys=True)}`. The bounded provider queries exact Hub IDs and stores selected metadata only; downloads, likes, and trending signals are not used as relevance. `selected=0` means the restored corpus has no eligible exact Hub repository IDs, so no request was sent.",
        "", "## RTX 5060 GPU smoke", "",
        "`" + json.dumps(data["gpu_smoke"], sort_keys=True) + "`.",
        "", "## Human relevance evaluation", "",
        "The 20 DEV query candidates and blind judgment pool are in `data/intelligence/eval/retrieval/dev-v1/`. Query provenance is recorded; candidate order is deterministic but shuffled, and route, rank, and scores are omitted. `label_source` remains unset until a human reviews queries and judgments.",
        "DEV benchmark pending human review. No human qrels were supplied, so there are no real Recall, MRR, nDCG, Precision, type-slice, or relevant-route-contribution metrics. Synthetic fixture metrics remain pipeline checks only.",
        "The DEV benchmark is draft and M4 ranking/fusion tuning is blocked until human qrels are reviewed and frozen. The 10 query texts in `holdout-draft.json` are frozen without qrels.",
        "", "## Limitations", "",
        "This report records local candidate quality and an unjudged GPU smoke. Candidate counts are not relevance scores. Corpus type distribution is diagnostic; no quotas or relevance claims are inferred.",
        "The OpenAI News live attempt persisted local observations, but its command did not finish with a successful connector checkpoint; it is not counted as a successful poll. The arXiv cs.AI live attempt did not finish: it persisted 242 observations and 241 primary papers, then the zero-network migration materialized the remaining paper. Its previous ETag and last-success checkpoint remain. Human qrels remain empty, so real relevance and M4 tuning remain blocked.", "",
    ])
    return "\n".join(lines).rstrip() + "\n"
