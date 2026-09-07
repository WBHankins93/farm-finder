# FarmFinder pipeline (redesign)

The config-driven replacement for `01-database/tools/`. A state is a file, not a
function; provenance is one field, not an evidence-grade lattice; QA is
automation-first, humans only on the residue. Target architecture and rationale:
the [architecture doc](https://claude.ai/code/artifact/ce23f408-212e-419c-b154-aa09f857e82a).

Zero third-party dependencies — stdlib only (Python 3.13). Config is JSON because
the repo has no PyYAML and `state.yaml` is already JSON content.

## Layout

```
01-database/pipeline/
├── model.py            # THE canonical Farm schema + app-record contract
├── cleanse.py          # normalize · classify category · dedupe · eligibility
├── geo.py              # county-centroid fallback (in-repo, no network)
├── privacy.py          # internal_until_public_use_review enforcement
├── qa.py               # automated residue rules + export
├── collect.py          # config-driven engine + adapter registry (per-source isolation)
├── adapters/           # one module per source type (pdf_list, html_table, csv_download, api)
├── publish.py          # -> app farms.json  (Postgres sink stubbed)
├── run.py              # ORCHESTRATOR: collect a state via live engine -> data/<ST>.json; --publish
├── migrate.py          # historical 10-state bridge retained for transition validation
├── scaffold_sources.py # generate source configs from existing state.yaml
├── regions.json        # region -> states (the release unit)
├── data/               # committed canonical store, data/<ST>.json (live-collected states)
├── sources/
│   ├── SCHEMA.md       # the source-config spec Codex authors against
│   ├── _common.json    # national sources
│   └── <region>/<ST>.json
└── tests/              # stdlib unit tests
```

## Run the pipeline

```bash
python3 01-database/pipeline/run.py --state KY   # collect one state via live adapters -> data/KY.json
python3 01-database/pipeline/run.py --all        # every state that has a source config
python3 01-database/pipeline/run.py --publish    # aggregate all states -> build/app-farms.json
```

`migrate.py` remains the one-time entities.csv bridge; `run.py --publish` prefers
a committed `data/<ST>.json` and falls back to that bridge per state.

## Run

```bash
python3 01-database/pipeline/migrate.py           # -> build/ (git-ignored)
python3 01-database/pipeline/scaffold_sources.py  # -> sources/<region>/<ST>.json
python3 -m unittest discover -s 01-database/pipeline/tests -p "test_*.py"
```

`build/` holds `app-farms.json` (product feed), `canonical.json` (full model),
`qa-residue.csv` (the only rows a human sees), and `migration-report.json`.
Nothing in `03-app/` or `research/` is touched — cutover is a separate step.

## Current national snapshot

Counts below are derived from the committed `data/<ST>.json` state stores and
the eligible feed produced by `run.py --publish` on 2026-08-30.

| | |
|---|---|
| Canonical collected records | **72,396** across 50 states |
| Eligible / public feed | **68,618** |
| QA residue | **3,778** durable named candidates |
| Mappable public records | **54,821** |
| Privacy-cleared public contacts | **10,308** |
| Without a captured website | **51,984** — absence may mean not yet captured, not verified absent |

The committed state files are authoritative. `build/app-farms.json` is a
reproducible, ignored artifact; `03-app/site/app/data/farms.json` is the
superseded 299-row workbook-era artifact.

## Historical 10-state migration checkpoint

The figures below describe the one-time staged-release bridge before the
50-state collection sweep. They are preserved as migration history, not current
coverage.

| | |
|---|---|
| Rows ingested | 15,703 across 10 states |
| Canonical after dedupe | 15,632 (71 merged) |
| **Eligible / published at that checkpoint** | **9,454** (prior human QA preserved) |
| QA residue | 6,178 — exported to `build/qa-residue.csv` |
| Mappable pins | 2,687 → **5,586** (+2,899 via in-repo county centroids) |
| Public contacts | 3,246 (website-sourced; the rest held internal) |

Geography-only residue is 1,365 rows — the population a geocode backfill plus
`qa.rule_reclear_now_geocoded` auto-clears, with no human judgment.

---

## What's done (my lane — the load-bearing design)

Complete, tested, and stable to build against:

1. **`model.Farm`** — the one schema every stage speaks; `to_app_record()` is
   verified to match `03-app/site/app/lib/farms.ts` exactly (25/25 keys).
2. **Cleanse rules** — product parsing, word-boundary category classification,
   identity dedupe, and the single `decide_eligibility` call.
3. **Geo fallback** — county-centroid synthesis from in-repo coordinates.
4. **Privacy gate** — contacts internal by default; conservative public rule.
5. **QA engine** — automated rules + residue export; migration mode (`rules=[]`)
   that preserves prior human QA rather than overriding it.
6. **Collect engine + adapter registry + config spec** — the interfaces below.
7. **The historical migration bridge** — all original 15,703 rows were folded
   in without loss before the national state stores superseded it.

## Handoff to Codex (data lane — mass, parallel, scoped)

**Dispatch via runbooks.** Each stream below has a strict work order in
[`handoff/`](handoff/README.md); hand a session one short prompt pointing at the
runbook for one state, then verify against the runbook's acceptance criteria.

- Stream C → [`handoff/stream-c-geocode-backfill.md`](handoff/stream-c-geocode-backfill.md) — **live now**
- Stream B → [`handoff/stream-b-wire-sources.md`](handoff/stream-b-wire-sources.md) — **blocked on the orchestrator `run.py`**

Follow the two-lane discipline in AGENTS.md: **do not** edit `model.py`,
`cleanse.py`, `geo.py`, `privacy.py`, `qa.py`, `collect.py`, or the tests — that's
the tooling lane and it's frozen for you. Each task below is one exclusive claim.

### A. Source adapters — one PR each, no shared files
Implement each planned adapter as a **single new file** `pipeline/adapters/<kind>.py`
decorated with `@adapter("<kind>")` — the engine auto-discovers every module in
`adapters/` on first use (`collect.load_adapters()`), so an adapter PR touches
exactly one new file plus its own test file, never the engine. Signature:
`(source: dict, ctx) -> Iterable[Farm]`; a template lives in
`adapters/__init__.py`. Build order (highest coverage first): `pdf_list`,
`html_table`, `csv_download`, `api`. Each returns raw `Farm`s; the engine
handles cleanse/geo/qa/publish and skips unbuilt adapters with a warning, so
partial progress never breaks a run.

### B. State configs — one PR per state
- Existing 10 states: `scaffold_sources.py` already generated their configs from
  `state.yaml`. Per state, verify each source's guessed `adapter` against
  `sources/SCHEMA.md` and correct it. Then drop the `staged-bridge` source once
  that state's live adapters cover it.
- New states: author `sources/<region>/<ST>.json` per the schema, one state per
  session, exclusive claim, branch from `main`.

### C. Geocode backfill — one PR per region
For rows still `ungeocoded` after the county-centroid fallback, backfill real
coordinates (Census/TIGERweb), then let `rule_reclear_now_geocoded` auto-clear
the geography-only residue. ~1,365 rows are waiting on this.

### D. The delete list — one PR, after the engine is validated on ≥1 full region
Remove, with counts refreshed in the same PR:
`collect_southeast.py`, `collect_texas.py`, `collect_alabama.py`,
`collect_mississippi.py`, `migrate_state_contract_v2.py`,
`corroboration_assistant.py`, `apply_operation_evidence.py`,
`audit_operation_evidence.py`, `qa_triage.py`, `assess_pr_scope.py`, the
per-state `decisions.csv` ledgers, `state-release-contract.md`, and the
evidence-grade sections of AGENTS.md (retire ~⅔; keep the two-lane dispatch).

### E. Cutover — gated, after a region is green (tooling lane, not parallel)
Point `03-app/site/app/data/farms.json` at the pipeline's `app-farms.json`, then
implement `publish.load_postgres` per the cutover runbook.
