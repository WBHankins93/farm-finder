# Texas state review report

> Release: `tx-county-northeast-qa-v12-2026-07-16`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not record-verified, approved, or canonical

## Outcome

Texas has completed the documented three-pass discovery process across all 254
counties. County Batch 07 reviewed Grayson, Guadalupe, Harris, Hill, and Jasper
after the West Texas checkpoint: the revised release retains 862 named
candidates, 730 currently meet staged field and evidence gates, and 132 remain
in research/QA. Texas is not complete and must not be promoted until all county
batches, managed evidence, approval, and canonical gates pass.

The earlier `record_verified` label was invalid because missing information and
assumed closures were being converted into exclusions. The national policy now
keeps those candidates staged.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 1,062 |
| Retained candidate entities | 862 |
| Promotion-eligible reviewed entities | 730 |
| Research/QA entities | 132 |
| Affirmatively excluded observations | 64 |
| Effective excluded entity groups | 44 |
| Append-only decisions | 118 |
| Counties reviewed | 254 of 254 |
| Counties with retained candidates | 178 |
| Counties searched with none found | 75 |
| Counties with promotion-eligible candidates | 172 |

Retained entity observation counts plus the 64 affirmatively excluded source
observations reconcile exactly to all 1,062 observations. Multiple source
observations can support one excluded entity group, which is why 64 observations
correspond to 44 effective exclusions.

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

## County Batch 03 — Angelina, Bee, Bowie, and Brazos

The East Texas batch processed all four QA candidates in the four counties.
Red River Beef Co and Scarmardo Foodservice were affirmatively excluded as a
butcher/meat-market operation and a broadline foodservice distributor. Lucky Penny
Homestead and Papalote Pea Patch remain in QA because current directory evidence
does not independently confirm their current farm operations. No county coverage
rows changed; the batch reduced QA by two and added two affirmative exclusions.

## County Batch 04 — Cameron, Camp, Chambers, and Cherokee

The South and Northeast Texas batch processed all five QA candidates in the four
counties. Mid-Valley Ag and McPeak Orchards were cleared through independent
operational and current authoritative evidence. Universal Farms remains in QA
because the current directory repeats an assumed closure and presents an address
conflict. Yellow Rose Meat Market was affirmatively excluded as a meat-market and
processing operation. No county coverage rows changed; the batch reduced QA by
three and added one affirmative exclusion.

## County Batch 05 — Clay, Comanche, Dallas, and Denton

The North Texas batch processed all five QA candidates in the four counties. Davis
20 Beef and Texas Green Star were cleared through current farm-owned or industry
corroboration. Texas Fruit & Pecan Orchard and Pro Health remain in QA because
current production evidence is incomplete. Hiland Dairy was affirmatively excluded
as a dairy processing/distribution operation. No county coverage rows changed; the
batch reduced QA by three and added one affirmative exclusion.

## County Batch 06 — Erath, Fayette, Gaines, Garza, and Gonzales

The West Texas batch processed all five QA candidates in the five counties. Blue
Jay Dairy, Weimar Meat Company, Canyon Valley Provisions, and Texas Tribal
Buffalo Project were cleared through current cooperative, farm-owned, official,
and independent evidence. Weimar Meat Company's current postal code was corrected
to 78962. West Texas Meats was affirmatively excluded as a meat processor with no
established farm-production operation. No county coverage rows changed; the
batch reduced QA by five, added four eligible entities, and added one affirmative
exclusion while removing the excluded entity from the retained set.

## County Batch 07 — Grayson, Guadalupe, Harris, Hill, and Jasper

The Northeast Texas batch processed seven QA candidates across the five counties.
Pennell Ag Services and River Creek LTD were excluded as an agricultural-service
carrier and a meat retailer, respectively. Boenig Pecans was excluded on current
retirement/closure evidence. Beauty's Community Garden was excluded as a
volunteer-led community garden rather than an independent farm operation. Tejas
Premium Meat was excluded as a USDA-establishment custom slaughter and export
plant. The Berry Patch was cleared through current farm-owned evidence, with its
location corrected from a Houston-area service classification to Kountze in
Hardin County. Brown's Berry Farm remains in QA because current corroboration was
not found. The batch reduced QA by six and added five affirmative exclusions.

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

The 132 QA entities are retained in `entities.csv`. Blockers overlap:

| Blocker | Entities |
|---|---:|
| County-equivalent missing | 90 |
| Single grade-E discovery listing needs corroboration | 34 |
| City or safe public service area missing | 58 |
| Member/vendor candidate needs independent farm-operation evidence | 27 |
| Reopened assumed/parser-derived closure needs corroboration | 5 |

Missing geography or contact detail does not imply that a farm is invalid or closed.
The correct follow-up is enrichment from farm-owned, official, or independently
corroborating sources.

## Effective exclusions

Every active exclusion has a source URL, retrieval date, append-only decision, and
an allowed affirmative reason:

| Reason | Entity groups |
|---|---:|
| Confirmed non-farm business or channel | 31 |
| Confirmed closed | 8 |
| Outside Texas jurisdiction | 4 |

The four off-state operations remain valid candidates for their home states. Market,
processor, software, legal, insurance, manufacturing, and other non-farm records are
preserved as evidence even though they are outside the farm-entity boundary.

## Reachability and contact fields

- 564 retained entities have a website value.
- 497 have at least one social profile.
- 750 have a direct public phone or email in staging.

These values describe field availability, not promotion readiness. A candidate with
none of these fields remains retained.

## Data quality checks

- Exactly four Texas state files are committed.
- Every retained row has a farm name and Texas entity ID.
- Entity IDs and normalized-name/county-equivalent keys are unique.
- All 132 QA rows contain explicit blockers.
- No active excluded normalized name remains staged.
- Every active exclusion uses affirmative evidence.
- Source, retained, and excluded observation counts reconcile.
- The corrected 299-row LA/MS canonical boundary is unchanged.

## Promotion blockers

1. Resolve or deliberately retain the remaining 132 QA candidates through append-only county batches.
2. Copy the three immutable evidence objects to managed production storage.
3. Re-run validation and bind owner approval to the resulting release fingerprint.
4. Promote Texas atomically in a separate canonical-release change.
