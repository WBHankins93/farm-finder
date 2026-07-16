# Mississippi state review report

> Release: `ms-coverage-reviewed-v1-2026-07-15`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **448 named candidates** from
**593 immutable observations**. **282** currently meet staged
field and evidence gates; **166** remain in explicit research/QA. Missing data never
caused deletion or exclusion. The observation total includes **79**
canonical identity anchors that preserve the existing cleaned MS canon without counting it
as a current collection pass.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 593 |
| Retained candidate entities | 448 |
| Promotion-eligible reviewed entities | 282 |
| Research/QA entities | 166 |
| Affirmatively excluded observations | 12 |
| Identity review groups | 103 |
| Counties reviewed | 82 of 82 |
| Counties with retained candidates | 74 |
| Counties with current-source candidates | 74 |
| Counties with eligible candidates | 71 |

## Canonical reconciliation

| Canonical outcome | Count |
|---|---:|
| Current canonical identity anchors | 79 |
| Rediscovered by a current source | 58 |
| Possible alias requiring identity review | 2 |
| Baseline only; current source not rediscovered | 19 |

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
| LocalHarvest — Mississippi county-seat gap search | 75 |
| MDAC Mississippi Farm Marketplace | 4 |
| MDAC Mississippi Farmers Market agricultural vendors | 20 |
| MDAC registered agritourism venues | 96 |
| PickYourOwn — East-central Mississippi | 18 |
| PickYourOwn — Jackson and west-central Mississippi | 5 |
| PickYourOwn — North Mississippi | 18 |
| PickYourOwn — Southeast Mississippi | 40 |
| PickYourOwn — Southwest Mississippi | 9 |

The source total above reconciles exactly to **593** observations and all
observation IDs are required to be unique. The statewide coverage denominator contains
**82** county equivalents. **74**
have retained candidates; **8** were searched without a retained result
(Carroll, Claiborne, Coahoma, Jefferson, Quitman, Smith, Tishomingo, Warren).

## Open QA blockers

Blocker counts overlap because one retained entity can require more than one follow-up.

| Blocker | Entities |
|---|---:|
| single grade-E discovery listing needs corroboration | 94 |
| source reports closure and requires affirmative curator decision | 41 |
| directory candidate needs independent farm-operation evidence | 39 |
| county missing | 35 |
| city or safe public service area missing | 25 |
| canonical baseline farm not rediscovered in current three-pass sources | 21 |
| same normalized name appears in multiple counties | 2 |

## Source passes

1. Official pass: Genuine MS Grown and Raised archives with current producer profiles.
2. Corroboration pass: MDAC farmers-market vendors, Farm Marketplace, agritourism venues, and EatWild.
3. Discovery pass: all five PickYourOwn regions plus targeted LocalHarvest county-gap searches.

## Quality boundaries

- The official marketing directory includes producers, processors, retailers, and value-added businesses. Named
  profiles without explicit farm-operation evidence remain QA candidates rather than being discarded.
- PickYourOwn closure claims remain retained pending an affirmative append-only curator decision.
- County and city-or-safe-service-area gaps remain explicit blockers in `entities.csv`.
- Outside-state radius results remain in immutable observations and `exclusions.csv`, never as Mississippi entities.
- Detailed observations, request logs, and raw source records remain outside Git in the evidence bundle.

## Promotion blockers

1. Resolve the 166 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Mississippi atomically in a separate canonical-release change.
