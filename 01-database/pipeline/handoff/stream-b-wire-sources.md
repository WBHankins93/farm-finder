# Runbook — Stream B: wire a state's config to live sources

**Goal:** make one state collect real data from live source directories through
the engine, instead of the placeholder `staged-bridge`.
**One session handles exactly one state.** Work top to bottom.

> ## ✅ Ready to dispatch
> The orchestrator `01-database/pipeline/run.py` is live. It runs a state config
> through collect → cleanse → geo → qa and persists the result to
> `data/<ST>.json`; `run.py --publish` aggregates all states into the app feed.
> The engine isolates per-source failures, so a source that 403s or fails to
> parse becomes a warning, not a crash — fix or drop those sources as you go.

## Why this exists

The four adapters (`pdf_list`, `html_table`, `csv_download`, `api`) are built and
merged, but every state currently lists a `staged-bridge` source — a placeholder
that only re-emits already-migrated rows. No new data collects until a state's
config names real adapters against real URLs. That is this job.

**In scope:** make the engine collect > 0 rows for the state from live sources.
**Out of scope (do NOT attempt here):** re-adjudicating existing QA residue,
corroboration/operation-evidence clearing — that is a separate future stream.

## State queue — two kinds

**Verify a scaffolded config** (data already exists; confirm adapter guesses):
- [ ] LA - [ ] MS - [ ] AL - [ ] AR - [ ] FL - [ ] GA - [ ] NC - [ ] SC - [ ] TN - [ ] TX

**Author a new config from scratch** (no prior data):
- [ ] KY - [ ] VA - [ ] WV   *(owner may take these directly)*

## Scope — the only file you may change

```
01-database/pipeline/sources/<region>/<ST>.json
```

Plus, if the orchestrator persists collected rows to a per-state data file, that
one generated file for this state. Touch **nothing** in the engine, the
adapters, the model, the tests, or any other state.

## Procedure

1. **Branch** from the current tip of main:
   ```bash
   git fetch origin && git checkout -b state/<ST>-wire origin/main
   ```
2. **Open** `sources/<region>/<ST>.json` (create it for a new state, per
   `sources/SCHEMA.md`).
3. **Set the right adapter for each source.** Inspect the URL and pick:

   | The source is… | `adapter` | add these per-source keys |
   |---|---|---|
   | JSON / REST endpoint | `api` | `page_param`, `page_start`, `field_map` (as needed) |
   | HTML page with a list/table | `html_table` | — |
   | downloadable CSV / spreadsheet | `csv_download` | `field_map` (source column → Farm field) |
   | PDF permit / certificate list | `pdf_list` | — |

   `field_map` only needs the columns the adapter would not already alias
   (`name`, `county`, `city`, `website`, `products`, `phone`, …).
4. **Run the state** and confirm it collects:
   ```bash
   python3 01-database/pipeline/run.py --state <ST>
   ```
   Expect a nonzero collected-row count and no adapter errors. Spot-check a
   handful of produced records for a real `name`, `county`, and `source`.
5. **Drop `staged-bridge`** from the config *only once* live adapters cover the
   state (an existing state may keep the bridge until then; a new state never
   had one).

## Acceptance criteria — all must hold

- `python3 01-database/pipeline/run.py --state <ST>` exits 0 and reports
  **> 0 rows collected** from live (non-`staged`) adapters.
- Every source in the config uses a real adapter type (or is a deliberately
  retained `staged-bridge` on a not-yet-finished existing state — state so in
  the PR body).
- No file outside the one config (and its generated data file) is changed —
  confirm with `git diff --name-only origin/main`.
- Standard gate passes:
  ```bash
  python3 01-database/tools/assess_pr_scope.py
  python3 -m unittest discover -s 01-database/pipeline/tests -p "test_*.py"
  ```

## PR

- Branch: `state/<ST>-wire`
- Title: `Wire <ST> sources to live adapters`
- Body must include: rows collected, which adapters each source now uses, and
  whether `staged-bridge` was dropped or retained (and why).
- **Mark the PR READY, not draft.**
