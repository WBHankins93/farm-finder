# Texas state review report

> Release: `tx-coverage-reviewed-v6-qa-2026-07-15`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not record-verified, approved, or canonical

## Outcome

Texas has completed the documented three-pass discovery process across all 254
counties. This cleansing checkpoint retains 856 named candidates: 733 currently
meet staged field and evidence gates, while 123 remain in research/QA. The
working objective is to drive the QA queue to 50 or fewer before moving to the
next state; production `record_verified` still requires QA to reach zero.

This checkpoint applied 26 affirmative exclusions and 18 evidence-backed
corrections/corroborations. The exclusions remove current non-farm businesses
(processors, retailers, distributors, and foodservice companies) and candidates
whose current farm identity is outside Texas. The corrections resolve Augustus
Ranch's county and corroborate Davis 20 Beef as a current Wichita Falls ranch,
Four Winds Ranch, Hi Fi Mycology, JJJM Grass Fed Beef, Michael Neighbors,
Ritchie Family Farms, Alaiyo Farm, Broken B Ranch, Ficarro Farms, Happy Feet
Farm, Hudson Plains Raw Dairy, South Texas Mushrooms, Synergic Farms, Wild Herd
Cattle & Kitchen, High Steaks Beef Company, Barnard Beef, and Conundrum Farms
with current Texas farm evidence and geography.
All original source observations remain preserved in immutable evidence.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 1,062 |
| Retained candidate entities | 856 |
| Promotion-eligible reviewed entities | 733 |
| Research/QA entities | 123 |
| Affirmatively excluded observations | 73 |
| Effective excluded entity groups | 53 |
| Append-only decisions | 121 |
| Counties reviewed | 254 of 254 |
| Counties with retained candidates | 179 |
| Counties searched with none found | 75 |
| Counties with promotion-eligible candidates | 172 |

Retained entity observation counts plus the 73 affirmatively excluded source
observations reconcile exactly to all 1,062 observations. Multiple source
observations can support one excluded entity group.

## QA profile

The 123 QA entities remain in `entities.csv`. Blockers overlap:

| Blocker | Entities |
|---|---:|
| County-equivalent missing | 58 |
| Single grade-E discovery listing needs corroboration | 51 |
| City or safe public service area missing | 41 |
| Member/vendor candidate needs independent farm-operation evidence | 44 |
| Reopened assumed/parser-derived closure needs corroboration | 6 |

Missing geography, contact detail, or current corroboration does not imply that a
farm is invalid or closed. The correct follow-up is enrichment from farm-owned,
official, or independently corroborating sources.

## Cleansing actions in this checkpoint

- Excluded 15 current farm identities outside Texas: Acadian Family Farm,
  Brookshire Farm, Crispin Grass-Fed Beef, Dark Water Ranch, Desert Micro,
  Floriography NM, Hardcastle Land and Cattle, Merry Meadows, Nitschke Natural
  Beef/Circle N Ranch, Raccoon Bend Farms, La Semilla Food Center, Nature's
  Comeback Bison Ranch, JX Ranch Natural Beef, Kingdom Cattle Co., and Hill
  Crest Creamery LLC.
- Excluded 11 current non-farm channel, processing, or retail records: Bluebonnet Meat
  Company, Direct Source Meats, River City Produce, Scarmardo Foodservice,
  Hiland Dairy, Gandy's Dairies, H-E-B, Moody's Quality Meats, and Tuttles Meat
  Market, LCF Ranch, and Red River Beef Co.
- Corroborated Augustus Ranch in Lavaca County and corrected Davis 20 Beef from
  the source's Clay County classification to Wichita County. Also resolved Four
  Winds Ranch, Hi Fi Mycology, JJJM Grass Fed Beef, Michael Neighbors, and
  Ritchie Family Farms with current Texas farm evidence and geography.
- Merged the duplicate JJJM Grass Fed Beef observation into the retained
  Collin County entity; both source observations remain linked to that entity.
- Preserved every excluded observation and decision append-only; no record was
  removed solely because information was missing.

## Promotion blockers

1. Resolve or deliberately retain the remaining 123 QA candidates through
   append-only review; the interim task checkpoint is 50 or fewer.
2. For canon-level `record_verified`, reduce the QA count to zero.
3. Copy the immutable evidence objects to managed production storage.
4. Re-run validation and bind owner approval to the resulting release
   fingerprint.
5. Promote Texas atomically in a separate canonical-release change.
