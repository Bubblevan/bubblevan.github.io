# Personal Research Intelligence data layer (M0)

This directory contains the versioned data contract and the small, seed-only
topic/source catalogs. It does not create another PKB: scripts/pkb remains the
capture pipeline, and this layer consumes its sanitized link/bookmark captures.

## Runtime data and privacy

The CLI writes local JSONL under events/ by default. That directory is
gitignored because observations may contain captured text. Avoid checking
captured bodies or browser-derived data into the public site repository.
Fixtures are synthetic and live under scripts/intelligence/fixtures/.

Sensitive browser state is not part of any intelligence record. The bridge
drops credential-bearing fields, removes private URL query parameters, and the
store rejects records that still contain secret-like keys or credential query
parameters.

The store validates each record against schemas/intelligence before writing.
The included validator is an offline Python-standard-library implementation of
the JSON Schema keywords used by these six contracts; unsupported schema
keywords fail closed.

## Storage boundary

- observations-YYYY-MM.jsonl and feedback-YYYY-MM.jsonl are write-once,
  append-only event partitions. A deterministic duplicate ID is ignored.
- sources.jsonl, artifacts.jsonl, and entities.jsonl are materialized
  canonical indexes. Upserts merge set-like fields, sort by ID, write a sibling
  temporary file, then atomically replace the previous index.
- Replaying an observation does not create another observation or another
  artifact relationship.

There is no database, vector index, model call, network request, browser
automation, or scheduled collector in M0.
