# QA residue triage — southeast (AR, FL, GA, LA, MS, NC, SC, TN, TX)

The publish loop collected 13 southeast states (Postgres at 20,335 eligible). What
did **not** publish is the QA residue: 4,741 non-geography rows held ineligible.
This runbook explains what that residue actually is, categorizes it, and hands the
grunt/research work off in **exclusive, non-stacking** streams (per AGENTS.md).

## The finding — it is not an accidental skip

The residue is dominated by a single inherited rule: contract-v2 required **two
independent sources** for every record. Records seen in only one directory were
flagged `single grade-E discovery listing needs corroboration` /
`directory candidate needs independent farm-operation evidence` and held. We
verified: name+county corroboration inside the currently-collected set is ~0, and
0 `products-missing` rows have hidden product data. So these are genuinely
single-source listings — the data is not there to auto-fix from what we have.

**But the single source is usually authoritative.** For the two worst states the
sole source is the state government's own grower registry:
- **GA**: 985 / 1,003 corroboration rows are from *Georgia Dept of Agriculture — Georgia Grown*.
- **TN**: 1,372 / 1,086 corroboration rows are from *Tennessee Dept of Agriculture — Pick TN Products*.
- **FL**: 850 are from *US Farm Trail*, a national **aggregator** (genuinely lower trust).

## Categorization (classification × severity), non-geo residue, all 9 states

| Family | Severity | Count | What it means / path |
|--------|----------|------:|----------------------|
| corroboration: single-source listing | LOW | 3,212 | Real farm, held by the 2-source rule. **1,993 clear if official directories self-corroborate.** |
| activity: no products/activity listed | MED | 879 | Directory gave name+location only. Enrich or accept. |
| geo-missing: no county/city | LOW | 295 | Backfill geography. |
| status: possibly closed | HIGH | 182 | **Needs research — may be closed.** |
| baseline: known farm not re-found | MED | 96 | Was in old canonical, not in new sources. |
| entity-type: is it a farm? | MED | 47 | Confirm it is an ag producer. |
| identity: name in multiple counties | MED | 22 | Dedup / disambiguate. |
| geo-conflict: county disagreement | LOW | 8 | Cross-source county conflict. |

Per-row detail (family, severity, `sole_source_tierA`, reason, name, county, city,
source, id) is in the **input artifact** below.

## The decision that unlocks ~2,000 rows (business call — not codex)

**Do we treat an official state Dept-of-Agriculture grower directory as
authoritative enough to publish a farm on its own (no second source)?**
A government grower registry is, by definition, authoritative on "is this a real
farm in this state." Recommended: **yes** for Tier-A official directories; keep the
2-source rule only for Tier-C national aggregators (US Farm Trail, EatWild,
PickYourOwn, LocalHarvest). This clears **1,993** rows (GA 921, TN 1,020, FL 27, +
others). It does **not** touch FL's aggregator bulk — that's Stream QA-B.

## Streams — each is one exclusive claim; do not stack, branch from `main`

### QA-A — Source-tier self-corroboration  *(tooling lane, not codex)*
Once the decision above is **yes**: add a `"tier": "authoritative" | "aggregator"`
field to each source in `sources/<region>/<ST>.json`, and a QA rule that clears a
corroboration-only blocker when the record's sole source is `authoritative`. This
edits `qa.py` (frozen for codex) — so it belongs to the tooling owner, not a codex
data session. Effect: ~1,993 residue → eligible on the next `run.py --state`.

### QA-B — Florida corroboration  *(codex, data lane)*
FL's 903 remaining corroboration rows are US-Farm-Trail-only. Author additional
**FL-specific** sources into `sources/southeast/FL.json` (regional/county extension
directories, Florida farmers-market associations, agritourism trails) so those
listings gain a second source. Acceptance: FL corroboration residue drops
materially after `run.py --state FL`; every added source verified against
`sources/SCHEMA.md`; no engine edits.

### QA-C — Closure / status research  *(codex, research)*  ← HIGH severity
The 182 `status: possibly closed` rows (filter the artifact:
`severity == HIGH`). For each, check whether the operation is currently active
(website live, recent social post, Google Business "open"). Produce
`build/qa-closure-decisions.csv` with `id, name, state, verdict(active|closed|unknown), evidence_url`.
This is the highest-value human-judgment slice — do it first among codex streams.

### QA-D — Activity / entity-type triage  *(codex, research)*
The 879 `activity-missing` + 47 `entity-type` rows: decide which are genuine farms
vs. non-farm businesses (wineries-only, retailers, offices). Produce
`build/qa-entity-decisions.csv` with `id, verdict(farm|nonfarm|unknown), category_if_farm`.
Rows confirmed `farm` from a Tier-A source publish once QA-A lands.

## Input artifact — regenerate any time

`build/qa-triage-southeast.csv` (4,741 rows). Regenerate:

```bash
cd 01-database/pipeline && python3 - <<'PY'
import json, csv
targets=["AR","FL","GA","LA","MS","NC","SC","TN","TX"]
TIERA=("department of agriculture","georgia grown","pick tennessee","picktn","farm to you",
       "certified sc","ncda","got to be nc","arkansas grown","genuine ms","ldaf",
       "kentucky proud","go texan","wv grown","visit nc farms","florida farm")
AGG=("us farm trail","eatwild","pickyourown","localharvest")
def tierA(s): s=s.lower(); return any(k in s for k in TIERA)
def classify(r):
    r=r.lower()
    if "closure" in r or "operating-status" in r: return ("status-possibly-closed","HIGH")
    if "confirm farm or agricultural-producer entity" in r: return ("entity-type","MED")
    if "products or farm activity missing" in r or "products or production scope" in r: return ("activity-missing","MED")
    if "same normalized name appears in multiple counties" in r: return ("identity-ambiguous","MED")
    if "canonical baseline farm not rediscovered" in r: return ("baseline-lost","MED")
    if "cross-directory conflict" in r: return ("geo-conflict","LOW")
    if "grade-e discovery" in r or "directory candidate needs independent" in r: return ("corroboration","LOW")
    if "county missing" in r or "city or safe public service area missing" in r or "county requires geography" in r: return ("geo-missing","LOW")
    return ("other","MED")
GEO={"county requires geography review","city or safe public service area requires review"}
def geo_only(x):
    p=[t.strip().lower() for t in x.split(";") if t.strip()]
    return bool(p) and all(z in GEO or z.startswith("missing geography") for z in p)
w=csv.writer(open("build/qa-triage-southeast.csv","w",newline=""))
w.writerow(["state","family","severity","sole_source_tierA","qa_reason","name","county","city","source","id"])
for st in targets:
    for f in json.load(open(f"data/{st}.json")):
        if f.get("eligible"): continue
        r=f.get("qa_reason","")
        if not r or geo_only(r): continue
        fam,sev=classify(r); src=(f.get("provenance") or {}).get("source","")
        w.writerow([st,fam,sev,tierA(src),r,f.get("name"),f.get("county"),f.get("city"),src,f.get("id")])
PY
```

## Out of scope here
Website/app presentation is a separate conversation. Regions outside the original
southeast set (OK/NM/AZ and the unconfigured regions) are parked until asked.
