---
title: "RI-M5 Daily Operations and Freshness"
date: 2026-09-29T00:00:00+08:00
draft: false
---

RI-M5 is the single-machine, one-shot daily operations path. Python orchestrates existing connectors, graph backfill, corpus snapshot, and the same `FeedService` used by the Streamlit UI. Windows Task Scheduler starts the command; the Python process exits after one run.

## Isolate M4 validation data

The one-time migration keeps all M4 smoke runs and events under `data/intelligence/private/feed-smoke/m4-v0-<timestamp>/`. Only the explicit profile is copied into `feed-production/`; production starts with zero feedback events and zero FeedRuns. The archive is retained.

```powershell
python -m scripts.intelligence.cli feed-archive-smoke
python -m scripts.intelligence.cli feed-profile --mode production
python -m scripts.intelligence.cli feed-stats --mode production
```

The migration writes a count-only report under the ignored `data/intelligence/runtime/ops/migrations/`. Repeating the command does not overwrite a production profile or add smoke events to production.

## Run once and inspect health

Install the supported dependencies into the interpreter that will run the scheduled task:

```powershell
python -m venv .ri-ops-venv
.ri-ops-venv\Scripts\python.exe -m pip install -r requirements-intelligence.txt -r requirements-ops.txt -r requirements-feed-ui.txt
.ri-ops-venv\Scripts\python.exe -m scripts.intelligence.cli intelligence-daily --mode production
.ri-ops-venv\Scripts\python.exe -m scripts.intelligence.cli ops-status --mode production
```

`intelligence-daily` polls active catalog entries, isolates connector failures, backfills the local graph without network access, snapshots the corpus, prepares or reuses the production FeedRun, and writes a DailyPipelineRun plus the current health manifest. A source failure produces a usable partial run. Dense warming is opt-in with `--dense`; scholarly graph enrichment is off by default and can be explicitly bounded with `--enrich-limit N`.

Runs live below `data/intelligence/runtime/ops/daily/` as immutable `YYYY-MM-DD-rNNNN.json` files. Connector status determines source health: `healthy`, `deferred`, `stale`, `failing`, or `never_run`. The freshness SLA is `operations.poll_sla_hours` in the source catalog, defaulting to 36 hours. It measures the last successful poll, even when a source has published nothing new. Diagnostics older than 90 days are pruned.

`ops-status` and the UI Ops page report the latest pipeline, corpus hash, FeedRun, source health, and whether a viewed FeedRun needs a manual refresh. Daily acquisition never replaces a viewed FeedRun. The Today page shows the freshness banner and offers **Refresh today's Feed** when new inputs are ready.

Exit codes are `0` completed, `2` partial but usable, and `1` failed. The scheduled task adds `--scheduled`, translating partial to Task Scheduler result `0`; the manifest and UI keep the partial warning.

## Install and smoke the Windows task

Choose a daily local time and pass it to the installer. The task action stores the absolute repository path and Python executable, runs from the repository root, has `StartWhenAvailable`, requires network availability, ignores overlapping instances, and stops after two hours. It runs under the current user with S4U; no account password or API credential is saved in the task.

```powershell
.\scripts\intelligence\ops\windows\install-task.ps1 `
  -At "HH:mm" `
  -PythonPath (Resolve-Path ".ri-ops-venv\Scripts\python.exe").Path `
  -HermesPath "D:\Software\Hermes\hermes-agent\venv\Scripts\hermes.exe"

Start-ScheduledTask -TaskName BubblevanResearchIntelligenceDaily
.\scripts\intelligence\ops\windows\status-task.ps1
python -m scripts.intelligence.cli ops-status --mode production
```

After the scheduled smoke completes, invoke the CLI once more without `--force`. A completed same-day run is returned as-is, so the manual idempotency check does not poll sources or create another feed revision. Use `--force` only when intentionally creating the next attempt.

```powershell
python -m scripts.intelligence.cli intelligence-daily --mode production
python -m scripts.intelligence.cli intelligence-daily --mode production --force
.\scripts\intelligence\ops\windows\uninstall-task.ps1
```

The scheduled entry point sends a completion summary to the configured Hermes Weixin home chat after every run, including partial and failed runs. It includes only the run date/status, aggregate source counts, new Observation/Artifact counts, Feed count, and a short corpus hash. It does not include source URLs, raw errors, content, or credentials. Hermes `send` delivers the text directly and does not invoke a model. A delivery failure makes the scheduled task return nonzero so it remains visible in Task Scheduler history.

Store and feed mutations use short-lived file locks at `data/intelligence/runtime/locks/store-write.lock` and `data/intelligence/private/locks/feed-write.lock`. Interactive writes wait at most five seconds; scheduled pipeline writes wait at most 60 seconds. Contention returns `lock_contended` with no mutation. Store directories remain single-writer across machines.

Task arguments contain no tokens, cookies, or request payloads. Secrets, when a connector needs them, remain in the process environment or an OS credential mechanism. DailyRun and source failure summaries store safe error classes and scrubbed summaries only.
