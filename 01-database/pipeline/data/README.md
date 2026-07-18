# Canonical data store

`data/<ST>.json` is the committed canonical record for a state that has been
collected through the live engine (`run.py`). It holds `model.Farm` records in
`to_record()` form and is the **source of truth** for that state going forward.

- A **new** state (KY/VA/WV) exists only here — there is no `entities.csv`.
- An **existing** state keeps using its `research/state-expansions/<ST>/entities.csv`
  migration bridge until its live adapters are verified; at that point its
  Stream B PR commits `data/<ST>.json` and retires the old `entities.csv`.

`run.py --publish` prefers `data/<ST>.json` when present and falls back to the
`entities.csv` bridge otherwise, so the app feed always reflects every state.

Do not hand-edit these files — regenerate with `python3 run.py --state <ST>`.
Only commit one after its sources are verified (Stream B); never commit a file
built from unverified guessed source URLs.
