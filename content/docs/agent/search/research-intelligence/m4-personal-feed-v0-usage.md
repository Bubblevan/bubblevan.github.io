---
title: "RI-M4 Personal Feed v0 — Local Usage"
date: 2026-09-29T00:00:00+08:00
draft: false
---

RI-M4 adds a private, local daily research feed. It uses an explicit topic/source profile, recent canonical Artifacts, optional local Dense retrieval, BM25, exact topic/source routes, and a deterministic diversity pass. It does not train a ranking model or call an LLM or web API.

## Start the local UI

Install the optional UI dependency into the project environment, then run Streamlit from the repository root:

```powershell
python -m pip install -r requirements-feed-ui.txt
python -m streamlit run apps/research_intelligence_feed.py
```

The server binds to `127.0.0.1`. Usage telemetry is disabled. Profile, feed snapshots, and feedback are stored below the ignored and Hugo-excluded `data/intelligence/private/` directory.

The first profile starts empty. On **Profile**, select topics and sources and save. **Today** aims for 12 cards from the previous seven days; if recent candidates are scarce or heavily filtered, it relaxes diversity caps and stops at 10 when another relaxation would make the feed too concentrated. A normal rerun returns the existing immutable FeedRun. **Refresh revision** creates a new revision and retains the old snapshot and its feedback. Impressions are recorded only when Today renders cards, at most once per FeedRun and Artifact.

Cards explain why they appeared and provide Useful, Not relevant, Save, Hide, Less source, and Less topic actions. Saved items have their own page. Stats show aggregate counts without card text.

## CLI

```powershell
python -m scripts.intelligence.cli feed-profile
python -m scripts.intelligence.cli sources
python -m scripts.intelligence.cli feed-profile --add-topic topic-search-agent --follow-source <source_id>
python -m scripts.intelligence.cli feed-daily --date 2026-09-29
python -m scripts.intelligence.cli feed-daily --date 2026-09-29 --refresh
python -m scripts.intelligence.cli feed-feedback <feed_run_id> <artifact_id> useful
python -m scripts.intelligence.cli feed-stats
```

Use repeated profile flags to add or remove several selections. `feed-feedback` also accepts `not_relevant`, `save`, `unsave`, `hide`, `unhide`, `deep_read`, source/topic reduce and restore actions, and `retract --supersedes-feedback-id <feedback_id>`. Save is a bookmark and never becomes a positive exemplar. Only active Useful events seed semantic candidates. Retraction appends an event; it does not edit history.

The UI is the default feed writer. Stop it before running CLI commands that mutate the intelligence store. Feed retrieval uses local model files only; if Dense is unavailable, recent, lexical, source, and exact-topic routes continue to produce a feed.
