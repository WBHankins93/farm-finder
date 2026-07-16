# Louisiana state review report

> Release: `la-coverage-reviewed-v1-2026-07-15`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **400 named candidates** from
**562 immutable observations**. **198** currently meet staged
field and evidence gates; **202** remain in explicit research/QA. Missing data never
caused deletion or exclusion. The observation total includes **220**
canonical identity anchors that preserve the existing cleaned LA canon without counting it
as a current collection pass.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 562 |
| Retained candidate entities | 400 |
| Promotion-eligible reviewed entities | 198 |
| Research/QA entities | 202 |
| Affirmatively excluded observations | 19 |
| Identity review groups | 124 |
| Counties reviewed | 64 of 64 |
| Counties with retained candidates | 59 |
| Counties with current-source candidates | 56 |
| Counties with eligible candidates | 52 |

## Canonical reconciliation

| Canonical outcome | Count |
|---|---:|
| Current canonical identity anchors | 220 |
| Rediscovered by a current source | 118 |
| Possible alias requiring identity review | 5 |
| Baseline only; current source not rediscovered | 97 |

Every cleaned canonical identity remains represented. A baseline-only identity is retained but
cannot be promotion-eligible until current evidence is found; possible aliases are never merged
silently.

## Source reconciliation

| Source | Immutable observations |
|---|---:|
| EatWild Louisiana directory | 4 |
| FarmFinder current canonical baseline — identity anchor only | 220 |
| LDAF 2026 FMNP roadside-stand directory | 68 |
| LDAF certified agritourism operations | 68 |
| LSU AgCenter statewide farm-food directory | 124 |
| LocalHarvest — Louisiana county-seat gap search | 70 |
| PickYourOwn — Baton Rouge and south-central Louisiana | 2 |
| PickYourOwn — New Orleans and Southeast Louisiana | 2 |
| PickYourOwn — Northern Louisiana | 3 |
| PickYourOwn — Southwestern Louisiana | 1 |

The source total above reconciles exactly to **562** observations and all
observation IDs are required to be unique. The statewide coverage denominator contains
**64** county equivalents. **56**
have retained candidates; **8** were searched without a retained result
(Calcasieu, Caldwell, Cameron, Claiborne, East Carroll, Madison, St. Charles, Winn).

## Open QA blockers

Blocker counts overlap because one retained entity can require more than one follow-up.

| Blocker | Entities |
|---|---:|
| single grade-E discovery listing needs corroboration | 144 |
| canonical baseline farm not rediscovered in current three-pass sources | 104 |
| county missing | 19 |
| directory candidate needs independent farm-operation evidence | 12 |
| city or safe public service area missing | 9 |
| source reports closure and requires affirmative curator decision | 8 |
| same normalized name appears in multiple counties | 6 |

## Source passes

1. Official pass: the 2026 LDAF Farmers' Market Nutrition Program roadside-stand directory and the LSU AgCenter statewide farm-food directory.
2. Corroboration pass: the LDAF certified agritourism directory and EatWild.
3. Discovery pass: the live PickYourOwn region index plus targeted LocalHarvest parish-gap searches.

## Quality boundaries

- The official marketing directory includes producers, processors, retailers, and value-added businesses. Named
  profiles without explicit farm-operation evidence remain QA candidates rather than being discarded.
- PickYourOwn closure claims remain retained pending an affirmative append-only curator decision.
- County and city-or-safe-service-area gaps remain explicit blockers in `entities.csv`.
- Outside-state radius results remain in immutable observations and `exclusions.csv`, never as Louisiana entities.
- Detailed observations, request logs, and raw source records remain outside Git in the evidence bundle.

## Promotion blockers

1. Resolve the 202 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Louisiana atomically in a separate canonical-release change.
