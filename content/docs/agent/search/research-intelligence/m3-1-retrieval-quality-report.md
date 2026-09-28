---
title: "M3.1 Corpus Quality and Relevance Evaluation"
---

# RI-M3.1 Corpus Quality, Artifact Semantics & Real Relevance Evaluation

## Root cause

M3 derived searchable Artifacts from encountered URLs without distinguishing the feed entry from links cited by its body. This promoted referenced and incidental URLs into the broad corpus while some RSS entries lacked a primary Artifact with the feed title, summary, and publication time. Retrieval then saw many untitled or empty records, and topic matches were sparse. M3.1 assigns mention roles, materializes RSS entries as typed primary Artifacts, and filters retrieval by content eligibility.

## Corpus before and after

- Before: `86a167d90c728792e0d4f5d3341b9b3edff17a635009490d56c210a3843c0b6a`; 814 Artifacts; types `{"model": 784, "other": 6, "paper": 22, "repository": 2}`; 792 missing publication times.
- After: `b1726f3073a25b3bb59155a12d3471eec4c6f40fc831de0d7fb8260963229d29`; 2950 Artifacts; types `{"blog": 1871, "dataset": 1, "model": 784, "other": 11, "paper": 265, "repository": 18}`; 815 missing publication times.
- Retrieval eligibility: `{"excluded": 0, "full_text": 2135, "graph_only": 29, "metadata_only": 786}`; indexed by route: `{"bm25": 2921, "dense": 2921, "graph": 2950}`; research-default profile: 2156.
- Missing title: 29; missing body: 836; primary: 2113; referenced: 837.
- The after corpus hash changes because primary RSS items now have their own title, bounded summary, publication time, topics, and provenance. Referenced links no longer inherit the feed item's body.

- Missing publication times change from 792 to 815 (+23); the increase corresponds to newly materialized referenced Artifacts without a source-reported time. These correctly do not inherit their parent entry's publication time.

## RSS primary materialization

Zero-network rematerialization: `{"final_state": {"artifact_total": 2950, "legacy_hf_model_ids_preserved": 767, "primary_artifact_total": 2113, "primary_artifacts_by_source": {"Hugging Face Blog": 868, "OpenAI News": 1003, "arXiv cs.AI": 242}, "zero_network": true}, "latest_run": {"artifacts_touched": 242, "counts": {"already_materialized": 1871, "materialized": 242, "primary_type:paper": 242}, "network_requests": 0, "observations_seen": 2113, "repaired_truncated_hf_blog_artifacts": 0, "restored_legacy_hf_model_ids": 0}}`.
| RSS source | Local observations | Primary Artifacts | Primary Artifact types | Missing title | Missing publication time | Live state |
|---|---:|---:|---|---:|---:|---|
| Hugging Face Blog | 868 | 868 | blog: 868 | 0 | 0 | previous-local-poll-only |
| OpenAI News | 1003 | 1003 | blog: 1003 | 0 | 0 | attempt-incomplete |
| arXiv cs.AI | 242 | 242 | paper: 242 | 0 | 0 | attempt-incomplete |
| arXiv cs.LG | 0 | 0 | — | 0 | 0 | local-data-only |

Live poll notes:
- Hugging Face Blog: Retained 868 local observations and an earlier validator from M1.1; not re-polled for M3.1.
- OpenAI News: The command did not return a final result. Runtime state has no last_success_at, ETag, or Last-Modified; zero-network migration later materialized the remaining primary Artifact.
- arXiv cs.AI: The live request did not return a final result before cancellation. 242 Observations and 241 primary Artifacts were persisted; zero-network migration materialized the remaining paper Artifact. The previous ETag and last_success_at were retained.

Migration latest run: `{"artifacts_touched": 242, "counts": {"already_materialized": 1871, "materialized": 242, "primary_type:paper": 242}, "network_requests": 0, "observations_seen": 2113, "repaired_truncated_hf_blog_artifacts": 0, "restored_legacy_hf_model_ids": 0}`.
Final materialized state: `{"artifact_total": 2950, "legacy_hf_model_ids_preserved": 767, "primary_artifact_total": 2113, "primary_artifacts_by_source": {"Hugging Face Blog": 868, "OpenAI News": 1003, "arXiv cs.AI": 242}, "zero_network": true}`.

The catalog assigns arXiv cs.AI/cs.LG to `paper`, Hugging Face Blog and OpenAI News to `blog`; unknown RSS feeds default to `blog`. GitHub release repository semantics remain unchanged.

## Retrieval quality and topic coverage

