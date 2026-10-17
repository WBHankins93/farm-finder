# Deployment readiness — national feed cutover

> Point-in-time report for branch `claude/national-feed-public-cutover`
> (commit `f53ff81`), 2026-09-14. Living detail lives in
> [`docs/architecture/public-discovery-api.md`](../architecture/public-discovery-api.md),
> [`docs/data-governance/source-of-truth.md`](../data-governance/source-of-truth.md),
> and [`docs/testing/discovery-acceptance.md`](../testing/discovery-acceptance.md);
> this file records what was measured and what is still open.

## 1. Why the app was not consuming the national output

Two independent blockers, both invisible to a passing test run:

1. **The national experience was behind an unset flag.** `app/page.tsx` read
   `process.env.EXPLORER_V2`, which nothing sets. Every default build returned
   the 299-row workbook explorer and shipped `public/farms.json` (45 MB) as a
   static asset. Cloudflare rejects assets over 25 MiB, so the default build
   was not deployable at all.
2. **The `/v1` routes could not have run on the deploy target.** They expanded
   the full feed into JavaScript objects at module scope. Measured with
   `--expose-gc` after collection: **152.5 MB retained** for the parsed array,
   **156.2 MB** with the id index. A Cloudflare Workers isolate is capped at
   **128 MB**. The design passed locally under Node and would have OOMed in
   production.

## 2. Architecture selected

A compact, column-oriented index published as a static asset, queried by the
existing bounded `/v1` routes. Chosen over Cloudflare D1 and a runtime change
because it needs no new infrastructure and does not depend on the gated
PostgreSQL/PostGIS cutover.

| | Before | After |
| --- | --- | --- |
| Dataset in an isolate | 152 MB retained | **18.9 MB** warm, **37.7 MB** worst case |
| Worker script (gzip) | 5.50 MiB | **0.60 MiB** |
| Largest static asset | 45 MB (rejected) | **8.00 MiB** |
| `dist/client` total | 50 MB | 6.1 MB |
| Warm query | — | **~8 ms** (in-process), ~18 ms over HTTP |

Facets (lat/lng, service bitflags, category, geo precision, product mask, name
rank) are typed arrays over one inflated buffer. Searchable text is a single
packed ASCII blob scanned once per token with `indexOf`, then intersected as
bitsets. Display text is packed UTF-8, decoded only for the rows a response
returns. Place centroids and dataset totals are precomputed at build time.

## 3. Data flow

```
01-database/pipeline/data/<ST>.json   72,396 collected records (committed)
        │  publish projection + privacy.py gate
        ▼
     68,618 eligible records            3,778 withheld by QA/eligibility
        │  scripts/build-web-feed.py — enforces app/data/feed-contract.json
        ├──► public/national-index.bin              (8.4 MB, generated, ignored)
        ├──► app/data/directory-stats.generated.json (all displayed counts)
        └──► public/farms.json          only when FARMFINDER_LEGACY_FEED=1
        │
        ▼
app/lib/discovery-index.ts  → /v1/farms, /v1/farms/map, /v1/farms/:id, /v1/places
        ▼
app/page.tsx + DiscoveryWorkspace (default build)
```

A contract violation aborts the build; it never writes a partial artifact.

## 4. Record counts

| Measure | Value |
| --- | --- |
| Collected across 50 states | 72,396 |
| Passing publication gates | 68,618 |
| Withheld by QA/eligibility | 3,778 |
| States represented | 50 / 50 |
| Mappable (public map locations) | 54,821 |
| Farm-gate points | 46,111 |
| County-approximate | 3,717 |
| City-level | 4,993 |
| Ungeocoded (listed, not mapped) | 13,797 |
| Without a confirmed website | 51,984 |
| With a privacy-cleared public contact | 10,308 |
| Distinct places in the autocomplete | 13,925 |

Product counts were corrected this change. The committed figures were both
stale and wrong: `"bee"` matched `"beef"`, tagging **3,165 beef and livestock
farms as honey producers** (43% of the honey count), and `"egg"` matched
`"eggplant"` (850 rows). Whole-word matching now applies to `bee`, `crab`,
`duck`, `egg`, `hog`, `milk`, `plant`, `rice`. `fish` is deliberately excluded
so catfish, shellfish and swordfish still classify as seafood.

| Guide | Was displayed | Now | Guide | Was displayed | Now |
| --- | --- | --- | --- | --- | --- |
| Vegetables | 16,939 | 17,346 | Honey | 7,375 | **4,271** |
| Fruit | 7,691 | 7,757 | Dairy | 1,004 | 995 |
| Eggs | 3,134 | **2,320** | Seafood | 372 | 370 |
| Beef | 1,838 | 1,844 | Rice | 593 | 519 |
| Pork | 982 | 990 | Flowers | 6,290 | 5,958 |
| Poultry | 1,853 | 1,860 | Mushrooms | 478 | 478 |

## 5. Privacy validation

`scripts/build-web-feed.py` fails the build, rather than warning, on any of:

- a published contact on a farm with no farm-published website (the only case
  `pipeline/privacy.py` promotes),
- an address-shaped string in a contact field,
- a geocoded record sitting at `0,0`,
- any field outside the 25-field public projection,
- a record with no `source` provenance.

Result on the current release, printed by every build:

```
privacy gates: 0 contacts without a public website, 0 address-shaped contacts,
0 null-island points, 0 internal fields, 68618/68618 records carry provenance
```

Each gate has a negative test in `scripts/tests/test_publication_gates.py`, and
`tests/rendered-html.test.mjs` re-checks the contact rule and the field
allowlist against live `/v1` responses rather than trusting the build alone.

