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
├── collect.py          # config-driven engine + adapter registry
├── publish.py          # -> app farms.json  (Postgres sink stubbed)
├── migrate.py          # fold the 15,703 staged rows into the model
├── scaffold_sources.py # generate source configs from existing state.yaml
├── regions.json        # region -> states (the release unit)
├── sources/
│   ├── SCHEMA.md       # the source-config spec Codex authors against
│   ├── _common.json    # national sources
│   └── <region>/<ST>.json
└── tests/              # 27 stdlib unit tests
```

## Run

```bash
python3 01-database/pipeline/migrate.py           # -> build/ (git-ignored)
python3 01-database/pipeline/scaffold_sources.py  # -> sources/<region>/<ST>.json
python3 -m unittest discover -s 01-database/pipeline/tests -p "test_*.py"
```

`build/` holds `app-farms.json` (product feed), `canonical.json` (full model),
`qa-residue.csv` (the only rows a human sees), and `migration-report.json`.
Nothing in `03-app/` or `research/` is touched — cutover is a separate step.

## Migration result (real data)

| | |
|---|---|
| Rows ingested | 15,703 across 10 states |
| Canonical after dedupe | 15,632 (71 merged) |
| **Eligible / published** | **9,454** (prior human QA preserved; app was 299) |
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
7. **The migration** — all 15,703 rows folded in, nothing lost.

## Handoff to Codex (data lane — mass, parallel, scoped)

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
