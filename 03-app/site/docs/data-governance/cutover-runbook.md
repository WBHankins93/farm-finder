# PostgreSQL cutover runbook

## Current cutover state

Cutover began on 2026-07-15. Historical release `2026-07-13-final-v1` completed the first reversible stage:

- The governed workbook passed its checksum, structure, row-count, state, and duplicate-group checks.
- Its exact bytes were uploaded to a private, versioned S3-compatible object.
- `dataset_releases` records the object URI, SHA-256 checksum, release manifest, and expected counts.
- One idempotent import batch stored all 315 workbook rows in `source_records`.
- Verification downloaded the recorded object version, re-hashed it, and reconciled all 315 rows.
- The release is `validated`, not `promoted`. The workbook remains the authoring authority and the public app still reads generated JSON.

The current workbook/manifest is now release `2026-07-15-enriched-v2`: 299 canonical rows after evidence review of the four former duplicate groups. V2 has not yet replaced or overwritten v1 in staging. Promotion remains blocked until v2 is staged, its fields and provenance are normalized into canonical relational tables, privacy rules are reviewed, and public-artifact equivalence passes.

## Local execution

From `03-app/site/`:

```bash
npm run data:setup
npm run cutover:local
```

`cutover:local` starts PostgreSQL/PostGIS and a loopback-only S3-compatible object store, validates the manifest, runs importer unit tests, stages the release, and independently verifies the database and stored object.

Individual commands are:

```bash
npm run infra:up
npm run data:validate
npm run cutover:test
npm run cutover:stage
npm run cutover:verify
```

The staging command is idempotent. Repeating it with the same release ID and checksum reuses the object version and successful import batch. It refuses to overwrite the same release object key or database release key with different bytes.

## Storage boundary

| Layer | Authority and contents |
|---|---|
| Git | Code, migrations, release manifest/checksum, tests, and small sanitized fixtures; the current workbook remains only for the reversible pre-promotion transition |
| Object storage | Immutable source releases and later media; private, versioned, checksum-addressed, and independently restorable |
| PostgreSQL staging | Release metadata, import attempts, and immutable raw source records |
| PostgreSQL canonical | Reviewed farms, geography, products, channels, links, contacts, assertions, and provenance after atomic promotion |
| Local working files | Temporary collection and review artifacts; never the only durable copy |

Local MinIO proves the S3-compatible contract but is not the production backup. Before promotion, provision a managed private bucket with versioning and migrate the recorded object to it. Production PostgreSQL must also have automated backups and point-in-time recovery.

## Mississippi collection while cutover proceeds

Do not edit release `2026-07-13-final-v1` or its stored object. The v2 workbook and ongoing Mississippi research are new release inputs.

1. Continue recording collection candidates and pass logs in the canonical workbook's `Research Queue` and `Source Log`; raw collection artifacts under `research/ms-expansion/` remain reproducible evidence, not a second database authority.
2. Treat staged candidates as working evidence, not automatic canonical updates.
3. When a Mississippi collection milestone is ready, freeze its inputs and assign a new release ID.
4. Produce a new immutable source file and manifest with its own checksum, counts, states, source inventory, and duplicate groups.
5. Upload and stage it as a new release. Never overwrite the validated v1 object.
6. Reconcile the new source records to stable farm identities; do not merge by name alone.
7. Promote only after privacy, provenance, licensing, coverage, identity, and public-artifact equivalence gates pass.

This lets collection continue without changing the release currently being reconciled.

## Index decisions for the staging path

No new index was added for this slice:

- `dataset_releases` already has unique B-tree indexes for `(dataset_code, release_key)` and `(dataset_code, source_sha256)`, which enforce immutable release identity.
- `import_batches.idempotency_key` already has a unique B-tree index, which makes replay lookup and duplicate prevention exact.
- `source_records(import_batch_id, source_record_key)` already has a unique B-tree index. Its leftmost `import_batch_id` supports the verification count and ordered batch lookup.
- `source_records_source_history_idx` supports future comparisons of the same source record key across releases.
- `raw_data` deliberately has no GIN index. Raw JSON is retained evidence; production search must use normalized relational columns.

Revisit indexes only after normalization queries and `EXPLAIN (ANALYZE, BUFFERS)` expose a missing access path.

## Remaining promotion gates

1. Preserve the completed evidence-based decisions for Butterfield Farm, Earth Friendly Farms, Faust Farms, and River Queen Greens when importing v2; do not recreate name-only merges.
2. Normalize official geography, products, sales channels, links, contacts, verification sources, identity notes, and location visibility.
3. Preserve field-level assertions linking every selected value to its source record.
4. Compare database-derived public output with the current 299-listing artifact.
5. Run public/private projection tests and structured query evals.
6. Copy the source release to managed versioned object storage and prove restoration.
7. Back up managed PostgreSQL and prove restoration into staging.
8. Promote atomically, change the authority mode, and switch the application to the versioned API.

Until all gates pass, `npm run db:reset` may recreate local PostgreSQL without changing production authority. It intentionally preserves the local object-storage volume. Never use a local reset command against shared or managed infrastructure.
