# Texas state review report

> Release: tx-coverage-reviewed-v6-qa-2026-07-15
>
> Contract: national state contract v2
>
> Lifecycle: coverage_reviewed — not record-verified, approved, or canonical

## Outcome

Texas completed the documented three-pass discovery process across all 254
counties. This QA checkpoint retains 803 named candidates:
800 currently meet staged field and evidence gates,
while 3 remain in research/QA.

The 2026-07-17 batch applied 63 append-only decisions: 32
affirmative outside-jurisdiction exclusions, 9 geography corrections, and
22 current-operation corroborations. Three status/current-operation
rows remain QA because available directory language is an assumption or lacks
current operating confirmation; no absence-based exclusion was applied.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | 1063 |
| Retained candidate entities | 803 |
| Promotion-eligible reviewed entities | 800 |
| Research/QA entities | 3 |
| Affirmatively excluded observations | 121 |
| Effective excluded entity groups | 101 |
| Append-only decisions | 357 |
| Counties reviewed | 254 of 254 |
| Counties with retained candidates | 178 |
| Counties with promotion-eligible candidates | 176 |

Retained entity observation counts plus affirmatively excluded source
observations reconcile to the immutable source total. Named candidates remain
durable in immutable evidence even when excluded from this state release.

## QA profile

The 3 QA entities remain in entities.csv:

| Blocker | Entities |
|---|---:|
| Current first-party operating-status or affirmative closure evidence missing | 3 |

The unresolved rows are Universal Farms, Upicberries, and Shoestring Cattle
Co.; their directory pages explicitly lack affirmative current closure or
operating confirmation. They remain QA under the non-deletion policy.

## Applied actions

- Excluded 32 current profiles whose cited current locations are outside Texas,
  each with outside_jurisdiction evidence.
- Corrected 9 Texas city/county records using current operation or authoritative
  local-food sources.
- Corroborated 22 current Texas operations, including farm, orchard, dairy,
  produce, and ranch operations, and cleared their QA blockers.
- Ran resolve_geography.py and corroboration_assistant.py before the row-by-row
  review; no automatic geography proposal was accepted and the assistant
  produced no accepted proposal in this batch.

## Promotion blockers

1. Resolve the three remaining rows with current first-party operating-status
   evidence or affirmative cited closure evidence.
2. After QA reaches zero, update lifecycle to record_verified.
3. Managed evidence copy, approval, and canonical promotion remain separate
   gates.
