# Phase 2 TRD: `scripts/kb` Local Pipeline

Status: Draft  
Owner: Bubblevan  
Phase: 2  
Last updated: 2026-07-19

## 1. Architecture

Phase 2 introduces a local command package:

```text
scripts/kb/
  __init__.py
  __main__.py
  markdown.py
  validate.py
  extract.py
```

It intentionally uses Python standard library only.

```text
Markdown files
  -> validate
  -> extract explicit markers
  -> generated/extraction/*.json
  -> review/promote commands
```

## 2. Commands

### 2.1 Validate

```bash
python -m scripts.kb validate
```

Responsibilities:

- Scan `content/**/*.md`.
- Parse frontmatter delimited by `---`.
- Validate files that use `schema: bubblevan/v1` or live under `content/projects` / `content/career`.
- Detect duplicate `id` values.
- Validate `content_kind` against the allowed set.
- Validate `projects` references against `data/projects.yaml`.
- Validate basic ids in `data/projects.yaml`, `data/bookmarks.yaml`, `data/reminders.yaml`, and `data/sources.yaml`.

Exit codes:

- `0`: no errors.
- `1`: validation errors found.

Warnings do not fail the command.

### 2.2 Extract

```bash
python -m scripts.kb extract content/daily/2026/jul/2026-7-19.md
```

Optional output directory:

```bash
python -m scripts.kb extract content/daily/2026/jul/2026-7-19.md --out generated/extraction
```

Responsibilities:

- Parse explicit one-line capture markers.
- Produce a deterministic JSON file.
- Keep source path and line number.
- Never mutate source markdown.

### 2.3 Review

```bash
python -m scripts.kb review
```

Responsibilities:

- Read `generated/extraction/*.json`.
- Hide items already listed in `generated/reviewed.json`.
- Show capture id, type, text, source, and action.
- Mark `project_log` as `Phase 3 / retrospective` because it is not promoted into `data/*.yaml` in Phase 2.

### 2.4 Promote

```bash
python -m scripts.kb promote <capture_id>
```

Responsibilities:

- Promote `task` and `event` items into `data/reminders.yaml`.
- Promote `link` items into `data/bookmarks.yaml`.
- Mark promoted ids in `generated/reviewed.json`.
- Refuse double promotion unless `--force` is passed.
- Leave `project_log` for the Phase 3 project retrospective flow.

## 3. Explicit Marker Grammar

Phase 2.1 uses a line-oriented grammar:

```text
@task [YYYY-MM-DD] text [#topic...]
@link URL [title/notes...] [#topic...]
@event [YYYY-MM-DD] text [#topic...]
@project PROJECT_ID text [#topic...]
```

Parsing strategy:

- Strip markdown list prefixes such as `- ` or `- [ ]`.
- Detect marker at the beginning of the remaining text.
- Extract topics with `#([A-Za-z0-9_-]+)`.
- Remove topics from `text`.
- Build `capture_id` from source path, line number, and raw line SHA-1.

## 4. JSON Schema Shape

```json
{
  "schema": "bubblevan/extraction/v1",
  "source_path": "content/daily/2026/jul/2026-7-19.md",
  "generated_at": "2026-07-19T12:00:00+08:00",
  "items": [
    {
      "capture_id": "cap-...",
      "type": "task",
      "source_path": "...",
      "line": 12,
      "raw": "@task 2026-07-30 Write note #stablepay",
      "text": "Write note",
      "topics": ["stablepay"],
      "due": "2026-07-30",
      "confidence": 1.0
    }
  ]
}
```

## 5. Data Contracts

Known project ids come from `data/projects.yaml`.

New content metadata should use:

```yaml
schema: bubblevan/v1
id: stable-id
content_kind: project
status: draft
visibility: public
```

`content_kind` is used instead of `kind` because Hugo reserves/deprecates `kind` in frontmatter.

## 6. Privacy Model

Phase 2 scripts do not provide secrecy. Promotion intentionally writes dashboard-facing data as public because this repository is treated as the public site source of truth.

Rules:

- `visibility: private` is metadata only.
- The validator warns about private content under public `content`.
- `promote` writes `visibility: public` by default for `task`, `event`, and `link`.
- The operator is responsible for not promoting content that should stay out of the public repository.
- Truly private reminders or interview material should move outside the public repository or into a private store in later phases.

## 7. Local State

`generated/reviewed.json` is local temporary state used to keep the review queue quiet after promotion. It is not the long-term source of truth and is ignored by Git with the rest of `generated/`.

Long-term state should live in `data/*.yaml`, `content/projects`, or a future private store.

## 8. Implementation Notes

No YAML package is required for Phase 2.1. The parser only needs enough frontmatter and simple YAML-list support for current repository data:

- top-level scalar fields
- top-level list fields
- list item ids in `data/*.yaml`

This is intentionally conservative. If schema complexity grows, a later phase can add PyYAML or a Node-based YAML parser.

## 9. Test Strategy

Manual verification for Phase 2.1:

```bash
python -m scripts.kb validate
python -m scripts.kb extract content/daily/2026/jul/2026-7-19.md
python -m scripts.kb review
```

Expected:

- Validator prints errors/warnings and exits predictably.
- Extractor writes `generated/extraction/<source-stem>.json`.
- Output JSON is deterministic except `generated_at`.

Future tests:

- Add fixtures under `scripts/kb/fixtures`.
- Unit test marker parsing.
- Unit test duplicate id validation.
- Unit test project reference validation.
