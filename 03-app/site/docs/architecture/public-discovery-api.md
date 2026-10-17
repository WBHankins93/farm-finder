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

## Serving layer

The routes are backed by a compact, column-oriented index built from the
committed state store by `scripts/discovery_index.py` and published as the
static asset `public/national-index.bin`. `app/lib/discovery-index.ts` inflates
it once per isolate and creates typed-array views over the single buffer.

This shape is load-bearing, not an optimization. The straightforward
alternative — expanding the 68,618-record feed into JavaScript objects — was
measured at **152 MB retained**, and a Cloudflare Workers isolate is capped at
**128 MB**, so it passes under Node and then fails on the deploy target. The
index measures 18.9 MB warm and 37.7 MB once the id-lookup map is built.

Keeping the dataset in an asset rather than in the bundle also keeps the worker
script at 0.60 MiB compressed, well inside the 10 MiB Paid and 3 MiB Free
limits. `scripts/check-deploy-budget.mjs` asserts both limits after every build.

| Structure | Purpose | Resident |
| --- | --- | --- |
| `latitude`/`longitude` (Float64) | radius and bbox filtering, clustering | 1.1 MB |
| `flags` (Uint16), `category`, `precision`, `productMask` | facet filters as bit tests | 0.4 MB |
| `nameRank` (Uint32) | A–Z ordering as an integer compare | 0.3 MB |
| packed ASCII search blob + offsets | free-text match and field-weighted relevance | 14.5 MB |
| packed UTF-8 display blob + offsets | full records, decoded only for returned rows | 19.7 MB |
| precomputed place centroids | `/v1/places` without walking the dataset | 1.5 MB |

Free-text search scans the blob once per token and intersects the resulting
bitsets, rather than scanning the dataset once per record. Warm queries measure
about 8 ms.

### Ordering is precomputed, not locale-dependent

`nameRank` is computed at build time from a folded, punctuation-trimmed name.
The previous implementation sorted with `String.localeCompare`, whose result
depends on the runtime's default locale — which is not guaranteed to be the
same in a Worker as under Node. Cursor pagination needs one total order, so the
order is now fixed in the artifact. A–Z listings therefore interleave
punctuation- and digit-leading names differently than before; every other
response — totals, scopes, distances, map features, places, and record payloads
— is byte-identical to the previous implementation.

### Relationship to the PostgreSQL/PostGIS cutover

This is the pre-cutover serving layer, and it is what runs today. The governed
PostgreSQL/PostGIS release remains the planned authority; when it is promoted,
it replaces the index behind these same response shapes. Nothing in the public
application queries PostgreSQL today.
