# Tennessee state review report

> Release: `tn-coverage-reviewed-v1-2026-07-15`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **5,425 named candidates** from
**5,656 immutable observations**. **1,626** currently meet staged
field and evidence gates; **3,799** remain in explicit research/QA. Missing data never
caused deletion or exclusion.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 5,656 |
| Retained candidate entities | 5,425 |
| Promotion-eligible reviewed entities | 1,626 |
| Research/QA entities | 3,799 |
| Affirmatively excluded observations | 0 |
| Identity review groups | 370 |
| Counties reviewed | 95 of 95 |
| Counties with retained candidates | 95 |
| Counties with eligible candidates | 95 |

## Source passes

1. Official pass: Tennessee Department of Agriculture — Pick Tennessee Products directory.
2. Corroboration pass: Tennessee Century Farms, Tennessee Agritourism, and EatWild.
3. Discovery pass: ten PickYourOwn regions.

## Quality boundaries

- The official marketing directory includes producers, processors, retailers, and value-added businesses. Named
  profiles without explicit farm-operation evidence remain QA candidates rather than being discarded.
- PickYourOwn closure claims remain retained pending an affirmative append-only curator decision.
- County and city-or-safe-service-area gaps remain explicit blockers in `entities.csv`.
- Outside-state radius results remain in immutable observations and `exclusions.csv`, never as Arkansas entities.
- Detailed observations, request logs, and raw source records remain outside Git in the evidence bundle.

## Promotion blockers

1. Resolve the 3,799 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Tennessee atomically in a separate canonical-release change.
