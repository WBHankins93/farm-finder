# FarmFinder — Agent guidelines and source of truth

> Last updated: 2026-07-18 · Owner: Ben Hankins
> Operating guide for every agent session (Codex, Claude, or other). Read it
> before changing anything.

## What FarmFinder is

A two-track product: (1) a provenance-kept database of independent farms and
local-food producers, built state-by-state and released region-by-region across
the U.S.; (2) a consumer directory/map application on that database, with an AI
assistant to search it.

**"LA" always means Louisiana, never Los Angeles.** FarmFinder stays
standalone: no other company's branding, workflow, customer records, or
promotions may enter the product, schema, or docs.

## Architecture

The data pipeline lives at `01-database/pipeline/` — a config-driven engine
(collect → cleanse → qa → publish) where **a state is a config file, not a
collector**. Read `01-database/pipeline/README.md` first: it defines the
canonical model, the adapter registry, and the five handoff workstreams (A–E).
The old contract-v2 governance apparatus is retired; its validator remains only
to keep the existing `research/state-expansions/` releases intact until the
Postgres cutover.

## Sources of truth (in authority order)

| What | Where | Validated by |
|---|---|---|
| Pipeline engine, model, and rules | `01-database/pipeline/` | `python3 -m unittest discover -s 01-database/pipeline/tests -p "test_*.py"` |
| Canonical collected farm data | `01-database/pipeline/data/<ST>.json` (72,396 rows across 50 states as of 2026-08-30) | `python3 01-database/pipeline/run.py --publish` plus pipeline tests |
| Eligible public directory feed | `01-database/pipeline/build/app-farms.json` (68,618 reproducible rows as of 2026-08-30) | `python3 01-database/pipeline/run.py --publish` |
| Public app's runtime index and displayed counts | `03-app/site/public/national-index.bin` + `app/data/directory-stats.generated.json` (generated, never committed) | `cd 03-app/site && npm run data:build && npm run data:gates` |
| Publication contract (editorial metadata + coverage floors only) | `03-app/site/app/data/feed-contract.json` | `cd 03-app/site && npm run data:gates` |
| Legacy staged releases (read-only transition input) | `research/state-expansions/<ST>/` | `python3 01-database/tools/validate_state_releases.py` |
| Per-state source configs | `01-database/pipeline/sources/<region>/<ST>.json` | `sources/SCHEMA.md` |
| Product/platform docs | `README.md`, `03-app/site/docs/` | — |

Pipeline outputs (`01-database/pipeline/build/`) are reproducible artifacts,
never committed, and so are the app's generated feeds under `03-app/site`.
`03-app/site/app/data/farms.json` is the superseded 299-row workbook-era
artifact: it is retained only as provenance evidence and as the
`EXPLORER_LEGACY=true` rollback surface, and must not be used for national
counts or runtime discovery.

**Displayed counts are derived, never typed.** Every number the public page
shows comes from `app/data/directory-stats.generated.json`, which
`scripts/build-web-feed.py` computes from the feed it just published. Do not
reintroduce a hand-maintained counts file. Everything else (old dashboards, v1/v2 workbooks, `outputs/`,
`.codex-work/`) is historical scratch.

## Standing rules

1. **Branch from latest `main` the same day you open the PR.** Never stack on
   another unmerged branch — squash-merges auto-close stacked PRs.
2. **One exclusive scope per session.** One state = one session; tooling files
   are a separate serial lane (below). Two sessions never share a file.
3. **Keep PRs small.** CI rejects >20 changed files or >15,000 additions
   without the `large-reviewed-change` label.
4. **Named candidates are durable.** Missing data produces a `qa_reason`, never
   a silent drop. Removal requires affirmative, cited evidence (confirmed
   non-farm, closed, out of jurisdiction, or duplicate identity).
5. **Privacy defaults.** Contacts and addresses stay internal until cleared by
   the publish-time privacy gate (`pipeline/privacy.py`). Never publish exact
   private locations; public coordinates use farm-confirmed or reduced-precision
   placement.
6. **Keep counts honest.** When published numbers change, update every doc that
   cites them in the same PR.

## Two lanes (dispatch discipline)

- **Tooling lane** — anything under `01-database/pipeline/` except
  `sources/<region>/<ST>.json` and `adapters/`, plus CI workflows and this file.
  Run serially, one PR at a time, merged before data-lane work resumes.
- **Data lane** — one state's source config, one adapter file, or one region's
  geocode backfill. Fans out in parallel after the tooling lane is quiet; each
  session gets an exclusive claim before dispatch (PR label `state:<ST>` or
  `lane:tooling`).

## Required checks before any PR

```bash
python3 01-database/tools/assess_pr_scope.py
python3 -m unittest discover -s 01-database/pipeline/tests -p "test_*.py"
python3 -m unittest discover -s 01-database/tools/tests -p "test_*.py"
python3 01-database/tools/validate_state_releases.py
```

If the change touches `03-app/site/`, also run from that directory:
`npm run data:validate`, `npm run data:gates`, `npm run lint`, `npm test`.
`npm test` builds the site, which also enforces the Cloudflare worker-script
and static-asset size limits.

## Active workstreams

Work the streams in `01-database/pipeline/README.md` (§ Handoff to Codex),
in order: **A** source adapters · **B** state configs · **C** geocode backfill
per region · **D** the remaining legacy delete list (after a region is green) ·
**E** Postgres cutover (tooling lane, gated).

QA is automation-first: rules in `pipeline/qa.py` drain the queue; humans only
ever review `build/qa-residue.csv`. There is no intake cap — collection and
review no longer compete.
