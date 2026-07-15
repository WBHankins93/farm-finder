# FarmFinder — Source of Truth

> Last updated: 2026-07-15 · Owner: Ben Hankins · Lives at `farm-finder/`

## What this is

FarmFinder is a two-track product initiative to make independent farms easier to find, starting in South Louisiana:

1. **Farm database** — a comprehensive database of local farms, starting with South Louisiana, then all of Louisiana, then state-by-state. Core observation driving this: ~90% of local farms in South Louisiana have no website — **verified against our own database** (89% of 81 LA farms in `01-database/local_farm_database.xlsx`, verified 2026-07-12; dashboard: `farmfinder-dashboard.html`). Note nuance: many are on Facebook; "no website" ≠ "no online presence at all" (30% of NOLA Metro farms have zero web presence including social).
2. **FarmFinder app** — long-term: a "Google Maps / Uber for local farms" built on the database. Test markets: South Louisiana + South Mississippi (two-state test), scale based on results.

### Standalone product boundary

FarmFinder is its own standalone product. Its README, application, UI, architecture, database, API, roadmap, telemetry, and product documentation must not contain or depend on any separate company's branding, business-development workflow, services, customer records, revenue strategy, or promotions.

FarmFinder still retains source-backed website, social, online-store, map, product, market, contact-visibility, provenance, and verification facts because those fields directly support farm discovery and directory quality. Unrelated private business material must remain outside the FarmFinder product and must not become a FarmFinder schema or service dependency.

**Note on geography:** "LA" in this project means **Louisiana**, not Los Angeles.

## How the tracks feed each other

Database coverage → verified listings + farm participation → consumer discovery → demand back to farms.

The database is the FarmFinder product asset. Every correction or voluntary contribution must enrich it through governed provenance and privacy rules, regardless of where the information originated.

## Repo layout

- `01-database/` — schema, collection SOP, and the farm data itself (CSV/xlsx now; migrate to real DB when the app track starts)
- `03-app/` — public directory plus the staged production platform foundation
- `research/` — market opportunity brief, competitor notes, sourced stats

## Current state (2026-07-15)

- **Pre-cutover canonical authoring source is `research/local_farm_database_final.xlsx`, sheet `All Farms` — 315 source rows / 311 normalized farm names** (239 LA / 72 MS public listings after name-based merging). The machine-readable release contract is `03-app/site/config/source-of-truth.json`; validate it with `npm run data:validate` from `03-app/site/`.
- The public site uses `03-app/site/app/data/farms.json` with 311 mapped listings. Cutover staging began 2026-07-15: the pinned workbook is stored in local versioned S3-compatible object storage and all 315 raw rows are registered as a validated PostgreSQL release. Canonical normalization, reconciliation, managed storage, promotion, and API cutover remain; PostgreSQL is not canonical yet.
- Older dashboards and v1/v2 workbooks remain historical snapshots, not editable authorities.
- Known identity-review groups: Butterfield Farm, Earth Friendly Farms, Faust Farms, and River Queen Greens each have two source rows. The public generator currently merges by normalized name; the PostgreSQL workflow will require evidence-based review.
- Current public artifact: 84 farms have a confirmed website and 227 do not (~73% without a confirmed website). The ~90% figure still applies only to the original field-collected South Louisiana cohort, not the expanded directory.
- Baseline stats computed: 89% of LA farms in DB lack a website; South MS is 47% online (different market dynamics between the two test states).
- Market brief written (`research/market-opportunity-brief.md`), sourced.

## Key decisions

- **Start narrow:** South Louisiana only until the database + farm-participation + consumer-discovery loop is proven. Then South MS. Then one state at a time.
- **Keep FarmFinder standalone:** no separate-company branding, commercial workflow, customer system, or promotion belongs in the product.
- **Retain useful digital-presence facts:** verified website, social, store, map, and contact-visibility data remain part of the farm directory.
- **Marketplace functionality comes last:** the current app work is directory, data governance, and production platform foundation; ordering waits for coverage, farm participation, and demonstrated consumer demand.

## Open questions

- Verify the "90% offline" claim with sourced data (USDA census, ag extension studies).
- Database licensing/ownership if farms contribute data — terms needed before app launch.
- What counts as a "farm" for inclusion (acreage, sales channel, licensed vs. hobby)?

## Next actions

1. Normalize and reconcile the staged 315-row PostgreSQL release to 311 candidate entities without silent merging, beginning with the four known identity-review groups.
2. Freeze the next Mississippi collection milestone as a new immutable release without overwriting the validated v1 release.
3. Provision managed versioned object storage and managed PostgreSQL backups before promotion.
4. Recompute contactability for FarmFinder participation, then recruit 5 farms for listing corrections, claims, or interviews.

Done: market brief (sourced) ✓ · 311/311 public listings mapped ✓ · source-of-truth release validation ✓ · PostgreSQL/PostGIS foundation verified ✓
