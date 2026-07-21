# Phase 1 Information Architecture RFC

Status: Draft  
Owner: Bubblevan  
Scope: Hugo/Hextra content architecture only  
Last updated: 2026-07-19

## 1. Background

The current site is a Hugo static site using the Hextra theme. It already has several meaningful content sections:

- `content/blog`: chronological essays, experiments, project logs, research notes, and personal reflections.
- `content/daily`: daily markdown records, currently acting as a mixed journal and raw capture space.
- `content/docs`: long-term knowledge notes, including research, self-study, undergraduate notes, and web development.
- `content/papers`: paper reading notes organized by research topic.
- `content/leetcode`: algorithm practice notes.
- `content/showcase`: project display pages.

The site has useful foundations: a custom home layout, custom blog list layout, daily timeline layout, tag cloud, breadcrumb partials, and image archiving scripts. The problem is not that the site lacks a theme or CMS. The problem is that content intent, review workflow, and presentation surfaces are not yet explicit enough.

Phase 1 should therefore keep the system static and Markdown-first. It should turn the current site into a better-organized personal knowledge and project asset system without adding a backend, database, agent runtime, WeChat bot, RSS pipeline, or external service.

## 2. Goals

Phase 1 should answer these questions:

1. What belongs in `blog`, `docs`, `daily`, `papers`, `leetcode`, and project-related sections?
2. How should raw daily records become discoverable without prematurely automating extraction?
3. How should project showcase pages become useful for retrospectives, resume material, and interview preparation?
4. What structured data should the homepage dashboard read from?
5. Which frontmatter fields should be introduced now so later scripts and agents can rely on stable metadata?

Phase 1 should produce:

- A clear content taxonomy.
- A lightweight frontmatter convention.
- A homepage dashboard data model.
- A project asset model for StablePay as the first example.
- A migration plan that preserves existing URLs where possible.
- Acceptance criteria for future implementation PRs.

## 3. Non-Goals

Phase 1 will not:

- Replace Hugo or Hextra.
- Clone or vendor external open-source projects.
- Add OpenClaw, WeChat, ClawBot, Telegram, or gateway integration.
- Add LLM extraction.
- Add semantic search.
- Add a database.
- Build private reminder delivery.
- Automatically rewrite all historical posts.

Historical content may be gradually normalized later. Phase 1 should define the target shape and apply it to a small, representative slice.

## 4. Core Principle

The site should use different storage surfaces for different content lifecycles:

```text
capture idea or event
  -> daily or inbox note
  -> structured bookmark/task/project/knowledge item
  -> long-term docs or project asset
  -> blog output or career-facing STAR card
```

Hugo/Hextra is responsible for display. Markdown and Git are responsible for durable knowledge and project history. YAML/JSON data files are responsible for dashboard cards and queryable state. Agents and gateway integrations can be added later, but they should consume the same schemas instead of redefining the system.

## 5. Content Taxonomy

### 5.1 `daily`

Purpose: low-friction chronological record.

Use for:

- What happened today.
- Short observations.
- Raw links worth remembering.
- Quick task notes.
- Meeting notes.
- Temporary project logs.
- Life records.

Do not use as the final home for:

- Stable technical explanations.
- Evergreen learning notes.
- Mature project case studies.
- Interview answers.
- Curated resource lists.

Recommended rule:

Daily is the inbox-like memory of the day. It is allowed to be messy, but it should contain enough markup for later extraction.

Phase 1 convention:

```markdown
## Log

## Links

- [title](https://example.com) #agent #github

## Tasks

- [ ] Follow up something by 2026-07-25

## Events

## Project Notes
```

### 5.2 `blog`

Purpose: time-bound public output.

Use for:

- A technical journey.
- A project milestone.
- A debugging story.
- A research or learning phase summary.
- A decision made under a specific historical context.

Do not use for:

- Canonical knowledge that should be rewritten when outdated.
- Raw daily fragments.
- Project facts that should be maintained over time.

Decision rule:

If future corrections should replace the old text, put it in `docs`. If the historical reasoning should remain visible, put it in `blog`.

### 5.3 `docs`