- Topic coverage: 2114/2950 (71.7%).
- Topic coverage by type: `{"blog": {"rate": 1.0, "total": 1871, "with_topic": 1871}, "dataset": {"rate": 0.0, "total": 1, "with_topic": 0}, "model": {"rate": 0.0, "total": 784, "with_topic": 0}, "other": {"rate": 0.0, "total": 11, "with_topic": 0}, "paper": {"rate": 0.913208, "total": 265, "with_topic": 242}, "repository": {"rate": 0.055556, "total": 18, "with_topic": 1}}`.
- Topic coverage by source: `{"Hugging Face Blog": {"rate": 0.525424, "total": 1652, "with_topic": 868}, "OpenAI News": {"rate": 1.0, "total": 1003, "with_topic": 1003}, "STORM releases": {"rate": 1.0, "total": 1, "with_topic": 1}, "arXiv cs.AI": {"rate": 1.0, "total": 242, "with_topic": 242}, "unattributed": {"rate": 0.0, "total": 52, "with_topic": 0}}`.
- Topic coverage by mention role: `{"primary": {"rate": 1.0, "total": 2113, "with_topic": 2113}, "referenced": {"rate": 0.001195, "total": 837, "with_topic": 1}}`.
- HF native tags and pipeline tags map only through exact topic aliases; unrecognized labels remain native metadata.
- Empty title and body records: 29; BM25 indexed: 0; Dense indexed: 0; graph nodes retained: 29.
- Empty title and body records are gated from BM25 and Dense while their graph objects remain available. Profiles are `research-default`, `all-artifacts`, and `models`.

## Ten-query qualitative smoke

- Before untitled BM25/Dense@10 rows across ten queries: 92/89; Topic returned candidates for 0/10.
- After untitled BM25/Dense@10 rows: 0/0; Topic returned candidates for 1/10.
- Query-seeded graph expansion returned candidates for 9/10 queries and 20 unique top-10 Artifacts.
- Before Graph top repetition came from manually injected seeds in the M3 smoke and is retained only as a diagnosis of the old run. It is not compared as a text-query Graph result. M3.1 pure text smoke has no manually selected graph seed.
| Query | BM25@10 | Dense@10 | Topic@10 | Graph-expand@10 |
|---|---:|---:|---:|---:|
| Search Agent | 10 | 10 | 0 | 2 |
| Agentic RL | 10 | 10 | 0 | 3 |
| Memory | 10 | 10 | 0 | 3 |
| RAG | 10 | 10 | 0 | 4 |
| Harness | 10 | 10 | 0 | 1 |
| Verifier / Reward | 10 | 10 | 0 | 0 |
| Inference Serving | 10 | 10 | 10 | 2 |
| Multimodal Agent | 10 | 10 | 0 | 4 |
| Post-training | 10 | 10 | 0 | 3 |
| AI for Science | 10 | 10 | 0 | 2 |

Type distribution at 10 by route: `{"bm25": {"blog": 71, "paper": 29}, "dense": {"blog": 58, "model": 1, "paper": 41}, "graph-expand": {"model": 20, "paper": 2, "repository": 2}, "topic": {"blog": 10}}`.

## Hugging Face metadata sample

`{"api_requests": 0, "artifacts_updated": 0, "cache_hits": 0, "limit": 20, "metadata_found": 0, "selected": 0, "selection_priority_counts": {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0}}`. The bounded provider queries exact Hub IDs and stores selected metadata only; downloads, likes, and trending signals are not used as relevance. `selected=0` means the restored corpus has no eligible exact Hub repository IDs, so no request was sent.

## RTX 5060 GPU smoke

`{"corpus_count": 2950, "corpus_hash": "b1726f3073a25b3bb59155a12d3471eec4c6f40fc831de0d7fb8260963229d29", "device": "cuda", "dimension": 1024, "embedded": 0, "embedding_docs_per_sec": null, "embedding_seconds": 0.0, "gpu_memory_total_mb": 8150.6, "gpu_name": "NVIDIA GeForce RTX 5060", "model_id": "Qwen/Qwen3-Embedding-0.6B", "model_revision": "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3", "peak_ram_mb": 2030.2, "peak_vram_mb": 1152.5, "reused": 2921}`.

## Human relevance evaluation

The 20 DEV query candidates and blind judgment pool are in `data/intelligence/eval/retrieval/dev-v1/`. Query provenance is recorded; candidate order is deterministic but shuffled, and route, rank, and scores are omitted. `label_source` remains unset until a human reviews queries and judgments.
DEV benchmark pending human review. No human qrels were supplied, so there are no real Recall, MRR, nDCG, Precision, type-slice, or relevant-route-contribution metrics. Synthetic fixture metrics remain pipeline checks only.
The DEV benchmark is draft and M4 ranking/fusion tuning is blocked until human qrels are reviewed and frozen. The 10 query texts in `holdout-draft.json` are frozen without qrels.

## Limitations

This report records local candidate quality and an unjudged GPU smoke. Candidate counts are not relevance scores. Corpus type distribution is diagnostic; no quotas or relevance claims are inferred.
The OpenAI News live attempt persisted local observations, but its command did not finish with a successful connector checkpoint; it is not counted as a successful poll. The arXiv cs.AI live attempt did not finish: it persisted 242 observations and 241 primary papers, then the zero-network migration materialized the remaining paper. Its previous ETag and last-success checkpoint remain. Human qrels remain empty, so real relevance and M4 tuning remain blocked.
