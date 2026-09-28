---
title: "M3.2.1 — Operational Validation Report"
date: 2026-09-29
---

# RI-M3.2.1 — LLM-Judged Pool Completion & Benchmark Provenance

Base commit: `d8d3bbb RI-M3.2 freeze GPT-6 Luna DEV-v1`

Branch: `codex/xhs-anonymous-reader-20260927`
Status: **complete**. M3, M3.1, and M3.2 are closed. No retrieval tuning was performed.

## Immutable DEV-v1 and completed DEV-v1.1

DEV-v1 remains byte-identical. Its `dev-v1.json` SHA-256 is `38fd0961a39a3b8edb68e2a3609b39e5c788304479a53a8f379f208536d565c8`; its `dev-v1-evaluation.json` SHA-256 is `918055efda38bab64eda8e7bf96f9b391184a2656566249dffc17a70dc40c204`.

DEV-v1.1 uses the same 20 query texts and corpus hash `30bd975b4de7be5f29b96078a101f9d565c84078f429792994c5cc8d50109433`. The exact current B0–B4 top-20 union contains 997 query/Artifact pairs: 515 judgments were reused from DEV-v1, Luna judged only the 482 new pairs, and 118 old pairs fell outside the current pool. The new benchmark hash is `1c281e2985c6d1fd6d9594bbd09bc11da132a8a90449fcf265105edc455635ee`; the qrels hash is `c28bb7dd6bd8f1bbabf66ad3fe94433685869d31e0ff1f47058a364afd06465a`.

Judge provenance is explicit: `judge_type=model`, model `GPT-6 Luna`, reviewer `GPT-6 Luna (automated model judge; not human)`, guideline `m3-2-1-gpt-6-luna`, prompt SHA-256 `08b900b8ede9fac28d705693cb45b2092be48802686670409f1fb49dfab34fb9`, grade scale 0/1/2. The prior 633 decisions were not rerun. The old full prompt and runtime revision, temperature, provider request ID, and individual decision times could not be recovered; those historical values remain unknown. New batch revision/temperature/request ID are null because the judging harness did not expose them. The optional second-judge consistency audit is `not_run`.

The 482 new grades are: 298 grade 0, 140 grade 1, and 44 grade 2. Their quality labels are 461 `none`, 15 `insufficient_metadata`, and 6 `broken_url`. The final 997-pair qrels contain 562 grade 0, 298 grade 1, and 137 grade 2. Across the final pool, 39 pairs are `insufficient_metadata`; their grade distribution is 30/8/1 for grades 0/1/2. Quality flags remain separate from relevance grades.

## Coverage gate

Coverage is calculated over returned result pairs. Empty route results have no pair requiring judgment and count as vacuously covered. Before the incremental Luna pass, the actual pool coverage was:

| Baseline | Judged@5 | Judged@10 | Judged@20 | Unjudged@20 |
|---|---:|---:|---:|---:|
| B0 | 1.000 | 1.000 | 0.598 | 161 |
| B1 | 1.000 | 1.000 | 0.630 | 148 |
| B2 | 1.000 | 1.000 | 0.525 | 116 |
| B3 | 1.000 | 0.930 | 0.725 | 110 |
| B4 | 1.000 | 0.965 | 0.710 | 116 |

After DEV-v1.1 froze, every B0–B4 baseline passed `Judged@10 = 1.0` and `Judged@20 = 1.0`. The historic DEV-v1 aggregate recorded B2 `Judged@10 = 0.75`; its five empty graph result lists caused that value. The pair audit found no unjudged B2 top-10 result, but did find 116 unjudged B2 results through rank 20. The evaluation now treats empty rankings as vacuously covered and still requires every returned result pair through rank 20 to be judged.

## B0–B4 comparison

The corpus, dense index manifest, route source fingerprint, route depth 50, top 20, `research-default` filter, and RRF k=60 were held constant. The dense manifest records `Qwen/Qwen3-Embedding-0.6B`, revision `main`, with normalized 1024-dimensional vectors. The final evaluation records this retrieval provenance and passed the official coverage gate.

| Baseline | P@10 v1 → v1.1 (Δ) | RR@10 v1 → v1.1 (Δ) | nDCG@10 v1 → v1.1 (Δ) | Recall@20 v1 → v1.1 (Δ) |
|---|---:|---:|---:|---:|
| B0 | 0.560 → 0.560 (0.000) | 0.823 → 0.823 (0.000) | 0.544 → 0.506 (-0.038) | 0.498 → 0.465 (-0.032) |
| B1 | 0.710 → 0.710 (0.000) | 0.908 → 0.908 (0.000) | 0.680 → 0.640 (-0.040) | 0.655 → 0.601 (-0.053) |
| B2 | 0.095 → 0.095 (0.000) | 0.325 → 0.325 (0.000) | 0.091 → 0.085 (-0.006) | 0.075 → 0.059 (-0.016) |
| B3 | 0.610 → 0.655 (+0.045) | 0.942 → 0.942 (0.000) | 0.639 → 0.621 (-0.018) | 0.658 → 0.544 (-0.115) |
| B4 | 0.625 → 0.645 (+0.020) | 0.933 → 0.933 (0.000) | 0.641 → 0.611 (-0.030) | 0.634 → 0.528 (-0.106) |

B3 and B4 each had previously unjudged top-10 candidates (14 and 7 pairs) that are now graded; their precision changes are judgment-pool effects, not ranking improvements. B2 remains weak: P@10 is unchanged and nDCG@10 moves only slightly. Some Recall deltas also reflect DEV-v1.1's larger judged candidate universe. The full per-metric values and deltas are in `data/intelligence/eval/retrieval/dev-v1.1/dev-v1.1-metric-delta.json`.

## Artifacts and completion evidence

- `dev-v1.1-label-pack.json`: exact current candidate inventory and frozen retrieval provenance.
- `dev-v1-1-judge-input.json` / `dev-v1-1-judge-output.json`: blind incremental model-judgment interchange.
- `dev-v1.1-qrels.json` / `dev-v1.1.json`: generic qrels v2 and immutable frozen benchmark.
- `dev-v1.1-evaluation.json`: `ir_measures` and `ranx` results; status `completed`, comparison eligibility `official`.
- [`m3-2-1-error-analysis.md`](m3-2-1-error-analysis.md): per-query B0–B4 result analysis.
- `pool-coverage.json` / `pool-delta.json`: pre-judgment coverage, exact new/removed pair inventory, and post-freeze gate.

Offline Python regression passed (210 tests). Hugo 0.153.0 production build passed with 1,187 pages. The current feedback inventory remains 0 events; M3.2.1 does not start LambdaRank, bandits, or RecBole.

The next milestone is **RI-M4 — Personal Feed v0 + Explicit Feedback Loop**, defined in [`m4-personal-feed-v0-trd.md`](m4-personal-feed-v0-trd.md).
