# Production implementation ledger

This ledger records each production capability, its implementation decision, current state, and acceptance gate. Update it in the same change that alters an architectural decision.

| Capability | Decision | State on 2026-07-15 | Acceptance gate |
|---|---|---|---|
| Service boundary | TypeScript modular monolith; web, API, worker deployables | Boundary documented | Versioned API with health/readiness and OpenAPI contract |
| Authentication | Managed OIDC identity; public reads anonymous | Planned | Verified sessions, logout, account deletion path |
| Authorization | Consumer, farm owner, curator, admin; farm-scoped claims | Schema foundation | Deny-by-default integration tests for every protected endpoint |
| PostgreSQL | Canonical after explicit dataset cutover | 30-table foundation runtime-verified | Pinned release imported and reconciled without silent data loss |
| PostGIS | Geography points and official administrative areas | Extension and radius test passing | Production-shaped radius and bounding-box plans use GiST index |
| Migrations | Ordered SQL initially; one forward-only history | Clean local database applies all three migrations | Production runner records and locks each migration |
| Background processing | One worker with idempotency, timeout, backoff, and terminal failure state | Job schema foundation | Crash/retry integration tests and duplicate-side-effect test |
| Structured questions | Allowlisted parameterized tools; no raw model SQL | Tool boundary documented | Golden counts/IDs pass against pinned release |
| Narrative retrieval | PostgreSQL full-text first; vectors deferred | Full-text schema foundation | Retrieval eval demonstrates need before vector index is added |
| Evals | Routing, arguments, data truth, citations, safety, latency/cost | Seed cases added | Deterministic PR gate and controlled live-model suite |
| Tracing | OpenTelemetry-compatible trace through HTTP, tool, DB, model | Planned | Trace ID plus p50/p95 latency, tokens, and cost per request |
| Prompt injection | Retrieved content is untrusted data and cannot authorize tools | Policy documented | Adversarial eval suite passes |
| PII | Public/private contact separation and non-public exact locations | Schema foundation | Public-role snapshot contains no private values |
| Tests | Unit, integration with PostGIS, API contract, migration, policy | Build/smoke and DB foundation tests passing | API, policy, importer, and eval checks block release |
| CI/CD | Build, tests, migration check, evals, staging smoke, promotion | Planned; repo boundary noted | Clean clone can reproduce every required input |
| Infrastructure | Local Compose now; managed Postgres/object store/telemetry/IaC later | Local PostGIS bootstrap and verification passing | Backup restore and staging deployment tested |
| Real users | Five pilot farms plus consumer cohort | Product action | Baseline and target metrics recorded before pilot |
| Outcomes | Correct-answer rate, search-to-contact, claims, corrections, freshness, latency, cost | Defined, not instrumented | Dashboard and case-study export |
| Architecture/case study | ADRs, diagrams, index decisions, failures, revisions | Foundation documented | Published after pilot with measured evidence |
| Object storage | Source releases and future images; metadata in PostgreSQL | Contract documented | Checksum, rights, variants, retention, signed access tested |
| National coverage | Official admin areas plus operational coverage regions | Schema foundation | Coverage completeness and freshness measured per region |

## Repository boundary decision still open

Only this site directory is currently tracked by Git. The canonical workbook, outreach, and research folders live two levels above it. No CI/CD claim is complete until one of these is chosen:

1. Promote the FarmFinder workspace root to the repository root.
2. Move/version governed data inputs inside this repository.
3. Publish each immutable dataset release to object storage and have CI verify its checksum.

The foundation validator works in the current workspace, but a clean clone of the site repository alone cannot access the workbook yet.
