# Arkansas state review report

> Release: `ar-coverage-reviewed-v1-2026-07-15`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **766 named candidates** from
**871 immutable observations**. **524** currently meet staged
field and evidence gates; **242** remain in explicit research/QA. Missing data never
caused deletion or exclusion.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 871 |
| Retained candidate entities | 766 |
| Promotion-eligible reviewed entities | 524 |
| Research/QA entities | 242 |
| Affirmatively excluded observations | 65 |
| Identity review groups | 38 |
| Counties reviewed | 75 of 75 |
| Counties with retained candidates | 75 |
| Counties with eligible candidates | 67 |

## Source passes

1. Official pass: the Arkansas Department of Agriculture Arkansas Grown directory.
2. Market-channel pass: University of Arkansas direct-sale farms and EatWild.
3. Discovery pass: five PickYourOwn regions plus LocalHarvest searches anchored to all county seats.

## Quality boundaries

- Arkansas Grown includes markets, processors, retailers, and value-added businesses. Named
  profiles without explicit farm-operation evidence remain QA candidates rather than being discarded.
- PickYourOwn closure claims remain retained pending an affirmative append-only curator decision.
- County and city-or-safe-service-area gaps remain explicit blockers in `entities.csv`.
- Outside-state radius results remain in immutable observations and `exclusions.csv`, never as Arkansas entities.
- Detailed observations, request logs, and raw source records remain outside Git in the evidence bundle.

## Promotion blockers

1. Resolve the 242 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Arkansas atomically in a separate canonical-release change.
