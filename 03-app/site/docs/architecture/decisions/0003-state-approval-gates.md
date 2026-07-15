# ADR-0003: Consolidated state approval gates

**Status:** Superseded by ADR-0004
**Date:** 2026-07-15
**Deciders:** FarmFinder owner

## Context

FarmFinder needs detailed provenance without asking a reviewer to reconcile seven
files by hand. Coverage collection, record verification, release approval, and
canonical promotion were also being described with the ambiguous word “complete.”
Large generated research files previously made a draft pull request exceed 400,000
added lines.

## Decision

The seven-file state contract remains the storage boundary, not the human workflow.
Automation reads and reconciles all seven files and produces one status report with
six gates: contract, coverage, record verification, managed evidence, approval, and
canonical promotion. The human review surface is `completion-report.md`; approval is
recorded inside `release-manifest.json` against a fingerprint of every committed
input and immutable evidence object.

The lifecycle uses only these precise states:

1. `researching`
2. `collected`
3. `coverage_reviewed`
4. `record_verified`
5. `approved`
6. `promoted`

No state may be `approved` while any candidate remains in QA, while evidence remains
only in local staging, or without an approver, timestamp, and matching release
fingerprint. No state may be `promoted` unless the canonical manifest contains it.

Every prospective pull request is assessed before publication. CI rejects more than
20 changed files, more than 15,000 additions, non-contract state files, or prohibited
generated artifacts. A deliberately large reviewed change requires the explicit
`large-reviewed-change` label.

## Options considered

### Review every contract file manually

Low implementation cost but high reviewer burden and a high risk of count, hash, or
identity inconsistencies being missed.

### Commit one flattened review workbook

Convenient to browse but creates another competing source of truth and repeats data
already present in the entity table and evidence objects.

### Generate one approval status from governed inputs

Keeps provenance complete, reduces human review to one summary and one decision, and
allows CI to prove that the summary matches the underlying release.

## Consequences

- “Coverage complete” can no longer be confused with “approved” or “canonical.”
- Reviewers do not need to inspect seven files independently.
- Any data or evidence change invalidates the recorded approval fingerprint.
- State data and pipeline changes should use separate, narrowly scoped commits and PRs.
- Large legitimate changes require an explicit exception rather than passing silently.
