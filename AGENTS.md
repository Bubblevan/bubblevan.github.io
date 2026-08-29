# AGENTS.md

## Project

This repository is a Hugo + Hextra static site for Bubblevan's personal operating dashboard, knowledge base, project retrospectives, papers, blog, daily notes, and career assets.

## Content architecture

- `content/docs/learning/`: model learning notes, CS336, PyTorch, RL, and Flow Matching.
- `content/docs/agent/`: Agent loop, planning, reasoning, and Hello Agent notes.
- `content/docs/harness/`: Agent Runtime / Harness material, including OpenClaw, Pi, Claude Code, Hermes, and dsh.
- `content/docs/embodied/`: embodied intelligence notes.
- `content/docs/full-stack/`: full-stack development notes. The URL slug is intentionally `full-stack`; do not reintroduce `docs/web`.
- Paper reading records belong in top-level `content/papers/`; do not create a parallel `content/docs/papers/` tree.
- `content/docs/context/`, `eval/`, and `systems/` are reserved for future material and should not be created merely as empty navigation sections.

Content placement and the distinction between `docs`, `blog`, `papers`, `projects`, and `daily` are documented in `content/docs/meta/content-rules.md`.

## Hard constraints

- Do not migrate the site to React, Next.js, Vue, Astro, or a CMS.
- Do not install MUI, shadcn/ui, Radix UI, or React dependencies unless explicitly requested.
- Keep the site Markdown-first, Git-first, and statically deployable through Hugo.
- Prefer Hugo partials, data files, shortcodes, and CSS over JavaScript-heavy UI.
- Preserve Hextra compatibility and dark mode.
- Do not modify theme internals unless no override path exists.

## UI direction

For dashboard-style UI work, edit the local Bubblevan UI Kit first:

- `assets/css/components.css`: tokens, card, badge, tag, button, progress, metric, list, empty state.
- `assets/css/dashboard.css`: dashboard/project/styleguide layouts, hero, KPI strip, grids, timeline, link matrix.
- `layouts/partials/components/`: reusable component partials.
- `layouts/partials/dashboard/`: dashboard sections and extraction-backed widgets.
- `layouts/partials/projects/`: project cards, grid, and stats.
- `layouts/_default/styleguide.html` with `content/_styleguide/index.md`: local draft style target.

Use MUI templates only for page composition ideas, shadcn/ui only for component feel, and GitHub Primer only for restrained engineering visual tone. Do not copy external component source.

## Visual style

- Clean technical dashboard.
- White or subtle translucent cards.
- Light borders, soft shadows, 14-18px radius.
- No black 1px hard borders.
- No raw table-like layout.
- Use clear hierarchy: hero, KPI strip, main grid, right rail.
- Chinese page titles are allowed; component labels should be consistent.

## Acceptance criteria

Before finishing a UI task:

- Run Hugo build.
- For UI kit changes, also run `hugo -D` and inspect the local draft styleguide.
- Check desktop, laptop, and mobile layout.
- Confirm dark mode remains readable.
- Confirm dashboard and projects pages share the same card/badge/progress styles.
- Avoid duplicated CSS scattered across templates.

## Agent automation

- Hermes runtime config and installed skills live outside this repo.
- Do not create repo-local Hermes runtime config under `.hermes/`; that path is ignored to avoid confusion.
- Project-side adapter guidance belongs under `scripts/pkb/` or the relevant `docs/harness/` page; do not create a second `docs/pkb` knowledge tree without an explicit decision.
- Capture-style requests should go through `python -m scripts.pkb.cli capture` or JSON drop files under `inbox/drop/<agent>/`.
- Local image/OCR assistance should use the on-demand llama.cpp wrapper in `scripts/local-vision/describe-image.ps1` before adding any long-running vision service.
