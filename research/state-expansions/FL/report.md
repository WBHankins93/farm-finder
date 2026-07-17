# Florida state review report

> Release: `fl-coverage-reviewed-v3-qa-2026-07-17`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

The three documented collection passes retained **1,515 named candidates** from
**2,082 immutable observations**. **237** currently meet staged
field and evidence gates; **1,278** remain in explicit research/QA. Missing data never
caused deletion or exclusion.

The complete primary corroboration cohort of **911** rows was screened. Across
the exact-blocker and expanded remaining-worklist runs, the assistant generated
**47 unique proposals** for **43 entities**; curator review accepted **33** and
rejected **14**. Twenty-nine accepted rows cleared all blockers and moved to
eligible staging. Four accepted rows and four conflict-only rows remain in QA
under named geography conflicts or residual identity blockers. Eligible staging
remains a reviewed handoff, not verification, approval, or canonical promotion.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 2,082 |
| Retained candidate entities | 1,515 |
| Promotion-eligible reviewed entities | 237 |
| Research/QA entities | 1,278 |
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

The source total above reconciles exactly to **2,049** collected observations;
the 33 accepted curator observations bring the release total to **2,082**.
All observation IDs are required to be unique. The statewide coverage denominator contains
**67** county equivalents. **66**
have retained candidates; **1** were searched without a retained result
(Lafayette).

## Open QA blockers

Blocker counts overlap because one retained entity can require more than one follow-up.

| Blocker | Entities |
|---|---:|
| single grade-E discovery listing needs corroboration | 1,173 |
| directory candidate needs independent farm-operation evidence | 459 |
| city or safe public service area missing | 346 |
| products or farm activity missing | 246 |
| source reports closure and requires affirmative curator decision | 61 |
| county missing | 61 |
| same normalized name appears in multiple counties | 29 |
| county requires geography review due cross-directory conflict | 8 |

## Corroboration QA batch

The first pass considered 354 exact-blocker single-source rows. After its five
promotions and three conflict reroutes, the expanded pass screened all **903**
remaining primary-corroboration rows, including multi-source grade-E-only
candidates. The expanded pass found 103 fetchable farm-owned sites, 22 website
hits, 16 cross-directory hits, and 7 geography conflicts. Combined review
accepted **33 of 47 unique proposals (70.21%)**; **43 of 911 cohort entities
(4.72%)** received at least one proposal.

Accepted evidence comprises **21 farm-owned website observations** and **12
authoritative cross-directory matches**. Every accepted website observation
had three internally consistent SHA-256 fetch hashes and target-specific dated
activity. Every accepted cross-directory observation matched contact and
geography against an independently collected grade-B government source.

Rejected proposals:

- `coroobs_237319f24ec124ad1928` — both records are PickYourOwn listings, so the second regional page is not an independent source.
- `coroobs_aa7bbfb9bc4a8907eada` — the cited source names the Blueberry Farm, not the target Peach Farm.
- `coroobs_25e123d31a7be71ee2c1` — the cited source names Kentner Pond, not the target Duke Field location.
- `coroobs_860a5d92eef99f055a3e` — the cited source names Kentner Pond, not the target Range Road 212 location.
- `coroobs_d73386daa015af80d00c` — the excerpt's only 2026 signal is a copyright line, not dated operating activity.
- `coroobs_131481e3077e4c2ec523` — the cited activity is a stale 2025 hurricane-recovery and suspended-tour notice.
- `coroobs_820714c5ed0e94818d69` — the cited U-pick season is 2025 and does not establish current 2026 activity.
- `coroobs_d58b866486569b62dfcc` — the excerpt says the farm will not open this year and supplies only a copyright-year signal.
- `coroobs_9884d724674c176e551c` — the excerpt describes a planned venue and explicitly says the 2026 U-pick season is not open.
- `coroobs_13fa2b69b36849890652` — the cited reopening date is in 2025 and does not establish current 2026 activity.
- `coroobs_e2563cb5155968835c37` — the farm URL resolves to unrelated gambling/spam content and cannot corroborate Honeyside Farms.
- `coroobs_ca6ac7a39a6c3c256821` — the excerpt's only date is a 2025 copyright line, not current operating evidence.
- `coroobs_4189c09d0d91280d9c10` — the cited observation is for the distinct Peach Farm operation, not the target Blueberry Farm.
- `coroobs_f2a4addac035903333d4` — the generic Ever After Farms listing does not independently name the target Blueberry Farm operation.

The 12 assistant geography conflicts are consolidated onto eight target rows
with routable `county requires geography review` blockers naming every peer;
no conflict item received a corroborate decision.

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

1. Resolve the 1,278 QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote Florida atomically in a separate canonical-release change.

## Judgment-only QA residue — 2026-07-17

This append-only batch added **3** evidence decisions and made no exclusions. The current contract counts are **1,515 entities**, **237 promotion-eligible reviewed**, and **1,278 research/QA**. The remaining judgment-only residue is **0** rows: **0** canonical-baseline research items and **0** status items without affirmative current closure/operation evidence. Missing evidence remains a routed research blocker.
