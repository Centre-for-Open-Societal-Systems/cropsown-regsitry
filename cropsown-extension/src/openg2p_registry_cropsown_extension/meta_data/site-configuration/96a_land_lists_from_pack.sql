-- Ownership type, Land preparation method and Cultivation type read the ETH-OAN pack's
-- newer Master Data lists:
--
--   ownership_type     OWNERSHIP_TYPE    -> LAND_OWNERSHIP_TYPE      (OWNER, TENANT, CROP_SHARE)
--   land_prep_method   LAND_PREP_METHOD  -> LAND_PREPARATION_METHOD  (LPM_*)
--   cultivation_type   MACHINERY         -> FARM_MACHINERY           (MACH_*)
--
-- Only the list a dropdown reads changes: ids, data paths, labels, rules and the stored
-- value (the value code) stay. Values already saved on records keep their old codes;
-- the old lists stay in Master Data, so those records still show their labels.
--
-- Every Crop Sown section is updated (Planning and Cultivation hold these dropdowns;
-- Record and intake forms share the sections). Runs after 89_master_data_dropdowns.sql
-- and before 97f / 97g, which copy the Planning ownership dropdown into the Cultivation,
-- Sowing and Harvest land fields, so those copies read the new list too. Only a dropdown
-- still on an old list is changed, so a second run changes nothing.
CREATE OR REPLACE FUNCTION pg_temp.crop_land_list(node jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN
            CASE WHEN node->'widget-data-source'->>'type' = 'api'
                      AND node->'widget-data-source'->'params'->>'attribute_id'
                          IN ('OWNERSHIP_TYPE', 'LAND_PREP_METHOD', 'MACHINERY')
                 THEN jsonb_set(node, '{widget-data-source,params,attribute_id}',
                          to_jsonb(CASE node->'widget-data-source'->'params'->>'attribute_id'
                                       WHEN 'OWNERSHIP_TYPE' THEN 'LAND_OWNERSHIP_TYPE'
                                       WHEN 'LAND_PREP_METHOD' THEN 'LAND_PREPARATION_METHOD'
                                       ELSE 'FARM_MACHINERY' END))
                 ELSE (SELECT COALESCE(jsonb_object_agg(key, pg_temp.crop_land_list(value)), '{}'::jsonb)
                         FROM jsonb_each(node))
            END
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.crop_land_list(element) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position))
        ELSE node
    END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.crop_land_list("section_ui_schema"::jsonb)::json
 WHERE "section_id" LIKE 'cropsown\_%'
   AND "section_ui_schema"::text ~ '"attribute_id": ?"(OWNERSHIP_TYPE|LAND_PREP_METHOD|MACHINERY)"';

DO $$
DECLARE missed text;
BEGIN
    SELECT string_agg(DISTINCT s."section_id" || '.' || COALESCE(w->>'column-key', w->>'widget-data-path'), ', ')
      INTO missed
      FROM "public"."g2p_register_sections" s,
           jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-source"."type" == "api")') w
     WHERE s."section_id" LIKE 'cropsown\_%'
       AND w->'widget-data-source'->'params'->>'attribute_id' IN ('OWNERSHIP_TYPE', 'LAND_PREP_METHOD', 'MACHINERY');
    IF missed IS NOT NULL THEN
        RAISE EXCEPTION 'Crop Sown dropdowns still on an old land list: %', missed;
    END IF;
END
$$;
