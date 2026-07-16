# Pipeline enrichment plan

> Drafted 2026-07-16 · Extends the [scalable data pipeline standard](scalable-data-pipeline.md).
> These are planned stages and policies; each lands with its own tooling and tests.

## Purpose

Collection and cleansing now outpace verification. The 2026-07-16 review measured
5,984 eligible rows against 7,060 QA rows across eight states, with geocoding
coverage ranging from 88% (AR) down to 0% (TN). This plan adds three enrichment
stages and one ingestion policy so throughput scales without lowering the
verification standard.

## 1. Geocoding enrichment stage

Geocoding must never block eligibility, QA resolution, or verification — it is a
display concern with privacy rules, not a trust gate.

- **Where:** a batch stage between eligible handoff and final verification,
  operating on `eligible-entities.csv` exports. It writes derived coordinates and
  an explicit precision label; it never edits identity, evidence, or status fields.
- **Precision ladder:** `farm_confirmed_exact` (farm-owner evidence only) →
  `public_business_address` → `city_centroid` → `county_centroid`. Every published
  coordinate carries its precision label; the public map already displays
  location-confidence language.
- **Privacy:** internal addresses (`address_internal`) may be geocoded only to
  produce *reduced-precision* public coordinates, consistent with
  `public_location_classification`. Never emit exact coordinates for
  internal-only addresses.
- **Mechanics:** reuse the FCC/Census geocoder paths already in
  `collect_southeast.py` and the cache pattern in
  `03-app/site/scripts/geocode-cache.json`; three attempts, cached results,
  deterministic reruns. Target: every eligible row has at least a county-centroid
  coordinate and a precision label.

## 2. Cross-state market presence and referrals

Farms operate across state lines: a Mississippi farm may sell at a Louisiana
farmers market, an expo, or a fair. Today the collector records an
`outside_jurisdiction` exclusion in the collecting state (correct — states are the
completeness boundary) but nothing guarantees the farm is picked up by its home
state's research queue.

- **Referral queue:** every `outside_jurisdiction` exclusion must also emit a
  referral record for the home state: farm name, evidence, source URL, retrieval
  date, and the observed market/channel presence in the collecting state. Store
  referrals under the home state's research inputs so its next collection or QA
  pass consumes them (a `referrals.csv` staged with collection inputs, not a
  fifth committed contract file).
- **Sales-presence overlay:** the home-state entity retains the out-of-state
  market relationship as a sales-channel fact (`farmers_market_sales` plus the
  market's state) rather than as a second identity. One farm, one home state,
  many market states. This maps onto the planned farm-to-market relationship
  tables in the PostgreSQL schema.
- **Non-deletion unchanged:** the exclusion in the collecting state remains
  append-only and evidence-cited; the referral is additive.

## 3. Automated corroboration

80–94% of eligible rows rest on a single observation. Verification of ~6,000
rows one at a time is the throughput cliff. Corroboration that is deterministic
should not consume human QA time.

- **Website liveness pass:** for rows with a farm-owned `website_url`, an
  automated three-attempt fetch with current-activity language detection
  (`audit_operation_evidence.dated_active_excerpt` already implements the
  heuristic) can generate a curator-verification observation at grade C. Human
  review is still required to *promote*; the automation only assembles evidence.
- **Cross-directory matching:** an eligible row appearing in two independent
  already-collected sources (e.g., a state directory and LocalHarvest) with
  consistent geography/contact is machine-corroborable; conflicting fields route
  to QA with the specific conflict named.
- **Decision hygiene rule:** every `corroborate`/`correct` decision must be
  reflected in its entity row (added observation or updated grades) in the same
  release change. The validator's evidence-grade gate now reads decision
  evidence, but entity rows should not silently lag their decisions. Known
  backlog instance: TX `Davis 20 Beef` (decision `txreview_20260715_097`).
- **Boundary:** automation never invents evidence and never excludes. It
  upgrades evidence grades with cited, dated fetches, or it adds a named QA
  blocker. Ambiguity stays human.

## 4. Source-tier ingestion policy

One low-signal source can create thousands of QA rows: the Tennessee Century
Farms registry (2,228 observations, a historic designation without
consumer-channel evidence) drove most of Tennessee's 3,799-row QA queue.

Before a source is collected, classify it:

| Tier | Meaning | Pipeline effect |
|---|---|---|
| `candidate` | Directory implies a currently operating, discoverable producer | Observations create candidates (current behavior) |
| `identity_hint` | Registry proves identity/history but not current consumer-facing operation | Observations only corroborate or enrich candidates that another source created; they never create standalone QA rows |
| `excluded_source` | Source fails reliability or scope review | Logged in the source plan with a decision, never parsed into candidates |

Record the tier in the `state.yaml` source plan. Recollection of Tennessee under
this policy should reclassify Century-Farms-only candidates rather than leaving
them as open-ended QA debt.

## Sequencing

1. Source-tier policy (documentation + validator awareness) — cheapest, stops new
   QA debt first.
2. Geocoding enrichment — unblocks the map product for existing eligible rows.
3. Automated corroboration — converts single-source eligible rows into
   verifiable ones and shrinks QA time per record.
4. Cross-state referrals — grows with each newly collected state.
