# QA operations standard

> Effective 2026-07-17 · Companion to the
> [scalable data pipeline standard](scalable-data-pipeline.md) and the
> [pipeline enrichment plan](pipeline-enrichment-plan.md).

## Purpose

QA is a pipeline stage with capacity, routing, and backpressure — not a
holding pen. The 2026-07 backlog reached 8,268 rows; after the automated
burn-down, 7,604 remained because collection was unbounded, rows entered QA
without a resolution route, and automation ran after humans instead of before.
The 2026-07-17 judgment batch applied 86 append-only decisions and
reduced the queue to 7,543 rows; the remaining judgment-only floor is 24 rows
(21 baseline research items and 3 unresolved status cases). This standard
makes the queue flow continuously and keeps it from backing up again.

The governing rule:

> Nothing enters QA without a routable blocker. Automation drains every queue
> before a human touches it. Collection slows down when QA is over budget.

## The four controls

### 1. Prevent — control what enters QA

- **Source tiers** (enforced by the validator): `identity_hint` sources may
  never create standalone QA rows; `excluded_source` is never parsed. Every
  new source is tiered before collection.
- **Intake budget**: a PR that adds a *new* state fails the scope gate while
  the committed QA total (excluding the new state) exceeds the intake cap in
  `assess_pr_scope.py` (`QA_INTAKE_CAP`, currently 36). The cap is roughly
  1.5× the post-burn-down judgment-only floor: `ceil(1.5 × 24) = 36`; it does
  not treat the larger automated geography, operation-evidence,
  corroboration, or outreach queues as human intake capacity. The
  `large-reviewed-change` label remains the explicitly reviewed exception.
- **Referrals, not dead ends**: `outside_jurisdiction` exclusions emit
  home-state referrals instead of silently shedding candidates.

### 2. Route — every QA row carries a resolution strategy

Blocker text must match the routing taxonomy below. `qa_triage.py` assigns
each QA row a primary strategy (first match in priority order) and flags
`unrouted` rows; collectors and reviewers must write blockers using this
vocabulary so the row is workable without re-reading it.

| Priority | Strategy | Blocker vocabulary (regex family) | Resolver |
|---|---|---|---|
| 1 | `geography` | county/city missing or requires geography review | Deterministic: Census place reference, TIGERweb, geocode cache |
| 2 | `corroboration` | single grade-E … needs corroboration | `corroboration_assistant.py`, then curator apply-batch |
| 3 | `operation_evidence` | farm-operation evidence; directory/member/vendor candidate; production scope | Assistant cross-directory pass + targeted research |
| 4 | `baseline` | canonical baseline farm not rediscovered | Human recollection review (LA/MS rebuilds) |
| 5 | `identity` | same normalized name; identity continuity; contact conflict | Human, evidence-based |
| 6 | `status_conflict` | operating status conflicts; reopened closure | Human, evidence-based |
| 7 | `contact_outreach` | no public outreach path captured | Research/outreach; often co-occurs and resolves last |
| — | `unrouted` | anything else | Fix the blocker text; a growing unrouted bucket is a process bug |

A row may match several strategies; it is worked under its primary one and
its residual blockers keep it in QA until all are cleared.

### 3. Drain — automation before humans

Standing order per state, cheapest first:

1. `qa_triage.py` — refresh worklists and counts.
2. Geography resolution — run before any human geography review; append
   `correct` decisions citing the Census source.
3. `corroboration_assistant.py` — produce the proposal bundle for
   `corroboration` and `operation_evidence` cohorts; humans apply or reject
   proposals, never re-derive them.
4. Human batches — only the residue, with drafted evidence attached.

Automation assembles evidence and never decides: no exclusions, no status
changes, no invented data (pipeline enrichment plan §3 boundary).

### 4. Review — cadence and WIP limits

- **Weekly cycle**: (a) refresh triage and assistant bundles; (b) run
  apply-batches midweek — each batch is one state, one PR, branched from
  same-day main; (c) end the week with `state_release_status.py` plus the
  triage summary, and record the queue trend in the PR description.
- **WIP limit**: one state-data PR in flight per state (AGENTS.md rule 2).
- **Batch size**: stay under the 20-file / 15,000-addition scope gate; split
  by county group or strategy rather than requesting exceptions.
- **Service target**: a state is "flowing" when its QA count is under 20% of
  its entities and its unrouted bucket is zero. States above that line get
  the next batch priority.

## Command reference

```bash
python3 01-database/tools/qa_triage.py                 # route + worklists + summary
python3 01-database/tools/corroboration_assistant.py --state FL   # evidence bundles
python3 01-database/tools/geocode_eligible.py AR       # display coordinates (not a QA gate)
python3 01-database/tools/referrals.py                 # cross-state referral staging
python3 01-database/tools/state_release_status.py      # gate status, all states
```

Worklists and proposal bundles are derived private artifacts under
`data/exports/` and `data/source-releases/work/`; they are never committed
and never a source of truth. The four-file state contract remains the only
authority, and every applied fix is an append-only decision with its entity
row updated in the same change.
