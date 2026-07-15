\set ON_ERROR_STOP on

BEGIN;

INSERT INTO farms (slug, name, normalized_name, status)
VALUES ('integration-test-farm', 'Integration Test Farm', 'integration test farm', 'published')
RETURNING id AS farm_id \gset

SELECT set_config('farmfinder.test_farm_id', :'farm_id', true);

INSERT INTO farm_locations (
    farm_id,
    locality,
    point,
    precision,
    is_primary,
    is_public
)
VALUES (
    :'farm_id',
    'Testville',
    ST_SetSRID(ST_MakePoint(-90.0, 30.0), 4326)::geography,
    'city',
    true,
    true
);

DO $$
BEGIN
    BEGIN
        INSERT INTO farm_locations (farm_id, locality, precision, is_primary)
        VALUES (
            current_setting('farmfinder.test_farm_id')::uuid,
            'Second Primary',
            'city',
            true
        );
        RAISE EXCEPTION 'expected duplicate primary location to be rejected';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END
$$;

INSERT INTO farm_field_assertions (
    farm_id,
    field_name,
    value,
    verification_status,
    is_canonical
)
VALUES (:'farm_id', 'name', '"Integration Test Farm"'::jsonb, 'verified', true);

DO $$
BEGIN
    BEGIN
        INSERT INTO farm_field_assertions (
            farm_id,
            field_name,
            value,
            verification_status,
            is_canonical
        )
        VALUES (
            current_setting('farmfinder.test_farm_id')::uuid,
            'name',
            '"Conflicting Name"'::jsonb,
            'observed',
            true
        );
        RAISE EXCEPTION 'expected duplicate canonical assertion to be rejected';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END
$$;

INSERT INTO app_jobs (queue_name, job_type, idempotency_key, payload)
VALUES ('imports', 'import_workbook', 'integration-release-1', '{}'::jsonb);

DO $$
BEGIN
    BEGIN
        INSERT INTO app_jobs (queue_name, job_type, idempotency_key, payload)
        VALUES ('imports', 'import_workbook', 'integration-release-1', '{}'::jsonb);
        RAISE EXCEPTION 'expected duplicate job idempotency key to be rejected';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END
$$;

DO $$
DECLARE
    nearby_count integer;
BEGIN
    SELECT count(*)
      INTO nearby_count
      FROM farm_locations
     WHERE is_public
       AND point IS NOT NULL
       AND ST_DWithin(
           point,
           ST_SetSRID(ST_MakePoint(-90.0, 30.0), 4326)::geography,
           1000
       );
    IF nearby_count <> 1 THEN
        RAISE EXCEPTION 'expected one nearby public farm, got %', nearby_count;
    END IF;
END
$$;

ROLLBACK;
