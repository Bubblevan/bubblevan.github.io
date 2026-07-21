# Phase 4 PRD v1: Review and Draft Automation Layer

Status: Draft
Owner: Bubblevan
Phase: 4
Last updated: 2026-07-19

## 1. Background

Phase 3 introduced the Personal Knowledge Capture Adapter Layer. Hermes, OpenClaw, WorkBuddy, and future agents can append private captures into:

- `inbox/raw/YYYY/MM/YYYY-MM-DD.md`
- `data/captures/YYYY-MM.jsonl`

This solved ingestion, but it does not decide what should become a dashboard item, project retrospective, docs page, or blog draft. Phase 4 starts after capture and before publication.

The product boundary is:

```text
Capture can be automatic.
Review and draft can be assisted.
Publish must be explicit.
```

## 2. Product Decision

Phase 4 is not an automatic publishing layer. It is a review and draft automation layer.

It may read captures, cluster them, summarize them, and produce review notes or draft material. It must not silently modify official Hugo `content/` pages or public dashboard `data/*.yaml`.

## 3. Goals

1. Import historical WeChat-style memo blobs into Phase 3 drop files.
2. Generate a readable capture review queue from `data/captures/*.jsonl`.
3. Classify captures into candidate actions:
   - keep raw
   - promote later
   - project retrospective
   - blog/docs draft candidate
   - dashboard candidate
4. Generate private draft material under `inbox/` for human review.
5. Keep Hugo build independent from Hermes Gateway, WeChat, OpenClaw, WorkBuddy, or network availability.

## 4. Non-Goals

Phase 4 v1 will not:

- Automatically publish blog posts.
- Automatically update official `data/*.yaml`.
- Automatically push to `main`.
- Crawl URL contents.
- Simulate login to Xiaohongshu, Zhihu, WeChat, QQ, or any restricted platform.
- Treat WorkBuddy output as a source of truth.

## 5. User Stories

### Historical WeChat Migration

As Bubblevan, I can paste or export a long WeChat memo into a local text file and run:

```bash
python -m scripts.pkb.cli import-wechat --file inbox/imports/wechat-2026-07-19.txt
```

The system writes a JSON drop file under `inbox/drop/hermes/` or another selected adapter directory. Running `process-drop` then appends standard captures.

### Daily Review

As Bubblevan, I can run:

```bash
python -m scripts.pkb.cli review-captures --since today
```

The system prints a concise queue and writes a markdown review note under `inbox/review/`.

### Draft Candidate

As Bubblevan, I can run:

```bash
python -m scripts.pkb.cli draft --topic agentic-rl --from today --dry-run
```

The system renders a draft outline from matching captures without writing official Hugo content.

## 6. Safety Requirements

- `visibility=private` remains the default.
- Review output is written to `inbox/review/` and safe JSON files.
- Draft output is written to `inbox/drafts/`, not `content/`.
- Agents may request a draft, but publishing requires explicit confirmation.
- URL records store only URL, user note, and user-provided title text.
- Xiaohongshu records keep share URL, title snippet, and user note only.
- Raw captures and drop files are not deleted.

## 7. Acceptance Criteria

- `import-wechat` can split a mixed WeChat memo containing URLs, Xiaohongshu share text, notes, tasks, and events into drop JSON.
- `process-drop` can ingest the generated drop JSON.
- `review-captures` can generate a readable markdown review file.
- `draft --dry-run` can render an outline without writing `content/`.
- Hugo build passes without any agent running.
- Phase 4 docs clearly state that official publication is out of scope without explicit confirmation.

