# Florida state review report

> Release: `fl-coverage-reviewed-v1-2026-07-15`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **1,515 named candidates** from
**2,049 immutable observations**. **205** currently meet staged
field and evidence gates; **1,310** remain in explicit research/QA. Missing data never
caused deletion or exclusion.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 2,049 |
| Retained candidate entities | 1,515 |
| Promotion-eligible reviewed entities | 205 |
| Research/QA entities | 1,310 |
| Affirmatively excluded observations | 2 |
| Identity review groups | 443 |
| Counties reviewed | 67 of 67 |
| Counties with retained candidates | 66 |
| Counties with eligible candidates | 53 |

## Source reconciliation

| Source | Immutable observations |
|---|---:|
| EatWild Florida directory | 14 |
| Florida Department of Agriculture and Consumer Services — CSA locator | 24 |
| Florida Department of Agriculture and Consumer Services — Florida Farm to You producer directory | 171 |
| Florida Department of Agriculture and Consumer Services — U-pick farm locator | 100 |
| LocalHarvest — Florida county-seat gap search | 12 |
| PickYourOwn — Alachua County | 38 |
| PickYourOwn — Baker, Columbia and Union Counties | 7 |
| PickYourOwn — Bay, Holmes, Walton and Washington County, mid-Panhandle | 6 |
| PickYourOwn — Bradford and Clay counties | 8 |
| PickYourOwn — Brevard County and Osceola County | 19 |
| PickYourOwn — Broward County | 4 |
| PickYourOwn — Charlotte and Glades County | 4 |
| PickYourOwn — Citrus County | 10 |
| PickYourOwn — Desoto and Hardee County | 7 |
| PickYourOwn — Dixie and Lafayette counties | 1 |
| PickYourOwn — Eastern Florida Panhandle: Jefferson, Madison and Taylor County | 14 |
| PickYourOwn — Escambia County (Pensacola area) | 6 |
| PickYourOwn — Flagler and St. John's counties | 4 |
| PickYourOwn — Gilcrist and Levy counties | 6 |
| PickYourOwn — Hamilton County | 2 |
| PickYourOwn — Hernando County | 15 |
| PickYourOwn — Highlands County | 2 |
| PickYourOwn — Indian River County, Okeechobee County, St. Lucie County | 3 |
| PickYourOwn — Jackson County, Calhoun County, Franklin, Gulf, Liberty counties | 10 |
| PickYourOwn — Jacksonville area; Duval and Nassau Counties | 19 |
| PickYourOwn — Manatee County | 6 |
| PickYourOwn — Marion County | 24 |
| PickYourOwn — Martin County or Palm Beach County, | 3 |
| PickYourOwn — Miami-Dade County | 8 |
| PickYourOwn — Okaloosa County | 10 |
| PickYourOwn — Orange County | 4 |
| PickYourOwn — Pasco County | 23 |
| PickYourOwn — Polk County | 21 |
| PickYourOwn — Putnam County | 17 |
| PickYourOwn — Santa Rosa County | 7 |
| PickYourOwn — Sarasota County | 2 |
| PickYourOwn — Seminole County | 4 |
| PickYourOwn — Southwest Florida - Collier Hendry and Lee counties | 8 |
| PickYourOwn — Sumter County | 7 |
| PickYourOwn — Suwannee County | 11 |
| PickYourOwn — Tallahassee area: Gadsden, Leon and Wakulla County | 10 |
| PickYourOwn — Tampa area - Hillsborough and Pinellas County | 45 |
| PickYourOwn — Volusia County | 4 |
| US Farm Trail — Florida discovery export | 1,329 |

The source total above reconciles exactly to **2,049** observations and all
observation IDs are required to be unique. The statewide coverage denominator contains
**67** county equivalents. **66**
have retained candidates; **1** were searched without a retained result
(Lafayette).

## Open QA blockers

Blocker counts overlap because one retained entity can require more than one follow-up.

| Blocker | Entities |
|---|---:|
| single grade-E discovery listing needs corroboration | 1,206 |
| directory candidate needs independent farm-operation evidence | 459 |
| city or safe public service area missing | 346 |
| products or farm activity missing | 246 |
| source reports closure and requires affirmative curator decision | 63 |
| county missing | 61 |
| same normalized name appears in multiple counties | 31 |

## Source passes

1. Official pass: the FDACS-created Florida Farm to You producer directory.
2. Corroboration pass: FDACS U-pick and CSA lists plus EatWild.
3. Discovery pass: US Farm Trail, 39 PickYourOwn regions, and targeted LocalHarvest county-gap searches.

## Quality boundaries

- The official marketing directory includes producers, processors, retailers, and value-added businesses. Named
  profiles without explicit farm-operation evidence remain QA candidates rather than being discarded.
- PickYourOwn closure claims remain retained pending an affirmative append-only curator decision.
- County and city-or-safe-service-area gaps remain explicit blockers in `entities.csv`.
- Outside-state radius results remain in immutable observations and `exclusions.csv`, never as Florida entities.
- Detailed observations, request logs, and raw source records remain outside Git in the evidence bundle.

## Promotion blockers

1. Resolve the 1,310 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Florida atomically in a separate canonical-release change.
