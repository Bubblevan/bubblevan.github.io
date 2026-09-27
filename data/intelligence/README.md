# Personal Research Intelligence data layer (M1)

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
Its local validator supports the keywords used by the seven current contracts;
unsupported schema keywords fail closed. Connector runs use the dependencies in
requirements-intelligence.txt; all fixture tests remain offline.

## Storage boundary

- observations-YYYY-MM.jsonl and feedback-YYYY-MM.jsonl are write-once,
  append-only event partitions. A deterministic duplicate ID is ignored.
- sources.jsonl, artifacts.jsonl, and entities.jsonl are materialized
  canonical indexes. Upserts merge set-like fields, sort by ID, write a sibling
  temporary file, then atomically replace the previous index.
- Replaying an observation does not create another observation or another
  artifact relationship.

RSS/Atom and GitHub Releases are the only pull connectors. They share one HTTP
transport and atomically stored checkpoints under runtime/connectors/. The
runtime/ and events/ directories are gitignored. Checkpoints advance only after
observations and their candidate artifacts have been persisted. Local runs are
one-shot; there is no daemon or scheduled collector. The optional Semantic
Scholar resolver uses exact DOI/arXiv identifiers and never auto-merges title
matches.
