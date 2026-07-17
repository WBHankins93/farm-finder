# South Carolina state review report

> Release: `sc-collected-v2-2026-07-17`
>
> Lifecycle: `collected` — not coverage-reviewed, not approved, and not canonical

## Result

This multi-source collection retained **1865 source observations** and reconciled them into **1603 candidate entities**. **1018** pass the initial staging field gates and route to Validation review. **585** remain in QA because required geography, production scope, outreach, or identity evidence is incomplete.

The geography QA batch applied **159** deterministic Census place-by-county proposals; two additional proposals were withheld because the resolved county collided with an existing same-name entity (`SC-533A3E8CF2`, `SC-F4D53865FC`) and now await identity review. The paired corrections are append-only grade-B decisions; eligible staging remains a handoff to Validation, not record verification or approval.

This is a broad source capture, not a claim that every operating farm in the state has been found. Directory overlap, stale listings, county gaps, and additional state-specific sources still require review.

| Measure | Count |
|---|---:|
| Source observations | 1865 |
| Candidate entities | 1603 |
| Initial eligible → Validation | 1018 |
| Research / QA | 585 |
| Counties with candidates | 47 of 46 |

## Validation routing

Rows with the initial field and evidence gates pass into Validation review. Non-passing rows remain retained in the QA queue; they are not discarded. Validation may return a row to QA when identity, county, farm status, or public-contact evidence does not pass.

## Geography QA batch

The resolver left **397** ambiguous or unlisted places unresolved and found **0** county conflicts; neither category was changed. Applied proposals replace only the county-equivalent value, remove the geography blocker, apply the drafted residual blockers and status, and append the exact paired `correct` decision.

## Sources captured

The collection includes the official/state directories, U.S. Farm Trail, EatWild, PickYourOwn, and—where available—state agritourism or farm-directory listings. Queued sources are recorded in `state.yaml`; every new named operation remains retained and only affirmative evidence can exclude a candidate.
