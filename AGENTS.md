# FarmFinder — Agent guidelines and source of truth

> Last updated: 2026-07-17 · Owner: Ben Hankins
> This file is the operating guide for every agent session (Codex, Claude, or
> other). Read it before changing anything.

## What FarmFinder is

A standalone two-track product: (1) a governed, provenance-first database of
independent farms and local-food producers, built state-by-state across the
continental United States; (2) a consumer directory/map application built on
that database. Louisiana and Mississippi are the current canonical coverage
area; eight more states have coverage-reviewed staged releases.

**"LA" always means Louisiana, never Los Angeles.**

FarmFinder must stay standalone: no other company's branding, workflow,
customer records, or promotions may enter the product, schema, or docs.

## Sources of truth (in authority order)

| What | Where | Validated by |
|---|---|---|
| Canonical pre-cutover farm data | `research/local_farm_database_final.xlsx`, sheet `All Farms` (299 rows: 220 LA / 79 MS) | `npm run data:validate` from `03-app/site/` |
| Machine-readable release contract | `03-app/site/config/source-of-truth.json` | same |
| Staged state releases (contract v2) | `research/state-expansions/<ST>/` — exactly `state.yaml`, `entities.csv`, `decisions.csv`, `report.md` | `python3 01-database/tools/validate_state_releases.py` |
| Pipeline rules | `01-database/state-release-contract.md`, `01-database/scalable-data-pipeline.md`, `01-database/pipeline-enrichment-plan.md`, `01-database/qa-operations.md` | contract unit tests |
| Product/platform docs | `README.md`, `03-app/site/docs/` | — |

Everything else (old dashboards, v1/v2 workbooks, `outputs/`, `.codex-work/`)
is historical or local scratch — never an editable authority. Raw observations,
request logs, and QA/identity/geography diagnostics live in versioned object
storage referenced by checksum from `state.yaml`; they are never committed.

## Current state (2026-07-17)

- Canonical: 299 LA/MS rows; public site reads the generated
  `03-app/site/app/data/farms.json`. PostgreSQL cutover is staged, not canonical.
- Staged states (entities / eligible / QA):
  AL 807/800/7 · AR 766/553/213 · FL 1,515/237/1,278 · GA 1,738/558/1,180 ·
  LA 1,200/993/207 · MS 737/581/156 · NC 3,415/2,208/1,207 · SC 1,601/1,148/453 ·
  TN 3,121/1,602/1,519 · TX 835/769/66.
- **QA is the standing priority.** The current committed queue is 6,286 rows
  against 9,449 eligible handoff rows; no new-state collection until the QA
  queue is materially reduced. Current routed totals are 2,597 geography,
  2,298 operation-evidence, 1,367 corroboration, and a
  24-row judgment-only floor: 21 canonical-baseline research items plus 3
  unresolved status cases. The 2026-07-17 residue batch applied 86
  append-only identity, status, and baseline decisions; missing evidence did
  not create any exclusion.
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

## Active workstreams (QA-first, in order)

The QA process itself is governed by `01-database/qa-operations.md`: every QA
row must carry routable blocker text (`python3 01-database/tools/qa_triage.py`
must report zero unrouted rows), automation drains queues before human
batches, and new-state collection PRs fail the scope gate while the committed
QA queue exceeds the intake cap.

1. **Geography QA batches** — resolve `county requires geography review` rows
   (NC 1,142, SC 397, plus 1,058 city/county-missing rows in other states)
   with the Census place-reference and TIGERweb machinery already in
   `collect_southeast.py` / `geocode_eligible.py`. Deterministic; append
   `correct` decisions citing the Census source.
2. **Corroboration batches** — run
   `01-database/tools/corroboration_assistant.py` per state (FL first: 874
   single-grade-E rows), then apply human-approved proposals as append-only
   decisions with paired entity patches.
3. **Farm-operation evidence batches** — TN (1,407) and GA (692)
   member/vendor-directory candidates; use the assistant's cross-directory
   pass plus targeted research.
4. **True human QA tail** (24 remaining rows after the 2026-07-17 batch: 21
   LA/MS baseline-not-rediscovered research items and 3 unresolved status
   cases) — case-by-case with evidence. The completed batch resolved the 34
   identity rows, 11 status rows, and 17 baseline rows that had sufficient
   current evidence; the 3 retained status items remain QA rather than being
   treated as closed.
5. After QA: PostgreSQL cutover of enriched release v2 (see
   `03-app/site/docs/data-governance/cutover-runbook.md`).

New-state collection is paused until the QA queue is materially reduced.
