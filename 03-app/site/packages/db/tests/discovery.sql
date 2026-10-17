\set ON_ERROR_STOP on

BEGIN;

INSERT INTO farms (slug, name, normalized_name, status)
VALUES ('discovery-alpha', 'Alpha Discovery Farm', 'alpha discovery farm', 'published')
RETURNING id AS farm_id \gset alpha_

SELECT set_config('farmfinder.discovery_alpha_id', :'alpha_farm_id', true);

INSERT INTO farms (slug, name, normalized_name, status)
VALUES ('discovery-beta', 'Beta Discovery Farm', 'beta discovery farm', 'published')
RETURNING id AS farm_id \gset beta_

INSERT INTO farms (slug, name, normalized_name, status)
VALUES ('discovery-private', 'Private Location Farm', 'private location farm', 'published')
RETURNING id AS farm_id \gset private_

INSERT INTO farms (slug, name, normalized_name, status)
VALUES ('discovery-hidden', 'Hidden Discovery Farm', 'hidden discovery farm', 'hidden')
RETURNING id AS farm_id \gset hidden_

INSERT INTO farm_locations (farm_id, locality, point, precision, is_primary, is_public)
VALUES
  (:'alpha_farm_id', 'Test City', ST_SetSRID(ST_MakePoint(-100.0, 40.0), 4326)::geography, 'city', true, true),
  (:'beta_farm_id', 'Test City', ST_SetSRID(ST_MakePoint(-100.02, 40.01), 4326)::geography, 'city', true, true),
  (:'private_farm_id', 'Test City', ST_SetSRID(ST_MakePoint(-100.01, 40.01), 4326)::geography, 'exact', true, false),
  (:'hidden_farm_id', 'Test City', ST_SetSRID(ST_MakePoint(-100.01, 40.0), 4326)::geography, 'city', true, true);

DO $$
DECLARE
  list_count integer;
  count_endpoint integer;
  map_count integer;
  first_page text[];
  second_page text[];
BEGIN
  WITH public_scope AS MATERIALIZED (
    SELECT f.id, f.name, l.point
      FROM farms f
      JOIN farm_locations l ON l.farm_id = f.id
     WHERE f.status = 'published'
       AND l.is_public
       AND l.point IS NOT NULL
       AND ST_DWithin(l.point, ST_SetSRID(ST_MakePoint(-100.0, 40.0), 4326)::geography, 10000)
  )
  SELECT count(*), count(*), count(*)
    INTO list_count, count_endpoint, map_count
    FROM public_scope;

  IF list_count <> 2 OR count_endpoint <> list_count OR map_count <> list_count THEN
    RAISE EXCEPTION 'list/count/map mismatch: list %, count %, map %', list_count, count_endpoint, map_count;
  END IF;

  SELECT array_agg(slug ORDER BY name, id)
    INTO first_page
    FROM (
      SELECT f.id, f.slug, f.name
        FROM farms f
       WHERE f.slug IN ('discovery-alpha', 'discovery-beta')
       ORDER BY f.name, f.id
       LIMIT 1
    ) page;

  SELECT array_agg(slug ORDER BY name, id)
    INTO second_page
    FROM (
      SELECT f.id, f.slug, f.name
        FROM farms f
       WHERE f.slug IN ('discovery-alpha', 'discovery-beta')
         AND (f.name, f.id) > ('Alpha Discovery Farm', current_setting('farmfinder.discovery_alpha_id')::uuid)
       ORDER BY f.name, f.id
       LIMIT 1
    ) page;

  IF first_page <> ARRAY['discovery-alpha'] OR second_page <> ARRAY['discovery-beta'] THEN
    RAISE EXCEPTION 'stable keyset pagination failed: first %, second %', first_page, second_page;
  END IF;
END
$$;

SET LOCAL enable_seqscan = off;

DO $$
DECLARE
  plan_row record;
  plan_text text := '';
BEGIN
  FOR plan_row IN EXECUTE $query$
    EXPLAIN (FORMAT JSON)
    SELECT farm_id
      FROM farm_locations
     WHERE is_public
       AND point IS NOT NULL
       AND ST_DWithin(point, ST_SetSRID(ST_MakePoint(-100.0, 40.0), 4326)::geography, 10000)
  $query$ LOOP
    plan_text := plan_row."QUERY PLAN"::text;
  END LOOP;

  IF plan_text NOT LIKE '%farm_locations_public_point_gist_idx%' THEN
    RAISE EXCEPTION 'public spatial query did not use the governed GiST index: %', plan_text;
  END IF;
END
$$;

ROLLBACK;
