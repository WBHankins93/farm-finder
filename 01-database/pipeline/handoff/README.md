# Codex handoff runbooks

Each runbook is a **complete work order**. Hand a session one short prompt:

```
Work through 01-database/pipeline/handoff/<runbook>.md for <ST>.
Follow every step, run the acceptance checks it lists, and open the PR
exactly as it specifies. Mark the PR READY (not draft). Do not do anything
the runbook does not ask for.
```

Then verification on your side is: did the PR meet the runbook's stated
acceptance criteria? The runbook includes a copy-paste verify script whose
output the session must paste into the PR body.

## Runbooks

| Runbook | Does | Status | Prerequisite |
|---|---|---|---|
| [stream-c-geocode-backfill.md](stream-c-geocode-backfill.md) | Fills missing coordinates on a collected state; clears geography residue | **live — dispatch now** | none |
| [stream-b-wire-sources.md](stream-b-wire-sources.md) | Points a state's config at live source adapters so the engine collects real data | **live — dispatch now** | none (orchestrator merged) |

## Loop automations

Different shape from the Codex PR runbooks above: a **loop** is one re-firing
prompt that advances a queue unattended (no PR per unit). See the mold before
building a new one.

| Doc | Does |
|---|---|
| [LOOP-PATTERN.md](LOOP-PATTERN.md) | **The reusable mold** — how to structure any loop automation (read first) |
| [LOOP-region-publish.md](LOOP-region-publish.md) | First instance: collect → validate → load Postgres, region by region |

## Rules that apply to every runbook

- **One state = one session = one PR.** Never two sessions on the same state.
- **Branch from `origin/main` at its tip.** Never stack on an open PR.
- **Stay in scope.** Each runbook names the only files you may touch. Editing
  anything else — especially the pipeline engine (`model.py`, `cleanse.py`,
  `geo.py`, `qa.py`, `collect.py`, `publish.py`, `migrate.py`) or its tests —
  fails review.
- **Mark the PR ready, not draft.** A draft PR blocks its own merge.
- Run the required checks in `AGENTS.md` before marking ready.
