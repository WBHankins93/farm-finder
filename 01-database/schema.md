# Farm Database Schema (v2 workbook contract)

> Historical schema for the original 112-farm workbook. Do not use this file to choose the current canonical dataset.

**Current pre-cutover authority:** `research/local_farm_database_final.xlsx`, sheet `All Farms`, governed by `03-app/site/config/source-of-truth.json` and `03-app/site/docs/data-governance/source-of-truth.md`. Release `2026-07-15-enriched-v2` contains 299 canonical rows and 299 normalized-name entities. `local_farm_database.xlsx` remains the v1 historical workbook.

The production PostgreSQL/PostGIS schema and index decisions now live in `03-app/site/packages/db/`. Until explicit cutover, the final research workbook is the editable authoring source; after cutover, workbooks become immutable imports/exports and PostgreSQL becomes canonical.

The canonical workbook now includes stable record IDs, record/website/contact statuses, direct social URLs, last-verified date, verification sources, and identity notes. The `Database Summary`, `Research Queue`, `QA Queue`, and `Source Log` sheets are part of the same workbook; they are not separate databases. **Geocoding added 2026-07-12:** the historical v1 sheets include `Latitude`, `Longitude`, `Geo Precision`, and `Geo Source`. Region-precision rows use a representative-city proxy; upgrade them to farm-confirmed public locations during outreach. The xlsx's `Web Presence Score` (0–10) remains a useful prioritization field.

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
| record_id | string | Stable workbook identifier, currently `FF-0001` pattern |
| record_status | enum | Canonical listing or a future reviewed status |
| website_verification_status | string | Reachability/research result and retry outcome |
| facebook_url / instagram_url | string | Direct public outreach paths when available |
| contact_status | enum | direct public contact / social outreach only / no public contact found |
| last_verified | date | Date of the latest evidence-backed field or reachability check |
| verification_source | string | One or more URLs supporting the current assertion |
| identity_notes | string | Duplicate, alias, geography, or inclusion cautions |
| date_added / date_verified | date | Data goes stale — run automated checks every six months |

## Collection SOP (repeatable per region — good future Claude Skill candidate)

1. Pull candidate lists: farmers market vendor rosters, LSU AgCenter / MSU Extension directories, LocalHarvest, state ag dept registries, CSA directories, Facebook groups.
2. Dedupe by name + parish.
3. For each farm: check for website, socials, Google Maps listing, online ordering. Fill booleans.
4. Record `Verification Source` and `Last Verified`.
5. Add unresolved website, contact, identity, and geography issues to `QA Queue`.
6. Compute state and region stats: % with website, % with any online presence, direct contact coverage, and county coverage.
