# Texas state review report

> Release: `tx-geography-enrichment-v20-2026-07-16`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not record-verified, approved, or canonical

## Outcome

Texas has completed the documented three-pass discovery process across all 254
counties. Geography Batch 14 assigned county equivalents to eight retained records
from published city, postal, farm-address, or service-area evidence; seven had
geography as their only blocker and cleared the promotion gate. Geography Batch 13
triaged 30 retained records with no city or safe public service area, bringing the
remaining county-missing QA surface to 58. The revised release retains 855 named
candidates, 763 currently meet staged field and evidence gates, and 92 remain
in research/QA. Texas is not complete and must not be promoted until all county
batches, managed evidence, approval, and canonical gates pass.

The earlier `record_verified` label was invalid because missing information and
assumed closures were being converted into exclusions. The national policy now
keeps those candidates staged.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 1,062 |
| Retained candidate entities | 855 |
| Promotion-eligible reviewed entities | 763 |
| Research/QA entities | 92 |
| Affirmatively excluded observations | 71 |
| Effective excluded entity groups | 50 |
| Append-only decisions | 254 |
| Counties reviewed | 254 of 254 |
| Counties with retained candidates | 181 |
| Counties searched with none found | 75 |
| Counties with promotion-eligible candidates | 175 |

Retained entity observation counts plus the 71 excluded or merged source
observations reconcile exactly to all 1,062 observations. Multiple source
observations can support one excluded entity group, which is why 71 observations
correspond to 50 effective exclusions.

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

## County Batch 08 — Jefferson, Karnes, Kaufman, and Lubbock

The South Plains batch processed seven QA candidates across the four counties.
Doguets Rice Milling, All Hale Meats, and Gandy's Dairies were excluded as
rice-milling, meat-processing, and wholesale-dairy operations rather than
independent farms. G Farms was cleared through current farm-owned evidence, and
The Orchard was cleared through current local business evidence after its
absence-based closure flag was corrected. Countyline Organic Vegetables and LBK
remain in QA because current searches did not establish sufficiently independent
farm-operation evidence or entity scope. No county coverage rows changed; the
batch reduced QA by five and added three affirmative exclusions.

## County Batch 09 — Mason, Matagorda, McLennan, Montague, Moore, Nacogdoches, and Nueces

The Central-East Texas batch processed nine QA candidates across seven counties.
HG Rice Mill, Barnard Beef, and Barton Beef were cleared through current farm,
ranch, and integrated farm/processor evidence. The Barnard Beef observation was
merged into the existing Barnard Beef Cattle Company entity after matching the
current Crawford address, phone, domain, and operation. Nocona Meat Company,
H-E-B, and Moody's Quality Meats were excluded as a processor, grocery retailer,
and meat retailer/processor. Sonlight Orchard, Wieck Farms, and Blueberry Farms
remain in QA because current corroboration was not found. No county coverage rows
changed; the batch reduced QA by six and added three affirmative exclusions.

## County Batch 10 — Remaining county-specific QA triage

The county-level triage pass reviewed the 30 remaining named QA candidates in
Angelina, Bee, Cameron, Cherokee, Comanche, Dallas, Hidalgo, Jasper, Karnes,
Lubbock, Mason, Moore, Parmer, Potter, Red River, Refugio, Swisher, Tarrant,
Terry, Titus, Travis, Uvalde, Van Zandt, Wharton, Wood, and Yoakum counties.
Each candidate received an append-only retain decision because the current record
did not provide sufficient evidence for promotion or an affirmative exclusion.
These candidates remain visible in QA; the next Texas pass is the continued
geography-enrichment review for the 66 retained rows still missing a county
equivalent.

## Geography Batch 11 — Published city and county corrections

The first geography-enrichment batch assigned county equivalents to 4K River
Ranch (Palo Pinto), Alaiyo Farm and Daniel's Farm/Ranch (Fort Bend), Broken B
Ranch (Bexar), Dautobi Acres (Hopkins), Ficarro Farms (Nueces), Four Winds Ranch
(Fannin), Good Flow Honey (Travis), Grow It 4 Dinner (Walker), and Happy Feet
Farm (Midland). All ten had county geography as their only blocker and therefore
cleared the promotion gate after correction. Sixty-six QA rows still require
geography enrichment, primarily because the source contains no city or safe
public service area.

