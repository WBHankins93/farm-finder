# Georgia state review report

> Release: `ga-coverage-reviewed-v1-2026-07-15`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **1,738 named candidates** from
**1,873 immutable observations**. **554** currently meet staged
field and evidence gates; **1,184** remain in explicit research/QA. Missing data never
caused deletion or exclusion.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 1,873 |
| Retained candidate entities | 1,738 |
| Promotion-eligible reviewed entities | 554 |
| Research/QA entities | 1,184 |
| Affirmatively excluded observations | 20 |
| Identity review groups | 95 |
| Counties reviewed | 159 of 159 |
| Counties with retained candidates | 150 |
| Counties with eligible candidates | 138 |

## Source reconciliation

| Source | Immutable observations |
|---|---:|
| EatWild Georgia directory | 13 |
| Georgia Department of Agriculture — Georgia Grown member directory | 1,535 |
| Georgia Farm Bureau — Certified Farm Markets | 101 |
| LocalHarvest — Georgia county-seat gap search | 62 |
| PickYourOwn — Augusta area | 10 |
| PickYourOwn — Coastal and southeastern Georgia | 34 |
| PickYourOwn — Macon area | 39 |
| PickYourOwn — North Georgia | 40 |
| PickYourOwn — Southwestern Georgia | 39 |

The source total above reconciles exactly to **1,873** observations and all observation IDs are
unique. The statewide coverage denominator contains **159** counties. **150** have retained
candidates; **9** were searched without a retained result (Baldwin, Brantley, Chattahoochee,
Echols, Heard, Marion, Quitman, Rockdale, and Warren).

## Open QA blockers

Blocker counts overlap because one retained entity can require more than one follow-up.

| Blocker | Entities |
|---|---:|
| Directory candidate needs independent farm-operation evidence | 985 |
| County missing | 376 |
| City or safe public service area missing | 357 |
| Single grade-E discovery listing needs corroboration | 115 |
| Products or farm activity missing | 67 |
| Source reports closure and requires affirmative curator decision | 32 |
| Same normalized name appears in multiple counties | 2 |

## Source passes

1. Official pass: the Georgia Department of Agriculture Georgia Grown member directory.
2. Corroboration pass: Georgia Farm Bureau Certified Farm Markets and EatWild.
3. Discovery pass: five PickYourOwn regions plus targeted LocalHarvest searches for counties with no retained candidate.

## Quality boundaries

- The official marketing directory includes producers, processors, retailers, and value-added businesses. Named
  profiles without explicit farm-operation evidence remain QA candidates rather than being discarded.
- PickYourOwn closure claims remain retained pending an affirmative append-only curator decision.
- County and city-or-safe-service-area gaps remain explicit blockers in `entities.csv`.
- Outside-state radius results remain in immutable observations and `exclusions.csv`, never as Georgia entities.
- Detailed observations, request logs, and raw source records remain outside Git in the evidence bundle.

## Promotion blockers

1. Resolve the 1,184 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Georgia atomically in a separate canonical-release change.
