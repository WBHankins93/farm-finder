# Louisiana state review report

> Release: `la-coverage-reviewed-v1-2026-07-16`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **1,200 named candidates** from
**1,414 immutable observations**. **964** currently meet staged
field and evidence gates; **236** remain in explicit research/QA. Missing data never
caused deletion or exclusion. The observation total includes **220**
canonical identity anchors that preserve the existing cleaned LA canon without counting it
as a current collection pass.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 1,414 |
| Retained candidate entities | 1,200 |
| Promotion-eligible reviewed entities | 964 |
| Research/QA entities | 236 |
| Affirmatively excluded observations | 30 |
| Identity review groups | 152 |
| Counties reviewed | 64 of 64 |
| Counties with retained candidates | 61 |
| Counties with current-source candidates | 61 |
| Counties with eligible candidates | 61 |

## Canonical reconciliation

| Canonical outcome | Count |
|---|---:|
| Current canonical identity anchors | 220 |
| Rediscovered by a current source | 130 |
| Possible alias requiring identity review | 6 |
| Baseline only; current source not rediscovered | 84 |

Every cleaned canonical identity remains represented. A baseline-only identity is retained but
cannot be promotion-eligible until current evidence is found; possible aliases are never merged
silently.

## Source reconciliation

| Source | Immutable observations |
|---|---:|
| EatWild Louisiana directory | 4 |
| FarmFinder current canonical baseline — identity anchor only | 220 |
| LDAF 2026 FMNP roadside-stand directory | 68 |
| LDAF June 2026 nursery certificate holders | 679 |
| LDAF June 2026 registered apiary businesses | 45 |
| LDAF March 2026 licensed hemp growers | 15 |
| LDAF certified agritourism operations | 68 |
| LSU AgCenter statewide farm-food directory | 124 |
| LocalHarvest — Louisiana county-seat gap search | 137 |
| Louisiana Crawfish Promotion and Research Board — suppliers | 25 |
| Louisiana Strawberry Marketing Board — growers | 16 |
| Louisiana Sweet Potato Commission — shippers and processors | 5 |
| PickYourOwn — Baton Rouge and south-central Louisiana | 2 |
| PickYourOwn — New Orleans and Southeast Louisiana | 2 |
| PickYourOwn — Northern Louisiana | 3 |
| PickYourOwn — Southwestern Louisiana | 1 |

The source total above reconciles exactly to **1,414** observations and all
observation IDs are required to be unique. The statewide coverage denominator contains
**64** county equivalents. **61**
have retained candidates; **3** were searched without a retained result
(Claiborne, East Carroll, Madison).

## Open QA blockers

Blocker counts overlap because one retained entity can require more than one follow-up.

| Blocker | Entities |
|---|---:|
| single grade-E discovery listing needs corroboration | 129 |
| canonical baseline farm not rediscovered in current three-pass sources | 93 |
| county missing | 44 |
| city or safe public service area missing | 44 |
| same normalized name appears in multiple counties | 16 |
| directory candidate needs independent farm-operation evidence | 9 |
| source reports closure and requires affirmative curator decision | 8 |

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

1. Resolve the 236 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Louisiana atomically in a separate canonical-release change.


## 2026 operating-evidence audit

The immutable collected-name universe contains **1,200 retained candidate entities**. Evidence supports
**826 distinct, in-scope operations** through an explicit 2026 program or current official producer
listing. Another **67** have weaker current evidence such as a reachable farm-owned website or a
recently expired grower certification. The evidence-bounded operating range is therefore **826–893**.

This is a public-evidence directory count, not the USDA statistical count of every agricultural operation.
Missing evidence never proves closure, and every collected name remains preserved for follow-up.