Purpose: evergreen knowledge base.

Use for:

- Current best understanding.
- Stable technical explanations.
- Learning paths.
- Reusable implementation notes.
- Architecture principles.
- Debugging playbooks.

Docs can reference blog posts as historical evidence, but docs should not be written as a diary.

### 5.4 `papers`

Purpose: research-paper reading notes.

Use for:

- Paper summaries.
- Method comparisons.
- Dataset and benchmark notes.
- Research taxonomy.

Long-term synthesis can either live in `docs/research/*` or as index pages inside `papers/*`. Phase 1 should keep `papers` as the paper-note store and use cross-links from `docs/research` when a concept becomes evergreen.

### 5.5 `leetcode`

Purpose: interview algorithm practice.

Use for:

- Problem notes.
- Patterns.
- Code templates.
- Review status.

It belongs near career preparation, but it should remain separate from project STAR cards because the retrieval mode is different.

### 5.6 Project Assets

The current `showcase` section mixes public display and project memory. Phase 1 should introduce a stronger project asset model.

Recommended direction:

- Introduce `content/projects/*` as the durable project asset home.
- Let `showcase` disappear after migration if old public routes are no longer needed.

Use project assets for:

- Project background.
- Architecture.
- Personal contribution.
- Key decisions.
- Evidence and metrics.
- Retrospectives.
- Links to blog posts and docs.
- Interview-ready summaries.

### 5.7 Career Assets

Career content is a projection of project assets, not the source of project truth.

Recommended future section:

- `content/career/project-cards`
- `content/career/star`
- `content/career/interview`
- `content/career/resumes`

Phase 1 can define the model but does not need to publish all career content publicly.

## 6. Recommended Directory Shape

Target shape:

```text
content/
  blog/
  daily/
  docs/
  papers/
  leetcode/
  projects/
    stablepay/
      _index.md
      architecture.md
      decisions/
      evidence/
      retrospectives/
    yuedong-sports/
    archaeological-reports/
  showcase/
  career/
    project-cards/
    star/
    interview/

data/
  dashboard.yaml
  reminders.yaml
  bookmarks.yaml
  sources.yaml
  projects.yaml

archetypes/
  blog.md
  daily.md
  doc.md
  project.md
  project-decision.md
  project-retrospective.md
  star.md

planning/
  IA-RFC-v1.md
  PRD-v1.md
  TRD-v1.md
```

Phase 1 does not have to fully migrate all files. It should create the shape and migrate one project deeply.

## 7. Frontmatter Convention

### 7.1 Common Fields

All new or touched content should use:

```yaml
---
schema: bubblevan/v1
id: stable-unique-id
content_kind: blog
title: Example Title
date: 2026-07-19
updated: 2026-07-19
status: draft
visibility: public
summary: One sentence summary.
topics: []
projects: []
aliases: []
review:
  last_reviewed:
  next_review:
provenance:
  captured_via: manual
  capture_id:
---
```

Field meanings:

- `schema`: metadata contract version.
- `id`: stable identifier for scripts and future agents.
- `content_kind`: content type, such as `blog`, `daily`, `doc`, `paper`, `project`, `project_decision`, `retrospective`, `bookmark`, `star`.
- `status`: `seed`, `draft`, `published`, `archived`, or `private`.
- `visibility`: display intent, usually `public` or `private`. This is not a security boundary in a public repository.
- `topics`: domain tags such as `openclaw`, `agent`, `backend`, `vla`.
- `projects`: related project ids such as `stablepay`.
- `review`: lightweight spaced-review metadata.
- `provenance`: future-compatible capture metadata.

### 7.2 Daily

```yaml
---
schema: bubblevan/v1
id: daily-20260719
content_kind: daily
title: 07-19
date: 2026-07-19
status: published
visibility: public
summary:
topics: []
projects: []
---
```

### 7.3 Blog

```yaml
---
schema: bubblevan/v1
id: blog-20260607-stablepay-onboard
content_kind: blog
title: StablePay Onboarding Notes
date: 2026-06-07
updated: 2026-06-07
status: published
visibility: public
summary: A historical note about StablePay onboarding and OpenClaw integration.
topics:
  - openclaw
  - payment
projects:
  - stablepay
---
```

