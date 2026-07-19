# AGENTS.md

## Project

This repository is a Hugo + Hextra static site for Bubblevan's personal operating dashboard, knowledge base, project retrospectives, papers, blog, daily notes, and career assets.

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
