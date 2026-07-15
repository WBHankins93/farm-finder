# Alabama coverage-reviewed staging release

> Release: `al-coverage-reviewed-2026-07-15`. This directory is private staging
> and does not change the canonical LA/MS workbook or public FarmFinder data.

## Status

Alabama completed the repository's three-pass collection and state completion gates
on 2026-07-15:

- 14 primary or channel datasets evaluated across passes 1–3;
- 1,048 immutable source observations;
- 850 proposed Alabama entities after deterministic identity review;
- 635 entities meet the staged promotion-field/evidence/privacy gates;
- 215 entities remain in the explicit research or QA queue;
- all 67 counties have candidates and a documented coverage status;
- 2 Sweet Grown records resolved outside Alabama and remain grade-F exclusions;
- the Alabama release validator passes.

`coverage_reviewed` means all qualifying farms found under the documented sources and
three-pass process as of the release date. It is not a claim that every
USDA-defined, private, or undiscoverable farm is known.

## Files

- `alabama-source-observations.csv` / `.json` — one immutable row per source observation.
- `alabama-candidate-entities.csv` / `.json` — deterministic proposed entities with promotion decisions.
- `raw-source-records.json` — parsed source snapshots and source-evaluation records.
- `identity-review.csv` — exact-name merge/split decisions and underlying observation IDs.
- `qa-queue.csv` — unresolved entity type, identity, geography, product, and corroboration work.
- `county-coverage.csv` — all 67 counties with pass-level and entity counts.
- `excluded-observations.csv` — grade-F boundary/closure/conflict records retained outside proposed entities.
- `source-pass-log.json` — request status, attempts, hashes, retrieval dates, and accept/reject decisions.
- `county-lookup-errors.json` — failed or non-Alabama geography lookups.
- `collection-summary.json` — reconciled release totals.
- `alabama-completion-report.md` — detailed findings, decisions, limitations, and next review work.

## Reproduce and validate

```bash
python3 01-database/tools/collect_alabama.py
python3 01-database/tools/validate_alabama_release.py
```

The collector requires `pdftotext` to extract the current official state farm-stand
roster. Exact addresses and direct contacts stay internal until public-use review.
