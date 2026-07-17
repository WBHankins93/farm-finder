# Texas state review report

> Release: `tx-coverage-reviewed-v6-qa-2026-07-15`
>
> Contract: national state contract v2
>
> Lifecycle: `coverage_reviewed` — not record-verified, approved, or canonical

## Outcome

Texas has completed the documented three-pass discovery process across all 254
counties. This rebased QA checkpoint retains 835 named candidates:
767 currently meet staged field and evidence gates, while 68
remain in research/QA. Production `record_verified` still requires QA to reach zero.

The reapplication preserves main's existing append-only history, appends 53
non-duplicate current QA dispositions, and repairs four duplicate entity groups.
It adds 13 affirmative exclusions and promotes 31 candidates
from QA to promotion-eligible review. All original source observations remain
preserved in immutable evidence.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 1,063 |
| Retained candidate entities | 835 |
| Promotion-eligible reviewed entities | 767 |
| Research/QA entities | 68 |
| Affirmatively excluded observations | 89 |
| Effective excluded entity groups | 69 |
| Append-only decisions | 290 |
| Counties reviewed | 254 of 254 |
| Counties with retained candidates | 178 |
| Counties searched with none found | 76 |
| Counties with promotion-eligible candidates | 173 |

Retained entity observation counts plus the 89 affirmatively
excluded source observations reconcile exactly to all 1063 observations.
Multiple source observations can support one excluded entity group.

## QA profile

The 68 QA entities remain in `entities.csv`. Blockers overlap:

| Blocker | Entities |
|---|---:|
| County-equivalent missing | 41 |
| Single grade-E discovery listing needs corroboration | 21 |
| City or safe public service area missing | 41 |
| Member/vendor candidate needs independent farm-operation evidence | 11 |

Missing geography, contact detail, or current corroboration does not imply that a
farm is invalid or closed. The correct follow-up is enrichment from farm-owned,
official, or independently corroborating sources.

## Reapplied actions

- Preserved main's existing affirmative exclusions and promotions; stale branch
  retain decisions that would regress current main were not reintroduced.
- Added current evidence-backed exclusions for non-farm channels, processors,
  distributors, and confirmed closures, with each new decision superseding the
  prior current disposition for that candidate.
- Promoted current farms with new geography or farm-operation corroboration,
  including Rio Fresh, Buena Tierra, Mid-Valley Ag, and Texas Tribal Buffalo
  Project.
- Consolidated Rio Fresh, South Tex Organics, Barnard Beef, and Val Verde
  duplicate labels while retaining all source observation IDs.
- Reflected curator verification for Davis 20 Beef as a second observation;
  its entity row now has `obs=2` and evidence grades `C; E`.

## Promotion blockers

1. Resolve or deliberately retain the remaining 68 QA candidates through
   append-only review; the interim task checkpoint is 50 or fewer.
2. For canon-level `record_verified`, reduce the QA count to zero.
3. Copy the immutable evidence objects to managed production storage.
4. Re-run validation and bind owner approval to the resulting release fingerprint.
5. Promote Texas atomically in a separate canonical-release change.
