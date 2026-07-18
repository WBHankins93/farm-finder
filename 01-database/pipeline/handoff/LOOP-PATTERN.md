# How to structure a loop automation — the reusable mold

The [region-publish loop](LOOP-region-publish.md) is the first instance of this
pattern; this doc is the pattern itself, so the next loop (or the next region) is
a fill-in-the-blanks job, not a redesign. Read this once; then every loop in the
project is built the same way.

---

## 1. What a loop actually is (and why that shapes everything)

A loop is **one prompt that re-fires on a schedule**. The critical fact:

> **Every firing starts with a fresh context. The loop has no memory of the last
> iteration.**

That single constraint drives every design rule below. The model that wakes up on
iteration 12 knows only two things: (a) the runbook you pointed it at, and (b)
whatever durable artifacts it can go read. It does *not* remember that iteration
11 collected Alabama. So the loop must be able to **reconstruct "where am I" from
scratch, every time, by looking at the world** — never from memory.

A loop system has exactly **two parts**, and keeping them separate is the whole
game:

| Part | What it is | Property it must have |
|------|-----------|----------------------|
| **Tools** | Deterministic scripts the loop calls (`run.py`, `load_postgres.py`) | Idempotent, exit-code honest, no interaction |
| **Runbook** | The markdown the model follows each firing (`LOOP-region-publish.md`) | Stateless, filesystem-driven, one unit of work |

If logic can be deterministic, it belongs in a **tool**, not in the runbook. The
runbook is only for the decisions that need judgment (classify state, read a
residue count, decide done vs. needs-review).

---

## 2. The five invariants — a loop that lacks any one of these will misbehave

### I. Durable, self-describing progress
The loop derives its position by **observing artifacts**, not by remembering.
Pick a signal that *is* the work product:
- Region loop: `data/<ST>.json` exists ⇒ that state is collected. The signal is
  the output file itself — it can't lie or desync.
- Prefer filesystem/DB truth. Use a written ledger (`build/loop-progress.json`)
  only for facts with no natural artifact (e.g. "region published") — and treat
  it as a cache, reconstructible from the primary signal.

### II. One bounded unit of work per firing
Each iteration does exactly one thing (collect *one* state, or publish *one*
region), reports, and ends. Bounded work = observable progress, a clean crash
boundary, and a context window that never overflows. Never "do the whole region
in one firing."

### III. Idempotent steps
Any step must be safe to run twice — because a crash mid-firing *will* re-run it.
- `run.py --state LA` regenerates `data/LA.json` from scratch — re-running is a
  no-op-equivalent.
- `load_postgres.py --refresh` is `TRUNCATE + COPY` in one transaction — load it
  ten times, same table. If a step appended instead of refreshed, a retry would
  double the data. **Design every write as replace-not-append where you can.**

### IV. An explicit state machine
Every item in the queue is in exactly one named state, and the runbook says how
to detect each and what to do. The region loop's states:
`pending → collected → (done | needs_review)`, plus `blocked` and `error` as
terminal off-ramps. If you can't enumerate the states, you can't write the loop.

