-- Crop Sown identifies the farmer by Farmer ID and a typed Fayda ID (FAN or FIN);
-- there is no "Verify with Fayda" step, which is Farmer-only. The Fayda
-- verification widget (widget-id identity_verification) is removed from the
-- record and intake sections that still carry it, wherever it sits in their
-- nested panels. The FAN and FIN fields stay; the FIN display, which no longer
-- comes from a verification, is labelled "Fayda FIN". Runs on every seed after the
-- register metadata, so it also removes the widget the older identity seed
-- files add back; on a database without the widget it changes nothing.
CREATE OR REPLACE FUNCTION pg_temp.crop_drop_widget(node jsonb, widget_id text) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN (
            SELECT COALESCE(jsonb_object_agg(key, pg_temp.crop_drop_widget(value, widget_id)), '{}'::jsonb)
              FROM jsonb_each(node))
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.crop_drop_widget(element, widget_id) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position)
             WHERE NOT (jsonb_typeof(element) = 'object' AND element ? 'widget'
                        AND element->>'widget-id' = widget_id))
        ELSE node
    END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.crop_drop_widget("section_ui_schema"::jsonb, 'identity_verification')::json
 WHERE "section_id" IN (
       'cropsown_intake_record_section_01',
       'cropsown_cropsown_record_section_01',
       'cropsown_production_details_section_01',
       'cropsown_common_intake_record_section_01')
   AND "section_ui_schema"::text LIKE '%"identity_verification"%';

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = replace("section_ui_schema"::jsonb::text,
       '"widget-label": "Fayda FIN (from verification)"', '"widget-label": "Fayda FIN"')::json
 WHERE "section_id" IN (
       'cropsown_intake_record_section_01',
       'cropsown_cropsown_record_section_01',
       'cropsown_production_details_section_01',
       'cropsown_common_intake_record_section_01')
   AND "section_ui_schema"::jsonb::text LIKE '%"widget-label": "Fayda FIN (from verification)"%';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM "public"."g2p_register_sections" s,
               jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (exists (@."widget"))') w
         WHERE s."section_id" IN (
               'cropsown_intake_record_section_01',
               'cropsown_cropsown_record_section_01',
               'cropsown_production_details_section_01',
               'cropsown_common_intake_record_section_01')
           AND w->>'widget-id' = 'identity_verification') THEN
        RAISE EXCEPTION 'Fayda verification widget still present on a Crop Sown section';
    END IF;
    IF EXISTS (
        SELECT 1 FROM "public"."g2p_register_sections"
         WHERE "section_ui_schema"::text LIKE '%Fayda FIN (from verification)%') THEN
        RAISE EXCEPTION 'A Crop Sown section still labels the FIN "from verification"';
    END IF;
END
$$;
