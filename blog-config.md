# Bubblevan blog configuration

This file adapts `bubblevan-blog-skills` to this Hugo repository. Private and paid writing material belongs under the ignored `state_dir`; it must not be copied into public article bodies.

## Site adapter

- `content_root`: `content/blog`
- `article_glob`: `content/blog/**/*.md`
- `article_url_prefix`: `/blog/`
- `asset_root`: `static/blog`
- `asset_url_prefix`: `/blog/`
- `language`: `zh-cn` with English technical terms and code
- `timezone`: `+0800`
- `writing_rules`: `content/blog/AGENTS.md`
- `today_is_published_when`: front matter `date` is today or earlier
- `future_content`: treat a future `date` as scheduled even when `hugo.toml` enables `buildFuture`

## Article schema

The repository contains both legacy and `bubblevan/v1` articles. Preserve the target article's existing schema unless migration is explicitly approved.

- legacy required fields: `date`, `title`, `authors`, `tags`
- current optional fields: `schema`, `id`, `content_kind`, `updated`, `status`, `visibility`, `summary`, `topics`, `projects`, `aliases`
- standard Hugo lifecycle field: `draft`; use `draft: true` when content must be excluded from ordinary builds, while retaining `status` and `visibility` for the site's metadata model
- accepted description fields: `summary` or `description`
- do not add `categories`, `type`, `weight`, or `related` unless the site's templates actually use them
- filename convention: `YYYY-MM-DD-slug.md`

## Writing contract

- Start from a real event, input, error, log, experiment, or result.
- Separate verified behavior, log-based inference, deliberate design choice, planned work, and unknown information.
- Keep original commands, filenames, error messages, elapsed times, and result counts when they carry evidence.
- Do not invent motivation, performance data, citations, implementation status, reading progress, or project ownership.
- Each section answers one concrete question and records its current result or limitation.
- Prefer plain modern Chinese. Keep technical names and code exact.
- Avoid repeated contrast templates, empty value claims, slogans, and unverifiable superlatives.
- Paid material and credentials remain local-only. Public drafts may keep only redacted source pointers unless separate publication approval is given.

## Local-only state

- `state_dir`: `.blog-state/`
- `source_set`: `${state_dir}/source-set.md`
- `voice_profile`: `${state_dir}/voice-profile.md`
- `content_map`: `${state_dir}/content-map.md`
- `research_dir`: `${state_dir}/research/`
- article-specific state: `${state_dir}/<slug>/`

The entire state directory is ignored by `.gitignore`. A file already tracked by Git is not protected by ignore rules and must be reported before any private workflow continues.
