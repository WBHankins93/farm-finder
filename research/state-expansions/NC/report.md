# North Carolina state review report

> Release: `nc-collected-v2-2026-07-17`
>
> Lifecycle: `collected` — not coverage-reviewed, not approved, and not canonical

## Result

This multi-source collection retained **4377 source observations** and reconciled them into **3415 candidate entities**. **1139** pass the initial staging field gates and route to Validation review. **2276** remain in QA because required geography, production scope, outreach, or identity evidence is incomplete.

The geography QA batch applied **1770** deterministic Census place-by-county proposals; two additional proposals were withheld because the resolved county collided with an existing same-name entity (`NC-868FE01B26`, `NC-50F76C606B`) and now await identity review. The paired corrections are append-only grade-B decisions; eligible staging remains a handoff to Validation, not record verification or approval.

This is a broad source capture, not a claim that every operating farm in the state has been found. Directory overlap, stale listings, county gaps, and additional state-specific sources still require review.

| Measure | Count |
|---|---:|
| Source observations | 4377 |
| Candidate entities | 3415 |
| Initial eligible → Validation | 1139 |
| Research / QA | 2276 |
| Counties with candidates | 99 of 100 |

## Validation routing

Rows with the initial field and evidence gates pass into Validation review. Non-passing rows remain retained in the QA queue; they are not discarded. Validation may return a row to QA when identity, county, farm status, or public-contact evidence does not pass.

## Geography QA batch

The resolver left **1142** ambiguous or unlisted places unresolved and found **0** county conflicts; neither category was changed. Applied proposals replace only the county-equivalent value, remove the geography blocker, apply the drafted residual blockers and status, and append the exact paired `correct` decision.

## Sources captured

The collection includes the official/state directories, U.S. Farm Trail, EatWild, PickYourOwn, and—where available—state agritourism or farm-directory listings. Queued sources are recorded in `state.yaml`; every new named operation remains retained and only affirmative evidence can exclude a candidate.

## Judgment-only QA residue — 2026-07-17

This append-only batch added **2** evidence decisions and made no exclusions. The current contract counts are **3,415 entities**, **1,139 promotion-eligible reviewed**, and **2,276 research/QA**. The remaining judgment-only residue is **0** rows: **0** canonical-baseline research items and **0** status items without affirmative current closure/operation evidence. Missing evidence remains a routed research blocker.
