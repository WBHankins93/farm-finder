# ADR-0002: Store state evidence outside Git behind one release contract

**Status:** Accepted
**Date:** 2026-07-15
**Deciders:** FarmFinder owner

## Context

The first Alabama and Texas staging releases added roughly 440,000 lines. More than
95% came from pretty-printed raw JSON, duplicate JSON mirrors of CSV tables, and
request logs. Repeating that layout for fifty states would make review noisy, create
ambiguous representations, and cause regenerated evidence to dominate Git history.

FarmFinder still needs immutable observations and raw source provenance for audit,
identity review, corrections, licensing, and reproducibility.

## Decision

Every state commits the seven files defined by
`01-database/state-release-contract.md`. Detailed evidence and deterministic review
outputs are compressed and stored under one private, versioned S3-compatible release
prefix. The manifest binds repository files and external artifacts by SHA-256,
version ID, row count, and schema version.

The current evidence bundle uses compressed CSV and JSONL. Parquet may replace the
observation encoding after the typed database ingestion path is available.

## Options considered

### Keep all CSV and JSON in Git

Easy to inspect locally, but duplicates the same logical tables, produces enormous
diffs, and scales poorly across repeated state updates.

### Commit compressed binary evidence

Reduces checkout size but Git cannot review binary contents usefully and historical
versions still accumulate in the repository.

### Versioned object storage with a committed manifest

Preserves immutable evidence while keeping reviews small and maintaining one explicit
source-of-truth contract. This option was selected.

## Consequences

- State PRs become reviewable and structurally identical.
- Raw evidence remains private and restorable by checksum and object version.
- CI can validate repository metadata without duplicating evidence in Git.
- Promotion requires a managed durable copy; local S3-compatible staging alone is
  insufficient.
- Artifact retrieval is required for full forensic review.
