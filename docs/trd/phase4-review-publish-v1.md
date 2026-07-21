# Phase 4 TRD v1: Review and Draft Automation Layer

Status: Draft
Owner: Bubblevan
Phase: 4
Last updated: 2026-07-19

## 1. Architecture

```text
Phase 3 captures
  -> import helpers
  -> review queue
  -> clustering / candidate actions
  -> inbox review notes
  -> inbox draft notes
  -> explicit Phase 5 publish/promote
```

Phase 4 consumes `data/captures/*.jsonl`. It does not require Hermes, Gateway, WeChat, OpenClaw, WorkBuddy, or network access at build time.

## 2. New Files

```text
docs/prd/phase4-review-publish-v1.md
docs/trd/phase4-review-publish-v1.md

schemas/review.schema.json
schemas/promotion.schema.json

scripts/pkb/import_wechat.py
scripts/pkb/review_captures.py
scripts/pkb/draft_from_captures.py

docs/pkb/agent-adapters/hermes/SKILL.md
```

## 3. Commands

### Import WeChat Memo

```bash
python -m scripts.pkb.cli import-wechat --file inbox/imports/wechat-2026-07-19.txt
```

Options:

- `--adapter hermes|openclaw|workbuddy`
- `--source-channel wechat|qq|desktop|manual`
- `--topic <topic>` repeatable
- `--project <project>`
- `--out <path>`

The command writes a JSON array drop file. It does not append captures directly.

### Review Captures

```bash
python -m scripts.pkb.cli review-captures --since today
```

Options:

- `--since today|YYYY-MM-DD|all`
- `--include-duplicates`
- `--out <path>`

The command writes:

- `inbox/review/YYYY-MM-DD.md`
- `data/review/queue.json`

`queue.json` is valid JSON. Phase 4 does not write JSONL under `data/review/`.

### Draft From Captures

```bash
python -m scripts.pkb.cli draft --topic agentic-rl --from today --dry-run
```

Options:

- `--topic <topic>`
- `--project <project>`
- `--from today|YYYY-MM-DD|all`
- `--dry-run`
- `--out <path>`

Without `--dry-run`, the command writes to `inbox/drafts/`, not `content/`.

## 4. WeChat Import Heuristics

The first version uses deterministic parsing:

- Each URL-bearing line becomes a `link` capture.
- Xiaohongshu share text is preserved as user-provided text and URL only.
- Lines with time/date/reminder wording become `event`.
- Lines with action wording become `task`.
- Lines with project-log wording become `project_log`.
- Other text becomes `note`.

The parser intentionally avoids URL fetching and login-based enrichment.

## 5. Candidate Actions

Review output maps capture types into candidate actions:

- `link` or `bookmark`: bookmark/source candidate.
- `task`: dashboard reminder candidate.
- `event`: schedule candidate.
- `project_log`: project retrospective candidate.
- `note`: keep raw or draft candidate.
- `duplicate`: inspect only.

These are suggestions only. They do not mutate official Hugo data.

## 6. Safety

- Phase 4 must not write official `content/` without explicit publish command design.
- Phase 4 must not write official `data/*.yaml`.
- Phase 4 must not run `git push`.
- Phase 4 must not delete raw captures.
- Phase 4 must not crawl URLs.
- Drafts default to private review locations.

## 7. Validation

Minimum validation commands:

```bash
python -m scripts.pkb.cli import-wechat --file inbox/imports/sample-wechat.txt --out inbox/drop/hermes/sample-phase4-import.json
python -m scripts.pkb.cli process-drop
python -m scripts.pkb.cli validate-captures
python -m scripts.pkb.cli review-captures --since today
python -m scripts.pkb.cli draft --from today --dry-run
```

Then run Hugo:

```bash
hugo
```
