# FarmFinder site architecture

## Product shape

The first release is a public discovery and knowledge tool, not a marketplace. It has one primary route and one job: help someone ask a practical local-food question, browse the product landscape, understand how each farm sells, and see verified directory matches on a map.

The page is organized in three layers:

1. A compact mission and coverage introduction.
2. A dataset-grounded question box for product, place, farm, season, and shopping-method questions.
3. A product field guide with specific product filters and seasonal context.
4. The discovery workspace: full-text search, state/category/product/service filters, synchronized farm list, clustered map, and farm detail panel.
5. Detailed farm profiles with summaries, products, sales paths, notes, contact options, source provenance, and location confidence.
6. A public update ledger and trust layer explaining source coverage, approximate locations, and the listing-update path.

## Data architecture

- Source of record: `research/local_farm_database_final.xlsx`, sheet `All Farms`.
- Release contract: `config/source-of-truth.json` pins the workbook checksum, structure, row count, candidate count, states, and known duplicate groups.
- Existing geocodes: recovered from `farmfinder-dashboard-v2.html` for the earlier 235-farm dataset.
- New locations: city/state geocodes are cached in `scripts/geocode-cache.json`; no geocoding service is called by the live site.
- Build artifact: `app/data/farms.json` contains 299 deduplicated listings. Duplicate names are merged and boolean selling options use an “any source says yes” rule.
- Refresh path: run `scripts/generate-farms.py` after updating the workbook. Add `--geocode` only when new city/state combinations require coordinates.

This static-first approach makes the directory fast, inexpensive, deployable without credentials, and resilient to third-party API downtime. The JSON record shape is already compatible with a later database migration.

## Production foundation status

- `packages/db/migrations/` defines the PostgreSQL/PostGIS canonical model, source evidence, official geography, coverage regions, auth/claims foundation, full-text retrieval, object metadata, jobs, outbox, and audit.
- `docs/architecture/index-register.md` records the query, cost, and review plan for every custom index.
- `infra/compose.yaml` bootstraps and verifies the schema on local PostGIS.
- `docs/data-governance/source-of-truth.md` defines farm, area, import, dedupe, and release promotion workflows.
- The API, worker, PostgreSQL importer, and database cutover are not implemented yet. The public site still reads the generated JSON artifact.

## Map architecture

MapLibre GL renders the map with an OpenFreeMap base style. Farm points are delivered as GeoJSON and clustered in the browser. Search and filters replace the map source in place, while list selection updates a separate highlight layer and flies the map to the selected farm.

Locations marked below street precision are deliberately described as approximate. The interface tells visitors to confirm before visiting.

## Interaction model

- Search covers name, product, town, parish/county, region, market presence, and notes.
- Filters can be combined across state, broad farm category, twelve specific product guides, and five ways to buy.
- Ask FarmFinder parses the question into products, places, farm names, seasons, and ways to buy; every result is backed by directory records and never claims live availability.
- Desktop keeps map and list visible together; mobile uses an explicit list/map switch.
- Farm profiles provide the detailed reading layer, while map selection keeps location exploration fast.
- Empty results provide a single reset action.

## Next platform steps

1. Import the pinned enriched workbook into immutable staging/source tables and reconcile its 299 rows to 299 candidate entities; retain the historical 315-row release separately.
2. Build the versioned read-only API and structured query tools against PostgreSQL.
3. Preserve source attribution and field-level verification dates during canonical promotion.
4. Add exact farm-gate coordinates only with farmer confirmation.
5. Introduce authentication only for claim and management flows; public discovery remains account-free.
