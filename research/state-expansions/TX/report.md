# Texas state review report

> Release: `tx-coverage-reviewed-v5-2026-07-15`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not record-verified, approved, or canonical

## Outcome

Texas has completed the documented three-pass discovery process across all 254
counties. The corrected release retains 883 named candidates: 716 currently meet
staged field and evidence gates, while 167 remain in research/QA. Texas is not
complete and must not be promoted until the QA queue, managed evidence, approval,
and canonical gates pass.

The earlier `record_verified` label was invalid because missing information and
assumed closures were being converted into exclusions. The national policy now
keeps those candidates staged.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 1,062 |
| Retained candidate entities | 883 |
| Promotion-eligible reviewed entities | 716 |
| Research/QA entities | 167 |
| Affirmatively excluded observations | 47 |
| Effective excluded entity groups | 27 |
| Append-only decisions | 76 |
| Counties reviewed | 254 of 254 |
| Counties with retained candidates | 179 |
| Counties searched with none found | 75 |
| Counties with promotion-eligible candidates | 171 |

Retained entity observation counts plus the 47 affirmatively excluded source
observations reconcile exactly to all 1,062 observations. Multiple source
observations can support one excluded entity group, which is why 47 observations
correspond to 27 effective exclusions.

## Missing-data and closure correction

Six farms were restored from closure handling:

- Glover Farm Vineyard
- Moody Farms and Flowers
- The Lazy S Citrus Grove
- The Orchard
- Universal Farms
- Upicberries

Five source entries explicitly described their closures as assumptions made because
current information was unavailable. Moody Farms and Flowers was incorrectly marked
closed because its parsed text spilled into a neighboring farm's closure notice. All
six now remain in QA for current corroboration; none is deleted.

Seven separate farms remain excluded with explicit current-source closure language:
Barton Hill Farms, Boldheart Farms, Heart of Texas Farms, Johnson's Backyard Garden,
Point Enterprises Orchards, Six Mile Pic-N-Pac Produce, and Yoes Peach Orchard.

## QA profile

The 167 QA entities are retained in `entities.csv`. Blockers overlap:

| Blocker | Entities |
|---|---:|
| County-equivalent missing | 90 |
| Single grade-E discovery listing needs corroboration | 64 |
| City or safe public service area missing | 58 |
| Member/vendor candidate needs independent farm-operation evidence | 58 |
| Reopened assumed/parser-derived closure needs corroboration | 6 |

Missing geography or contact detail does not imply that a farm is invalid or closed.
The correct follow-up is enrichment from farm-owned, official, or independently
corroborating sources.

## Effective exclusions

Every active exclusion has a source URL, retrieval date, append-only decision, and
an allowed affirmative reason:

| Reason | Entity groups |
|---|---:|
| Confirmed non-farm business or channel | 16 |
| Confirmed closed | 7 |
| Outside Texas jurisdiction | 4 |

The four off-state operations remain valid candidates for their home states. Market,
processor, software, legal, insurance, manufacturing, and other non-farm records are
preserved as evidence even though they are outside the farm-entity boundary.

## Reachability and contact fields

- 580 retained entities have a website value.
- 500 have at least one social profile.
- 772 have a direct public phone or email in staging.

These values describe field availability, not promotion readiness. A candidate with
none of these fields remains retained.

## Data quality checks

- Exactly four Texas state files are committed.
- Every retained row has a farm name and Texas entity ID.
- Entity IDs and normalized-name/county-equivalent keys are unique.
- All 167 QA rows contain explicit blockers.
- No active excluded normalized name remains staged.
- Every active exclusion uses affirmative evidence.
- Source, retained, and excluded observation counts reconcile.
- The corrected 299-row LA/MS canonical boundary is unchanged.

## Promotion blockers

1. Resolve or deliberately retain all 167 QA candidates through append-only review.
2. Copy the three immutable evidence objects to managed production storage.
3. Re-run validation and bind owner approval to the resulting release fingerprint.
4. Promote Texas atomically in a separate canonical-release change.
