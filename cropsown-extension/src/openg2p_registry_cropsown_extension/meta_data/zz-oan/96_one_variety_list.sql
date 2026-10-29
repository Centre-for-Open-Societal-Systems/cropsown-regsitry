-- Crop Sown has one variety field on the planning and cultivation tables: the
-- "Variety" dropdown on the SEED_VARIETY list (widget data path seed_variety),
-- which the ETH-OAN pack of openg2p-data seeds. The separate "Crop Variety"
-- dropdown (widget data path crop_variety, list CROP_VARIETY) meant the same
-- thing, so it is removed from the table columns of the planning section and of
-- the cultivation section, and the remaining dropdown is labelled "Variety".
-- Record and intake forms share these two sections, so one update covers both.
-- The crop_variety database columns stay; only the form no longer shows them.
--
-- Explicit-id UPDATEs, so a plain upgrade repairs a database that already holds
-- the older sections; on a repaired database every statement changes nothing.
-- Runs after the register metadata and the older label files.
CREATE OR REPLACE FUNCTION pg_temp.crop_drop_column(node jsonb, data_path text) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN (
            SELECT COALESCE(jsonb_object_agg(key, pg_temp.crop_drop_column(value, data_path)), '{}'::jsonb)
              FROM jsonb_each(node))
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.crop_drop_column(element, data_path) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position)
             WHERE NOT (jsonb_typeof(element) = 'object'
                        AND COALESCE(element->>'widget-data-path' = data_path OR element->>'column-key' = data_path, false)))
        ELSE node
    END
$$;

CREATE OR REPLACE FUNCTION pg_temp.crop_relabel_column(node jsonb, data_path text, new_label text) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN (
            SELECT COALESCE(jsonb_object_agg(key,
                       CASE WHEN key = 'widget-label' AND node->>'widget-data-path' = data_path
                            THEN to_jsonb(new_label)
                            ELSE pg_temp.crop_relabel_column(value, data_path, new_label) END), '{}'::jsonb)
              FROM jsonb_each(node))
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.crop_relabel_column(element, data_path, new_label) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position))
        ELSE node
    END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.crop_relabel_column(
           pg_temp.crop_drop_column("section_ui_schema"::jsonb, 'crop_variety'), 'seed_variety', 'Variety')::json
 WHERE "section_id" IN (
       'cropsown_planning_details_section_01',
       'cropsown_cultivation_details_section_01')
   AND ("section_ui_schema"::text LIKE '%crop_variety%' OR "section_ui_schema"::text LIKE '%Seed Variety%');

-- Display text: drop the retired Crop Variety keys, then merge the English translations of the
-- variety label (seed wins over the older files)
UPDATE "public"."registry_languages"
SET "domain_translation" = ((COALESCE("domain_translation"::jsonb, '{}'::jsonb) - 'crop_variety' - 'Crop Variety') ||
'{
 "seed_variety": "Variety",
 "Seed Variety": "Variety",
 "SEED_VARIETY": "Variety",
 "Variety": "Variety"
}'::jsonb)::json
WHERE "language_code" = 'en';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM "public"."g2p_register_sections"
         WHERE "section_id" IN ('cropsown_planning_details_section_01', 'cropsown_cultivation_details_section_01')
           AND "section_ui_schema"::text LIKE '%crop_variety%') THEN
        RAISE EXCEPTION 'The Crop Variety dropdown is still on a Crop Sown planning or cultivation section';
    END IF;
    IF EXISTS (
        SELECT 1 FROM "public"."g2p_register_sections" s,
               jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-path" == "seed_variety")') w
         WHERE s."section_id" IN ('cropsown_planning_details_section_01', 'cropsown_cultivation_details_section_01')
           AND w->>'widget-label' <> 'Variety') THEN
        RAISE EXCEPTION 'The seed_variety dropdown of a Crop Sown section is not labelled Variety';
    END IF;
    IF EXISTS (
        SELECT 1 FROM "public"."registry_languages"
         WHERE "language_code" = 'en' AND "domain_translation"::jsonb ?| ARRAY['crop_variety', 'Crop Variety']) THEN
        RAISE EXCEPTION 'The English translations still name the retired Crop Variety dropdown';
    END IF;
END
$$;