## Geography Batch 12 — Additional city-based corrections

The second geography-enrichment batch assigned county equivalents to Bluebonnet
Meat Company (Hood), Buena Tierra (Mason), Dusty Road Farm (Leon), Hi Fi Mycology
(Travis), HooFin Wings Ranch (Tarrant), Hudson Plains Raw Dairy (Armstrong),
jjjmgrassfedbeef.com (Collin), LCF Ranch (Hudspeth), Mineral Wells Aquaponics
(Palo Pinto), Quail Haven Urban Farm (Tarrant), Ritchie Family Farms (La Salle),
RNR Cattle Company (Wise), Synergic Farms (Eastland), and Wild Herd Cattle &
Kitchen (Mason). The two first records retain their existing type/corroboration
blockers; the other twelve cleared the geography-only gate.

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

The 92 QA entities are retained in `entities.csv`. Blockers overlap:

| Blocker | Entities |
|---|---:|
| County-equivalent missing | 58 |
| Single grade-E discovery listing needs corroboration | 26 |
| City or safe public service area missing | 58 |
| Member/vendor candidate needs independent farm-operation evidence | 17 |
| Reopened assumed/parser-derived closure needs corroboration | 4 |

Missing geography or contact detail does not imply that a farm is invalid or closed.
The correct follow-up is enrichment from farm-owned, official, or independently
corroborating sources.

## Effective exclusions

Every active exclusion has a source URL, retrieval date, append-only decision, and
an allowed affirmative reason:

| Reason | Entity groups |
|---|---:|
| Confirmed non-farm business or channel | 37 |
| Confirmed closed | 9 |
| Outside Texas jurisdiction | 4 |

The four off-state operations remain valid candidates for their home states. Market,
processor, software, legal, insurance, manufacturing, and other non-farm records are
preserved as evidence even though they are outside the farm-entity boundary.

## Reachability and contact fields

- 559 retained entities have a website value.
- 498 have at least one social profile.
- 745 have a direct public phone or email in staging.

These values describe field availability, not promotion readiness. A candidate with
none of these fields remains retained.

## Data quality checks

- Exactly four Texas state files are committed.
- Every retained row has a farm name and Texas entity ID.
- Entity IDs and normalized-name/county-equivalent keys are unique.
- All 99 QA rows contain explicit blockers.
- No active excluded normalized name remains staged.
- Every active exclusion uses affirmative evidence.
- Source, retained, and excluded observation counts reconcile.
- The corrected 299-row LA/MS canonical boundary is unchanged.

## Promotion blockers

1. Resolve or deliberately retain the remaining 92 QA candidates through append-only geography-enrichment and identity/type batches.
2. Copy the three immutable evidence objects to managed production storage.
3. Re-run validation and bind owner approval to the resulting release fingerprint.
4. Promote Texas atomically in a separate canonical-release change.
## Geography Batch 13 — No-city geography triage

Thirty retained QA records without a city or safe public service area received
append-only retain decisions. Their source records do not support a defensible
county assignment, and no affirmative exclusion evidence was established. They
remain visible in QA for evidence-bound geography enrichment rather than being
assigned a guessed county.

## Geography Batch 14 — Published city and farm-location corrections

Eight retained records received append-only county corrections from published
locations: Augustus Ranch and Jim Franks Farm Direct Meat to Lavaca; Bee Space
Apiaries to Collin; Big Oaks Ranch to Rusk; Cimarron Organics to Potter; Direct
Source Meats to Bexar; Harmony Hollow Apiaries to Dallas; and Texas Farm Patch to
Atascosa. Seven had geography as their only blocker and moved to the promotion-
eligible review set. Direct Source Meats remains in QA because its producer/type
classification and independent farm-operation evidence are unresolved.

## Geography Batch 15 — Remaining no-city QA triage

Twenty-eight additional retained QA records without a city or safe public service
area received append-only retain decisions. The source records do not support a
defensible county assignment, so they remain visible in QA for future evidence-
bound geography enrichment rather than receiving guessed counties.
