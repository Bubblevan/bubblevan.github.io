---
title: "RI-M6 PaperFlow Reference"
date: 2026-09-29T00:00:00+08:00
draft: false
---

## Why this reference matters

[PaperFlow](https://github.com/OpenRaiser/PaperFlow) is a useful reference for the researcher's daily loop: collect papers, adapt suggestions from explicit feedback, prepare reading reports, and maintain a local research workspace. Its paper also describes a personalized paper discovery and reading workflow ([arXiv:2606.07454](https://arxiv.org/abs/2606.07454)).

RI is broader in scope. It collects across papers, repositories, people, organizations, feeds, and other public sources; preserves source observations and provenance; resolves canonical Artifacts; and builds a shared graph and personal daily feed. That difference matters when adapting ideas: PaperFlow's paper-centered interaction patterns can inform our feed, while RI's cross-source identity, source discovery, provenance, and operational controls remain the foundation.

| PaperFlow concept | RI-M6 counterpart | Reuse boundary |
| --- | --- | --- |
| Daily paper collection | OpenReview submissions, Hugging Face Daily Papers, and exact-ID OpenAlex polls | Reuse date-window and bounded-poll patterns; retain each provider's explicit identifiers and provenance. |
| Preference adaptation from user behavior | M4 explicit feedback projection and the existing Feed profile | Preserve explicit, explainable feedback semantics; M6 does not add an implicit ranking feature. |
| Reading reports and a local paper workspace | Canonical Artifact, Observation history, and the daily feed | Reports may be a later presentation layer; do not make them a second source of record. |
| Paper-centered recommendations | Cross-source candidate retrieval and Source Coverage | A paper may arrive from several sources; deduplicate by exact identity and retain every contribution. |

The PaperFlow project is a comparison reference, not an RI runtime dependency. RI-M6 does not copy its retrieval implementation or replace the existing JSONL event store, provenance model, connector state, or graph.

## M6 references

- [RI-M6 architecture and operational boundaries](architecture.md)
- [RI-M5 Daily Operations and Freshness](m5-daily-operations.md)
