---
title: "RI-M4 — Personal Feed v0 + Explicit Feedback Loop"
date: 2026-09-29
---

# RI-M4 — Personal Feed v0 + Explicit Feedback Loop

## Goal

Give the single local user a useful, explainable set of new AI and research items each day, then capture direct preference feedback. M4 turns the existing source, observation, artifact, entity, topic, graph, and retrieval data into a daily reading workflow. It does not train a ranking model.

The v0 should answer three questions for every card: what is this, why did it reach my feed, and what can I tell the system about it?

## User experience

- A private **Today** view contains 10–15 items and can be regenerated safely for the same date.
- Each card shows title, short summary, canonical source, publication time, artifact type, and one or two concrete reasons for inclusion, such as a selected topic, followed source, or similar saved item.
- The user can mark **useful**, **not relevant**, **save**, **hide this item**, **show less from this source**, or **show less of this topic**. Feedback is one click and can be undone where practical.
- “Open” and “save” are usage events. They are not silently converted into positive relevance labels. Explicit useful/not-relevant/hide actions are preference signals.
- The user chooses initial topics and followed sources explicitly. Empty preferences use broad research defaults and diversify across topic and source.

The feed and interaction history are private local data. Do not publish them in the public Hugo build or include raw query text in feedback records.

## Candidate generation and ordering

1. Read canonical Artifacts and recent primary Observations from the existing local store. Include only eligible, non-incidental items with stable canonical identity and a usable display title or summary.
2. Deduplicate by canonical Artifact ID and exclude items the user has explicitly hidden. Prefer items with a recent publication time; use first observation time only as a documented fallback.
3. Match candidates against the explicit profile: selected topics, followed Sources, and a small set of user-saved positive examples. Reuse the existing BM25/Dense/Graph retrieval routes to find candidates; do not change their parameters as part of M4.
4. Order with a small deterministic policy: explicit negative feedback exclusions first; direct profile/topic or followed-source matches next; freshness as a bounded tie-breaker; then stable Artifact ID. Do not use popularity, downloads, likes, or source prestige as relevance.
5. Apply a simple diversity pass so one Source or topic cannot fill the whole feed. Keep ranking reasons attached to every item. Start with readable fixed caps, measure the resulting mix, and change them only through a reviewed product decision.
6. If fewer than 10 candidates qualify, widen the lookback once and label older items. Never fabricate or repeat an item simply to fill the page.

The policy is intended for predictable product behavior, not offline benchmark optimization. Keep its version and inputs in each feed run so the user can reproduce a date's list.

## Data and interfaces

- `FeedProfile`: one local profile ID, selected topic IDs, followed source IDs, hidden Artifact IDs, and a small list of saved positive examples. Store explicit choices separately from inferred statistics.
- `FeedRun`: feed date, corpus hash, policy version, candidate count, selected Artifact IDs, and the inclusion reasons shown to the user. Store a compact impression record so duplicate exposure can be reduced and later explained.
- `FeedbackEvent`: event ID, Artifact ID, explicit action, timestamp, surface (`daily_feed`), and optional reason code such as `wrong_topic`, `too_old`, `too_technical`, or `duplicate`. Do not persist full search queries or card text in the event.
- CLI: `feed-profile` to inspect/update local preferences, `feed-daily --date YYYY-MM-DD` to generate a run, and `feed-feedback <artifact_id> <action>` to record a direct response. Re-running a date updates the same run deterministically and does not duplicate feedback events.
- UI: a private local feed view backed by the same local store. It must not put personal feed content into public Hugo output, analytics, or third-party requests.

The existing M1/M2 JSONL stores are single-writer. M4 must preserve that constraint; synchronization across machines is a later deployment milestone. Keep event schemas additive and versioned.

## Feedback interpretation

Explicit `useful` and `not_relevant` events are the strongest initial preference evidence. `save` and `hide` are separate action types. `show_less_from_source` and `show_less_of_topic` update explicit profile constraints rather than changing the global relevance of that source or topic. `open` and `deep_read` describe engagement and remain distinct from explicit relevance feedback.

Expose counts by action and time window through `feedback-stats`; do not print raw private event content. M4 v0 uses these events to adjust transparent profile rules only. There are currently zero feedback events, so no LambdaRank/LightGBM, contextual bandit, or RecBole work is unlocked.

## Acceptance criteria

- A local daily run returns 10–15 eligible, canonical, deduplicated Artifacts when enough candidates exist.
- A fixed corpus/profile/date produces the same ordered feed and reasons.
- Each item has at least one user-visible reason; filtering, recency, and diversity decisions are auditable.
- Explicit topic/source choices and negative feedback measurably change the next feed in deterministic fixtures.
- Re-running the same date does not duplicate a `FeedRun` or `FeedbackEvent`.
- No query text, credentials, or private feed content appears in public Hugo output or third-party analytics.
- `feedback-stats` reports event counts by action and Artifact without exposing event bodies.
- Existing retrieval DEV metrics remain a regression guard only; M4 does not tune B0–B4 or claim that model-judged pseudo-gold is human ground truth.

## Out of scope

Model training, personalized embeddings, pairwise preference learning, online exploration, automated source subscriptions, multi-user recommendations, and changes to connector/source-discovery milestones. Reconsider ranking learning only after enough explicit preference events and reviewable evaluation groups exist.

## Delivery sequence

1. Freeze the profile, run, and feedback schemas and deterministic policy contract.
2. Add local profile and feedback CLI commands with privacy-safe summaries.
3. Build the daily candidate pool and deterministic ordering with fixtures for exclusions, freshness fallback, topic/source coverage, and deduplication.
4. Add the private local feed UI and explainability text.
5. Run a small operational period, inspect action counts and feed diversity, then decide whether M4.1 needs a refined rule. Do not begin model-based ranking as part of v0.
