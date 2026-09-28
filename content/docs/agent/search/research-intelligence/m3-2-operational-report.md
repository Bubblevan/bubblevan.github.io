---
title: "M3.2 — Operational Report"
date: 2026-09-28
---

# M3.2 — Operational Report

Base commit: `6eb52f519d8f942427fd565485384d86bfa0cdce`

Branch: `codex/xhs-anonymous-reader-20260927`
State: M3.2 tooling and offline validation are ready; human evaluation is still open. M4 remains locked.

## Completed

- Added the canonical Artifact repository API and cycle-checked read-only redirect maps. Product code now reads Artifacts through canonical views; remaining raw reads are in migration/audit code, tests, or the repository's explicit `raw_rows()` API.
- Added `artifact-stats` and changed product `stats` to count canonical Artifacts. Current store: 3,313 physical rows, 784 redirected rows, 2,529 canonical Artifacts (2,134 blogs, 354 papers, 28 repositories, 1 dataset, 12 other).
- Added blind Argilla and offline JSON annotation adapters. Candidate identity is stable per `(benchmark_hash, query_id, artifact_id)`. Export adds only missing IDs and leaves existing records untouched. Import validates hashes, identity, external record ID, and 0/1/2 grade values. Quality issue labels remain separate from qrels.
- Produced a 633-record blind handoff at `data/intelligence/eval/retrieval/dev-v1/dev-v1-annotation-json.json`. It contains no route/rank/score/retriever/fusion fields. The 19 repeated query-candidate display rows for the two blank HF Blog candidates receive only a source/Observation display fallback; the label pack and corpus were not changed.
- Added complete-review freeze checks and an `eval-run` implementation for B0–B4, topic-route reporting, per-query/category/specificity/type slices, `ir-measures`, ranx diagnostics, and error analysis. The runner refuses a draft, incomplete, hash-mismatched, or stale-corpus benchmark.
- Added optional `requirements-evaluation.txt`; the base ingestion requirements remain unchanged. Added annotation guidance and documented the frozen benchmark as the qrels source of truth after validation.
- Added `feedback-stats`. Current feedback inventory is empty (0 events, 0 unique Artifacts); based on that observed count, M4 should start with deterministic content/profile ranking and diversity. LTR and online bandits are not justified by current feedback volume.

## Offline validation

- Offline Python suite: **191 tests passed**, including repository identity, blind payload, JSON/Argilla resume round-trip, import validation, grade parity with `ir-measures`, and RRF parity with ranx.
- Current corpus hash still matches the label pack: `30bd975b4de7be5f29b96078a101f9d565c84078f429792994c5cc8d50109433`.
- Label pack benchmark hash: `638e90aa3d5cc76f7a592f1fbe55fa1483f96e530f8c6e3d58e65644536a4366`.
- Hugo is not installed on this host, so local production build was unavailable. The branch CI build is the Hugo validation gate.

## Open human gates

The current process has no `ARGILLA_API_URL` or `ARGILLA_API_KEY`, so a live Argilla sync/633-record server round-trip could not run. The offline 633-record export is ready for review. The qrels file remains a draft; no judgments were inferred. As a result, DEV-v1 cannot yet be frozen and B0–B4 metrics or error analysis must not be reported as real human-evaluated results. HOLDOUT was left untouched.

To use Argilla, configure its URL/key in the process environment and run `eval-export-argilla`. To use the offline handoff, enter each grade under `responses.relevance` in the JSON export (optional `responses.quality_issue`), then import with `eval-import-json`. After all 633 judgments are present, `eval-freeze` requires reviewer and timestamp metadata; only then may `eval-run` be used. Neither path starts M4.
