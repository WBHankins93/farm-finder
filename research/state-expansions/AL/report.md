# Alabama state review report

> Release: `al-coverage-reviewed-v6-qa-2026-07-16`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not approved and not canonical

## Outcome

Alabama has statewide discovery coverage across all 67 counties. This identity
and type QA revision retains 807 named candidates: 799 currently meet staged
field and evidence gates, while eight remain visible in the research/QA queue.
Camp Creek Canning and Canning with Cox Crew were affirmatively excluded after
current evidence identified prepared-food processors rather than independent
farm operations. Rainbow Omega's earlier exclusion was superseded by stronger
current evidence and remains excluded. Alabama is not approved or canonical;
the immutable evidence bundle still requires a managed production-storage copy.

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
| Affirmatively excluded observations | 9 |
| Effective excluded entity groups | 9 |
| Append-only decisions | 92 |
| Counties reviewed | 67 of 67 |
| Counties with retained candidates | 67 |
| Counties with promotion-eligible candidates | 67 |

Entity observation counts plus the nine affirmatively excluded observations
reconcile exactly to all 1,057 observations.

## Current QA queue

The current release retains eight candidates in QA. Missing, stale, or
conflicting details remain research work rather than deletion:

| Candidate | County | Follow-up required |
|---|---|---|
| Easterling's Big Peach | Chilton | Resolve conflicting current operating status. |
| Deloney Farms | Dale | Resolve the same-name identity conflict. |
| Bertie K. Burton | DeKalb | Obtain current corroboration. |
| Gilbert Strawberry Farm | DeKalb | Obtain independent corroboration. |
| Vic & Tillie Hummer | Houston | Obtain direct corroboration. |
| Lone Oak | Jackson | Confirm the county-distinct operation without merging the Macon County operation. |
| Fresh Off The Farm | Mobile | Obtain direct corroboration. |
| George R. Carlton | Tallapoosa | Obtain direct operational corroboration. |

All eight remain in `entities.csv`; none is treated as closed merely because a
website, recent listing, or other field is unavailable.

## Append-only QA batch

The `alreview_20260716_080`–`090` batch contains 11 researched dispositions.
Two current QA candidates were affirmatively excluded as prepared-food
processors. Rainbow Omega's prior exclusion was corroborated with grade-B
current member and organization evidence. The remaining eight dispositions
retain named candidates in QA, including a county-distinct Jackson County Lone
Oak row separate from the Macon County operations.

All decisions remain in `decisions.csv`; superseded decisions are retained for
auditability. The batch skips no researched row as a true duplicate: each row
either changes the effective outcome or adds materially newer, more specific,
or higher-grade evidence. The two current `main` decisions that had already
superseded stale links are correctly superseded by `alreview_20260716_082` and
`alreview_20260716_088`.

## Affirmative exclusions retained

Seven earlier records plus the two new processor decisions are positively
identified as educational, cooperative, institutional, prepared-food, or
outside-jurisdiction records rather than Alabama independent farm entities:
Auburn University Transformation Garden, Enterprise State Community College,
East Alabama Black Belt Farmer's Cooperative, Guntersville Middle School FFA,
Viking Horticulture / Mary G. Montgomery High School Academy of Agribusiness,
Rainbow Omega Eastaboga, Camp Creek Canning, Canning with Cox Crew, and Ganus
Farms. Ganus Farms is a valid farm, but its address and coordinates place it in
Mississippi, so it is preserved for Mississippi review rather than Alabama
staging.

Each exclusion has an effective append-only decision, an evidence URL, a
retrieval date, and an allowed affirmative reason. Superseded absence-based
exclusions remain in decision history but no longer affect the candidate table.

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

1. Resolve or deliberately retain the 8 QA candidates through append-only decisions.
2. Copy the immutable evidence objects from local versioned staging to managed
   production storage.
3. Re-run validation and bind owner approval to the resulting release fingerprint.
4. Promote Alabama atomically in a separate canonical-release change.
