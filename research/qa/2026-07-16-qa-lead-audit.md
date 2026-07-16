# FarmFinder QA lead audit — 2026-07-16

> **Post-audit note (2026-07-16):** the committed contract figures below reflect
> the branch state at audit time. Main has since merged the AL/TX QA
> dispositions (#10, #15): the committed Alabama release is now
> `al-coverage-reviewed-v5-qa-2026-07-15` (808 entities / 9 QA) and the
> committed Texas release is `tx-coverage-reviewed-v6-qa-2026-07-15`
> (855 entities / 119 QA). The staging-handoff mismatch described in the first
> P1 finding has therefore been reconciled; the finding is retained as the
> record of why that reconciliation was required.

## Scope

This audit covers the current source-of-truth workbook, the committed national
state-release contract, the cutover staging path, and the local state-pipeline
handoffs. It also records the first Alabama record-review batch.

## Gate status

| Layer | Result | Evidence |
|---|---|---|
| Canonical workbook structure/checksum | Pass | `npm run data:validate` — 299 rows, 299 candidate entities, no duplicate groups |
| Committed state contracts | Pass structurally | AL: 810 entities / 11 QA; TX: 883 entities / 167 QA |
| Coverage gate | Pass for AL/TX | 67/67 Alabama counties; 254/254 Texas counties have final searched status |
| Record verification | Blocked | QA queues are non-zero |
| Managed evidence | Blocked | Both committed releases still require managed-storage copies |
| Approval/promotion | Blocked | No approval is bound to the current release fingerprints |
| Cutover unit tests | Pass | 4 tests with the supported `PYTHONPATH=scripts` invocation |

The structural validator passing does not mean either state is approved. The
state lifecycle remains `coverage_reviewed`.

## Pipeline control findings

### P1 — staging handoffs are not the committed state-release authority

The local ignored `data/exports/state-pipeline` manifest contains six staged
states (`AL`, `AR`, `FL`, `GA`, `TN`, `TX`) with 4,444 eligible and 6,663 QA
rows. Its AL handoff is `al-coverage-reviewed-v5-qa-2026-07-15` with 9 QA rows;
the committed AL contract is `al-coverage-reviewed-v4-2026-07-15` with 11 QA
rows. Its TX handoff is `tx-coverage-reviewed-v6-qa-2026-07-15` with 119 QA
rows; the committed TX contract is `tx-coverage-reviewed-v5-2026-07-15` with
167 QA rows.

These are valid staging observations, but the mismatch is a release-integrity
risk if an operator treats ignored exports as promotion input. Every handoff
must be reconciled to a four-file state release and a new immutable evidence
bundle before it can affect approval or canonical data.

### P1 — duplicate source-record keys were replay-order dependent

The cutover importer previously assigned duplicate keys using input order. A
spreadsheet reorder could change which raw observation owned `source:farms:01`,
which breaks idempotent replay and evidence lineage. Fixed in
`03-app/site/scripts/cutover_common.py`; regression coverage now reorders
same-name observations with different contents.

### P1 — decision supersession cycles were accepted

The append-only decision validator checked unknown references but accepted a
cycle, allowing every decision in the cycle to appear superseded. Fixed in
`01-database/tools/state_policy.py`; regression coverage rejects cycles.

### P2 — CI review output was state-hard-coded

The state-release workflow reported only `AL TX`, even when more committed state
directories existed. The status command now discovers all two-letter committed
state directories when no state arguments are supplied, and CI uses that mode.

### P1 — newly started NC/SC releases currently fail the all-state gate

During the audit, new local `NC` and `SC` research directories appeared. NC is a
researching bootstrap with stale repository-file hashes; SC has extra CSV values
past the `entities.csv` header. The validator now reports these as structured
state failures instead of crashing. Neither state is coverage-reviewed, approved,
or canonical. These work-in-progress directories were left untouched.

## Alabama batch 01 — nine current QA records

Evidence was checked on 2026-07-16 against the cited public sources. No record
was excluded. The outcomes below are review dispositions, not approval decisions.

| Candidate | QA disposition | Reason |
|---|---|---|
| Easterling's Big Peach | Retain; candidate for correction in next release | Current 2026 PickYourOwn listing provides address, phone, products, and open hours; independent farm-owned corroboration is still absent. |
| Camp Creek Canning | Retain in QA; producer-type review | Sweet Grown Alabama provides a member page with products, address, phone, and email; evidence supports a local producer/product maker, not necessarily a farm operation. |
| Canning with Cox Crew | Retain in QA; producer-type review | 2025 Alabama promotional coverage corroborates homemade salsa, but does not establish farm production. |
| Deloney Farms | Retain in identity QA | Current U-pick listing and a 2025 Alabama LLC record show the same normalized name with different addresses; do not merge or promote until identity/geography is resolved. |
| Bertie K. Burton | Retain; corroboration needed | Current directory listing has identifying details, but no independent corroborating source was found. |
| Gilbert Strawberry Farm | Retain; corroboration candidate | Current 2026 listing and an independent strawberry directory agree on name, location, phone, and product; farm-owned confirmation is still preferred before promotion. |
| Vic & Tillie Hummer | Retain; corroboration needed | Current listing has pecans, address, phone, and hours; no independent corroborating source was found. |
| Fresh Off The Farm | Retain; corroboration candidate | Current listing has detailed produce, address, phone, email, and hours; an older roadside-stand listing also matches, but a current farm-owned source is still preferred. |
| George R. Carlton | Retain; corroboration candidate | Current listing has blueberries, address, phone, and hours; public agricultural records support the name/geography historically, but not current farm sales. |

Sources reviewed:

- https://www.pickyourown.org/ALmontg.htm
- https://www.pickyourown.org/ALhuntsv.htm
- https://www.pickyourown.org/ALmobile.htm
- https://www.sweetgrownalabama.org/sga-members/1947
- https://www.thisisalabama.org/sweet-grown-alabama-christmas-gift-boxes/
- https://strawberryplants.org/pick-your-own-strawberries/
- https://al.ltd-dir.com/companies/deloney-farms-llc/
- https://doczz.net/doc/8896090/roadside-stands-in-mobile-county-farmers

## Next QA batches

1. Alabama: resolve producer-type and identity cases above; create a new
   immutable release rather than editing the current release in place.
2. Texas: work county-missing records in county batches, beginning with records
   that already have a city/address and a named source URL.
3. Arkansas, Florida, Georgia, and Tennessee: do not promote ignored staged
   exports. First package each state into the four-file contract, bind evidence
   objects, and run the shared validator.
4. Before any approval: reconcile the handoff fingerprint, evidence object
   checksums/version IDs, entity counts, QA count, and public/private projection.
