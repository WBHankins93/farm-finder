# FarmFinder — Agent guidelines and source of truth

> Last updated: 2026-07-16 · Owner: Ben Hankins
> This file is the operating guide for every agent session (Codex, Claude, or
> other). Read it before changing anything.

## What FarmFinder is

A standalone two-track product: (1) a governed, provenance-first database of
independent farms and local-food producers, built state-by-state across the
continental United States; (2) a consumer directory/map application built on
that database. Louisiana and Mississippi are the current canonical coverage
area; six more states have coverage-reviewed staged releases.

**"LA" always means Louisiana, never Los Angeles.**

FarmFinder must stay standalone: no other company's branding, workflow,
customer records, or promotions may enter the product, schema, or docs.

## Sources of truth (in authority order)

| What | Where | Validated by |
|---|---|---|
| Canonical pre-cutover farm data | `research/local_farm_database_final.xlsx`, sheet `All Farms` (299 rows: 220 LA / 79 MS) | `npm run data:validate` from `03-app/site/` |
| Machine-readable release contract | `03-app/site/config/source-of-truth.json` | same |
| Staged state releases (contract v2) | `research/state-expansions/<ST>/` — exactly `state.yaml`, `entities.csv`, `decisions.csv`, `report.md` | `python3 01-database/tools/validate_state_releases.py` |
| Pipeline rules | `01-database/state-release-contract.md`, `01-database/scalable-data-pipeline.md`, `01-database/pipeline-enrichment-plan.md` | contract unit tests |
| Product/platform docs | `README.md`, `03-app/site/docs/` | — |

Everything else (old dashboards, v1/v2 workbooks, `outputs/`, `.codex-work/`)
is historical or local scratch — never an editable authority. Raw observations,
request logs, and QA/identity/geography diagnostics live in versioned object
storage referenced by checksum from `state.yaml`; they are never committed.

## Current state (2026-07-16)

- Canonical: 299 LA/MS rows; public site reads the generated
  `03-app/site/app/data/farms.json`. PostgreSQL cutover is staged, not canonical.
- Staged coverage-reviewed states (entities / eligible / QA):
  AL 808/799/9 · AR 766/524/242 · FL 1,515/205/1,310 · GA 1,738/554/1,184 ·
  LA 1,200/964/236 · MS 737/576/161 · TN 3,121/1,589/1,532 · TX 855/736/119.
- The QA backlog (4,793) is below the eligible set (5,947). Priority remains QA
  throughput and enrichment (see `01-database/pipeline-enrichment-plan.md`),
  not new-state collection.
- The contract v2 validator enforces the evidence-grade gate: grade-F blocks
  eligibility; grade-E-only observation evidence requires a corroborating
  append-only decision at grade A–D.

## Standing rules for every session

1. **Branch from latest `main` the same day you open the PR.** Before touching
   `research/state-expansions/<ST>/`, confirm your merge-base is not behind
   main's last commit to that directory (`git log -1 origin/main -- <dir>`).
   Stale-base state PRs fork release history and get closed.
2. **One state-data PR in flight per state.** Never stack state-data PRs on
   other unmerged branches.
3. **Keep PRs small and focused.** Commit early and often. CI rejects more than
   20 changed files or 15,000 additions without the `large-reviewed-change`
   label; don't aim for the ceiling.
4. **Decisions are append-only.** Corrections supersede; they never erase.
   Every `corroborate`/`correct` decision must be reflected in its entity row
   (observation or grades) in the same change.
5. **Non-deletion policy.** A named candidate is durable. Missing data creates
   a QA blocker, never an exclusion. Exclusions require affirmative, cited
   evidence for exactly one of: `confirmed_nonfarm`, `confirmed_closed`,
   `outside_jurisdiction`, `duplicate_identity`.
6. **Privacy defaults.** Internal addresses/contacts stay
   `internal_until_public_use_review`. Never publish exact private locations;
   public coordinates use farm-confirmed or reduced-precision placement.
7. **Eligible staging is not verification.** Never report eligible handoffs as
   `record_verified`, approved, or canonical.
8. **Keep counts honest everywhere.** When entity/decision counts change,
   update `state.yaml` counts, repository-file hashes, `report.md`, and any
   doc that cites the numbers, in the same PR.

## Required checks before any PR

```bash
python3 01-database/tools/assess_pr_scope.py
python3 -m unittest discover -s 01-database/tools/tests -p "test_*.py"
python3 01-database/tools/validate_state_releases.py
```

If the change touches `03-app/site/`, also run from that directory:
`npm run data:validate`, `npm run lint`, `npm test`.

## Active workstreams

1. Re-apply the closed AL/TX QA disposition batches from current main
   (research preserved on `codex/qa-alabama-identity`,
   `codex/qa-texas-county-batches`, `codex/qa-texas-batch-03`).
2. Source-tier ingestion policy, then geocoding enrichment, then automated
   corroboration, then cross-state referrals — in that order, per
   `01-database/pipeline-enrichment-plan.md`.
3. PostgreSQL cutover of enriched release v2 (see
   `03-app/site/docs/data-governance/cutover-runbook.md`).
