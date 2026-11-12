-- Sowing date and Date of observation: today or an earlier date, never a future one.
--
--   Sowing table (cropsown_sowing_details_section_01), column sowing_date
--   Infestation table (cropsown_infestation_details_section_01), column observation_date
-- Each date picker gets its own limit: maxDate "today", with its message. The server
-- refuses a future date on every channel (field_rules.PAST_ONLY), and the ODK Sowing
-- form already does (". <= today()"). Date of observation is no longer compared with
-- the Sowing date (g2p_register_domain_service_infestation.py).
--
-- Merges keys only, so a second run changes nothing.
UPDATE "public"."registry_languages"
   SET "domain_translation" = (COALESCE("domain_translation"::jsonb, '{}'::jsonb) || jsonb_build_object(
       'validation_sowing_date_future', 'Sowing date: the date is in the future. Enter today''s date or an earlier date.',
       'validation_observation_date_future', 'Date of observation: the date is in the future. Enter today''s date or an earlier date.'))::json;

CREATE OR REPLACE FUNCTION pg_temp.date_not_future(node jsonb, key text) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    result jsonb;
BEGIN
    IF jsonb_typeof(node) = 'array' THEN
        SELECT COALESCE(jsonb_agg(pg_temp.date_not_future(value, key) ORDER BY ord), '[]'::jsonb)
          INTO result FROM jsonb_array_elements(node) WITH ORDINALITY AS a(value, ord);
        RETURN result;
    ELSIF jsonb_typeof(node) <> 'object' THEN
        RETURN node;
    END IF;
    IF node->>'column-key' = key AND node->>'widget' = 'date' THEN
        RETURN node || jsonb_build_object('widget-data-options',
            COALESCE(node->'widget-data-options', '{}'::jsonb)
            || jsonb_build_object('maxDate', 'today', 'maxDateMessage', 'validation_' || key || '_future'));
    END IF;
    SELECT COALESCE(jsonb_object_agg(k, pg_temp.date_not_future(v, key)), '{}'::jsonb)
      INTO result FROM jsonb_each(node) AS e(k, v);
    RETURN result;
END
$$;

DO $$
DECLARE
    item record;
BEGIN
    FOR item IN SELECT * FROM (VALUES
            ('cropsown_sowing_details_section_01', 'sowing_date'),
            ('cropsown_infestation_details_section_01', 'observation_date')) AS v(section_id, column_key) LOOP
        UPDATE "public"."g2p_register_sections"
           SET "section_ui_schema" = pg_temp.date_not_future("section_ui_schema"::jsonb, item.column_key)::json
         WHERE "section_id" = item.section_id;
        IF NOT EXISTS (
            SELECT 1 FROM "public"."g2p_register_sections" s,
                   jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.**') c
             WHERE s."section_id" = item.section_id AND jsonb_typeof(c) = 'object'
               AND c->>'column-key' = item.column_key AND c->'widget-data-options'->>'maxDate' = 'today') THEN
            RAISE EXCEPTION '% limit not in place in %', item.column_key, item.section_id;
        END IF;
    END LOOP;
END
$$;