### 7.4 Doc

```yaml
---
schema: bubblevan/v1
id: doc-backend-rate-limit-baseline
content_kind: doc
title: Rate Limit Baseline Design
date: 2026-07-19
updated: 2026-07-19
status: seed
visibility: public
summary: Current best understanding of rate limit baseline design.
topics:
  - backend
  - rate-limit
projects:
  - stablepay
review:
  last_reviewed: 2026-07-19
  next_review: 2026-08-19
---
```

### 7.5 Project Home

```yaml
---
schema: bubblevan/v1
id: project-stablepay
content_kind: project
title: StablePay
date: 2026-03-11
updated: 2026-07-19
status: active
visibility: public
summary: Payment and agent gateway project.
topics:
  - payment
  - agent
  - backend
project:
  role: Backend / Agent Infrastructure
  stage: active
  highlights: []
  tech_stack: []
  repository:
  demo:
---
```

### 7.6 Project Decision

```yaml
---
schema: bubblevan/v1
id: decision-stablepay-payment-idempotency
content_kind: project_decision
title: Payment Idempotency Design
date: 2026-07-19
status: draft
visibility: public
projects:
  - stablepay
decision:
  status: proposed
  context:
  options: []
  choice:
  consequences: []
---
```

### 7.7 Project Retrospective

```yaml
---
schema: bubblevan/v1
id: retro-stablepay-rate-limit-429
content_kind: retrospective
title: Rate Limit 429 Investigation
date: 2026-07-19
status: draft
visibility: public
projects:
  - stablepay
retro:
  situation:
  task:
  action:
  result:
  evidence: []
  lessons: []
---
```

### 7.8 STAR Card

```yaml
---
schema: bubblevan/v1
id: star-stablepay-rate-limit-debug
content_kind: star
title: Debugging Rate Limit Regression in StablePay
date: 2026-07-19
status: draft
visibility: private
projects:
  - stablepay
career:
  target_roles:
    - backend
    - agent-engineer
  competencies:
    - troubleshooting
    - system-design
    - observability
star:
  situation:
  task:
  action:
  result:
  metrics: []
  followups: []
---
```

## 8. Homepage Dashboard Read Model

Phase 1 should keep the dashboard static and data-file driven. It can read from `data/*.yaml` and selected content sections.

Recommended modules:

1. Profile summary: existing About Me content.
2. Today / soon: public-safe reminders from `data/reminders.yaml`.
3. Recent daily: latest `daily` entries.
4. Recent knowledge updates: latest `docs` and `papers`.
5. Project focus: selected items from `data/projects.yaml` or `content/projects`.
6. Recommended sources: curated source list from `data/sources.yaml`.
7. Bookmarks to revisit: selected public-safe items from `data/bookmarks.yaml`.
8. Interview preparation: links into `career` or project STAR material.

Suggested `data/reminders.yaml`:

```yaml
- id: reminder-cuhk-registration
  title: CUHK registration follow-up
  due: 2026-08-01
  status: todo
  visibility: public
  topics:
    - school
```

Suggested `data/bookmarks.yaml`:

```yaml
- id: bookmark-hextra
  title: Hextra
  url: https://github.com/imfing/hextra
  saved_at: 2026-07-19
  status: active
  revisit_at: 2026-08-19
  visibility: public
  topics:
    - hugo
    - site
  notes: Theme currently used by this site.
```

Suggested `data/sources.yaml`:

```yaml
- id: source-rsshub
  title: RSSHub
  url: https://github.com/DIYgod/RSSHub
  type: github
  weight: 0.8
  topics:
    - rss
    - automation
```

Suggested `data/projects.yaml`:

```yaml
- id: stablepay
  title: StablePay
  url: /projects/stablepay/
  status: active
  role: Backend / Agent Infrastructure
  readiness:
    facts: 0.6
    architecture: 0.4
    evidence: 0.3
    star: 0.2
  topics:
    - payment
    - openclaw
    - backend
```

