# Arkansas state review report

> Release: `ar-coverage-reviewed-v3-qa-2026-07-17`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **766 named candidates** from
**875 immutable observations**. **553** currently meet staged
field and evidence gates; **213** remain in explicit research/QA. Missing data never
caused deletion or exclusion.

The corroboration QA batch screened the full **79-row** primary corroboration
cohort. It reviewed **7 unique** assistant proposals, accepted **4**, and
rejected **3**. All four accepted rows cleared their sole blocker and moved to
eligible staging. Three geography conflict items remain on two QA rows with
named, routable blockers. Eligible staging remains a reviewed handoff, not
verification, approval, or canonical promotion.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 875 |
| Retained candidate entities | 766 |
| Promotion-eligible reviewed entities | 553 |
| Research/QA entities | 213 |
| Affirmatively excluded observations | 65 |
| Identity review groups | 38 |
| Counties reviewed | 75 of 75 |
| Counties with retained candidates | 75 |
| Counties with eligible candidates | 67 |

## Corroboration QA batch

The existing assistant bundle considered 67 exact-blocker rows. After its four
accepted promotions and two geography-conflict reroutes, an expanded pass
screened all 73 rows still routed to corroboration, including the compound-
blocker rows omitted by the exact-blocker run. Together the passes account for
the full original 79-row cohort.

The passes generated 7 unique proposals for 7 unique entities, an **8.86%
unique-entity hit rate** across the original cohort. Curator review accepted 4
of 7 proposals (**57.14% proposal acceptance rate**) and rejected 3. The
expanded pass surfaced only those same three rejected website signals, so it
added no new unique proposals, observations, or decisions.

Accepted proposals: Sacred Hollow Farm's farm-owned site supplied three cited
SHA-256 fetches and a target-specific 2026 open-season excerpt; Jamison Farm,
Triple M Farm, and Sta-n-Step Blueberry Farm matched independent grade-B
Arkansas Grown observations by contact and consistent geography.

Rejected proposals:

- `coroobs_af75e31a69f7517660e4` — Peebles Farms cites only a stale 2025 season excerpt, not current 2026 activity.
- `coroobs_8c3a7b2e0c7893b31759` — Suzanne's Fruit Farm matched only a 2026 copyright line, not dated operating activity.
- `coroobs_b66990aa77629c567dc1` — Cox Berry Farm cites a stale 2025 excerpt that says the farm was closed that summer.

The three assistant geography conflicts are consolidated onto two target rows
with routable `county requires geography review` blockers naming every peer;
their original grade-E corroboration blockers remain, and no conflict item
received a decision.

QA triage moved from **242 to 238** total rows and from **79 to 73** primary
corroboration rows. Geography-routed QA moved from **130 to 132**, eligible
staging moved from **524 to 528**, and unrouted QA remained **0**.

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

1. Resolve the 213 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Arkansas atomically in a separate canonical-release change.
