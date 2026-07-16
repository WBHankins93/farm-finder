# Source-of-truth and coverage workflow

## Authority modes

### Before PostgreSQL cutover

The workbook identified by `config/source-of-truth.json` is the only editable authoring source. The manifest pins its sheet, checksum, row count, candidate-entity count, required columns, allowed states, and known duplicate groups. The generated JSON is a build artifact, not another source of truth.

Cutover staging began on 2026-07-15 with historical release `2026-07-13-final-v1`: its 315 raw rows are stored as a versioned object and registered in local PostgreSQL. The current manifest now pins enriched release `2026-07-15-enriched-v2`, containing 299 canonical workbook rows after evidence-based duplicate review. V2 must be staged as a new immutable object; it must not overwrite v1. Staging does not change authority. The workbook remains authoritative until reviewed canonical entities are promoted atomically and the manifest authority mode changes.

### After PostgreSQL cutover

Promoted canonical tables are the only mutable source of truth. Workbooks, directory downloads, API responses, and farm submissions are immutable source releases stored in object storage and represented by `dataset_releases`, `import_batches`, and `source_records`.

No spreadsheet may be edited and reintroduced as an authoritative replacement after cutover. Changes arrive as new source records or curator actions with audit evidence.

## Digital-presence facts and visibility

FarmFinder retains governed, source-backed website, social, online-store, map, market, product, contact, and verification information because those facts directly support farm discovery and directory quality.

- Every fact retains its provenance, confidence, verification, consent, and public/private visibility rules.
- Private contacts and non-public locations never become public fields and are never returned through public APIs, exports, logs, analytics, or model prompts.
- A correction enters FarmFinder only as a sourced assertion or curator action with appropriate consent and visibility.
- FarmFinder stores only product and operational data required for the directory, farm participation, governance, and platform reliability.

## Adding a new farm

1. Register the source, license/terms, retrieval date, and immutable file checksum.
2. Create an import batch with a unique idempotency key.
3. Store the raw row in `source_records` before normalization.
4. Normalize names, products, links, contacts, and geography without discarding original text.
5. Compare candidates using name, administrative area, address, contact, links, and source identifiers.
6. Automatically accept only high-confidence matches. Send ambiguous and same-name cases to curator review.
7. Preserve each source value in `farm_field_assertions`; select canonical values according to verification recency and curator policy.
8. Validate required public fields, visibility, provenance, and geographic precision.
9. Promote the dataset release atomically. Failed or partial imports never become visible.
10. Record the affected farm IDs, source records, actor, and release in the audit log.

## Adding a new area

1. Add official geography to `admin_areas` using stable FIPS/GNIS identifiers where available.
2. Keep official geography separate from operational collection areas.
3. Create a `coverage_region` for a foodshed, metro, agricultural district, or county cluster.
4. Map the coverage region to one or more official administrative areas.
5. Register the sources expected for that region and define a coverage target.
6. Report discovered farms, verified contacts, precise locations, source freshness, and unresolved duplicates for that region.

States remain the top-level official namespace. Collection can proceed in smaller regions without making those regions substitutes for states, counties, or Louisiana parishes.

Active Mississippi collection remains a separate working set during cutover. When a collection milestone is ready, freeze it as a new immutable release with a new ID and checksum; never overwrite the currently validated release. See the [cutover runbook](cutover-runbook.md).

## Canonical-value policy

- A verified farm-owner correction outranks older third-party directory data unless legal or safety review blocks it.
- More recent observations do not erase older observations; they supersede them with evidence.
- A boolean is not true merely because any historical source said yes. The canonical value uses status, recency, confidence, and verification.
- Absence from one source is not proof that a product, market channel, or website does not exist.
- Exact locations and private contacts are independently classified; canonical does not automatically mean public.
- Derived fields such as `has_website` are computed from active canonical links rather than maintained separately.

## Release gates

- Manifest checksum and workbook structure match.
- Required values are present and allowed values are valid.
- Duplicate groups are reviewed or explicitly carried as unresolved.
- Source licensing/terms and retrieval dates are recorded.
- Counts reconcile from source rows to candidate entities to promoted entities.
- Query evals are pinned to the release being promoted.
- The previous release remains restorable.
