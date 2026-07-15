# State release contract

> Contract version 1 · Effective 2026-07-15

## Purpose

FarmFinder must support fifty state research programs without creating fifty
different schemas or treating generated diagnostics as competing sources of truth.
Each state therefore commits exactly seven small contract files under
`research/state-expansions/<STATE>/` and stores detailed evidence in private,
versioned object storage.

## Repository authority

`entities.csv` is the only committed staged entity table for a state.
`manual-decisions.csv` is the only mutable human decision input. The state is not
canonical or public until an explicit promotion release updates the global source
of truth.

The committed state directory contains only:

- `state-config.json`
- `sources.json`
- `manual-decisions.csv`
- `entities.csv`
- `county-coverage.csv`
- `completion-report.md`
- `release-manifest.json`

JSON mirrors of CSV tables are prohibited. Derived QA, identity, exclusion, and
geography files are prohibited in the state directory because the release process
can regenerate them from immutable observations and manual decisions.

## Private evidence bundle

Every manifest points to one immutable prefix:

```text
state-expansions/TX/tx-coverage-reviewed-2026-07-15/
  observations.csv.zst
  raw-source-records.jsonl.zst
  request-log.jsonl.zst
  qa-queue.csv.zst
  identity-review.csv.zst
  exclusions.csv.zst
  geography-errors.jsonl.zst
```

`.zst` means Zstandard compression. JSONL stores one JSON record per line. The
observation table currently remains CSV before compression to avoid adding a
Parquet runtime dependency; PostgreSQL ingestion may replace it with typed Parquet
later without changing the repository contract.

Every artifact entry records its role, object key, object version, checksum,
compressed byte size, row count, privacy, and content type. An artifact key is
immutable: changed bytes require a new release ID.

## Lifecycle

States progress through `researching`, `collected`, `coverage_reviewed`,
`record_verified`, and `promoted`. Completing the three collection passes permits
`coverage_reviewed`; it does not imply that every candidate has cleared QA.

## Required checks

The shared validator enforces the seven-file allowlist, a five-megabyte state-folder
budget, one schema version, state and county consistency, three-pass source coverage,
unique IDs and identity keys, promotion fields, evidence grades, manual-decision
provenance, count reconciliation, artifact hashes, immutable object versions, and
the unchanged LA/MS canonical boundary.
