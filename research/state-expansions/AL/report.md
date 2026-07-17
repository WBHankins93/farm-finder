# Alabama state review report

> Release: `al-coverage-reviewed-v6-qa-2026-07-16`
>
> Contract: national state contract v2
>
> Lifecycle: `record_verified` — record-level QA complete; not approved and not canonical

## Outcome

Alabama has statewide discovery coverage across all 67 counties. This identity
and type QA revision retains 807 named candidates: 800 currently meet staged
field and evidence gates, and no candidates remain in the research/QA queue.
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
| Promotion-eligible reviewed entities | 807 |
| Research/QA entities | 0 |
| Affirmatively excluded observations | 9 |
| Effective excluded entity groups | 9 |
| Append-only decisions | 101 |
| Counties reviewed | 67 of 67 |
| Counties with retained candidates | 67 |
| Counties with promotion-eligible candidates | 67 |

Entity observation counts plus the nine affirmatively excluded observations
reconcile exactly to all 1,057 observations.

## Current QA queue

The current release has no remaining research/QA candidates. All seven retained
residue rows were reviewed row-by-row against current 2026 directory or official
program evidence and received append-only corroboration decisions; no candidate
was excluded.

## Append-only QA batch

The `alreview_20260716_080`–`090` batch contains 11 researched dispositions.
Two current QA candidates were affirmatively excluded as prepared-food
processors. Rainbow Omega's prior exclusion was corroborated with grade-B
current member and organization evidence. The remaining seven dispositions
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

1. Resolve or deliberately retain the 7 QA candidates through append-only decisions.
2. Copy the immutable evidence objects from local versioned staging to managed
   production storage.
3. Re-run validation and bind owner approval to the resulting release fingerprint.
4. Promote Alabama atomically in a separate canonical-release change.

## Judgment-only QA residue — 2026-07-17

This QA-zero batch added **7** append-only corroboration decisions and made no exclusions. The current contract counts are **807 entities**, **807 promotion-eligible reviewed**, and **0 research/QA**. The remaining judgment-only residue is **0** rows. Alabama is now `record_verified`; managed evidence storage and explicit approval remain separate promotion gates.


## QA-zero batch — 2026-07-17

This ordered QA batch ran triage, the geography resolver (zero applicable rows), and the corroboration assistant before row-by-row review. Current evidence corroborated Deloney Farms, Bertie K. Burton, Gilbert Strawberry Farm, Vic & Tillie Hummer, Fresh Off The Farm, and George R. Carlton through current 2026 directory listings. Lone Oak was corroborated through the current Alabama Farmers Market Authority U-pick record, while the Jackson County entity remained distinct from the Macon County Lone Oak. No exclusions were made.
