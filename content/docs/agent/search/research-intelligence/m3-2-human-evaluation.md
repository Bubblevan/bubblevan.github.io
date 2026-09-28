---
title: "M3.2 — Relevance Evaluation & Retrieval Stack Consolidation"
date: 2026-09-29
---

# M3.2 — Relevance Evaluation & Retrieval Stack Consolidation

This document originally described a human-only workflow. The active DEV benchmarks use explicitly recorded GPT-6 Luna model judgments. These development relevance judgments are useful for regression and diagnosis, but are model-judged pseudo-gold rather than human evaluation or objective ground truth.

DEV-v1 is the immutable initial Luna-judged pool. DEV-v1.1 reuses judgments for pairs still in the exact current B0–B4 top-20 union and sends only newly added pairs to the judge. Both benchmarks retain the same 20 queries and frozen corpus hash. No retrieval configuration is tuned in M3.2.1.

## Relevance guidelines

- **0 — Irrelevant:** the item does not answer the query or materially help investigate it.
- **1 — Relevant/useful:** the item contributes useful context, evidence, a method, or a source to follow.
- **2 — Directly important:** the item directly addresses the query or is a central result/example for it.
- Judge the content against the query. Do not reward recency, source prestige, popularity, personal author affinity, or where the retrieval system placed the item.
- Use the optional quality issue independently from relevance. `insufficient_metadata`, `broken_url`, `suspected_duplicate`, and `identity_problem` describe data quality; `none` means no issue was noticed. Do not turn a data-quality label into a relevance grade.
- If metadata is thin, use the canonical URL and visible source excerpt. Mark `insufficient_metadata` separately; it does not force grade 0, and the best-supported relevance grade is still recorded.

## Annotation and qrels source of truth

Argilla is an optional external UI. Configure `ARGILLA_API_URL` and `ARGILLA_API_KEY` in the process environment; an optional `ARGILLA_WORKSPACE` selects the workspace. Credentials are never command-line arguments, fields, metadata, qrels, or logs. `requirements-evaluation.txt` contains Argilla, `ir-measures`, and `ranx`; ingestion dependencies do not include them.

The hashed blind label pack is the candidate inventory. Its deterministic shuffled order is preserved on export. Every Argilla record is keyed by `(benchmark_hash, query_id, artifact_id)`, and existing records are left untouched during export so interrupted reviews can resume without duplicating records or overwriting judgments. Route, rank, score, retriever, fusion, and contribution metadata are prohibited from annotation payloads.

Imported judgments are validated against the pack's hashes and exact query/artifact inventory. Generic qrels use `bubblevan/retrieval-qrels/v2` and record `{type, name, model}` for each judgment; the legacy human-qrels schema remains readable. Model outputs use `bubblevan/retrieval-model-judgment/v1`, are matched exactly to the blind input, and fail closed on missing, duplicate, unknown, or invalid pairs. Only a successful import, complete candidate coverage, and explicit `eval-freeze` can create a frozen benchmark. `dev-v1.json` and `dev-v1-evaluation.json` are immutable; DEV-v1.1 lives alongside them.

The two blank Hugging Face Blog candidates may receive a display-only source name and Observation excerpt in the annotation UI. This context is not written back to the corpus, frozen label pack, or benchmark hash.

## Retrieval metrics and interpretation

Official DEV reports use `ir-measures` for P@10, RR@10, nDCG@10, Recall@5/10/20, and Judged@5/10/20; `ranx` provides the existing independent aggregate and per-query checks. Coverage is computed over returned candidate pairs, so an empty ranking has no missing judgments and passes the judgment-coverage test vacuously. The B0–B4 official gate requires Judged@10 and Judged@20 to equal 1.0 for every baseline. Otherwise status is `incomplete_judgment_pool`, and results remain exploratory. With 20 queries, report paired per-query differences descriptively; do not claim statistical significance or benchmark SOTA.

After DEV freeze, B0–B4 are BM25, Dense, graph expansion, BM25+Dense RRF, and BM25+Dense+Graph RRF. Topic-only evaluation is reported separately for queries eligible for that route. Include per-query results, broad/specific and category slices, judged counts, and an error analysis. Treat poor results on this 20-query DEV as correctness and diagnosis signals, not permission to tune repeatedly. Keep HOLDOUT untouched.

## Feedback inventory and M4 decision

`feedback-stats` reports event/action counts, unique canonical Artifacts, time span, and per-Artifact counts without exposing query text or event bodies. Current feedback events are 0. M4 therefore starts with a deterministic daily feed, transparent content/profile ranking, diversity, and explicit feedback capture. Do not introduce LambdaRank, contextual bandits, or RecBole before enough genuine preference feedback exists.

## Current operational gate

The judge prompt is frozen at `data/intelligence/eval/retrieval/judges/gpt-6-luna-v1.md`; its SHA-256 is stored with DEV-v1.1 provenance. Historical DEV-v1 judgments retain their original reviewer/guideline/time, while unrecoverable prompt hash and runtime revision/temperature/request IDs stay null. The optional consistency audit is recorded as `not_run` unless a second judgment pass is performed.

To produce a fresh pool, run `eval-build-model-judge-pool`; inspect `pool-coverage.json` and `pool-delta.json`, then send only `dev-v1-1-judge-input.json` to the approved judge workflow. Save its schema-conforming output as `dev-v1-1-judge-output.json`, validate and merge with `eval-import-model-judgments`, freeze with `eval-freeze`, then run `eval-run` against DEV-v1.1. Route/rank/score data is kept in the separate retrieval report and never enters the judge payload.
