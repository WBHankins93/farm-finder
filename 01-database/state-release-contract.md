# National state release contract

> Contract version 2 · Effective 2026-07-15

## Purpose

FarmFinder uses one deterministic collection, cleaning, review, and promotion
process for every state. Collection may be scheduled by geographic region, but
approval and canonical promotion are always state-based.

## Non-deletion policy

A source observation containing a farm name is a durable candidate even when every
other field is empty. Missing geography, products, contact details, website,
corroboration, or operating-status evidence creates a research blocker. It never
creates an exclusion and never authorizes deletion.

An exclusion requires affirmative, cited evidence for exactly one reason:

- `confirmed_nonfarm`
- `confirmed_closed`
- `outside_jurisdiction`
- `duplicate_identity`

Excluded and superseded observations remain in immutable evidence storage. Legal
form, including LLC or corporation, is not itself an exclusion reason. FarmFinder
prioritizes independent and smaller producers during research without silently
discarding a named operation.

## Four committed files

Every state directory contains exactly:

- `state.yaml` — state and county-equivalent configuration, source plan, release
  metadata, evidence pointers, counts, lifecycle, and approval fingerprint.
  Each source in the plan should declare an ingestion `tier` (`candidate`,
  `identity_hint`, or `excluded_source`) per the
  [pipeline enrichment plan](pipeline-enrichment-plan.md); invalid tiers fail
  validation and untiered legacy sources warn until the state is recollected.
- `entities.csv` — the normalized candidate table. It includes both promotion-
  eligible rows and unresolved named candidates. New or touched rows also carry
  the operating-model and public-location classifications defined below.
- `decisions.csv` — append-only corrections, merges, corroborations, and affirmative
  exclusions with evidence references. Corrections supersede earlier decisions;
  they do not erase them.
- `report.md` — generated findings, county-equivalent coverage, unresolved work,
  validation results, and promotion readiness.

`state.yaml` uses the JSON-compatible subset of YAML so the standard Python runtime
can parse it deterministically without YAML tags, anchors, or environment-dependent
coercion.

Raw source records, request logs, immutable observations, and generated QA views are
not committed. They live in versioned managed storage or the staging database and
are referenced by checksum and object version from `state.yaml`. QA queues,
exclusions, identity reviews, and geography diagnostics are derived views, not
additional sources of truth.

## Eligible pipeline handoff

After `coverage_reviewed` validation and complete county coverage, the pipeline may
export rows with `promotion_status=promotion_eligible_reviewed` to a derived
eligible-record handoff. The same run exports a state-scoped `qa-queue.csv` and a
consolidated QA queue for follow-up. Use
`01-database/tools/export_state_pipeline.py` to generate these private artifacts
under `data/exports/state-pipeline/`.

This handoff is not approval, canonical promotion, or `record_verified`. QA rows
remain in `entities.csv`, remain counted in the release, and remain blockers for
record verification and approval. Their presence does not block collection or
eligible handoff for the next state.

## Geography

The shared field is `county_equivalent`. The displayed label is configured per
state: county, parish, borough, census area, or independent city. Census/FIPS codes
provide the stable national identity.

### Operating model and public location

Every new or touched entity should carry an `operating_model` classification:

- `fixed_location_farm` — a farm or producer with a stable production or
  customer-facing location that can be represented as its own public service
  area.
- `market_circuit` — a farm or small producer whose customer-facing operation
  is conducted through recurring farmers markets, fairs, events, or other
  shared/mobile venues rather than a fixed public farm gate.

`market_circuit` is a positive operating-model classification, not an entity
type, evidence grade, or promotion status. Its public location must use
`public_location_classification: market_circuit_service_area`. The public city,
county-equivalent, and any reduced-precision coordinate identify the documented
venue/service area; they must not imply that the venue is the producer or expose
the producer's private address. Venue contact and location may be the legitimate
public path for this model, and venue-based contact/location is never an
exclusion reason or a QA penalty by itself.

The classification changes sorting and display only. It does not waive current
operation, producer-type, product, corroboration, identity, or status evidence
gates. A market-circuit row may therefore retain QA blockers for those other
issues, but a venue-based contact/location gap alone must be resolved through
the documented market/service-area evidence rather than treated as a defect.

Legacy staged rows that predate this field remain valid until their next state
rewrite; consumers should treat a missing value as `fixed_location_farm` only
for backward compatibility, never as evidence that a fixed public farm gate
exists.

### Collector pre-classification boundary

Every new state collector must run its Census place-reference geography pass and
its same-run cross-directory corroboration pass after collection and before
reconciliation or `classify_candidate`. The corroboration pass may merge only
independent observations that agree on identity, contact, and geography; contact
or geography conflicts remain separate and carry a routable QA blocker. This is
mandatory pipeline sequencing: the NC/SC backlog of roughly 3,500 QA rows came
from a collector that skipped these two passes. Website-liveness fetching remains
a post-hoc assistant operation and is not part of collection.

## Lifecycle and review

States progress through `researching`, `collected`, `coverage_reviewed`,
`record_verified`, `approved`, and `promoted`.

- `coverage_reviewed`: every county-equivalent and required source pass has a
  documented result; candidates may remain unresolved.
- `record_verified`: every retained candidate has a disposition and the QA count is
  zero. This does not imply managed-storage approval.
- `approved`: validation, managed immutable evidence, and approval fingerprint pass.
- `promoted`: the approved state release was atomically added to canonical data.

When an already-canonical state is recollected, its staged release remains
`coverage_reviewed` or `record_verified` until a new atomic promotion replaces the
existing slice. `release.canonicalRebuild` binds that work to the current canonical
release ID and row count, accounts for every existing state record as rediscovered,
possible-alias, or baseline-only, and prevents a staged rebuild from falsely
claiming that its new candidates are already canonical.

The reviewer reads `report.md` and the generated status output. Any entity, decision,
evidence checksum, object version, or policy change invalidates prior approval.

## Required checks

The shared validator enforces the four-file allowlist, schema version, state and
county-equivalent consistency, candidate retention, unique identities, required
promotion fields, append-only decision provenance, affirmative exclusion reasons,
count reconciliation, immutable evidence references, approval fingerprint, and
canonical boundary.

Before publishing a pull request, run:

```bash
python3 01-database/tools/assess_pr_scope.py
python3 -m unittest discover -s 01-database/tools/tests -p "test_*.py"
python3 01-database/tools/validate_state_releases.py
```

CI rejects non-contract state artifacts, more than 20 changed files, or more than
15,000 additions unless an explicitly reviewed exception is labeled
`large-reviewed-change`.
