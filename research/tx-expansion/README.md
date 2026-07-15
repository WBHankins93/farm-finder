# Texas coverage-reviewed staging release

> Release: `tx-coverage-reviewed-2026-07-15`. This directory is private staging
> and does not change the canonical LA/MS workbook or public FarmFinder data.

## Status

Texas completed the repository's three-pass collection and state completion gates
on 2026-07-15:

- 29 source, channel, official-geography, and curator-decision datasets evaluated across passes 1–3;
- 1,060 immutable source and curator-decision observations;
- 899 proposed Texas entities after deterministic identity and scope review;
- 337 entities meet the staged promotion-field/evidence/privacy gates;
- 562 entities remain in the explicit research or QA queue;
- all 254 counties were searched and have a documented coverage status;
- 178 counties have at least one candidate, while 76 are `searched_none_found`;
- 39 manual verification decisions are retained with their evidence and rationale;
- 13 explicitly closed PickYourOwn observations and 20 curator-excluded entity groups remain auditable;
- the Texas release validator passes.

`coverage_reviewed` means all qualifying farms found under the documented sources and
three-pass process as of the release date. It is not a claim that every
USDA-defined, private, commodity-only, or publicly undiscoverable farm is known.

## Files

- `texas-source-observations.csv` / `.json` — one immutable row per source observation.
- `texas-candidate-entities.csv` / `.json` — deterministic proposed entities with promotion decisions.
- `raw-source-records.json` — parsed source snapshots and source-evaluation records.
- `identity-review.csv` — exact-name merge/split decisions and underlying observation IDs.
- `qa-queue.csv` — unresolved entity type, identity, geography, product, and corroboration work.
- `county-coverage.csv` — all 254 counties with pass-level and entity counts.
- `excluded-observations.csv` — grade-F closure records retained outside proposed entities.
- `geography-conflicts.csv` — source-versus-exact-address county conflicts and decisions.
- `source-pass-log.json` — request status, attempts, hashes, retrieval dates, and accept/reject decisions.
- `county-lookup-errors.json` — observations still lacking a defensible county after conservative fallbacks.
- `manual-verification-decisions.csv` — evidence-backed corroboration/exclusion decisions applied without overwriting source assertions.
- `collection-summary.json` — reconciled release totals.
- `texas-completion-report.md` — detailed findings, decisions, limitations, and next review work.

## Reproduce and validate

```bash
python3 01-database/tools/collect_texas.py
python3 01-database/tools/validate_texas_release.py
```

The collector requires `pdftotext` for the official farm-to-school vendor resource.
Exact source addresses and direct contacts remain internal until public-use review.
