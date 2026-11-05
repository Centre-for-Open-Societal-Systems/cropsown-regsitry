-- Drop the read-only Ethiopian-calendar copies of five dates from the crop forms.
--
--   planning              planned_date_ec             Planned Date (EC)
--   cultivation           actual_cultivation_date_ec  Actual Cultivation Date (EC)
--   sowing                sowing_date_ec              Sowing Date (EC)
--   infestation           observation_date_ec         Date of Observation (EC)
--   cluster, cultivation  establishing_date_ec        Establishing Date (EC)
--   cluster
--
-- Each was a read-only box next to its date, filled by the server from the
-- Gregorian date. The date picker itself already shows and accepts Ethiopian
-- dates (98_ethiopian_dates.sql), so the copy only repeated it. The server no
-- longer fills these fields either. Their database columns are kept, so no data
-- is removed; they are simply no longer shown or written.
--
-- Only these widgets (form fields and table columns) are removed; every other
-- widget, label, rule and setting in the sections stays. A second run changes
-- nothing. Runs after the register metadata and the earlier overlays, before
-- 98_ethiopian_dates.sql.
CREATE OR REPLACE FUNCTION pg_temp.crop_drop_ec_dates(node jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN (
            SELECT COALESCE(jsonb_object_agg(key, pg_temp.crop_drop_ec_dates(value)), '{}'::jsonb)
              FROM jsonb_each(node))
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.crop_drop_ec_dates(element) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position)
             WHERE NOT (jsonb_typeof(element) = 'object'
                        AND COALESCE(element->>'column-key', element->>'widget-data-path', '') IN (
                            'planned_date_ec', 'actual_cultivation_date_ec', 'sowing_date_ec',
                            'observation_date_ec', 'establishing_date_ec')))
        ELSE node
    END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.crop_drop_ec_dates("section_ui_schema"::jsonb)::json
 WHERE "section_id" IN (
       'cropsown_planning_details_section_01',
       'cropsown_cultivation_details_section_01',
       'cropsown_sowing_details_section_01',
       'cropsown_infestation_details_section_01',
       'cropsown_cluster_details_section_01',
       'cropsown_cultivation_cluster_details_section_01');

DO $$
DECLARE left_over text;
BEGIN
    SELECT string_agg(s."section_id" || '.' || m[1], ', ')
      INTO left_over
      FROM "public"."g2p_register_sections" s,
           regexp_matches(s."section_ui_schema"::text,
               '"(?:column-key|widget-data-path)": *"(planned_date_ec|actual_cultivation_date_ec|sowing_date_ec|observation_date_ec|establishing_date_ec)"',
               'g') m;
    IF left_over IS NOT NULL THEN
        RAISE EXCEPTION 'Crop Sown Ethiopian date copies still on the forms: %', left_over;
    END IF;
END
$$;
