BEGIN;

CREATE TABLE dataset_releases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_code text NOT NULL,
    release_key text NOT NULL,
    source_uri text NOT NULL,
    source_sha256 character(64) NOT NULL,
    source_row_count integer NOT NULL CHECK (source_row_count >= 0),
    candidate_entity_count integer CHECK (candidate_entity_count >= 0),
    status text NOT NULL DEFAULT 'staged'
        CHECK (status IN ('staged', 'validated', 'promoted', 'rejected', 'superseded')),
    manifest jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    validated_at timestamptz,
    promoted_at timestamptz,
    UNIQUE (dataset_code, release_key),
    UNIQUE (dataset_code, source_sha256),
    CHECK (source_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE TABLE data_sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE,
    name text NOT NULL,
    source_type text NOT NULL
        CHECK (source_type IN ('farm', 'directory', 'market', 'government', 'farm_submission', 'curator', 'other')),
    homepage_url text,
    license_name text,
    license_url text,
    terms_notes text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE import_batches (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_release_id uuid REFERENCES dataset_releases(id),
    source_id uuid NOT NULL REFERENCES data_sources(id),
    idempotency_key text NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    started_at timestamptz,
    completed_at timestamptz,
    source_record_count integer CHECK (source_record_count >= 0),
    error_summary text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE source_records (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    import_batch_id uuid NOT NULL REFERENCES import_batches(id) ON DELETE RESTRICT,
    source_id uuid NOT NULL REFERENCES data_sources(id),
    source_record_key text NOT NULL,
    record_hash character(64) NOT NULL,
    raw_data jsonb NOT NULL,
    observed_at timestamptz,
    ingested_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (import_batch_id, source_record_key),
    CHECK (record_hash ~ '^[0-9a-f]{64}$')
);

CREATE TABLE admin_areas (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id uuid REFERENCES admin_areas(id),
    country_code character(2) NOT NULL DEFAULT 'US',
    subdivision_code character(2),
    fips_code text,
    gnis_id text,
    area_type text NOT NULL
        CHECK (area_type IN ('country', 'state', 'county', 'parish', 'municipality', 'census_place', 'other')),
    name text NOT NULL,
    slug text NOT NULL UNIQUE,
    boundary geometry(MultiPolygon, 4326),
    centroid geography(Point, 4326),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE coverage_regions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE,
    name text NOT NULL,
    region_type text NOT NULL
        CHECK (region_type IN ('foodshed', 'metro', 'agricultural_district', 'county_cluster', 'custom')),
    description text,
    status text NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'collecting', 'active', 'paused', 'complete')),
    target_source_count integer CHECK (target_source_count >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE coverage_region_admin_areas (
    coverage_region_id uuid NOT NULL REFERENCES coverage_regions(id) ON DELETE CASCADE,
    admin_area_id uuid NOT NULL REFERENCES admin_areas(id) ON DELETE RESTRICT,
    PRIMARY KEY (coverage_region_id, admin_area_id)
);

CREATE TABLE farms (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE,
    name text NOT NULL,
    normalized_name text NOT NULL CHECK (normalized_name <> ''),
    legal_name text,
    description text,
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'hidden', 'closed', 'duplicate', 'archived')),
    first_seen_release_id uuid REFERENCES dataset_releases(id),
    last_seen_release_id uuid REFERENCES dataset_releases(id),
    created_by_source_record_id uuid REFERENCES source_records(id),
    last_verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE farm_locations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id uuid NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    admin_area_id uuid REFERENCES admin_areas(id),
    source_record_id uuid REFERENCES source_records(id),
    address_line_1 text,
    address_line_2 text,
    locality text,
    postal_code text,
    point geography(Point, 4326),
    precision text NOT NULL DEFAULT 'unknown'
        CHECK (precision IN ('exact', 'street', 'postal_code', 'city', 'parish', 'county', 'metro', 'region', 'approximate', 'unknown')),
    is_primary boolean NOT NULL DEFAULT false,
    is_public boolean NOT NULL DEFAULT true,
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id uuid REFERENCES products(id),
    slug text NOT NULL UNIQUE,
    name text NOT NULL,
    normalized_name text NOT NULL UNIQUE,
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE product_aliases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    alias text NOT NULL,
    normalized_alias text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (normalized_alias, product_id)
);

CREATE TABLE farm_products (
    farm_id uuid NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    product_id uuid NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    source_record_id uuid REFERENCES source_records(id),
    original_label text,
    availability_status text NOT NULL DEFAULT 'unknown'
        CHECK (availability_status IN ('available', 'seasonal', 'planned', 'unavailable', 'unknown')),
    seasonality text,
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (farm_id, product_id)
);

CREATE TABLE sales_channels (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE,
    name text NOT NULL,
    description text
);

CREATE TABLE farm_sales_channels (
    farm_id uuid NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    sales_channel_id uuid NOT NULL REFERENCES sales_channels(id) ON DELETE RESTRICT,
    source_record_id uuid REFERENCES source_records(id),
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (farm_id, sales_channel_id)
);

