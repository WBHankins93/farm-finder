# Tennessee state review report

> Release: `tn-coverage-reviewed-v1-2026-07-16`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **3,121 named candidates** from
**5,551 immutable observations**. **1,602** currently meet staged
field and evidence gates; **1,519** remain in explicit research/QA. Missing data never
caused deletion or exclusion. The observation total includes **0**
canonical identity anchors that preserve the existing cleaned TN canon without counting it
as a current collection pass.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 5,551 |
| Retained candidate entities | 3,121 |
| Promotion-eligible reviewed entities | 1,602 |
| Research/QA entities | 1,519 |
| Affirmatively excluded observations | 0 |
| Identity review groups | 194 |
| Counties reviewed | 95 of 95 |
| Counties with retained candidates | 95 |
| Counties with current-source candidates | 95 |
| Counties with eligible candidates | 95 |

## Canonical reconciliation

| Canonical outcome | Count |
|---|---:|
| Current canonical identity anchors | 0 |
| Rediscovered by a current source | 0 |
| Possible alias requiring identity review | 0 |
| Baseline only; current source not rediscovered | 0 |

Every cleaned canonical identity remains represented. A baseline-only identity is retained but
cannot be promotion-eligible until current evidence is found; possible aliases are never merged
silently.

## Source reconciliation

| Source | Immutable observations |
|---|---:|
| EatWild Tennessee directory | 12 |
| Middle Tennessee State University — Tennessee Century Farms registry | 2,236 |
| PickYourOwn — Clarksville area | 24 |
| PickYourOwn — Columbia area | 17 |
| PickYourOwn — Eastern Tennessee | 23 |
| PickYourOwn — Knoxville area | 25 |
| PickYourOwn — Middle Tennessee | 53 |
| PickYourOwn — North-central Tennessee | 14 |
| PickYourOwn — Northeastern Tennessee | 16 |
| PickYourOwn — Northwestern Tennessee | 10 |
| PickYourOwn — Southwestern-central Tennessee | 7 |
| PickYourOwn — Western Tennessee | 10 |
| Tennessee Agritourism Association — active farm members | 88 |
| Tennessee Department of Agriculture — Pick Tennessee Products directory | 3,016 |

The source total above reconciles exactly to **5,551** observations and all
observation IDs are required to be unique. **2,217**
unmatched identity-hint observations remain immutable evidence but do not create entities or
QA rows under the source-tier policy. The statewide coverage denominator contains
**95** county equivalents. **95**
have retained candidates; **0** were searched without a retained result
(none).

## Open QA blockers

Blocker counts overlap because one retained entity can require more than one follow-up.

| Blocker | Entities |
|---|---:|
| directory candidate needs independent farm-operation evidence | 1,372 |
| products or farm activity missing | 387 |
| single grade-E discovery listing needs corroboration | 99 |
| source reports closure and requires affirmative curator decision | 33 |
| county missing | 17 |
| same normalized name appears in multiple counties | 12 |
| city or safe public service area missing | 6 |

## Source passes

1. Official pass: the Tennessee Department of Agriculture Pick Tennessee Products directory.
2. Corroboration pass: Tennessee Century Farms, Tennessee Agritourism, and EatWild.
3. Discovery pass: ten PickYourOwn regions.

## Quality boundaries

- The official marketing directory includes producers, processors, retailers, and value-added businesses. Named
  profiles without explicit farm-operation evidence remain QA candidates rather than being discarded.
- PickYourOwn closure claims remain retained pending an affirmative append-only curator decision.
- County and city-or-safe-service-area gaps remain explicit blockers in `entities.csv`.
- Outside-state radius results remain in immutable observations and `exclusions.csv`, never as Tennessee entities.
- Detailed observations, request logs, and raw source records remain outside Git in the evidence bundle.

## Promotion blockers

1. Resolve the 1,532 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Tennessee atomically in a separate canonical-release change.

## Judgment-only QA residue — 2026-07-17

This append-only batch added **13** evidence decisions and made no exclusions. The current contract counts are **3,121 entities**, **1,602 promotion-eligible reviewed**, and **1,519 research/QA**. The remaining judgment-only residue is **0** rows: **0** canonical-baseline research items and **0** status items without affirmative current closure/operation evidence. Missing evidence remains a routed research blocker.