## 6. Tests and builds run

| Check | Result |
| --- | --- |
| `npm run lint` | clean |
| `npx tsc --noEmit` | clean |
| `npm run test:unit` | 28 passed |
| `npm test` (build + rendered HTML) | 7 passed |
| `npm run data:gates` | 17 passed |
| `npm run build` + deploy budget | worker 0.60/10.00 MiB, largest asset 8.00/25.00 MiB |
| `python3 -m unittest 01-database/pipeline/tests` | 48 passed |
| `python3 -m unittest 01-database/tools/tests` | 3 passed |
| `01-database/tools/validate_state_releases.py` | clean |

**Equivalence check against the previous implementation** (20 query shapes,
9 map requests at three zooms, 5 place searches, record lookups): every total,
scope, distance, map feature, place centroid and record payload is
byte-identical. The only difference is A–Z ordering, which is now precomputed
instead of relying on `String.localeCompare` — deliberate, because cursor
pagination needs one total order and `localeCompare` depends on the runtime's
default locale.

**Browser verification** against the running app, city "Madison, WI":
`/v1/places` resolved the hero form's input, the list returned *496 farms
within 50 miles*, the MapLibre canvas rendered, and all `/v1` calls returned
200. Measured payloads — list 2.0 KB gzip, map 16.1 KB gzip, national bbox
3.2 KB gzip — all inside the documented 200 KB / 300 KB gates.

Two defects were found by looking at the running app rather than the tests:
the Ask box's own placeholder question returned zero results, and the explorer's
live status line kept saying "Choose a city to begin nearby search" on the
hero → explorer path. Both are fixed and covered by tests.

## 7. Remaining risks

1. **The manual browser acceptance matrix has not been run** against the
   national explorer. `docs/testing/discovery-acceptance.md` lists eight checks
   covering keyboard, screen reader, reduced motion, focus trapping, back/forward,
   and GPS handling. This is the largest open gap before a production deploy.
2. **No deploy has been attempted.** Every size measurement is from a local
   build. The 8.00 MiB asset and 0.60 MiB worker fit the documented limits, but
   `wrangler deploy` has not confirmed it, and cold-start cost for the first
   isolate to inflate the index has not been measured on real Workers.
3. **No automated performance or visual-regression infrastructure exists.**
   LCP, INP and p95 API latency remain manual promotion checks.
4. **Product classification is heuristic.** It is a keyword projection over
   governed product text, not a verified attribute. The worst false positives
   are fixed; a listing whose text never names its products stays unclassified.
5. **13,797 records (20%) are ungeocoded** and appear in lists but never on the
   map. The page labels this, but it is real coverage thinning at the map level.
6. **The id-lookup map is built lazily** on the first `/v1/farms/:id` request,
   adding ~19 MB and a one-time pause on that request in a cold isolate.
7. **Duplicate hydration requests.** The workspace issues `/v1/places` and
   `/v1/farms` about three times on first load. Harmless and cached, but it
   should be collapsed before a traffic-bearing launch.
8. **This branch changes 27 files**, over the 20-file CI limit. It needs the
   `large-reviewed-change` label; it cannot be usefully split, because flipping
   the default and making the serving layer survive 128 MB are the same change,
   and AGENTS.md requires count-citing docs to move with it.

## 8. Deployment steps

Nothing has been pushed or deployed. In order:

1. Open the PR from `claude/national-feed-public-cutover` with the
   `large-reviewed-change` label.
2. `cd 03-app/site && npm run data:setup` on a clean checkout, then
   `npm run data:validate`, `npm run data:gates`, `npm run lint`, `npm test`.
3. Walk the eight browser acceptance checks in
   `docs/testing/discovery-acceptance.md` at desktop and 390 px.
4. `npm run build` and confirm the deploy-budget line, that
   `dist/client/national-index.bin` exists, and that `dist/client/farms.json`
   does not.
5. Deploy to a preview URL first. Confirm `/v1/farms`, `/v1/farms/map`,
   `/v1/places` and `/v1/farms/:id` all return 200 on a cold isolate — that is
   the real test of the memory budget.
6. Watch Worker CPU and memory on the first cold starts before sending traffic.
7. Rollback: redeploy the previous version. `EXPLORER_LEGACY=true` is a local
   comparison switch only — its 45 MB feed cannot be deployed.

## 9. Recommended LinkedIn Featured screenshots

Lead with evidence of scale and restraint, not with a hero shot.

1. **Explorer with a real city** — "Madison, WI", *496 farms within 50 miles*,
   list and map side by side. One frame showing national data, bounded
   querying, and honest scoping.
2. **Browse-the-harvest tiles** — the twelve product counts. The caption is the
   story: these are derived from the published feed, and correcting whole-word
   matching removed 3,165 beef farms miscounted as honey producers.
3. **Map at national zoom** — server-side clustering over 54,821 mappable
   points, with the "approximate location" labeling visible.
4. **A farm profile showing a city-level pin** with its precision label and its
   source. This is the provenance-and-privacy frame.
5. **Terminal: one build** — the publication and privacy gate lines
   (`72,396 collected → 68,618 eligible`, `0 contacts without a public
   website`) next to the deploy-budget line. Shows the gates are enforced
   mechanically.
6. **Optional, for an engineering audience:** the before/after memory figure —
   152 MB retained against a 128 MB isolate cap, reduced to 18.9 MB. It is the
   most interesting decision in the project.

Caption honestly: this is a working national directory with enforced privacy
gates, not a deployed production service. The PostgreSQL/PostGIS cutover and
hybrid search are planned, and nothing in the public path uses either today.