### V. A guaranteed stop condition
A loop that can't decide it's finished runs forever and burns budget. State the
termination test explicitly ("every region `published` and no `pending` state
anywhere ⇒ `ScheduleWakeup stop`"). Also define **off-ramps** for things that
can't complete (blocked states) so one stuck item doesn't wedge the whole loop.

---

## 3. Supporting practices (the difference between works-once and works-unattended)

- **Prove every step by hand first.** Before wrapping anything in a loop, run
  each command once and watch it: `run.py --state LA` ✔, `run.py --publish` ✔,
  `load_postgres.py --refresh` ✔. A loop is an amplifier — it multiplies a broken
  step by N. Never automate an unproven command.
- **Distinguish expected failure from fatal failure.** Live sources returning 403
  is normal weather — log and continue. A traceback / non-zero exit is a real
  failure — record it, mark the item `error`, **bound retries** (≤2), move on. A
  loop that retries a hard failure forever is the classic runaway.
- **Make "done" a written gate, not a vibe.** The region loop's approval gate is
  one rule: residue empty or geography-only ⇒ pass. Whatever your quality bar is,
  encode it as a check the loop runs, not a judgment it improvises.
- **Enumerate the guardrails — what the loop must NEVER do.** Ours: no git
  commit/push, no fabricated metadata, no editing the frozen tooling lane, no
  inventing source URLs. Side-effectful loops need an explicit "not allowed" list
  because the model will otherwise try to be helpful at 3am.
- **Report every iteration, and a final summary.** One or two lines per firing so
  a human skimming the transcript sees the frontier advance; a table at the end so
  the leftovers (blocked / needs-review) are collected in one place.
- **Pace deliberately.** See §5.

---

## 4. The skeleton — copy this for the next loop

**Runbook structure** (mirror `LOOP-region-publish.md`):

```
# Loop runbook — <what it does>, <unit> by <unit>
Scope decisions baked in:   <the non-obvious choices; what's in/out of scope>
One-time setup:             <commands to run once before the first firing>
Launch:                     /loop Follow <path-to-this-runbook>. Do one unit, report, schedule next.

Per-iteration algorithm:
  1. Load order       — where the ordered queue comes from
  2. Find the frontier— first not-done item (derived from a durable signal)
  3. Classify         — pending / done / blocked / error
  4. Do ONE unit      — the single command; parse its result; update the ledger; END
  5. Gate/rollup      — when a group completes, run the publish/finalize step; END
  6. Off-ramps        — what to do with blocked/error items so they don't stall
  7. Stop condition   — the exact test for "finished" → ScheduleWakeup stop

Report:    per-iteration line format + final summary table
Guardrails: the explicit NEVER list
```

**Generic per-iteration logic** (the shape every firing takes):

```
state = read_durable_progress()          # filesystem + ledger, never memory
item  = first_incomplete(queue, state)   # the frontier
if item is None:
    emit_final_report(); ScheduleWakeup(stop=True); return
if blocked(item):
    record_blocked(item); continue_to_next_group_or_item()
result = do_one_unit(item)               # ONE bounded, idempotent action
record(result); maybe_run_rollup_gate()
report_one_line()
ScheduleWakeup(delaySeconds=~60)         # or stop if that was the last unit
```

**Ledger template** (`build/loop-progress.json`) — only for facts with no natural
artifact:

```json
{
  "units":  { "<id>": {"status": "done|needs_review|blocked|error", "at": "...", "metrics": {}, "note": "" } },
  "groups": { "<id>": {"finalized": false, "at": null, "count": null, "blocked": [], "review": [] } }
}
```

---

## 5. Launching, pacing, and stopping (the harness mechanics)

- **Launch:** `/loop <prompt>`. Point the prompt at the runbook; the same prompt
  re-fires each cycle, so keep the instruction to "do one unit, report, schedule
  the next."
- **Dynamic vs. interval:** `/loop <prompt>` (no interval) is **self-paced** — the
  loop chooses when to wake via `ScheduleWakeup`. `/loop 5m <prompt>` fires on a
  fixed 5-minute clock. Use **dynamic** when each iteration does real work
  synchronously (ours does) and interval when you're polling something external.
- **Pacing rule of thumb:** each of our iterations does its work *inside the
  firing* (the script runs to completion in the turn), so there's nothing to poll
  — schedule the next wake ~60s out. Only stretch the delay when you're genuinely
  waiting on external state (a CI run, a deploy) that changes on its own clock.
- **Stopping:** call `ScheduleWakeup` with `stop: true` the moment the termination
  test passes. That's the only clean way to end a dynamic loop — don't let it
  coast.

---

## 6. Pre-launch checklist for any new loop

```
[ ] Every command runs correctly by hand, once, watched.
[ ] Each write step is idempotent (replace, not append) — safe to re-run after a crash.
[ ] Progress is derivable from durable artifacts, not from memory.
[ ] Every queue item maps to one named state; the runbook detects each.
[ ] Expected failures are distinguished from fatal ones; retries are bounded.
[ ] "Done" is a written check, not a judgment call.
[ ] There is an explicit stop condition AND off-ramps for un-completable items.
[ ] The NEVER list (side effects the loop must not take) is written down.
[ ] One-time setup is documented and done.
[ ] Per-iteration report format + final summary are defined.
```

If all ten are checked, the loop is safe to run unattended. If any is blank, that
gap is exactly where it will misbehave.
