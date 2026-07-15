# Texas state completion report

> Release: `tx-coverage-reviewed-2026-07-15`
> Reviewed: 2026-07-15
> Boundary: private Texas staging; LA/MS remains canonical

## Decision

Texas is **coverage reviewed** under FarmFinder's documented three-pass state
standard. The release contains 1,021 source observations reconciled to 919 proposed
entities. Of those, 319 meet the staged promotion gates and 600 remain explicitly
blocked for further research or QA. No Texas rows were added to the LA/MS canonical
workbook or public application in this release.

This is a bounded research conclusion, not a claim that every farm in Texas has been
found. FarmFinder targets publicly discoverable, consumer-facing farms and producers;
private and commodity-only farms are outside the directory scope.

## Collection results

| Measure | Result |
|---|---:|
| Source/channel/geography datasets evaluated | 28 |
| Successful collection requests | 897 / 897 |
| Retained source observations | 1,021 |
| Proposed Texas entities | 919 |
| Promotion-eligible staged entities | 319 (34.7%) |
| Research/QA entities | 600 (65.3%) |
| Counties with candidates | 179 / 254 |
| Counties with at least one eligible entity | 111 / 254 |
| Website present | 599 entities (65.2%) |
| Any retained social URL | 507 entities (55.2%) |
| Direct phone or email retained internally | 792 entities (86.2%) |
| Explicit closure exclusions | 13 |

Among the 319 eligible entities, 251 have a website, 203 have at least one retained
social URL, and 301 have a direct phone or email retained internally.

The 75 `searched_none_found` counties are Andrews, Archer, Armstrong, Bailey, Baylor,
Borden, Briscoe, Brooks, Cochran, Coke, Crockett, Crosby, Culberson, Dawson, Deaf Smith,
Dickens, Duval, Foard, Glasscock, Gray, Gregg, Hale, Hall, Hansford, Haskell, Hemphill,
Hockley, Hudspeth, Hutchinson, Irion, Jack, Jeff Davis, Jim Hogg, Jones, Kenedy, Kent,
King, Kinney, Kleberg, Knox, Lamb, Lipscomb, Loving, Lynn, Madison, McMullen, Mills,
Newton, Nolan, Ochiltree, Oldham, Pecos, Reagan, Real, Roberts, Runnels, San Augustine,
Scurry, Shackelford, Sherman, Starr, Stephens, Sterling, Stonewall, Terry, Throckmorton,
Upton, Victoria, Ward, Wheeler, Wilbarger, Willacy, Winkler, Young, and Zapata. Zero is
not evidence that a county has no farms; it means the documented sources returned no
qualifying public candidate with a defensible county assignment.

## Source passes

### Pass 1 — state and official

- Texas Department of Agriculture GO TEXAN Farm And Ranch: 100 grade-B observations.
- Texas Department of Agriculture Farm to School vendor resource: 111 PDF rows parsed;
  100 producer/processor candidates retained and 11 distributors retained only in raw
  evidence. The 100 candidates require farm-operation review unless independently
  corroborated.
- Texas Department of Agriculture 2026 Certified Farmers Markets: evaluated as channel
  infrastructure; markets were not converted into farm entities.
- U.S. Census TIGERweb: exactly 254 Texas counties established the denominator.

### Pass 2 — local-food and producer directories

- Texas Center for Local Food Farms & Ranches: 254 detailed profiles. Two hundred are
  primarily typed as farms/ranches; distributor- or community-garden-primary profiles
  require independent farm-operation evidence.
- EatWild Texas: 51 pastured-product farm observations.
- Shop Texas Farms: all three directory pages and 56 detailed member profiles. Member
  status alone does not prove a farm, so uncorroborated rows remain type-review items.

### Pass 3 — discovery and county gaps

- All 13 published PickYourOwn Texas regions: 158 observations across 251 county
  sections, including 13 explicit closure exclusions. The San Angelo region had 15
  county sections and no active farm listing under the parser's farm block.
- LocalHarvest: all 254 official Texas county seats searched, yielding 2,880 search-card
  appearances deduplicated to 302 detailed farm profiles. Twelve profiles were current
  enough for grade D; 290 remain grade E because their exposed update date was older
  than 180 days or absent.
- USDA AMS Local Food Directories: official interface evaluated, but no documented
  public bulk/API contract was available; no hidden endpoint was scraped.
- US Farm Trail Texas: evaluated and rejected as an automatic entity source because of
  mixed entity types, duplicates, and weak per-record provenance.
