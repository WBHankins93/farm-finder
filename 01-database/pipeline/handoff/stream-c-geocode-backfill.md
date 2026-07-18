# Runbook — Stream C: geocode backfill

**Goal:** fill missing coordinates on one already-collected state so its farms
map and its "county requires geography review" residue auto-clears.
**One session handles exactly one state.** Work top to bottom; do not improvise.

## Why this works

Most staged rows arrived without coordinates. A privacy-safe **city/county
centroid** (never a precise private address) is enough to (1) place a pin and
(2) resolve a "county requires geography review" blocker — a city centroid
implies its county. Once coordinates land in `entities.csv`, the pipeline's
`qa.rule_reclear_now_geocoded` promotes those rows automatically on the next
build. North Carolina proved it: residue 1,199 → 634.

## State queue — claim one, check it off in your PR

- [ ] LA   - [ ] MS   - [ ] AR   - [ ] SC   - [ ] TN   - [ ] GA   - [ ] FL
- [x] NC  (done — reference: PR #77)

## Scope — the only files you may change

```
research/state-expansions/<ST>/entities.csv   # fill blank lat/lng only
research/state-expansions/<ST>/state.yaml      # update the entities.csv sha256
```

Touch nothing else. Do **not** edit any tool, the pipeline engine, or another
state. `01-database/tools/geocode_eligible.py` is used **as a library** — read
it, call its Census centroid helpers (`load_places`, `load_counties`,
`choose_city`, `parse_centroid`); do **not** modify it.

## Procedure

1. **Branch** from the current tip of main:
   ```bash
   git fetch origin && git checkout -b state/<ST>-geocode origin/main
   ```
2. **Find the gap.** Rows in `entities.csv` whose `latitude` or `longitude` is
   blank are the work. Rows that already have coordinates are done — leave them.
3. **Resolve centroids** using the Census machinery in `geocode_eligible.py`:
   resolve each blank row to its **city** centroid; fall back to its **county**
   centroid when the city is unknown or unresolvable. These are the same
   privacy-safe centroids that module already produces — reuse its cache at
   `03-app/site/scripts/geocode-cache.json`.
4. **Write coordinates into the blank cells only.** Never overwrite an existing
   coordinate. Never change any other column — not products, not evidence, not
   promotion, not identity.
5. **Update the hash.** Recompute the `entities.csv` sha256 and set it in
   `state.yaml` wherever that file's checksum is recorded.

## Acceptance criteria — all must hold

Run this and **paste its output into the PR body**. It must report
`OVERWRITTEN: 0`, `other column changes: 0`, `out of bounds: 0`, and
`sha256 matches: True`.

```bash
ST=<ST> python3 - <<'PY'
import csv, io, json, hashlib, os, subprocess
ST = os.environ["ST"]
root = f"research/state-expansions/{ST}"
BBOX = {  # approximate outer bounds (lat_min, lat_max, lng_min, lng_max)
  "LA":(28.8,33.1,-94.1,-88.7), "MS":(30.1,35.1,-91.7,-88.0),
  "AR":(32.9,36.6,-94.7,-89.6), "SC":(31.9,35.3,-83.4,-78.4),
  "TN":(34.9,36.8,-90.4,-81.6), "GA":(30.3,35.1,-85.7,-80.7),
  "FL":(24.3,31.1,-87.7,-79.9), "NC":(33.7,36.6,-84.4,-75.4),
}
base = subprocess.run(["git","show",f"origin/main:{root}/entities.csv"],
                      capture_output=True, text=True).stdout
b = {r["entity_id"]: r for r in csv.DictReader(io.StringIO(base))}
h = {r["entity_id"]: r for r in csv.DictReader(open(f"{root}/entities.csv"))}
assert set(b) == set(h), "ROW SET CHANGED — must be identical"
filled = overwritten = other = 0
for eid, hb in h.items():
    bb = b[eid]
    for col in bb:
        if bb[col] != hb[col]:
            if col in ("latitude","longitude"):
                overwritten += 1 if bb[col].strip() else 0
                filled += 0 if bb[col].strip() else 1
            else:
                other += 1
la_lo,la_hi,lo_lo,lo_hi = BBOX[ST]
oob = 0
for r in h.values():
    if r["latitude"].strip():
        lat, lng = float(r["latitude"]), float(r["longitude"])
        if not (la_lo<=lat<=la_hi and lo_lo<=lng<=lo_hi): oob += 1
sha = hashlib.sha256(open(f"{root}/entities.csv","rb").read()).hexdigest()
sha_ok = sha in open(f"{root}/state.yaml").read()
print(f"rows: {len(h)} | coord cells filled: {filled} | OVERWRITTEN: {overwritten}")
print(f"other column changes: {other} | out of bounds: {oob} | sha256 matches: {sha_ok}")
PY
```

Then the standard gate:

```bash
python3 01-database/tools/validate_state_releases.py   # must pass
python3 01-database/tools/assess_pr_scope.py           # must pass
```

## PR

- Branch: `state/<ST>-geocode`
- Title: `Backfill <ST> release coordinates`
- Body must include: coord cells filled (before/after count) and the pasted
  acceptance-script output.
- **Mark the PR READY, not draft.**