CREATE TABLE farm_links (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id uuid NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    source_record_id uuid REFERENCES source_records(id),
    link_type text NOT NULL
        CHECK (link_type IN ('website', 'online_store', 'facebook', 'instagram', 'maps', 'other')),
    url text NOT NULL,
    is_primary boolean NOT NULL DEFAULT false,
    is_active boolean NOT NULL DEFAULT true,
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (farm_id, link_type, url)
);

CREATE TABLE farm_contacts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id uuid NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    source_record_id uuid REFERENCES source_records(id),
    contact_type text NOT NULL
        CHECK (contact_type IN ('email', 'phone', 'person', 'mailing_address', 'other')),
    label text,
    value text NOT NULL,
    normalized_value text,
    visibility text NOT NULL DEFAULT 'private'
        CHECK (visibility IN ('public', 'claimed_farm', 'curator', 'private')),
    consent_recorded_at timestamptz,
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE markets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE,
    name text NOT NULL,
    admin_area_id uuid REFERENCES admin_areas(id),
    source_record_id uuid REFERENCES source_records(id),
    schedule_text text,
    website_url text,
    point geography(Point, 4326),
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'seasonal', 'paused', 'closed', 'unknown')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE farm_markets (
    farm_id uuid NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    market_id uuid NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    source_record_id uuid REFERENCES source_records(id),
    schedule_notes text,
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (farm_id, market_id)
);

CREATE TABLE farm_field_assertions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id uuid NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    source_record_id uuid REFERENCES source_records(id),
    field_name text NOT NULL,
    value jsonb NOT NULL,
    verification_status text NOT NULL DEFAULT 'observed'
        CHECK (verification_status IN ('observed', 'verified', 'disputed', 'rejected', 'superseded')),
    confidence numeric(4, 3) CHECK (confidence >= 0 AND confidence <= 1),
    is_canonical boolean NOT NULL DEFAULT false,
    observed_at timestamptz,
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app_users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_provider text NOT NULL,
    external_subject text NOT NULL,
    email text,
    display_name text,
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'deleted')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (identity_provider, external_subject)
);

CREATE TABLE organizations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    organization_type text NOT NULL
        CHECK (organization_type IN ('farm', 'market', 'partner', 'internal')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE organization_memberships (
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    role text NOT NULL
        CHECK (role IN ('member', 'farm_owner', 'manager', 'curator', 'admin')),
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('invited', 'active', 'suspended', 'revoked')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, user_id)
);

CREATE TABLE farm_claims (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id uuid NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    organization_id uuid REFERENCES organizations(id) ON DELETE SET NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'revoked')),
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    reviewed_by_user_id uuid REFERENCES app_users(id),
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE saved_farms (
    user_id uuid NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    farm_id uuid NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, farm_id)
);

CREATE TABLE documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id uuid REFERENCES farms(id) ON DELETE CASCADE,
    source_record_id uuid REFERENCES source_records(id),
    title text NOT NULL,
    source_url text,
    document_type text NOT NULL
        CHECK (document_type IN ('farm_description', 'note', 'interview', 'directory_entry', 'policy', 'other')),
    visibility text NOT NULL DEFAULT 'public'
        CHECK (visibility IN ('public', 'claimed_farm', 'curator', 'private')),
    content_checksum character(64) NOT NULL,
    published_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (content_checksum ~ '^[0-9a-f]{64}$')
);

CREATE TABLE document_chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index integer NOT NULL CHECK (chunk_index >= 0),
    content text NOT NULL,
    token_count integer CHECK (token_count >= 0),
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', coalesce(content, ''))
    ) STORED,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE media_assets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id uuid REFERENCES farms(id) ON DELETE CASCADE,
    document_id uuid REFERENCES documents(id) ON DELETE CASCADE,
    storage_provider text NOT NULL,
    bucket text NOT NULL,
    object_key text NOT NULL,
    content_type text NOT NULL,
    content_length bigint CHECK (content_length >= 0),
    content_sha256 character(64) NOT NULL,
    width integer CHECK (width > 0),
    height integer CHECK (height > 0),
    alt_text text,
    rights_holder text,
    license_code text,
    visibility text NOT NULL DEFAULT 'public'
        CHECK (visibility IN ('public', 'claimed_farm', 'curator', 'private')),
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'ready', 'quarantined', 'deleted')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (storage_provider, bucket, object_key),
    CHECK (content_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE TABLE app_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_name text NOT NULL,
    job_type text NOT NULL,
    idempotency_key text,
    payload jsonb NOT NULL,
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'dead_letter', 'cancelled')),
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts integer NOT NULL DEFAULT 5 CHECK (max_attempts > 0),
    timeout_seconds integer NOT NULL DEFAULT 60 CHECK (timeout_seconds > 0),
    run_after timestamptz NOT NULL DEFAULT now(),
    locked_at timestamptz,
    locked_by text,
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    completed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE outbox_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type text NOT NULL,
    aggregate_id uuid NOT NULL,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'published', 'failed')),
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_user_id uuid REFERENCES app_users(id),
    trace_id text,
    event_type text NOT NULL,
    entity_type text NOT NULL,
    entity_id uuid,
    before_value jsonb,
    after_value jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
