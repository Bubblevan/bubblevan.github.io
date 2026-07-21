# Phase 3 PRD v3: Personal Knowledge Capture Adapter Layer

Status: Draft  
Owner: Bubblevan  
Phase: 3  
Last updated: 2026-07-19

## 1. Background

The site is a Hugo + Hextra personal knowledge base, blog, project retrospective system, daily journal, and career asset dashboard.

Phase 1 established the content architecture: `daily`, `docs`, `blog`, `papers`, `projects`, `career`, dashboard data files, and reusable page structure.

Phase 2 added local extraction and review tooling around explicit markers such as `@task`, `@link`, `@event`, and `@project`. That pipeline turns markdown captures into generated extraction JSON, then review and promote steps can move selected items into `data/*.yaml`.

The original Phase 3 direction was to build a custom Gateway API and connect it to WeChat/ClawBot. That plan is now retired. Phase 3 v3 uses an adapter-first architecture that depends on existing Agent software instead of introducing a new always-on custom API.

## 2. Product Decision

The system core is not Hermes, OpenClaw, WorkBuddy, or any single Agent product. The stable core is the **Capture Contract**:

```text
agent input
  -> pkb capture contract
  -> inbox/raw + data/captures/*.jsonl
  -> Phase 2 extraction
  -> review queue
  -> promote into data/*.yaml or content/*
```

Agent software is replaceable. Captures and Git-backed site content are durable.

## 3. Agent Positioning

### Hermes Agent / Hermes Desktop

Hermes is the preferred Phase 3 mainline adapter because it is already installed and suitable for local Windows-native operation. It is positioned as the local resident Agent layer with desktop/CLI/gateway/skills/cron/local-file style capabilities. Hermes should call `pkb capture` or write drop files. It must not directly edit Hugo content or dashboard data.

Public docs support this positioning: Hermes exposes CLI, desktop, gateway, skills, cron, messaging, and local delivery surfaces, while Hermes Desktop is described as a native app using the same agent core and shared config/sessions/skills.

### OpenClaw / ClawBot

OpenClaw remains useful as a channel adapter, especially for WeChat, QQ, Windows Hub, daemon, and auto-start style IM ingestion. It is not the knowledge base core. If Hermes can directly connect to a WeChat-like channel reliably, OpenClaw can remain optional.

OpenClaw's Windows docs emphasize Windows Hub, tray/launch-at-login, Gateway setup, Command Center diagnostics, Windows node capabilities, and Gateway auto-start patterns. That makes it suitable as a channel/runtime adapter rather than the long-term content store.

### WorkBuddy

WorkBuddy is not a core dependency for Phase 3. It is treated as closed/commercial or uncertain with respect to local Git-first export guarantees. It may be used manually to summarize research, reports, or webpages into a copyable capture block, but it should not directly modify this repository and should not be treated as a source of truth.

There are multiple WorkBuddy/WorksBuddy-style products and docs online. Some emphasize local-first workflow support, while others are commercial suites or agent workstations. Because Git-first export and repository-safe automation are not guaranteed for the user's exact installed product, Phase 3 treats WorkBuddy as optional manual input only.

## 4. Goals

1. Introduce a local Capture CLI that can be called by Hermes, OpenClaw, WorkBuddy manual exports, or future agents.
2. Persist every capture to append-only raw stores:
   - `inbox/raw/YYYY/MM/YYYY-MM-DD.md`
   - `data/captures/YYYY-MM.jsonl`
3. Support drop-file ingestion from:
   - `inbox/drop/hermes`
   - `inbox/drop/openclaw`
   - `inbox/drop/workbuddy`
4. Validate capture records against a stable schema.
5. Keep Hugo build independent of whether any Agent software is running.
6. Preserve Phase 2 extraction/review/promote as the downstream processing layer.

## 5. Non-Goals

Phase 3 v3 will not:

- Build a custom HTTP Gateway API.
- Run a server process for capture.
- Automatically push to `main`.
- Let any Agent directly write `content/` or official `data/*.yaml` dashboard files.
- Delete raw captures.
- Fetch, scrape, or archive full URL content.
- Simulate login or scrape Xiaohongshu, WeChat, QQ, or other restricted platforms.
- Replace Phase 2 extraction.

## 6. Capture Types

Supported capture `type_hint` values:

- `link`
- `bookmark`
- `task`
- `event`
- `project_log`
- `note`

The CLI should accept at least:

```bash
python -m scripts.pkb.cli capture --type link --url https://example.com --text "Useful article"
python -m scripts.pkb.cli capture --type task --text "Write Phase 3 TRD"
python -m scripts.pkb.cli capture --type event --text "CUHK registration"
python -m scripts.pkb.cli capture --type project_log --project stablepay --text "Need retrospective"
python -m scripts.pkb.cli process-drop
python -m scripts.pkb.cli validate-captures
```

## 7. Safety Requirements

- `visibility` defaults to `private`.
- Agent adapters may only call `pkb capture` or write JSON into `inbox/drop/<adapter>/`.
- Agent adapters must not directly modify `content/`, `data/*.yaml`, `generated/`, git branches, or remotes.
- Captures are append-only; raw captures must not be deleted by Phase 3 tools.
- URL content is not fetched in Phase 3; only URL, title/text, and user notes are stored.
- Xiaohongshu and similar platforms only store shared URL, title if provided, and user notes.
- No automatic `git push`.
- No automatic promotion into Hugo dashboard data.

## 8. Acceptance Criteria

Phase 3 v3 is acceptable when:

- `python -m scripts.pkb.cli capture --type link --url ... --text ...` writes both raw markdown and monthly JSONL.
- `capture` commands support `link`, `task`, `event`, and `project_log`.
- Duplicate URL captures either do not create duplicate active captures or are marked with `duplicate_of`.
- `process-drop` reads JSON files from `inbox/drop/hermes`, `inbox/drop/openclaw`, and `inbox/drop/workbuddy`.
- `validate-captures` verifies required capture fields.
- Hugo build does not require Hermes, OpenClaw, WorkBuddy, network access, or any Agent being online.
- PRD/TRD explicitly state that Phase 3 v3 does not self-develop a Gateway API.

## 9. References

- Hermes cron and gateway behavior: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md
- Hermes Desktop docs: https://hermes-agent.nousresearch.com/docs/user-guide/desktop
- Hermes install/docs overview: https://hermes-agent.nousresearch.com/docs/
- OpenClaw Windows Hub docs: https://docs.openclaw.ai/windows
- OpenClaw Windows daemon/auto-start notes: https://github.com/clawdbot/clawdbot/blob/main/docs/platforms/windows.md
- Work Buddy docs example: https://docs.work-buddy.ai/
- Tencent WorkBuddy quickstart/privacy examples: https://www.workbuddy.ai/docs/workbuddy/Quickstart and https://www.workbuddy.ai/document/privacy-policy
