# SC collected release

> Release: `sc-collected-v2-2026-07-16`
>
> Lifecycle: `collected` — not coverage-reviewed, not approved, and not canonical

## Result

This multi-source collection retained **1865 source observations** and reconciled them into **1603 candidate entities**. **1011** pass the initial staging field gates and route to Validation review. **592** remain in QA because required geography, production scope, outreach, or identity evidence is incomplete.

This is a broad source capture, not a claim that every operating farm in the state has been found. Directory overlap, stale listings, county gaps, and additional state-specific sources still require review.

| Measure | Count |
|---|---:|
| Source observations | 1865 |
| Candidate entities | 1603 |
| Initial eligible → Validation | 1011 |
| Research / QA | 592 |
| Counties with candidates | 46 of 46 |

## Validation routing

Rows with the initial field and evidence gates pass into Validation review. Non-passing rows remain retained in the QA queue; they are not discarded. Validation may return a row to QA when identity, county, farm status, or public-contact evidence does not pass.

## Sources captured

The collection includes the official/state directories, U.S. Farm Trail, EatWild, PickYourOwn, and—where available—state agritourism or farm-directory listings. Queued sources are recorded in `state.yaml`; every new named operation remains retained and only affirmative evidence can exclude a candidate.
