# ADR-0001: PostgreSQL platform and hybrid question answering

**Status:** Accepted for foundation implementation  
**Date:** 2026-07-15  
**Decider:** FarmFinder owner

## Context

FarmFinder currently builds a static 311-listing JSON artifact from a workbook. The next production case must support trustworthy geographic and product queries, source provenance, farm claims, background imports, authorization, and eventually narrative question answering across a national dataset.

The existing application is TypeScript. The workbook ingestion script is Python. The currently tracked Git repository contains only `03-app/site`; research and database files are adjacent workspace assets rather than versioned contents of that repository.

## Decision

1. Use a TypeScript modular monolith with separate `web`, `api`, and `worker` deployment units.
2. Use PostgreSQL as the canonical operational database after an explicit cutover, with PostGIS for geographic queries and `pg_trgm` for fuzzy names.
3. Keep Python for bounded ingestion and research tasks while API, query, auth, and job contracts remain TypeScript-owned.
4. Use structured, validated query tools for counts, filters, comparisons, and distance searches.
5. Use full-text retrieval first and add vector retrieval only after a useful narrative corpus and eval baseline exist.
6. Store original source files and future images in object storage; store their metadata, rights, checksums, and relationships in PostgreSQL.
7. Begin with one PostgreSQL-backed worker/job mechanism. Do not introduce Kafka, Kubernetes, a separate vector database, or microservices without measured need.
8. Govern the pre-cutover workbook with a machine-readable release manifest. After cutover, the workbook becomes an import/export artifact and PostgreSQL becomes the only mutable canonical store.

## Options considered

### TypeScript modular monolith

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Cost | Low initially |
| Scalability | High enough for national directory scale |
| Team/context fit | Strong; extends the existing application |

**Advantages:** one language for public contracts, authorization, query tools, and observability; easy refactoring; separate deployment where runtime behavior requires it.  
**Disadvantages:** Python data tooling still needs a maintained interface and dependency lock.

### FastAPI service plus TypeScript web

| Dimension | Assessment |
|---|---|
| Complexity | Medium-high |
| Cost | Low initially |
| Scalability | High enough |
| Team/context fit | Moderate |

**Advantages:** excellent fit for Python ingestion and data libraries.  
**Disadvantages:** duplicates contracts and operational conventions across languages before that complexity buys anything.

### Continue static JSON plus client-side question parsing

| Dimension | Assessment |
|---|---|
| Complexity | Low |
| Cost | Very low |
| Scalability | Poor for national data, claims, and private fields |
| Team/context fit | Strong only for the prototype |

**Advantages:** simple, fast, resilient prototype.  
**Disadvantages:** no authoritative write path, weak provenance, no authorization boundary, and eventually sends too much data to browsers.

## Consequences

- Database migrations and API contracts become reviewable production artifacts.
- Public browse/search can remain cached while mutations and complex queries use the API.
- Data ingestion becomes more explicit because source records and canonical entities are separate.
- National expansion is primarily a coverage and data-governance problem, not a database-sharding problem.
- PostgreSQL extensions and indexes must be supported by the chosen managed provider.
- Repository consolidation must be revisited before CI can validate the workbook and application from a clean clone.

## Revisit triggers

- Split services only when independent ownership, scaling, security, or deployment cadence is measured.
- Add vector indexing only when full-text retrieval fails documented eval cases.
- Add table partitioning only after query plans, vacuum behavior, or maintenance windows justify it.
- Add a separate queue only when PostgreSQL job contention or delivery requirements exceed the worker design.

## Action items

1. Establish and validate the canonical dataset release manifest.
2. Apply the initial PostgreSQL/PostGIS schema and index register.
3. Import the pinned workbook into staging and compare 315 source rows to 311 candidate entities.
4. Build read-only query tools and API contracts.
5. Add authentication and claims before accepting public writes.
6. Consolidate the project Git boundary or make the source dataset available to CI as a versioned artifact.
