BEGIN;

CREATE INDEX source_records_source_history_idx
    ON source_records (source_id, source_record_key, ingested_at DESC);
COMMENT ON INDEX source_records_source_history_idx IS
    'Find all observed versions of one upstream record; B-tree is selective by source and key.';

CREATE UNIQUE INDEX admin_areas_country_fips_unique_idx
    ON admin_areas (country_code, fips_code)
    WHERE fips_code IS NOT NULL;
COMMENT ON INDEX admin_areas_country_fips_unique_idx IS
    'Prevents two official areas from claiming the same country/FIPS identifier; custom areas may omit FIPS.';

CREATE INDEX admin_areas_parent_type_name_idx
    ON admin_areas (parent_id, area_type, name);
COMMENT ON INDEX admin_areas_parent_type_name_idx IS
    'Supports hierarchical state/county/parish/city browsing without indexing large geometry values.';

CREATE INDEX farms_published_updated_idx
    ON farms (updated_at DESC, id)
    WHERE status = 'published';
COMMENT ON INDEX farms_published_updated_idx IS
    'Supports the public directory and freshness feeds; partial index excludes drafts and archived entities.';

CREATE INDEX farms_normalized_name_trgm_idx
    ON farms USING gin (normalized_name gin_trgm_ops);
COMMENT ON INDEX farms_normalized_name_trgm_idx IS
    'Supports fuzzy farm-name search and identity review; carries GIN write/storage cost and must be checked with query statistics.';

CREATE INDEX farms_last_seen_release_idx
    ON farms (last_seen_release_id, status);
COMMENT ON INDEX farms_last_seen_release_idx IS
    'Reconciles one dataset release to canonical entities and finds farms missing from the latest release.';

CREATE UNIQUE INDEX farm_locations_one_primary_idx
    ON farm_locations (farm_id)
    WHERE is_primary;
COMMENT ON INDEX farm_locations_one_primary_idx IS
    'Enforces at most one canonical primary location per farm while allowing historical and alternate locations.';

CREATE INDEX farm_locations_public_point_gist_idx
    ON farm_locations USING gist (point)
    WHERE is_public AND point IS NOT NULL;
COMMENT ON INDEX farm_locations_public_point_gist_idx IS
    'Supports public radius, nearest-neighbor, and bounding-area queries without indexing private coordinates.';

CREATE INDEX farm_locations_public_area_farm_idx
    ON farm_locations (admin_area_id, farm_id)
    WHERE is_public;
COMMENT ON INDEX farm_locations_public_area_farm_idx IS
    'Supports exact county/parish/state filters and counts for public locations.';

CREATE INDEX farm_products_product_farm_idx
    ON farm_products (product_id, farm_id)
    WHERE availability_status IN ('available', 'seasonal', 'unknown');
COMMENT ON INDEX farm_products_product_farm_idx IS
    'Reverses the farm-first primary key for product discovery and counts; excludes explicitly unavailable products.';

CREATE INDEX farm_sales_channels_channel_farm_idx
    ON farm_sales_channels (sales_channel_id, farm_id);
COMMENT ON INDEX farm_sales_channels_channel_farm_idx IS
    'Supports filters and counts such as CSA, farmers market, on-farm, shipping, and online ordering.';

CREATE INDEX farm_links_active_type_farm_idx
    ON farm_links (link_type, farm_id)
    WHERE is_active;
COMMENT ON INDEX farm_links_active_type_farm_idx IS
    'Supports website/social/online-store coverage metrics; inactive historical links remain unindexed evidence.';

CREATE INDEX markets_public_point_gist_idx
    ON markets USING gist (point)
    WHERE point IS NOT NULL AND status IN ('active', 'seasonal');
COMMENT ON INDEX markets_public_point_gist_idx IS
    'Supports nearby-market queries while excluding closed and unknown markets from the hot spatial index.';

CREATE INDEX farm_markets_market_farm_idx
    ON farm_markets (market_id, farm_id);
