# Phase 3 TRD v3: Capture Adapter Technical Design

Status: Draft  
Owner: Bubblevan  
Phase: 3  
Last updated: 2026-07-19

## 1. Architecture Name

**Personal Knowledge Capture Adapter Layer**

## 2. System Flow

```text
Hermes / OpenClaw / WorkBuddy / future Agent
  -> local pkb capture CLI or inbox/drop/*.json
  -> inbox/raw/YYYY/MM/YYYY-MM-DD.md
  -> data/captures/YYYY-MM.jsonl
  -> Phase 2 extraction
  -> review queue
  -> promote to data/*.yaml or content/*
```

Phase 3 v3 does not include a custom Gateway API. The CLI and drop directories are the integration boundary.

## 3. Directory Contract

```text
schemas/
  capture.schema.json

scripts/pkb/
  __init__.py
  cli.py
  capture.py
  normalize_url.py
  dedupe.py
  process_drop.py

docs/pkb/agent-adapters/
  hermes/SKILL.md
  openclaw/SKILL.md
  workbuddy/prompt-pack.md

inbox/
  raw/YYYY/MM/YYYY-MM-DD.md
  drop/hermes/*.json
  drop/openclaw/*.json
  drop/workbuddy/*.json

data/captures/
  YYYY-MM.jsonl
```

## 4. Capture Schema

Every capture includes:

- `capture_id`
- `created_at`
- `source_agent`
- `source_platform`
- `source_channel`
- `source_message_id`
- `type_hint`
- `text`
- `urls`
- `project_hint`
- `topics`
- `visibility`
- `dedupe_key`
- `content_sha256`
- `status`
- `raw.original_text`

`visibility` defaults to `private`. `status` is usually `new`; duplicate records can use `duplicate`.

## 5. CLI Design

### Capture

```bash
python -m scripts.pkb.cli capture --type link --url https://example.com --text "Example"
python -m scripts.pkb.cli capture --type task --text "Write notes"
python -m scripts.pkb.cli capture --type event --text "Registration deadline"
python -m scripts.pkb.cli capture --type project_log --project stablepay --text "Need retrospective"
```

Useful optional flags:

- `--topic <topic>` repeatable
- `--source-agent hermes`
- `--source-platform windows`
- `--source-channel cli`
- `--source-message-id <id>`
- `--visibility private|public`

### Process Drop

```bash
python -m scripts.pkb.cli process-drop
```

Reads JSON objects or arrays from:

- `inbox/drop/hermes/*.json`
- `inbox/drop/openclaw/*.json`
- `inbox/drop/workbuddy/*.json`

Drop files are not deleted. Processed files are tracked by content hash in `data/captures/drop-processed.json`.

### Validate Captures

```bash
python -m scripts.pkb.cli validate-captures
```

Validates `data/captures/*.jsonl` for required fields and simple type constraints. It does not require the external `jsonschema` package.

## 6. Deduplication

Deduplication uses `dedupe_key`:

- For URL captures: normalized first URL.
- For project captures: `project:<project_hint>:<content_sha256>`.
- For other captures: `text:<type_hint>:<content_sha256>`.

When a duplicate is found, the new capture is still appended for auditability but is marked:

```json
{
  "status": "duplicate",
  "duplicate_of": "cap-..."
}
```

## 7. Phase 2 Integration

Raw markdown is written in a Phase-2-friendly marker style:

```markdown
- @link https://example.com Example #topic
- @task Write notes #topic
- @event Registration deadline #topic
- @project stablepay Need retrospective #topic
```

Phase 2 extraction can then process `inbox/raw/**/*.md` in the same style as daily notes.

## 8. Adapter Rules

### Hermes

Hermes should be the default local resident Agent. It calls `python -m scripts.pkb.cli capture ...` and never edits `content/` or official dashboard `data/*.yaml` directly.

### OpenClaw

OpenClaw is a channel adapter for WeChat/QQ or similar IM channels. It either calls the same CLI or writes drop JSON with `source_channel=wechat` or `source_channel=qq`.

### WorkBuddy

WorkBuddy is a manual import/product-reference path. It should produce a copyable capture block or drop JSON. It is not the source of truth and must not modify the repository.

## 9. Security Notes

- No self-hosted custom Gateway API in Phase 3 v3.
- No automatic push to `main`.
- No raw capture deletion.
- No URL scraping.
- No simulated login.
- Default `visibility` is `private`.
- Agent adapters are untrusted input producers.

## 10. External References

- Hermes has CLI/desktop/gateway/cron/skills surfaces suitable for local Agent operation: https://hermes-agent.nousresearch.com/docs/
- Hermes cron can deliver to local files and configured platform targets through the gateway scheduler: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md
- Hermes Desktop shares the same agent core/config/sessions/skills and runs on Windows: https://hermes-agent.nousresearch.com/docs/user-guide/desktop
- OpenClaw Windows Hub provides tray status, launch-at-login, local gateway setup, diagnostics, and Windows node capabilities: https://docs.openclaw.ai/windows
- OpenClaw Windows docs include gateway service and auto-start patterns: https://github.com/clawdbot/clawdbot/blob/main/docs/platforms/windows.md
- WorkBuddy-style products are treated as optional manual import/product references, not trusted Git-first pipeline dependencies: https://docs.work-buddy.ai/ and https://www.workbuddy.ai/docs/workbuddy/Quickstart
