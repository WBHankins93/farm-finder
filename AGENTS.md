# FarmFinder — Source of Truth

> Last updated: 2026-07-15 · Owner: Ben Hankins · Lives at `bdev/20-sproutflow/farm-finder/`

## What this is

FarmFinder is a three-track initiative to get underrepresented small farms online, starting in South Louisiana:

1. **Farm database** — a comprehensive database of local farms, starting with South Louisiana, then all of Louisiana, then state-by-state. Core observation driving this: ~90% of local farms in South Louisiana have no website — **verified against our own database** (89% of 81 LA farms in `01-database/local_farm_database.xlsx`, verified 2026-07-12; dashboard: `farmfinder-dashboard.html`). Note nuance: many are on Facebook; "no website" ≠ "no online presence at all" (30% of NOLA Metro farms have zero web presence including social).
2. **Sproutflow Studios outreach niche** — use the database as a lead list. Sproutflow builds these farms an online presence (mostly static sites, some with online ordering — reference point: rareseeds.com). The nature-related brand name is an immediate trust signal with this audience. This funds and grows Sproutflow while building the database.
3. **FarmFinder app** — long-term: a "Google Maps / Uber for local farms" built on the database. Test markets: South Louisiana + South Mississippi (two-state test), scale based on results.

**Note on geography:** "LA" in this project means **Louisiana**, not Los Angeles.

## How the tracks feed each other

Database → outreach leads → Sproutflow revenue + farm relationships → farms become seed content & early adopters for the app → app drives demand back to farms.

The database is the shared asset. Every outreach conversation should enrich it (contact info, products, seasonality, willingness to be listed).

## Repo layout

- `01-database/` — schema, collection SOP, and the farm data itself (CSV/xlsx now; migrate to real DB when the app track starts)
- `02-outreach/` — Sproutflow positioning, service tiers, outreach scripts and pipeline
- `03-app/` — public directory plus the staged production platform foundation
- `research/` — market opportunity brief, competitor notes, sourced stats

## Current state (2026-07-15)

- **Pre-cutover canonical authoring source is `research/local_farm_database_final.xlsx`, sheet `All Farms` — 315 source rows / 311 normalized farm names** (239 LA / 72 MS public listings after name-based merging). The machine-readable release contract is `03-app/site/config/source-of-truth.json`; validate it with `npm run data:validate` from `03-app/site/`.
- The public site uses `03-app/site/app/data/farms.json` with 311 mapped listings. PostgreSQL/PostGIS foundation migrations exist and pass locally, but the workbook has not been imported or cut over; PostgreSQL is not canonical yet.
- Older dashboards and v1/v2 workbooks remain historical snapshots, not editable authorities.
- Known identity-review groups: Butterfield Farm, Earth Friendly Farms, Faust Farms, and River Queen Greens each have two source rows. The public generator currently merges by normalized name; the PostgreSQL workflow will require evidence-based review.
- Current public artifact: 84 farms have a confirmed website and 227 do not (~73% without a confirmed website). The ~90% figure still applies only to the original field-collected South Louisiana cohort, not the expanded directory.
- Baseline stats computed: 89% of LA farms in DB lack a website; South MS is 47% online (different market dynamics between the two test states).
- Outreach plan drafted (`02-outreach/outreach-plan.md`) — 24 LA farms score high on outreach-fit (no site, active at markets).
- Market brief written (`research/market-opportunity-brief.md`), sourced.

## Key decisions

- **Start narrow:** South Louisiana only until the database + outreach loop is proven. Then South MS. Then one state at a time.
- **Sproutflow funds the mission:** outreach is revenue-first (site builds), database is the byproduct/asset.
- **Keep farm sites simple:** static-first, ordering only where the farm actually needs it. Don't over-engineer.
- **Marketplace functionality comes last:** the current app work is directory, data governance, and production platform foundation; ordering waits for coverage and farm relationships.

## Open questions

- Verify the "90% offline" claim with sourced data (USDA census, ag extension studies).
- Pricing for farm site builds (one-time vs. hosted/monthly retainer)?
- Database licensing/ownership if farms contribute data — terms needed before app launch.
- What counts as a "farm" for inclusion (acreage, sales channel, licensed vs. hobby)?

## Next actions

1. Import the pinned 315-row release into PostgreSQL staging and reconcile it to 311 candidate entities without silent merging.
2. Recompute the outreach-fit/contactability list against the 311-listing release, then pick 5 pilot farms.
3. Upgrade approximate geocodes to farm-confirmed locations during outreach; never expose a private exact location by default.

Done: market brief (sourced) ✓ · 311/311 public listings mapped ✓ · source-of-truth release validation ✓ · PostgreSQL/PostGIS foundation verified ✓