COMMENT ON INDEX farm_markets_market_farm_idx IS
    'Reverses the farm-first primary key for market vendor lookups.';

CREATE UNIQUE INDEX farm_field_assertions_one_canonical_idx
    ON farm_field_assertions (farm_id, field_name)
    WHERE is_canonical;
COMMENT ON INDEX farm_field_assertions_one_canonical_idx IS
    'Enforces one selected canonical assertion per farm field while preserving all source evidence.';

CREATE INDEX farm_field_assertions_history_idx
    ON farm_field_assertions (farm_id, field_name, observed_at DESC, created_at DESC);
COMMENT ON INDEX farm_field_assertions_history_idx IS
    'Supports provenance timelines and canonical-value review.';

CREATE UNIQUE INDEX app_users_email_unique_idx
    ON app_users (lower(email))
    WHERE email IS NOT NULL AND status <> 'deleted';
COMMENT ON INDEX app_users_email_unique_idx IS
    'Prevents duplicate active accounts by case-insensitive email while allowing deleted-account tombstones.';

CREATE INDEX organization_memberships_user_active_idx
    ON organization_memberships (user_id, role, organization_id)
    WHERE status = 'active';
COMMENT ON INDEX organization_memberships_user_active_idx IS
    'Supports authorization checks from authenticated user to active organization roles.';

CREATE UNIQUE INDEX farm_claims_active_user_farm_idx
    ON farm_claims (farm_id, user_id)
    WHERE status IN ('pending', 'approved');
COMMENT ON INDEX farm_claims_active_user_farm_idx IS
    'Prevents duplicate active claims by the same user while retaining rejected and revoked history.';

CREATE INDEX farm_claims_review_queue_idx
    ON farm_claims (created_at, farm_id)
    WHERE status = 'pending';
COMMENT ON INDEX farm_claims_review_queue_idx IS
    'Supports the curator claim-review queue; small partial index excludes completed history.';

CREATE INDEX documents_public_farm_idx
    ON documents (farm_id, published_at DESC, id)
    WHERE visibility = 'public';
COMMENT ON INDEX documents_public_farm_idx IS
    'Fetches public narrative evidence for one farm without scanning private or curator material.';

CREATE INDEX document_chunks_search_vector_idx
    ON document_chunks USING gin (search_vector);
COMMENT ON INDEX document_chunks_search_vector_idx IS
    'Supports PostgreSQL full-text narrative retrieval; vector indexing is intentionally deferred pending eval evidence.';

CREATE INDEX media_assets_ready_farm_idx
    ON media_assets (farm_id, created_at DESC)
    WHERE status = 'ready' AND visibility = 'public';
COMMENT ON INDEX media_assets_ready_farm_idx IS
    'Fetches displayable public media for farm profiles without indexing pending, private, or quarantined objects.';

CREATE UNIQUE INDEX app_jobs_idempotency_idx
    ON app_jobs (queue_name, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
COMMENT ON INDEX app_jobs_idempotency_idx IS
    'Prevents duplicate logical jobs in one queue; callers must reuse the key when retrying the same work.';

CREATE INDEX app_jobs_ready_idx
    ON app_jobs (run_after, created_at, id)
    WHERE status = 'queued';
COMMENT ON INDEX app_jobs_ready_idx IS
    'Supports FOR UPDATE SKIP LOCKED job claims ordered by readiness; excludes completed and running jobs.';

CREATE INDEX outbox_events_pending_idx
    ON outbox_events (available_at, created_at, id)
    WHERE status IN ('pending', 'failed');
COMMENT ON INDEX outbox_events_pending_idx IS
    'Supports reliable event publication and retry without scanning published history.';

CREATE INDEX audit_events_entity_timeline_idx
    ON audit_events (entity_type, entity_id, created_at DESC);
COMMENT ON INDEX audit_events_entity_timeline_idx IS
    'Supports an append-only change timeline for one entity; audit payload JSON remains deliberately unindexed.';

COMMIT;