- YouPickTexas: evaluated and rejected because the displayed placeholder-style contact
  data and unclear source provenance did not meet the release evidence standard.
- Census 2020 ZCTA-to-county and place-by-county references were used only for wholly
  single-county ZIP tabulation areas or places. Ambiguous cross-county geography was
  not inferred.

## Identity accountability

There are 78 multi-observation normalized-name groups:

- 70 merged because the exact normalized name resolved to one geography;
- 7 cross-county groups merged only after exact shared contact, website, social, city,
  or address evidence established one operation and a preferred geography;
- 1 group remains split: The Blueberry Farm has plausible separate operations in
  Tyler County/Warren and Wood County/Quitman.

The cross-county merges are American Criollo Beef Alliance, Bandera Grassland,
Barnard Beef Cattle Company, Blessington Farms, Circle J Meat, The Farm at Bald Hill,
and Weise Farms. Barnard was merged only after identical normalized name and P.O.
Box/ZIP evidence was found; the conflicting county assertions remain in the identity
review record.

Three Texas names collide with current LA/MS names—Briarhill Farms, Brookshire Farm,
and Hill Crest Creamery—but no cross-state merge occurred. No fuzzy-name group was
silently merged. Every multi-source decision and underlying observation ID is in
`identity-review.csv`.

## Open issues

The 600 QA entities can carry more than one blocker:

| Blocker | Entities |
|---|---:|
| Single grade-E discovery listing needs current corroboration | 479 |
| Member/vendor/mixed-type candidate needs farm-operation evidence | 149 |
| County remains unresolved | 97 |
| City or safe public service area missing | 75 |
| Product or farm-activity specificity missing | 45 |
| Official Farm And Ranch category conflicts with business-name signals | 6 |
| Same normalized name remains split across counties | 2 entity rows / 1 group |

The 97 county-blocked entities represent 107 source observations. The release attempted
143 exact-address Census geography requests; 61 returned no match. Conservative
single-county ZCTA and Census-place fallbacks reduced the unresolved observation count
from 235 to 107. Records without an exact match or a wholly single-county fallback were
left unresolved rather than assigned from a nearby county-seat search.

One official source-county conflict is retained: Hill Farm To Table Ranch was listed
as Navarro County but its exact address resolved to Hill County. The exact-address
county is used in the proposed entity and the conflict remains in
`geography-conflicts.csv`.

Six GO TEXAN-only names remain blocked because their business-name signals conflict
with an automatic farm interpretation: Bastrop 1832 Farmers Market, Wylie Urban Farm
And Market, QF Seasoning Company, Hillsboro Farmers Market, ETX Legends Coffee Co, and
Cowpuncher Coffee LLC.

## URL and data-quality corrections made during review

- LocalHarvest's global CSAware footer link was removed from farm website fields;
  only profile-specific contact-block websites are retained.
- Shop Texas Farms' shared interactive directory map was removed from member website
  fields; only profile-specific external sites remain.
- Map, social, asset-host, and malformed URLs are rejected from the website field.
- Shop Texas Farms addresses are parsed only from the profile's address block, not
  surrounding review or directory text.
- Farm-to-school ZIP extraction uses the final ZIP-like value in the address so a
  five-digit rural street number cannot be mistaken for the postal code.
- Texas Center for Local Food counties are accepted only when they match the official
  254-county denominator; city-like location terms are not treated as counties.

## Quality and privacy controls

- Every eligible staged entity has a name, reviewed farm entity type, state, county,
  city or safe service area, product/activity, source URL/date, identity decision, and
  address/contact visibility classification.
- Exact source addresses and direct contacts remain internal pending public-use review;
  a future public release should use farm-confirmed visitor locations or reduced
  precision.
- Source observations are never overwritten by reconciliation. Entity rows point back
  to all contributing observation IDs.
- Markets, retailers, processors, distributors, community gardens, and directory
  members are not promoted as farms without farm-operation evidence.
- The validator checks count reconciliation, unique IDs, URL hygiene, all 254 county
  statuses, promotion fields, evidence grades, every major source/profile request,
  raw-evidence completeness, and that the LA/MS canonical manifest remains 311 rows
  with allowed states LA/MS.

## Release disposition

Texas is complete at the `coverage_reviewed` research stage and ready for deliberate
immutable-release review. Promotion is intentionally separate: the 319 eligible
staged entities should not be appended to the canonical workbook until a new release
ID, storage object, checksum, app mapping, rollback point, and public-location/privacy
review are prepared. The 600 QA entities remain valuable evidence but are not approved
public farm listings.
