---
title: "RI-M7 Social Sources"
---

# RI-M7 — Social & Browser-Assisted Source Acquisition

## Acquisition policy

Priority is official API, native RSS/Atom, a configured RSSHub feed, browser-assisted acquisition, then manual URL import. RSSHub output uses the existing `rss-atom` connector and requires explicit `RSSHUB_BASE_URL`; no public RSSHub endpoint is assumed. A Zhihu author feed must pass a feed probe and human approval before it becomes an active source.

Browser acquisition is interactive and uses only an already-open adopted Chrome tab through `chrome-use`. Daily scheduled acquisition skips interactive sources. A run is bounded to 3 sources, 10 items per source, 20 page visits, and concurrency 1. Login pages and security challenges stop the source without retries or bypass attempts.

## Privacy and provenance

The collector stores canonical public object IDs, URLs, titles, body text, authors, timestamps, and explicit outbound links. It does not store authentication data, Chrome profile paths, raw browser output, or raw snapshots by default. Browser Observation provenance is `retrieval_mode=browser_assisted`, `collector=chrome-use`, `evidence_level=rendered_page`. RSSHub observations retain `retrieval_mode=rss`, `collector=rss-atom`, and `upstream_adapter=rsshub`.

XHS notes materialize as primary `social_post` Artifacts; Zhihu Answers materialize as primary `discussion` Artifacts. Explicitly linked papers, repositories, models, and blogs remain referenced candidates. Optional image extraction is disabled by default and records candidates with `evidence_level=image_extract` only.

## Validation record

This report records browser version and sanitized counts/statuses only; it must not include cookies, account names, browser profile paths, or signed URL parameters.

### Live browser smoke — 2026-09-30

- Browser CLI: chrome-use 1.5.145; the selected Chrome extension relay connected.
- Zhihu Answer: completed; 1 page fetched, 1 new Observation, 7 Artifacts touched. The visible sign-in dialog was closed before extraction. The rendered answer body was readable. JavaScript stayed enabled: chrome-use exposes no page-level script-disable command, and the extension rejected navigation to `chrome://settings`; no Chrome profile settings were changed.
- XHS manual note: completed from the already-open signed page; 1 page fetched, 1 new Observation, 1 Artifact touched. Its URL was canonicalized before entering the private inbox; the signed query was not persisted.
- Approved `tabris` profile subscription: one-item smoke attempted, but the profile route redirected to a login shell and yielded no note links (`dom_changed`, fetched 0). It remains unsynced; no login, CAPTCHA, or challenge was bypassed.
- RSSHub: `RSSHUB_BASE_URL` is not configured; no public RSSHub endpoint is assumed.

### Materialization and retrieval

- After the two successful social captures, graph and feed postprocessing completed. Graph: 6,953 Artifacts, 6,653 Observations, 29 entities, and 17,365 edges. Feed status: revised; no refresh is pending.
- Final post-capture `corpus_hash`: `eb49f587986dc4975146470d1e0539132ad8a05cdffbbcebd72a2b1688e5b347`.
- Sparse/graph retrieval build completed for that hash. The existing Dense manifest still points to the prior corpus and reports `stale`; Dense was not rebuilt.
- Rolling source coverage keeps interactive browser sync separate from scheduled poll counts. Ops currently reports 13 healthy scheduled sources and the `tabris` profile as never successfully synced.
- Privacy scan across 9,064 event, runtime, private-inbox, and local-log files found no signed XHS query, Authorization/Cookie header, or named provider-key assignment.

Offline regression, production Hugo build, and CI results are recorded after final validation below.

### Offline validation — 2026-09-30

- Python unittest discovery: 312 tests passed.
- Python compileall: passed; `git diff --check`: passed (only Git's LF-to-CRLF notices).
- Hugo production build: passed with Hugo 0.153.0; 1,195 pages, 61 non-page files, 2,393 static files, and 29 aliases.
- GitHub Actions: checked after the branch push and reported with the release result.
