# Alabama state completion report

> Release: `al-coverage-reviewed-2026-07-15`
> Reviewed: 2026-07-15
> Boundary: private Alabama staging; LA/MS remains canonical

## Decision

Alabama is **coverage reviewed** under FarmFinder's documented three-pass state
standard. The release contains 1,048 source observations reconciled to 850 proposed
entities. Of those, 635 meet the staged promotion gates and 215 remain explicitly
blocked for further research or QA. No Alabama rows were added to the LA/MS canonical
workbook or public application in this release.

This is a bounded research conclusion, not a claim that every farm in Alabama has been
found. FarmFinder targets publicly discoverable, consumer-facing farms and producers;
private and commodity-only farms are outside the directory scope.

## Collection results

| Measure | Result |
|---|---:|
| Primary/channel datasets evaluated | 14 |
| Retained source observations | 1,048 |
| Proposed Alabama entities | 850 |
| Promotion-eligible staged entities | 635 (74.7%) |
| Research/QA entities | 215 (25.3%) |
| Counties with candidates | 67 / 67 |
| Counties with at least one eligible entity | 66 / 67 |
| Website present | 252 entities (29.6%) |
| Any retained social URL | 419 entities (49.3%) |
| Direct phone or email retained internally | 776 entities (91.3%) |
| Grade-F/off-state exclusions | 2 |

The single county without a promotion-eligible entity is Sumter. It has two retained
PickYourOwn discovery candidates, but both remain grade-E-only and need current
corroboration before promotion.

## Source passes

### Pass 1 — state and official

- Sweet Grown Alabama: 407 records explicitly typed as farms.
- Alabama Farmers Market Authority farm-stand map: 117 records.
- Alabama Farmers Market Authority U-pick map: 82 records.
- 2026 statewide FMA farm-stand roster: 134 parsed roster observations.
- Alabama Plant Protection bee-seller list: 34 records retained for entity-type review.
- Alabama Farm to School farmer page: evaluated; no public searchable producer roster.

### Pass 2 — market channels and producer directories

- Bama Beef Sales Directory: 98 direct-sale beef producers.
- EatWild Alabama: 10 physically Alabama-based farm profiles; out-of-state suppliers
  serving Alabama were not accepted as Alabama farms.
- FMA farmers-market map: 157 raw market/channel records retained in the source
  snapshot, but none were typed as farms.

### Pass 3 — discovery and county gaps

- All four Alabama PickYourOwn regions: 166 retained observations across 66 published
  county sections. Pickens, the only county without a PickYourOwn section, already had
  candidates in official/statewide and Bama Beef sources.
- US Farm Trail Alabama page: evaluated and rejected as an automatic entity source.
  Its rendered data mixed farms, markets, duplicates, off-state results, and weak
  per-record provenance. The rejection is logged rather than silently omitted.

## Identity accountability

There are 146 multi-observation normalized-name groups:

- 135 merged because the exact normalized name resolved to one geography;
- 6 cross-county groups merged only after shared phone/email/social or repeated-city
  evidence identified one operation and a preferred source geography;
- 1 JYJ Red Angus group merged through curator review using the current Sweet Grown
  individual profile and farm-owned evidence for Columbia/Houston County;
- 4 groups remain split because the same normalized name refers to plausible distinct
  operations in different counties: Circle M Ranch, Edmondson Farm, JJ's Produce, and
  Lone Oak.

No fuzzy-name group was silently merged. The observation IDs and decision for every
multi-source group are in the manifest-pinned `identity_review` evidence artifact.

## Open issues

The 215 QA entities can carry more than one blocker:

| Blocker | Entities |
|---|---:|
| Single grade-E discovery listing needs corroboration | 111 |
| City or safe public service area missing | 102 |
| Bee seller needs evidence of a qualifying farm operation | 29 |
| Same normalized name remains split across counties | 8 entity rows / 4 groups |
| Product or farm activity specificity missing | 6 |

Two Sweet Grown entries were excluded from Alabama entities because their public
addresses and coordinates resolve outside the state: Ganus Farms (Waynesboro,
Mississippi) and Rocky Hollow Patch at Angel Farm (Cave Spring, Georgia). Both source
observations remain in the manifest-pinned `exclusions` evidence artifact.

Four geography service responses are logged as errors: the two correct non-Alabama
FCC results above and two Census exact-address misses. The latter were resolved by
documented city/ZIP geography review (Red Briar Highlands in Clay County and Wide Open
Spaces in Etowah County). Primary collection datasets had no request failures.

## Quality and privacy controls

- Every eligible staged entity has a name, reviewed entity type, state, county, city
  or safe service area, product/activity, source URL/date, identity decision, and
  address/contact visibility classification.
- Exact source addresses and direct contacts remain internal pending public-use
  review; a future public release should use farm-confirmed visitor locations or
  reduced precision.
- Source observations are never overwritten by reconciliation. Entity rows point back
  to all contributing observation IDs.
- Markets, retailers, and directories are not promoted as farms without farm-operation
  evidence.
- The validator checks count reconciliation, IDs, county coverage, promotion fields,
  evidence grades, source-pass coverage, and that the LA/MS canonical manifest remains
  at 311 rows with allowed states LA/MS.

## Release disposition

Alabama is complete at the `coverage_reviewed` research stage and ready for deliberate
immutable-release review. Promotion is intentionally separate: the 635 eligible staged
entities should not be appended to the canonical workbook until a new release ID,
storage object, checksum, app mapping, rollback point, and public-location/privacy
review are prepared.
