\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
        RAISE EXCEPTION 'postgis extension is missing';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
        RAISE EXCEPTION 'pg_trgm extension is missing';
    END IF;
    IF to_regclass('public.farms') IS NULL THEN
        RAISE EXCEPTION 'farms table is missing';
    END IF;
    IF to_regclass('public.source_records') IS NULL THEN
        RAISE EXCEPTION 'source_records table is missing';
    END IF;
    IF to_regclass('public.farm_locations_public_point_gist_idx') IS NULL THEN
        RAISE EXCEPTION 'public spatial index is missing';
    END IF;
    IF to_regclass('public.app_jobs_ready_idx') IS NULL THEN
        RAISE EXCEPTION 'ready-job index is missing';
    END IF;
END
$$;

SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('postgis', 'pg_trgm')
ORDER BY extname;

SELECT count(*) AS farmfinder_table_count
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename NOT IN ('spatial_ref_sys');

SELECT count(*) AS documented_custom_index_count
FROM pg_class AS index_class
JOIN pg_namespace AS namespace
  ON namespace.oid = index_class.relnamespace
WHERE namespace.nspname = 'public'
  AND index_class.relkind = 'i'
  AND obj_description(index_class.oid, 'pg_class') IS NOT NULL;
