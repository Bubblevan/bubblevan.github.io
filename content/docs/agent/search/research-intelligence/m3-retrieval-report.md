---
title: "M3 Multi-route Retrieval Report"
---

# RI-M3 Retrieval Report

## Corpus

- Artifacts: 814 (22 papers, 0 blogs, 2 repositories, 784 models, 0 datasets).
- Indexed canonical documents: 814; missing `published_at`: 792.
- Corpus hash: `86a167d90c728792e0d4f5d3341b9b3edff17a635009490d56c210a3843c0b6a`.

Most rows are Hugging Face model Artifacts; this is a small and source-skewed corpus rather than a representative paper library.

## Routes and fusion

- BM25: bm25s over title (repeated twice), body, authors, topics and exact graph entity names; Jieba and CJK bigrams cover Chinese.
- Dense: Sentence Transformers with the configured Qwen embedding model, normalized vectors and exact cosine dot product.
- Graph: bounded one-hop citation, exact common-author and accepted-source co-mention evidence from explicit seed Artifacts.
- Topic: exact topic IDs; source route remains available for exact source evidence but is not part of these query runs.
- Fusion: RRF with `k=60`; raw route scores are retained and not added.

## Offline benchmark

- Frozen fixture: `synthetic-v1`; benchmark hash `c7e14626221a9685026a8dedbf2e36cd53d02b25204cfe259a04c82fcbdaf532`; fixture corpus hash `48a1d4948356b53c48a246779d9001775e7ed1629a46658bc12ef33a997ecbda`.
- Labels: `synthetic_fixture`; this one-query fixture checks candidate-route mechanics and is not a real-corpus relevance claim.
- Human-confirmed DEV (30–50 queries) and HOLDOUT (15–20 queries) qrels have not been collected, so the real corpus has no judged Recall/MRR/nDCG/Precision yet.

| Baseline | Recall@5 | MRR@10 | nDCG@10 | Precision@10 |
|---|---:|---:|---:|---:|
| B0 BM25 | 0.333 | 1.000 | 0.469 | 0.100 |
| B1 Dense | 0.333 | 1.000 | 0.469 | 0.100 |
| B2 Graph | 0.333 | 1.000 | 0.469 | 0.100 |
| B3 BM25 + Dense RRF | 0.667 | 1.000 | 0.765 | 0.200 |
| B4 BM25 + Dense + Graph RRF | 1.000 | 1.000 | 1.000 | 0.300 |

- Synthetic route unique hits at K=5: `{"bm25": ["art-111111111111111111111111"], "dense": ["art-222222222222222222222222"], "graph": ["art-333333333333333333333333"]}`; union Recall@5: 1.000; FutureLeakCount: 0.
The real corpus runs below are unjudged smoke queries, so these synthetic metrics do not estimate real-world retrieval quality.

## Real query smoke

All ten fixed queries ran with BM25, Dense, Graph, Topic and RRF. The seed is a manually selected existing Artifact to make the Graph route testable; it does not mark a relevance judgment.

| Query category | BM25 | Dense | Graph | Topic | RRF | Candidate union | Failed/skipped |
|---|---:|---:|---:|---:|---:|---:|---|
| Search Agent | 10 | 10 | 3 | 0 | 10 | 20 | — |
| Agentic RL | 10 | 10 | 1 | 0 | 10 | 17 | — |
| Memory | 10 | 10 | 1 | 0 | 10 | 18 | — |
| RAG | 10 | 10 | 1 | 0 | 10 | 15 | — |
| Harness | 10 | 10 | 1 | 0 | 10 | 17 | — |
| Verifier / Reward | 10 | 10 | 1 | 0 | 10 | 19 | — |
| Inference Serving | 10 | 10 | 1 | 0 | 10 | 18 | — |
| Multimodal Agent | 10 | 10 | 1 | 0 | 10 | 15 | — |
| Post-training | 10 | 10 | 1 | 0 | 10 | 16 | — |
| AI for Science | 10 | 10 | 3 | 0 | 10 | 19 | — |