## 9. Phase 1 Implementation Plan

### Step 1: Freeze the Content Rules

Create a short published or private note that defines:

- Daily is chronological capture.
- Blog is historical output.
- Docs is evergreen knowledge.
- Papers is paper reading.
- Projects is durable project memory.
- Career is project-derived interview material.

### Step 2: Add Archetypes

Add or update Hugo archetypes for:

- `blog`
- `daily`
- `doc`
- `project`
- `project-decision`
- `project-retrospective`
- `star`

These archetypes should embed the common frontmatter fields.

### Step 3: Create Static Data Files

Add:

- `data/reminders.yaml`
- `data/bookmarks.yaml`
- `data/sources.yaml`
- `data/projects.yaml`

Start with 3 to 5 hand-written entries. Do not automate yet.

### Step 4: Build Homepage Partials

Split `layouts/hextra-home.html` into dashboard-oriented partials:

- `layouts/partials/home/profile.html`
- `layouts/partials/home/reminders.html`
- `layouts/partials/home/recent-daily.html`
- `layouts/partials/home/recent-knowledge.html`
- `layouts/partials/home/project-focus.html`
- `layouts/partials/home/recommended-sources.html`
- `layouts/partials/home/bookmarks.html`

Keep the first screen useful. Avoid a marketing landing page.

### Step 5: Create `content/projects`

Add `content/projects/_index.md`.

Migrate or copy one project deeply, preferably StablePay:

```text
content/projects/stablepay/
  _index.md
  architecture.md
  decisions/
  evidence/
  retrospectives/
```

The old showcase pages do not need to remain if those routes are intentionally retired.

### Step 6: Define Career Projection

Create only one or two initial career files:

```text
content/career/project-cards/stablepay.md
content/career/star/stablepay-rate-limit-debug.md
```

These should be marked `visibility: private` unless you intentionally want them published. If the repository is public, genuinely private content should stay outside the repository or be encrypted.

### Step 7: Validate Manually

Phase 1 can use a lightweight validation checklist before any script exists:

- New content has `schema`, `id`, `content_kind`, `date`, `status`, and `visibility`.
- Project-related pages include `projects`.
- Public pages do not contain private reminders or sensitive interview notes.
- Existing important URLs remain available.
- Hugo build succeeds.

## 10. Migration Strategy

Use a gradual migration, not a bulk rewrite.

Recommended order:

1. Add this RFC and agree on the model.
2. Add archetypes and data files.
3. Add homepage dashboard partials.
4. Create `content/projects/stablepay` as the first complete project bundle.
5. Link existing StablePay blog posts from the project page.
6. Keep `showcase` as an index during transition.
7. Normalize frontmatter only when touching a file for real work.

Do not rename every historical daily file in Phase 1. That will create noise without improving the architecture.

## 11. Open Questions

1. Should `career` be public, hidden from menus, or kept outside the public repository?
2. Should `showcase` remain the public portfolio route while `projects` becomes the richer internal route?
3. Should reminders in `data/reminders.yaml` be public-safe only, with private reminders kept elsewhere?
4. Should `papers` remain separate from `docs/research`, or should paper notes be folded into a single research knowledge tree over time?
5. What is the minimum acceptable homepage dashboard for the first implementation PR?

## 12. Acceptance Criteria

Phase 1 is complete when:

- The content taxonomy is documented and understandable.
- New frontmatter conventions are documented and represented in archetypes.
- Static data files exist for dashboard modules.
- The homepage can render at least three dashboard modules from content or data.
- StablePay has a non-empty project asset page.
- The old `showcase` route policy is explicit: either retired intentionally or preserved by a separate compatibility task.
- Hugo build succeeds.
- No backend, database, external agent, or WeChat integration is required.

## 13. Later Phase Handoff

Phase 2 should consume this RFC as its contract. Its job is to add local scripts that extract tasks, links, events, and project notes from daily or inbox markdown into the Phase 1 schemas.

Phase 3 should add gateway and WeChat/OpenClaw capture without changing the public content model.

Phase 4 should add reminders, revisit scheduling, recommendation ranking, and richer interview-card generation.
