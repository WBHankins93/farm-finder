# Alabama state review report

> Release: `al-identity-qa-v5-2026-07-16`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

Alabama has statewide discovery coverage across all 67 counties. This immutable
identity/type QA revision retains 807 named candidates: 799 currently meet staged
field and evidence gates, while eight remain visible in the research/QA queue.
Three candidates were affirmatively excluded after current evidence established
that they were processors or an institution, not independent farm entities.
Alabama is not approved or canonical; the immutable evidence bundle still requires
a managed production-storage copy.

The earlier `record_verified` claim was withdrawn. It reached zero QA partly by
excluding candidates when current corroboration or fields were missing. That
behavior violates the national retention policy.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 1,057 |
| Retained candidate entities | 807 |
| Promotion-eligible reviewed entities | 799 |
| Research/QA entities | 8 |
| Affirmatively excluded observations | 6 |
| Effective excluded entity groups | 9 |
| Append-only decisions | 90 |
| Counties reviewed | 67 of 67 |
| Counties with retained candidates | 67 |
| Counties with promotion-eligible candidates | 67 |

Entity observation counts plus the six affirmatively excluded observations
reconcile exactly to all 1,057 observations.

## Missing-data correction

Fourteen candidates were restored from the former exclusion set. Missing, stale,
or conflicting details now produce research work rather than deletion.

Three restored records contain sufficient current production and geography detail
for staged eligibility:

- Black Creek Milling — the source describes its quail farm and locally grown corn.
- Generations Forward Learning Farm — the source describes a 12-acre producing farm,
  orchards, produce, U-pick, and public programs.
- Rocky Hollow Patch at Angel Farm — the source explicitly says the farm property
  crosses into Alabama even though its postal address is in Georgia.

Eight retained candidates remain in QA:

| Candidate | County | Follow-up required |
|---|---|---|
| Easterling's Big Peach | Chilton | Resolve conflicting current operating status. |
| Deloney Farms | Dale | Resolve the same-name identity conflict. |
| Bertie K. Burton | DeKalb | Obtain current corroboration. |
| Gilbert Strawberry Farm | DeKalb | Obtain current corroboration. |
| Vic & Tillie Hummer | Houston | Obtain current corroboration. |
| Lone Oak | Jackson | Obtain current corroboration without merging the Macon County operation. |
| Fresh Off The Farm | Mobile | Obtain current corroboration. |
| George R. Carlton | Tallapoosa | Obtain current corroboration. |

The three affirmative type decisions are recorded in the 2026-07-16 append-only
batch: Camp Creek Canning and Canning with Cox Crew are prepared-food processors;
Rainbow Omega is a nonprofit residential/vocational organization whose growing
program does not make the organization an independent farm entity under the
FarmFinder boundary.

All eleven remain in `entities.csv`; none is treated as closed merely because a
website, recent listing, or other field is unavailable.

## Affirmative exclusions retained

Five records are positively identified as educational or cooperative institutions
rather than independent farm entities: Auburn University Transformation Garden,
Enterprise State Community College, East Alabama Black Belt Farmer's Cooperative,
Guntersville Middle School FFA, and Viking Horticulture / Mary G. Montgomery High
School Academy of Agribusiness. Ganus Farms is a valid farm but its address and
coordinates place it in Mississippi, so it is preserved for Mississippi review
rather than Alabama staging.

Each exclusion has an effective append-only decision, an evidence URL, a retrieval
date, and an allowed affirmative reason. Superseded absence-based exclusions remain
in decision history but no longer affect the candidate table.

## Data quality checks

- Exactly four state files are committed.
- Every retained row has a farm name and Alabama entity ID.
- Entity IDs and normalized-name/county-equivalent keys are unique.
- All research/QA rows contain an explicit blocker.
- No active excluded normalized name remains staged.
- All active exclusions use `confirmed_nonfarm` or `outside_jurisdiction`.
- Source observations, retained observations, and exclusions reconcile.
- The LA/MS canonical boundary is unchanged.

## Promotion blockers

1. Resolve or deliberately retain the eight QA candidates through append-only decisions.
2. Copy the immutable evidence objects from local versioned staging to managed
   production storage.
3. Re-run validation and bind owner approval to the resulting release fingerprint.
4. Promote Alabama atomically in a separate canonical-release change.
