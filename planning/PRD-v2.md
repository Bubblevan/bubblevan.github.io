# Phase 2 PRD: Local Extraction and Review Pipeline

Status: Draft  
Owner: Bubblevan  
Phase: 2  
Last updated: 2026-07-19

## 1. Problem

Phase 1 established the site as a Markdown-first personal knowledge and project asset system. It added `projects`, `career`, dashboard data files, archetypes, and a shared `content_kind` convention.

The remaining problem is operational: daily notes still contain mixed information that is easy to forget. Links, tasks, project notes, and event reminders can appear in `content/daily`, but they do not yet become structured records for the dashboard, project assets, or later review.

Phase 2 should make daily notes extractable without introducing a backend, database, WeChat bot, or LLM dependency.

## 2. Goals

1. Add local scripts that validate Phase 1 metadata and data files.
2. Extract explicitly marked items from daily or inbox markdown into JSON review files.
3. Keep generated extraction output traceable to the source file and line.
4. Prepare a human review queue before anything is promoted into `data/*.yaml` or `content/projects`.
5. Create a foundation for later LLM extraction without requiring it now.

## 3. Non-Goals

Phase 2 will not:

- Add OpenClaw, WeChat, gateway, Telegram, or webhook input.
- Add a database.
- Add semantic search or embeddings.
- Let scripts directly rewrite historical daily notes.
- Auto-promote generated items into public pages without review.
- Depend on external network access.
- Require an LLM for the first working version.

## 4. Users

Primary user: Bubblevan.

The workflow should support:

- Writing daily notes quickly.
- Marking useful fragments with light syntax.
- Running one local command to extract structured items.
- Reviewing generated JSON before promotion.
- Keeping project/career/dashboard data aligned with the content model.

## 5. User Stories

1. As the site owner, I want to run a validator so I can know whether new project/career content follows the Phase 1 schema.
2. As the site owner, I want to write `@task` in daily notes so reminders can be captured without manually editing `data/reminders.yaml`.
3. As the site owner, I want to write `@link` in daily notes so interesting resources are not lost.
4. As the site owner, I want to write `@project stablepay ...` so project notes can later become retrospectives or evidence.
5. As the site owner, I want extracted items to include source file and line number so I can audit every generated record.

## 6. Explicit Capture Syntax

Phase 2.1 supports these explicit markers:

```markdown
@task 2026-07-30 Write StablePay rate-limit root cause note #stablepay #backend
@link https://github.com/imfing/hextra Hextra theme reference #hugo #site
@event 2026-08-01 CUHK registration follow-up #school
@project stablepay K6 baseline result still needs final evidence table #backend
```

Rules:

- Markers may appear in any markdown file, but the default target is `content/daily`.
- A marker owns one physical line only.
- Topics are parsed from `#topic`.
- Each extracted item includes a deterministic `capture_id`.
- Extractor output is JSON. It does not modify source markdown.

## 7. Outputs

Default extraction output:

```text
generated/extraction/YYYY-MM-DD.json
```

Each item should include:

- `capture_id`
- `type`
- `source_path`
- `line`
- `raw`
- `text`
- `topics`
- type-specific fields such as `url`, `due`, `event_date`, `project_id`
- `confidence`

## 8. Validation Scope

The validator should check:

- Duplicate frontmatter `id`.
- Required fields for files using `schema: bubblevan/v1`.
- Allowed `content_kind` values.
- `projects` references point to known `data/projects.yaml` ids.
- `data/projects.yaml` has unique project ids.
- `data/bookmarks.yaml`, `data/reminders.yaml`, and `data/sources.yaml` may be empty.
- Private visibility is reported as a warning when it appears under public `content`.

Phase 2.1 should avoid forcing all historical posts to adopt new metadata. It should validate files that opt into `schema: bubblevan/v1` and the newly introduced `content/projects` and `content/career` areas.

## 9. Acceptance Criteria

Phase 2.1 is acceptable when:

- `python -m scripts.kb validate` runs locally and returns non-zero only on schema errors.
- `python -m scripts.kb extract <markdown-file>` emits JSON extraction output.
- Extracted items preserve source path and line number.
- Scripts use only Python standard library.
- Scripts do not mutate content files.
- Hugo build remains independent from extraction.
- Documentation explains the workflow clearly enough for future sub-agents.

## 10. Future Extensions

Phase 2 includes:

- Review queue rendering.
- Promote command that writes approved `task`, `event`, and `link` items to `data/*.yaml`.
- Public dashboard promotion as an intentional operator decision.
- Local temporary reviewed state in `generated/reviewed.json`.

Future extensions can add:

- Dashboard read-model builder.
- LLM extraction behind an explicit flag.
- Tests with fixture markdown files.

Phase 3 can reuse the same extraction schema for gateway and WeChat captures.
