# Public discovery API

The public farm explorer reads bounded, versioned responses from `/v1` instead
of downloading the complete national feed. All endpoints are anonymous,
read-only, and return public projections only.

## Endpoints

### `GET /v1/places`

Query parameters: `q` (two or more characters) and `limit` (maximum 8).
Results contain a stable place slug, city/state label, governed centroid, and
farm count. This first contract resolves cities and states only; it does not
send visitor input to an external geocoder.

### `GET /v1/farms`

Accepted parameters:

- `q`, `near`, `lat`, `lng`, `radiusMiles`
- `bbox=west,south,east,north`
- `category`, `product`, repeated or comma-delimited `services`
- `sort=distance|relevance|name`, opaque `cursor`, and `limit` (maximum 50)

The response contains bounded farm summaries, the exact match count, an opaque
next cursor, normalized scope, active sort, and the dataset release identifier.
Filters use AND across groups and across selected sales channels.

### `GET /v1/farms/map`

This endpoint accepts the same filters plus `zoom`. It returns only public,
mappable records. Exact shared coordinates are always represented as a terminal
cluster; result sets over 2,000 points use a stable 64-pixel world-grid at the
requested zoom. Clusters include their centroid, count, bounds, and whether the
client should expand the cluster or show its represented farms.

### `GET /v1/farms/:id`

Returns one public farm record by canonical ID or `404` when it is unavailable.
The explorer uses this endpoint when a map-selected farm is outside the current
list page.

## Location privacy

Browser location is requested only after an explicit user action. The client
rounds coordinates before sending a nearby query, keeps them out of shareable
URLs, and must not send them to analytics. Production request logging must
redact `lat` and `lng` values.

## Data adapter

The first mergeable contract is backed by the current canonical web artifact so
the routes remain deterministic in development and CI. The national explorer
adapter replaces that source with the governed PostgreSQL/PostGIS release while
preserving these response shapes.
