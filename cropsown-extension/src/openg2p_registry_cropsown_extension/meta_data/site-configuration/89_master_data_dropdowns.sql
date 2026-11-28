-- Master Data dropdowns: cropping system, seed type, seed source, agro-ecological
-- zone, growth stage and severity level read their choices from Master Data.
--
-- These eleven dropdowns carried a fixed list of options in the form
-- (MONO_CROPPING, LOCAL, "GOVERNMENT / WOREDS AGRICULTURE", KOLLA, EMERGENCE, LOW
-- ...). Those codes are not the ETH-OAN pack codes, so a value chosen in the form
-- could not match the Master Data list the registry validates against. Each one
-- now reads its pack list instead, like every other coded dropdown:
--
--   planning     cropping_system, seed_class, seed_source
--   cultivation  cropping_system, actual_seed_class, actual_seed_source
--   sowing, cluster, cultivation cluster   agro_ecological_zone
--   infestation  growth_stage, severity_level
--
--   CROPPING_SYSTEM (CSYS_*), SEED_TYPE (SEED_*), SEED_SOURCE (SEEDSRC_*),
--   AGRO_ECOLOGICAL_ZONE (AEZ_*), CROP_GROWTH_STAGE (GS_*), INFESTATION_SEVERITY (SEV_*)
--
-- In these six pack lists the value id and the value code are the same, so the
-- stored value is the pack code. Only the widget's data source changes: ids, data
-- paths, labels, rules and validation stay. Record and intake forms share these
-- sections, so one update covers both.
--
-- Only a widget that still has a fixed option list is changed, so a database that
-- already reads the lists is left as it is and a second run changes nothing. Runs
-- after the register metadata and the label overlays, before 98_ethiopian_dates.sql.
CREATE OR REPLACE FUNCTION pg_temp.crop_list_source(node jsonb, data_path text, attribute_id text) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN
            CASE WHEN COALESCE(node->>'widget-data-path' = data_path OR node->>'column-key' = data_path, false)
                      AND node->'widget-data-source'->>'type' = 'static'
                 THEN node || jsonb_build_object('widget-data-source', jsonb_build_object(
                          'type', 'api', 'method', 'POST', 'service', 'attributes', 'endpoint', 'values',
                          'params', jsonb_build_object('page_size', 200, 'attribute_id', attribute_id),
                          'labelKey', 'value_display', 'valueKey', 'value_code'))
                 ELSE (SELECT COALESCE(jsonb_object_agg(key, pg_temp.crop_list_source(value, data_path, attribute_id)), '{}'::jsonb)
                         FROM jsonb_each(node))
            END
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.crop_list_source(element, data_path, attribute_id) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position))
        ELSE node
    END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.crop_list_source(pg_temp.crop_list_source(pg_temp.crop_list_source(
           "section_ui_schema"::jsonb,
           'cropping_system', 'CROPPING_SYSTEM'),
           'seed_class', 'SEED_TYPE'),
           'seed_source', 'SEED_SOURCE')::json
 WHERE "section_id" = 'cropsown_planning_details_section_01';

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.crop_list_source(pg_temp.crop_list_source(pg_temp.crop_list_source(
           "section_ui_schema"::jsonb,
           'cropping_system', 'CROPPING_SYSTEM'),
           'actual_seed_class', 'SEED_TYPE'),
           'actual_seed_source', 'SEED_SOURCE')::json
 WHERE "section_id" = 'cropsown_cultivation_details_section_01';

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.crop_list_source(
           "section_ui_schema"::jsonb, 'agro_ecological_zone', 'AGRO_ECOLOGICAL_ZONE')::json
 WHERE "section_id" IN (
       'cropsown_sowing_details_section_01',
       'cropsown_cluster_details_section_01',
       'cropsown_cultivation_cluster_details_section_01');

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.crop_list_source(pg_temp.crop_list_source(
           "section_ui_schema"::jsonb,
           'growth_stage', 'CROP_GROWTH_STAGE'),
           'severity_level', 'INFESTATION_SEVERITY')::json
 WHERE "section_id" = 'cropsown_infestation_details_section_01';

DO $$
DECLARE missed text;
BEGIN
    SELECT string_agg(s."section_id" || '.' || COALESCE(w->>'column-key', w->>'widget-data-path'), ', ')
      INTO missed
      FROM "public"."g2p_register_sections" s,
           jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-source"."type" == "static")') w
     WHERE (s."section_id", COALESCE(w->>'column-key', w->>'widget-data-path')) IN (
           ('cropsown_planning_details_section_01', 'cropping_system'),
           ('cropsown_planning_details_section_01', 'seed_class'),
           ('cropsown_planning_details_section_01', 'seed_source'),
           ('cropsown_cultivation_details_section_01', 'cropping_system'),
           ('cropsown_cultivation_details_section_01', 'actual_seed_class'),
           ('cropsown_cultivation_details_section_01', 'actual_seed_source'),
           ('cropsown_sowing_details_section_01', 'agro_ecological_zone'),
           ('cropsown_cluster_details_section_01', 'agro_ecological_zone'),
           ('cropsown_cultivation_cluster_details_section_01', 'agro_ecological_zone'),
           ('cropsown_infestation_details_section_01', 'growth_stage'),
           ('cropsown_infestation_details_section_01', 'severity_level'));
    IF missed IS NOT NULL THEN
        RAISE EXCEPTION 'Crop Sown dropdowns still on a fixed option list: %', missed;
    END IF;
END
$$;
