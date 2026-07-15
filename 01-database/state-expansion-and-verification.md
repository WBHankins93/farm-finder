# FarmFinder state expansion and verification system

> Effective 2026-07-15. The canonical pre-cutover release remains
> `research/local_farm_database_final.xlsx`, sheet `All Farms`, until a reviewed
> release is promoted through `03-app/site/config/source-of-truth.json`.

## Scope

FarmFinder is not attempting to catalog every USDA-defined farm. That would include
large commodity operations and private farms with no consumer-facing activity. The
collection target is a publicly discoverable farm or producer with evidence of at
least one of these channels:

- direct-to-consumer sales, CSA, farm stand, U-pick, or agritourism;
- a farmers-market or food-hub relationship;
- a public producer profile or branded product sold to consumers;
- a farm-owned website or social account that offers products or visits.

Processors, retailers, associations, and markets may be collected as candidates, but
must be typed correctly and are not promoted as farms without farm-operation evidence.

## State-first, region-second model

1. States are the official completeness boundary. Every farm row must resolve to one
   state and, before promotion, one county or parish whenever public evidence allows.
2. Use counties/parishes as collection work units and coverage denominators.
3. Build regional overlays only after the participating states pass their release
   gates. Regional overlays may be Census divisions, foodsheds, metros, or agricultural
   districts; they never replace official state/county geography.
4. Expand outward in waves: finish Mississippi, then the Gulf South, then the remaining
   South, Midwest, Northeast, and West. Alaska and Hawaii remain state releases and get
   Pacific/noncontiguous regional overlays after collection.

## Three-pass collection rule

Each state receives three independently logged collection passes before it can be
marked `coverage_reviewed`:

1. **State/official pass** — agriculture department, extension, state branding
   directory, certified market/vendor rosters, and official open-data sources.
2. **Market-channel pass** — farmers markets, CSAs, food hubs, U-pick, agritourism,
   meat/egg/dairy directories, and producer associations.
3. **Discovery/gap pass** — national directories and county-by-county searches for
   counties with zero or low coverage.

Every HTTP request is attempted up to three times. After the third failure, record the
URL, attempts, error, and date, mark the source `unreachable_after_3_attempts`, and move
on. Never drop a source or candidate silently.

Mississippi's initial staged run uses:

- Pass 1: Genuine MS Grown and Raised archives plus individual producer profiles.
- Pass 2: Mississippi Department of Agriculture and Commerce farmers-market vendors
  and active Farm Marketplace listings.
- Pass 3: all five Mississippi PickYourOwn regions, excluding listings explicitly
  marked permanently closed.

The collector is `01-database/tools/collect_mississippi.py`. It writes staging data to
`research/ms-expansion/` and does not edit the canonical workbook.

All new or rebuilt state releases must follow
`01-database/state-release-contract.md`. Detailed observations and diagnostics belong
in the private evidence bundle; only the four-file contract is committed under
`research/state-expansions/<STATE>/`. The shared validator is
`01-database/tools/validate_state_releases.py`.

Alabama completed all three collection passes on 2026-07-15. Its corrected
coverage-reviewed private release contains 1,057 source observations reconciled to
810 retained entities; 799 are staged-eligible and 11 remain in explicit research/QA.
All 67 counties have a final searched status and at least one eligible candidate. The
collector is `01-database/tools/collect_alabama.py`, and the four-file release is under
`research/state-expansions/AL/`. Alabama is not record-verified, approved, promotion-
ready, or canonical.

Texas completed all three collection passes on 2026-07-15. Its corrected coverage-
reviewed private release contains 1,062 source and curator observations reconciled to
883 retained entities; 716 are staged-eligible and 167 remain in explicit research/QA.
All 254 counties have a final searched status: 179 have candidates, 75 are
`searched_none_found`, and 171 have at least one eligible entity. The collector is
`01-database/tools/collect_texas.py`, and the four-file release is under
`research/state-expansions/TX/`. Texas is not record-verified, approved, promotion-
ready, or canonical.

## Record and field verification

Verification is assertion-based. A source observation never erases an older one; it
creates a newer assertion that can supersede it after review.

| Grade | Evidence | Default freshness |
|---|---|---:|
| A | Farm-owner confirmation or correction | 365 days |
| B | Current state/extension/official producer profile | 180 days |
| C | Live farm-owned website/social page | 90-day link scan; 180-day content review |
| D | Current market roster or reputable secondary directory | 180 days |
| E | Search result or single older secondary listing | 90 days to verify |
| F | Conflicting, closed, unreachable, or older than threshold | Do not promote |

Fields are reviewed independently. An official profile can verify identity and city
without proving that every product or sales channel is current.

Required promotion fields:

- farm name and entity type;
- state and county/parish, or an explicit public-location exception;
- city/town or safe public service area;
- products or farm activity;
- at least one source URL, retrieval date, and source name;
- identity decision for possible duplicates;
- public/private classification for address and contact fields.

## Six-month scan

Run `03-app/site/.venv/bin/python 01-database/tools/quarterly_verify.py` every six
months. The script retains its historical filename, but the operating cadence is semiannual. The scanner:

1. revalidates the pinned workbook checksum, row count, required fields, states, and
   normalized-name duplicate groups;
2. checks canonical websites and staging source/contact URLs with up to three attempts;
3. treats 2xx/3xx as reachable and 401/403/405/429 as reachable-but-restricted;
4. flags 404/410 as broken and repeated timeout/DNS/TLS failures as
   `unreachable_after_3_attempts`;
5. compares URL status to the previous dated audit;
6. writes a dated JSON report plus CSV exception queues in
   `research/quarterly-audits/YYYY-MM-DD/`;
7. makes no automatic canonical changes.

After the scan, a curator reviews changed/broken URLs, conflicting fields, missing
counties, and identity candidates. Only a complete atomic release is promoted; the
previous release remains restorable.

## State completion gates

A state can be marked `coverage_reviewed` when:

- all three source passes are complete or explicitly failed after three attempts;
- every county has a documented status: candidates found, searched-none-found, source
  blocked, or follow-up required;
- candidate/source counts reconcile to proposed entities without silent merging;
- every proposed public row passes required fields and privacy classification;
- broken/conflicting evidence is resolved or carried as an explicit review item;
- the state release validator passes and the prior release is restorable.

“All farms” therefore means all qualifying farms found under the documented sources and
three-pass process as of the release date, not a claim that every farm in the state is
known.

## Privacy and change control

- Never publish a private exact farm/home location by default. Public coordinates use
  a farm-confirmed visitor location, a public business address, or reduced precision.
- Keep source contact information internal until public-use permission is clear.
- Farm-owner corrections outrank older third-party data.
- The six-month job creates an exception queue; it does not overwrite values, delete a
  farm after a single 404, or infer closure from absence in one directory.
