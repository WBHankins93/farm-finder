# FarmFinder site architecture

## Product shape

The first release is a public discovery tool, not a marketplace. It has one primary route and one job: let someone search the full farm library, understand how each farm sells, and see the results on a map.

The page is organized in three layers:

1. A compact mission and coverage introduction.
2. The discovery workspace: full-text search, state/category/service filters, synchronized farm list, clustered map, and farm detail panel.
3. A trust layer explaining source coverage, approximate locations, and the listing-update path.

## Data architecture

- Source of record: `research/local_farm_database_final.xlsx`, sheet `All Farms`.
- Existing geocodes: recovered from `farmfinder-dashboard-v2.html` for the earlier 235-farm dataset.
- New locations: city/state geocodes are cached in `scripts/geocode-cache.json`; no geocoding service is called by the live site.
- Build artifact: `app/data/farms.json` contains 311 deduplicated listings. Duplicate names are merged and boolean selling options use an “any source says yes” rule.
- Refresh path: run `scripts/generate-farms.py` after updating the workbook. Add `--geocode` only when new city/state combinations require coordinates.

This static-first approach makes the directory fast, inexpensive, deployable without credentials, and resilient to third-party API downtime. The JSON record shape is already compatible with a later database migration.

## Map architecture

MapLibre GL renders the map with an OpenFreeMap base style. Farm points are delivered as GeoJSON and clustered in the browser. Search and filters replace the map source in place, while list selection updates a separate highlight layer and flies the map to the selected farm.

Locations marked below street precision are deliberately described as approximate. The interface tells visitors to confirm before visiting.

## Interaction model

- Search covers name, product, town, parish/county, region, market presence, and notes.
- Filters can be combined across state, farm category, and five ways to buy.
- Desktop keeps map and list visible together; mobile uses an explicit list/map switch.
- Selecting a list record and selecting a map marker share the same state and detail panel.
- Empty results provide a single reset action.

## Next platform steps

1. Move records to a real database when farmers can claim or edit listings.
2. Preserve source attribution and field-level verification dates during migration.
3. Add exact farm-gate coordinates only with farmer confirmation.
4. Add market entities and farm-to-market relationships before ordering.
5. Introduce authentication only for claim and management flows; public discovery should remain account-free.
