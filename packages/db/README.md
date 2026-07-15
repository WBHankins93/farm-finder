# Database package

This package owns the PostgreSQL/PostGIS schema and forward-only migrations. It does not own API authorization or model prompts.

## Migration order

1. `0001_extensions.sql`: PostGIS and trigram support.
2. `0002_core_schema.sql`: releases, provenance, geography, farms, taxonomy, markets, identity, retrieval, media metadata, jobs, outbox, and audit.
3. `0003_indexes.sql`: only indexes tied to a documented query, invariant, or worker operation.

The local Compose database applies these files only when its volume is first created. `npm run db:reset` deletes that local volume and all local data. Production will use a migration runner that records each applied migration and never relies on container initialization hooks.

`npm run db:verify` checks extensions, core tables, and documented indexes. `npm run db:test` exercises database invariants and a PostGIS radius query inside a transaction that is always rolled back.

## Schema principles

- Source rows are immutable; canonical farm values can change without erasing their evidence.
- Official administrative areas and operational coverage regions are different concepts.
- Products, sales channels, and markets are relationships, not delimited strings.
- `has_website` is derived from active website links rather than stored independently.
- Exact locations and contacts carry independent visibility classifications.
- Object bytes do not live in PostgreSQL. `media_assets` stores object keys, checksums, dimensions, rights, and visibility.
- JSONB is used for raw evidence and bounded metadata, not as a substitute for searchable relational columns.
- Vector columns and indexes are deferred until narrative evals demonstrate a full-text retrieval gap.

See the [index decision register](../../docs/architecture/index-register.md) before adding, changing, or removing an index.
