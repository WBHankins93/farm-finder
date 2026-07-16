# Texas state review report

> Release: `tx-county-central-qa-v7-2026-07-16`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not record-verified, approved, or canonical

## Outcome

Texas has completed the documented three-pass discovery process across all 254
counties. County Batch 02 reviewed Bastrop, Bexar, and Blanco after the Hidalgo
checkpoint: the revised release retains 872 named candidates, 721 currently meet
staged field and evidence gates, and 151 remain in research/QA. Texas is not
complete and must not be promoted until all county batches, managed evidence,
approval, and canonical gates pass.

The earlier `record_verified` label was invalid because missing information and
assumed closures were being converted into exclusions. The national policy now
keeps those candidates staged.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 1,062 |
| Retained candidate entities | 872 |
| Promotion-eligible reviewed entities | 721 |
| Research/QA entities | 151 |
| Affirmatively excluded observations | 54 |
| Effective excluded entity groups | 34 |
| Append-only decisions | 93 |
| Counties reviewed | 254 of 254 |
| Counties with retained candidates | 179 |
| Counties searched with none found | 75 |
| Counties with promotion-eligible candidates | 171 |

Retained entity observation counts plus the 54 affirmatively excluded source
observations reconcile exactly to all 1,062 observations. Multiple source
observations can support one excluded entity group, which is why 54 observations
correspond to 34 effective exclusions.

## County Batch 01 — Hidalgo

The Hidalgo batch processed all 12 QA candidates in the county. Four were
affirmatively excluded as a market, distributor, pasta processor, or meat
supplier. Six vendor/directory records were resolved through official evidence or
identity merges: Little Bear Produce, Rio Fresh, South Tex Organics, The Lazy S
Citrus Grove, and Val Verde Vegetable. Rio Fresh facility labeling and the two
Val Verde spelling variants were merged into their retained farm entities. Only
Wonderful Citrus remains in Hidalgo QA because its Texas production footprint and
Mission facility scope require county-specific review.

## County Batch 02 — Bastrop, Bexar, and Blanco

The Central Texas batch processed all five QA candidates in the three counties.
M&P Produce and River City Produce were affirmatively excluded as produce
distribution businesses, and Texas Lavender Hills was excluded on current closure
evidence. VRDNT was cleared through current farm-owned evidence, and M & J
Lavender Farm was cleared through current directory and independent business
corroboration. No county coverage rows changed; the batch reduced QA by two and
added three affirmative exclusions.

## Missing-data and closure correction

Five farms were restored from closure handling:

- Glover Farm Vineyard
- Moody Farms and Flowers
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

The 151 QA entities are retained in `entities.csv`. Blockers overlap:

| Blocker | Entities |
|---|---:|
| County-equivalent missing | 90 |
| Single grade-E discovery listing needs corroboration | 52 |
| City or safe public service area missing | 58 |
| Member/vendor candidate needs independent farm-operation evidence | 45 |
| Reopened assumed/parser-derived closure needs corroboration | 0 |

Missing geography or contact detail does not imply that a farm is invalid or closed.
The correct follow-up is enrichment from farm-owned, official, or independently
corroborating sources.

## Effective exclusions

Every active exclusion has a source URL, retrieval date, append-only decision, and
an allowed affirmative reason:

| Reason | Entity groups |
|---|---:|
| Confirmed non-farm business or channel | 22 |
| Confirmed closed | 8 |
| Outside Texas jurisdiction | 4 |

The four off-state operations remain valid candidates for their home states. Market,
processor, software, legal, insurance, manufacturing, and other non-farm records are
preserved as evidence even though they are outside the farm-entity boundary.

## Reachability and contact fields

- 570 retained entities have a website value.
- 499 have at least one social profile.
- 761 have a direct public phone or email in staging.

These values describe field availability, not promotion readiness. A candidate with
none of these fields remains retained.

## Data quality checks

- Exactly four Texas state files are committed.
- Every retained row has a farm name and Texas entity ID.
- Entity IDs and normalized-name/county-equivalent keys are unique.
- All 151 QA rows contain explicit blockers.
- No active excluded normalized name remains staged.
- Every active exclusion uses affirmative evidence.
- Source, retained, and excluded observation counts reconcile.
- The corrected 299-row LA/MS canonical boundary is unchanged.

## Promotion blockers

1. Resolve or deliberately retain the remaining 151 QA candidates through append-only county batches.
2. Copy the three immutable evidence objects to managed production storage.
3. Re-run validation and bind owner approval to the resulting release fingerprint.
4. Promote Texas atomically in a separate canonical-release change.
