# Mississippi state review report

> Release: `ms-coverage-reviewed-v1-2026-07-16`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **737 named candidates** from
**957 immutable observations**. **575** currently meet staged
field and evidence gates; **162** remain in explicit research/QA. Missing data never
caused deletion or exclusion. The observation total includes **79**
canonical identity anchors that preserve the existing cleaned MS canon without counting it
as a current collection pass.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 957 |
| Retained candidate entities | 737 |
| Promotion-eligible reviewed entities | 575 |
| Research/QA entities | 162 |
| Affirmatively excluded observations | 45 |
| Identity review groups | 135 |
| Counties reviewed | 82 of 82 |
| Counties with retained candidates | 79 |
| Counties with current-source candidates | 79 |
| Counties with eligible candidates | 79 |

## Canonical reconciliation

| Canonical outcome | Count |
|---|---:|
| Current canonical identity anchors | 79 |
| Rediscovered by a current source | 59 |
| Possible alias requiring identity review | 2 |
| Baseline only; current source not rediscovered | 18 |

Every cleaned canonical identity remains represented. A baseline-only identity is retained but
cannot be promotion-eligible until current evidence is found; possible aliases are never merged
silently.

## Source reconciliation

| Source | Immutable observations |
|---|---:|
| EatWild Mississippi directory | 3 |
| FarmFinder current canonical baseline — identity anchor only | 79 |
| Genuine MS — Grown | 102 |
| Genuine MS — Raised | 124 |
| LocalHarvest — Mississippi county-seat gap search | 151 |
| MDAC 2025–2026 certified nursery growers | 257 |
| MDAC Mississippi Farm Marketplace | 4 |
| MDAC Mississippi Farmers Market agricultural vendors | 20 |
| MDAC registered agritourism venues | 96 |
| MDAC-linked Mississippi Christmas Tree Farms | 31 |
| PickYourOwn — East-central Mississippi | 18 |
| PickYourOwn — Jackson and west-central Mississippi | 5 |
| PickYourOwn — North Mississippi | 18 |
| PickYourOwn — Southeast Mississippi | 40 |
| PickYourOwn — Southwest Mississippi | 9 |

The source total above reconciles exactly to **957** observations and all
observation IDs are required to be unique. The statewide coverage denominator contains
**82** county equivalents. **79**
have retained candidates; **3** were searched without a retained result
(Claiborne, Jefferson, Warren).

## Open QA blockers

Blocker counts overlap because one retained entity can require more than one follow-up.

| Blocker | Entities |
|---|---:|
| single grade-E discovery listing needs corroboration | 89 |
| county missing | 49 |
| source reports closure and requires affirmative curator decision | 41 |
| city or safe public service area missing | 30 |
| directory candidate needs independent farm-operation evidence | 22 |
| canonical baseline farm not rediscovered in current three-pass sources | 20 |
| same normalized name appears in multiple counties | 4 |

## Source passes

1. Official pass: Genuine MS Grown and Raised archives with current producer profiles.
2. Corroboration pass: MDAC farmers-market vendors, Farm Marketplace, agritourism venues, and EatWild.
3. Discovery pass: all five PickYourOwn regions plus targeted LocalHarvest county-gap searches.

## Quality boundaries

- The official marketing directory includes producers, processors, retailers, and value-added businesses. Named
  profiles without explicit farm-operation evidence remain QA candidates rather than being discarded.
- A named vendor explicitly classified as an agricultural farmers-market vendor is an in-scope producer even if
  the record documents only market sales; the market venue is not merged with the producer entity.
- PickYourOwn closure claims remain retained pending an affirmative append-only curator decision.
- County and city-or-safe-service-area gaps remain explicit blockers in `entities.csv`.
- Outside-state radius results remain in immutable observations and `exclusions.csv`, never as Mississippi entities.
- Detailed observations, request logs, and raw source records remain outside Git in the evidence bundle.

## Promotion blockers

1. Resolve the 161 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Mississippi atomically in a separate canonical-release change.


## 2026 operating-evidence audit

The immutable collected-name universe contains **737 retained candidate entities**. Evidence supports
**283 distinct, in-scope operations** through an explicit 2026 program or current official producer
listing. Another **268** have weaker current evidence such as a reachable farm-owned website or a
recently expired grower certification. The evidence-bounded operating range is therefore **283–551**.

This is a public-evidence directory count, not the USDA statistical count of every agricultural operation.
Missing evidence never proves closure, and every collected name remains preserved for follow-up.
