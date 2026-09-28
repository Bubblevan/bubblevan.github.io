---
title: "M3.1 Corpus Identity Repair and DEV Label Pack"
---

# RI-M3.1 Corpus Identity Repair and DEV Label Pack

> Historical M3.1.1 checkpoint. DEV-v1 was subsequently frozen as the initial GPT-6 Luna-judged development benchmark, and M3.2.1 added the complete DEV-v1.1 pool. Use [the current M3.2 operational report](m3-2-operational-report.md) for active hashes and metrics; do not treat the draft-state notes below as current.

## Hugging Face identity repair

The historical `huggingface:model:blog/...` records have been repaired without deleting their Artifact IDs. All 784 affected IDs now redirect to canonical Hugging Face Blog Artifacts, and all 784 incorrect model aliases have been removed. The repair created 35 missing canonical blog Artifacts. The migration is idempotent.

Full-store audit after repair:

| Audit | Model-typed URLs |
|---|---:|
| HF blog URLs typed model | 0 |
| HF papers URLs typed model | 0 |
| HF docs/API/etc typed model | 0 |
| HF datasets URLs typed model | 0 |
| HF spaces URLs typed model | 0 |

The docs/API/etc group also covers the reserved `collections`, `join`, `organizations`, and `tasks` roots. Total reserved-namespace violations: **0**.

## Successful source replay

Each connector completed successfully after the identity repair. Checkpoint timestamps below are UTC.

| Source | Result | Fetched | New observations | Duplicates | Checkpoint |
|---|---|---:|---:|---:|---|
| arXiv cs.AI (`src-9ba78cdae54743ea73623d2b`) | HTTP 200, success | 331 | 89 | 242 | success `2026-09-28T10:15:29.791851Z`; ETag retained; high watermark `2026-09-28T04:00:00Z` |
| OpenAI News (`src-74d6a6418ec8044df3bcb76d`) | HTTP 200, success | 1230 | 227 | 1003 | success `2026-09-28T10:17:32.104811Z`; high watermark `2026-09-25T19:00:00Z` |
| Hugging Face Blog (`src-967980510ffe7b2003b96be0`) | HTTP 200, success | 869 | 1 | 868 | success `2026-09-28T10:24:08.132648Z`; ETag retained; high watermark `2026-09-28T09:44:05Z` |

All three ConnectorState records have `consecutive_failures=0` and `backoff_until=null`. Their state was produced by connector runs; it was not edited by hand.

## Frozen corpus and indexes

After source replay, zero-network rematerialization saw 2,430 observations, found all already materialized, and touched no Artifacts. Graph rebuild produced 2,981 nodes and 7,532 edges. The subsequent retrieval build froze this corpus:

- Corpus hash: `30bd975b4de7be5f29b96078a101f9d565c84078f429792994c5cc8d50109433`
- Canonical retrieval documents: 2,529 (2,134 blog, 354 paper, 28 repository, 1 dataset, 12 other)
- BM25 and Dense indexed documents: 2,454 each; Graph indexed documents: 2,529
- Dense model: `Qwen/Qwen3-Embedding-0.6B`, revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, 1,024 dimensions, CUDA on NVIDIA GeForce RTX 5060

The label-pack run and the final manifest report the same corpus hash. The Dense index reused all 2,454 document vectors for this frozen corpus.

## Graph expansion identity check

The graph retriever now loads and flattens Artifact and Entity redirects once per build, then canonicalizes graph endpoints from those maps. This keeps redirected historical IDs out of route results and avoids rereading the redirect JSONL for every graph edge on every query.

A real DEV query against the frozen corpus returned 50 `graph-expand` candidates. The route check found:

- Historical HF Blog redirect IDs returned as independent candidates: **0**
- Candidate IDs missing from the canonical retrieval snapshot: **0**
- Reserved HF namespace URLs typed as model: **0**
- Route index build failures: **0**

The regression test also verifies that a historical bogus model ID resolves to the canonical blog, is excluded from the models profile, and does not appear as its own graph-expand candidate.

## New blind DEV-v1 label pack

The previous `dev-v1-label-pack.*` has been replaced. The new pack is based on the frozen corpus above:

- Queries: 20
- Candidate pool: 633
- Corpus hash: `30bd975b4de7be5f29b96078a101f9d565c84078f429792994c5cc8d50109433`
- Benchmark hash: `638e90aa3d5cc76f7a592f1fbe55fa1483f96e530f8c6e3d58e65644536a4366`
- Status at this historical checkpoint: draft, awaiting 0/1/2 grades

The candidate records expose only Artifact ID, title, type, summary excerpt, canonical URL, and publication time. Route, rank, and score fields are absent. An audit of all 633 candidates found zero missing records, ID redirects, type mismatches, canonical URL mismatches, or HF Blog/Papers model identities. A manual sample of 20 candidates found no identity garbage. Two sampled Hugging Face Blog records have blank titles and summaries, but their canonical URLs and `blog` types are valid; this is missing display metadata rather than an identity conflict.

Files preserved from this historical checkpoint:

- `data/intelligence/eval/retrieval/dev-v1/dev-v1-label-pack.md`
- `data/intelligence/eval/retrieval/dev-v1/dev-v1-label-pack.json`
- `data/intelligence/eval/retrieval/dev-v1/dev-v1-qrels.json`

These files are retained as the initial pack. `dev-v1.json` and `dev-v1-evaluation.json` are immutable. Current development evaluation uses `dev-v1.1/`, whose 997-pair pool is fully GPT-6 Luna-judged and passes the B0–B4 coverage gate. M4 is defined by [the Personal Feed v0 TRD](m4-personal-feed-v0-trd.md).
