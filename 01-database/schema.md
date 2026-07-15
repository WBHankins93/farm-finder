# Farm Database Schema (v1)

> Historical schema for the original 112-farm workbook. Do not use this file to choose the current canonical dataset.

**Current pre-cutover authority:** `research/local_farm_database_final.xlsx`, sheet `All Farms`, governed by `03-app/site/config/source-of-truth.json` and `03-app/site/docs/data-governance/source-of-truth.md`. The pinned release contains 315 source rows and 311 normalized-name candidates. `local_farm_database.xlsx` remains the v1 historical workbook.

The production PostgreSQL/PostGIS schema and index decisions now live in `03-app/site/packages/db/`. Until explicit cutover, the final research workbook is the editable authoring source; after cutover, workbooks become immutable imports/exports and PostgreSQL becomes canonical.

Fields worth adding to the xlsx that the draft schema had: `outreach_status`, `date_verified`, `source`. **Geocoding added 2026-07-12:** columns `Latitude`, `Longitude`, `Geo Precision`, `Geo Source` on all three farm sheets — 112/112 rows geocoded (64 city-level via GeoNames, 5 small communities via Wikipedia/GNIS, 48 at area/parish/region precision because the row only lists a vague region like "S. Louisiana" or "MS Gulf Coast"). Region-precision rows use a representative-city proxy; upgrade them to true coordinates as street addresses are collected during outreach. Pre-geocoding backup: `local_farm_database.backup-2026-07-12.xlsx`. The xlsx's `Web Presence Score` (0–10) is a good prioritization field the draft lacked — keep it.

**Baseline stats (computed 2026-07-12):** NOLA Metro: 56 farms, 7% with website; South Louisiana: 26 farms, 19%; combined LA: 89% without a website. South Mississippi: 30 farms, 47% with website — a materially more-online market.

## Fields

| Field | Type | Notes |
|---|---|---|
| farm_id | string | `LA-SO-0001` pattern: state, region, sequence |
| name | string | Legal/trade name |
| region | string | e.g. `south-la`, `south-ms` |
| parish_county | string | Parish (LA) / county (MS) |
| city | string | |
| address | string | Optional at first pass |
| lat / lng | decimal | Geocode later in bulk; required before app launch |
| products | string | Semicolon-separated: produce; eggs; beef; honey... |
| seasonality | string | Free text for now |
| sales_channels | string | farmstand; farmers-market; csa; wholesale; online |
| has_website | bool | Core metric — this is the stat we're building |
| website_url | string | |
| has_social | bool | |
| social_urls | string | |
| has_online_ordering | bool | |
| google_maps_listed | bool | Distinct from website — many are map-listed but siteless |
| phone / email | string | |
| contact_name | string | |
| source | string | Where we found them (market roster, ag ext list, drive-by, referral) |
| outreach_status | enum | none / contacted / replied / meeting / client / declined |
| outreach_notes | string | |
| date_added / date_verified | date | Data goes stale — verify annually |

## Collection SOP (repeatable per region — good future Claude Skill candidate)

1. Pull candidate lists: farmers market vendor rosters, LSU AgCenter / MSU Extension directories, LocalHarvest, state ag dept registries, CSA directories, Facebook groups.
2. Dedupe by name + parish.
3. For each farm: check for website, socials, Google Maps listing, online ordering. Fill booleans.
4. Record `source` and `date_verified`.
5. Compute region stats: % with website, % with any online presence. This is both the pitch stat and the app's coverage metric.