These are candidate counts, not relevance scores. `candidate_set_complementarity_unjudged` below records unique IDs and overlap without claiming that they are useful.

## Top-10 qualitative inspection

The ten query result sets were inspected route by route. The counts below are top-ten rows with both title and summary empty; the notes describe visible output behavior and are not qrels.

| Query | Untitled BM25 | Untitled Dense | Review note |
|---|---:|---:|---|
| Search Agent | 9/10 | 7/10 | Visible research items include an agent-network paper and a deep-research security paper; most top rows are model records with both title and summary blank. |
| Agentic RL | 10/10 | 10/10 | BM25 and Dense top tens are all untitled model records; Graph returns the same broad human-learning paper seen for other seeds. |
| Memory | 10/10 | 9/10 | BM25 top ten and nine of ten Dense rows are untitled model records; Graph returns the same broad shared-neighborhood paper. |
| RAG | 8/10 | 6/10 | The RAPTOR paper appears near the top in both BM25 and Dense; most other rows are untitled model records. |
| Harness | 9/10 | 10/10 | One task-agent paper is visible in BM25; the remaining BM25 rows and all Dense rows lack titles and summaries. |
| Verifier / Reward | 8/10 | 10/10 | BM25 exposes evaluation and research-agent papers; Dense top ten are untitled model records. |
| Inference Serving | 9/10 | 10/10 | The text routes return almost entirely untitled model records; the visible paper is about search effects rather than serving systems. |
| Multimodal Agent | 9/10 | 9/10 | Wyvern ranks first in both BM25 and Dense; nine of ten rows per route still lack titles and summaries. |
| Post-training | 10/10 | 10/10 | BM25 and Dense top tens are all untitled model records; Graph again returns the same broad shared-neighborhood paper. |
| AI for Science | 10/10 | 8/10 | BM25 top ten are untitled model records; Dense includes a search-effects paper, with no clear science-system match in the visible titles. |

Graph's top result repeated for 10 of the ten seeds, showing that this sparse route follows the shared citation neighborhood rather than query-specific text relevance.

## Latency and dense resource use

- Model: `Qwen/Qwen3-Embedding-0.6B` at revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, dimension 1024.
- Newly embedded documents: 814; observed throughput: 54.647 docs/s.
- Dense vector index on disk: 3420439 bytes; peak RAM 2021.0 MiB; peak VRAM 1711.2 MiB.
- Route latency p50/p95 (ms): `{"bm25": {"p50_ms": 0.95, "p95_ms": 268.85}, "dense": {"p50_ms": 41.637, "p95_ms": 46.96}, "graph": {"p50_ms": 7.03, "p95_ms": 8.297}, "topic": {"p50_ms": 0.112, "p95_ms": 0.139}}`.
- Total smoke wall time: 33.07 seconds.

## Ablation and failure review

- Unjudged top-10 unique candidate totals by route across all queries: `{"bm25": 60, "dense": 60, "graph": 14, "topic": 0}`.
- Mean pairwise top-10 Jaccard overlap: 0.043.
- Topic route has limited coverage because only a small portion of the local Artifact corpus has canonical topics.
- Graph route depends on the manually selected seed and sparse citation/author edges; it cannot provide broad text-only retrieval on its own.
- The corpus contains no blog Artifacts and very few papers, so the memory, serving and science categories may return nearby model catalog rows rather than direct research matches.
- 792 Artifacts lack a publication timestamp in the current store. Historical `as_of` searches use first-observed fallback and exclude rows with neither clock.
- Query-level result lists and provenance are preserved in the ignored runtime smoke JSON for manual follow-up; no raw local results are copied into this published report.

## Limits

This report records a local smoke on one RTX 5060 8 GB desktop. It is not a benchmark comparison, relevance claim, model guarantee or quality score. No Feedback, freshness weighting, LLM rewriting or reranking is used.
