# PostgreSQL index decision register

Every non-constraint index must have a query or invariant, a known cost, and a validation plan. Primary keys and `UNIQUE` constraints create implicit B-tree indexes and are not duplicated here.

| Index | Query or invariant | Why this shape | Cost/risk | Production validation |
|---|---|---|---|---|
| `source_records_source_history_idx` | Show versions of one upstream record | Source/key equality then newest first | Additional write per import | Confirm importer/review query uses it |
| `admin_areas_country_fips_unique_idx` | Official identifier uniqueness | Partial unique permits custom areas with no FIPS | Small maintenance cost | Reject duplicate fixture; monitor conflicts |
| `admin_areas_parent_type_name_idx` | Browse children of state/county/parish | Matches hierarchy filters and name order | Low | `EXPLAIN` state and parish browse |
| `farms_published_updated_idx` | Public directory/freshness feed | Partial index excludes non-public statuses | Updates touch index | p95 directory query; scan ratio |
| `farms_normalized_name_trgm_idx` | Typo-tolerant name search and dedupe candidates | GIN trigram supports similarity/`ILIKE` patterns | High relative write/storage cost | Keep only if fuzzy eval and `pg_stat_user_indexes` show use |
| `farms_last_seen_release_idx` | Reconcile promoted dataset release | Release equality followed by status | Low | Import reconciliation plan |
| `farm_locations_one_primary_idx` | At most one primary location per farm | Partial unique expresses invariant directly | Primary-location switches require transaction | Constraint test |
| `farm_locations_public_point_gist_idx` | Radius, nearest, map bounds | GiST on geography; excludes private/null points | Spatial index is larger and slower to update | `EXPLAIN ANALYZE` radius/bbox; ensure private rows absent |
| `farm_locations_public_area_farm_idx` | County/parish/state filters and counts | Area first, farm second | Duplicate with some join paths | Compare area count query plans |
| `farm_products_product_farm_idx` | Farms/count by product | Reverses farm-first PK; excludes known unavailable | Availability updates touch index | Product filter/count evals |
| `farm_sales_channels_channel_farm_idx` | Filter/count by CSA, market, shipping, etc. | Reverses farm-first PK | Low | Channel filter plans |
| `farm_links_active_type_farm_idx` | Website/social/store coverage metrics | Type first and only active links | Link verification updates touch index | Coverage report plan |
| `markets_public_point_gist_idx` | Nearby active/seasonal markets | Partial spatial index | Spatial maintenance | Nearby-market plan |
| `farm_markets_market_farm_idx` | List market vendors | Reverses farm-first PK | Low | Market detail query plan |
| `farm_field_assertions_one_canonical_idx` | One canonical value per farm field | Partial unique preserves noncanonical evidence | Canonical switch requires transaction | Concurrency test |
| `farm_field_assertions_history_idx` | Field provenance timeline | Farm/field equality then newest | Evidence imports append to it | Review-screen plan |
| `app_users_email_unique_idx` | Active case-insensitive email uniqueness | Expression + partial tombstone policy | Email updates and policy coupling | Duplicate-account test |
| `organization_memberships_user_active_idx` | Authorization lookup from user | Matches user/role/org checks, active only | Role changes touch index | Authorization query plan |
| `farm_claims_active_user_farm_idx` | Prevent duplicate active claim | Partial unique preserves history | Status transition must be transactional | Concurrent claim test |
| `farm_claims_review_queue_idx` | Oldest pending claims | Small partial queue index | Low | Curator queue plan |
| `documents_public_farm_idx` | Public documents for farm | Excludes private evidence | Visibility changes touch index | Farm profile query plan |
| `document_chunks_search_vector_idx` | Narrative full-text retrieval | GIN on stored `tsvector` | Chunk ingestion/storage cost | Retrieval eval, latency, index hit rate |
| `media_assets_ready_farm_idx` | Public profile media | Excludes pending/private/quarantined assets | Status transitions touch index | Profile media plan |
| `app_jobs_idempotency_idx` | One logical job per queue/key | Partial unique permits jobs without a key | Keys require stable caller semantics | Retry/duplicate-side-effect test |
| `app_jobs_ready_idx` | Claim runnable jobs | Partial ordered queue supports `SKIP LOCKED` | Hot index under high job churn | Worker contention and queue-lag metrics |
| `outbox_events_pending_idx` | Publish/retry events | Partial queue excludes published history | Hot index under event churn | Outbox lag and retry plan |
| `audit_events_entity_timeline_idx` | Entity change history | Entity equality, newest first | Append-only storage growth | Audit lookup plan and retention review |

## Deliberate omissions

- No general GIN indexes on `raw_data`, job payloads, evidence, or audit JSONB. Those values are retained for provenance, not unrestricted production search.
- No vector index yet. Add one only with a retrieval eval, corpus size, chosen distance metric, expected recall, memory estimate, and measured full-text shortfall.
- No state partitions. Add partitioning only after query plans, vacuum behavior, backup/restore, or retention operations show a real need.
- No standalone indexes whose leftmost columns duplicate an existing primary key or unique constraint.

## Review procedure

Before release, run representative `EXPLAIN (ANALYZE, BUFFERS)` queries on production-shaped data. After release, review `pg_stat_user_indexes`, slow query traces, table/index size, write rate, and vacuum behavior. An unused index is a removal candidate only after accounting for infrequent administrative and integrity queries.

Large-table index changes must use a deployment-safe procedure such as `CREATE INDEX CONCURRENTLY` outside a transaction. The initial migration uses ordinary index creation because the tables are empty.
