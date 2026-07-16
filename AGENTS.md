# FarmFinder — Source of Truth

> Last updated: 2026-07-15 · Owner: Ben Hankins · Lives at `farm-finder/`

## What this is

FarmFinder is a two-track product initiative to make independent farms easier to find, starting in South Louisiana:

1. **Farm database** — a comprehensive database of local farms across the continental United States, built state-by-state starting with South Louisiana and then all of Louisiana. Core observation driving this: ~90% of local farms in South Louisiana have no website — **verified against our own database** (89% of 81 LA farms in `01-database/local_farm_database.xlsx`, verified 2026-07-12; dashboard: `farmfinder-dashboard.html`). Note nuance: many are on Facebook; "no website" ≠ "no online presence at all" (30% of NOLA Metro farms have zero web presence including social).
2. **FarmFinder app** — long-term: a continental-U.S. "Google Maps / Uber for local farms" built on the database. South Louisiana + South Mississippi are the first test markets, not the product boundary; coverage scales state-by-state based on results.

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
- `research/` — market opportunity brief, sourced stats, and four-file state-release contracts under `research/state-expansions/<STATE>/`

## Current state (2026-07-15)

- **Pre-cutover canonical authoring source is `research/local_farm_database_final.xlsx`, sheet `All Farms` — 299 canonical rows / 299 record IDs** (220 LA / 79 MS). The same workbook contains `Database Summary`, `Research Queue`, `QA Queue`, and `Source Log`; no separate farm database file is authoritative. The machine-readable release contract is `03-app/site/config/source-of-truth.json`; validate it with `npm run data:validate` from `03-app/site/`.
- The public site uses `03-app/site/app/data/farms.json` with 299 mapped listings. Cutover staging began 2026-07-15 with historical release `2026-07-13-final-v1`; the corrected `2026-07-15-enriched-v2` workbook must be staged as a new immutable release before promotion. PostgreSQL is not canonical yet.
- Older dashboards and v1/v2 workbooks remain historical snapshots, not editable authorities.
- Butterfield Farm, Earth Friendly Farms, Faust Farms, and River Queen Greens were evidence-reviewed and merged to one canonical row each; their separate source provenance remains in `Source Tab` and `Source Log`. No exact normalized-name duplicate groups remain.
- Current canonical workbook: 88 rows are flagged as having a website, 85 contain a website URL, and 3 flagged rows still need URL research. Direct public contacts exist for 243 listings; 56 lack a direct phone/email, including 42 with a social-only outreach path and 14 with no public outreach path.
- Mississippi's current canonical slice contains 79 reviewed rows after five Louisiana-market records were corrected to their Mississippi home state. Mississippi is not statewide-complete: historical staging still contains 262 candidates, including 211 new candidates, and 17 county gaps that must be reconciled before statewide promotion.
- Mississippi staging contains 262 candidates from three collection passes: 51 existing/possible canonical matches and 211 new candidates. It covers 65 of 82 counties; 17 county gaps remain explicitly queued.
- Alabama's corrected coverage-reviewed private release contains 1,057 source observations reconciled to 810 retained entities: 799 staged-eligible and 11 in explicit research/QA. All 67 counties have a final searched status and at least one eligible candidate. Alabama passes the four-file contract and coverage gates, but is not approved, promotion-ready, or part of the LA/MS canon.
- Texas's corrected coverage-reviewed private release contains 1,062 source and curator observations reconciled to 883 retained entities: 716 staged-eligible and 167 in explicit research/QA. All 254 counties have a final searched status; 179 have candidates, 75 are `searched_none_found`, and 171 have at least one eligible entity. Texas passes the four-file contract and coverage gates, but is not approved, promotion-ready, or part of the LA/MS canon.
- Every new or rebuilt state follows `01-database/state-release-contract.md`: exactly four committed files, retained staged candidates, append-only decisions, and private evidence bound by version IDs and SHA-256 checksums. Validate all state contracts with `npm run states:validate` from `03-app/site/`.
- Baseline stats computed: 89% of LA farms in DB lack a website; South MS is 47% online (different market dynamics between the two test states).
- Market brief written (`research/market-opportunity-brief.md`), sourced.

## Key decisions

- **Start narrow, build national:** South Louisiana only until the database + farm-participation + consumer-discovery loop is proven. Then South MS. Then one state at a time until the continental United States is covered.
- **Keep FarmFinder standalone:** no separate-company branding, commercial workflow, customer system, or promotion belongs in the product.
- **Retain useful digital-presence facts:** verified website, social, store, map, and contact-visibility data remain part of the farm directory.
- **Keep state evidence out of Git:** raw observations, request logs, and deterministic QA/identity/geography outputs live in versioned object storage; the committed release manifest is their integrity contract.
- **Marketplace functionality comes last:** the current app work is directory, data governance, and production platform foundation; ordering waits for coverage, farm participation, and demonstrated consumer demand.

## Open questions

- Verify the "90% offline" claim with sourced data (USDA census, ag extension studies).
- Database licensing/ownership if farms contribute data — terms needed before app launch.
- What counts as a "farm" for inclusion (acreage, sales channel, licensed vs. hobby)?

## Next actions

1. Continue high-priority research for the 3 website flags without URLs and 56 listings without direct phone/email; work the explicit `QA Queue` and preserve evidence in `Source Log`.
2. Continue Mississippi county-gap and candidate identity review; do not promote the 211 new candidates without evidence-based inclusion and identity checks.
3. Stage `2026-07-15-enriched-v2` as a new immutable release without overwriting validated v1.
4. Provision managed versioned object storage and managed PostgreSQL backups before promotion.
5. Resolve the 11 Alabama and 167 Texas QA entities, copy each release's immutable evidence to managed storage, and record approval only after the current release fingerprint passes every promotion gate. The next collection order is Arkansas, Tennessee, Georgia, then Florida.

Done: market brief (sourced) ✓ · 299/299 public listings mapped ✓ · source-of-truth release validation ✓ · PostgreSQL/PostGIS foundation verified ✓
