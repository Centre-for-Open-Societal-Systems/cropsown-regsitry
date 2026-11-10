-- The Crop record's Crop sown ID, crop year and production season cannot be
-- edited on an approved record.
--
-- Crop record section (cropsown_cropsown_record_section_01, "Edit Details" on an
-- approved record) only:
--   Crop sown ID, Crop year  -> display widgets (shown, not editable), like
--                               Farmer name and Fayda FIN next to them
--   Production season        -> read-only select, so it keeps showing the
--                               season's name rather than its code
-- The values are still sent on save, and the server rejects any change to them
-- (g2p_register_domain_service_crop_sown.py). The intake forms use their own
-- sections, so a new intake still chooses its crop year and season.
--
-- Only these three widgets change. A second run changes nothing. Sorts after
-- 41_crop_record_tab_layout.sql, which lays this section out.
--
-- This file also labels an intake's record name "ID" (the second part below).
-- It shares this file because 98_ethiopian_dates.sql must be the last overlay
-- and 93 and 94 are the only free numbers before it.
CREATE OR REPLACE FUNCTION pg_temp.crop_record_header_readonly(node jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN
            CASE
                WHEN node->>'widget-id' IN ('functional_record_id', 'crop_year') AND node ? 'widget-data-path'
                    THEN node || '{"widget": "display", "widget-type": "display", "widget-readonly": true, "widget-required": false}'::jsonb
                WHEN node->>'widget-id' = 'production_season' AND node ? 'widget-data-path'
                    THEN node || '{"widget-readonly": true}'::jsonb
                ELSE (SELECT COALESCE(jsonb_object_agg(key, pg_temp.crop_record_header_readonly(value)), '{}'::jsonb)
                        FROM jsonb_each(node))
            END
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.crop_record_header_readonly(element) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position))
        ELSE node
    END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.crop_record_header_readonly("section_ui_schema"::jsonb)::json
 WHERE "section_id" = 'cropsown_cropsown_record_section_01';

DO $$
DECLARE editable text;
BEGIN
    SELECT string_agg(w->>'widget-id', ', ')
      INTO editable
      FROM "public"."g2p_register_sections" s,
           jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-path" != null)') w
     WHERE s."section_id" = 'cropsown_cropsown_record_section_01'
       AND w->>'widget-id' IN ('functional_record_id', 'crop_year', 'production_season')
       AND COALESCE((w->>'widget-readonly')::boolean, false) IS NOT TRUE;
    IF editable IS NOT NULL THEN
        RAISE EXCEPTION 'Crop record fields still editable: %', editable;
    END IF;
END
$$;


-- ---------------------------------------------------------------------------
-- "ID" instead of "Name" for an intake's record name.
--
-- An intake only carries the Farmer ID and Fayda ID (no farmer name), so its
-- record name is the Farmer ID. The staff UI overrides of the intake submission
-- card, the intake list column and the submission header
-- (ui/staff-ui/overrides/src/...) label it with the key intake_record_id. The
-- shared record_name key ("Name") stays for registers, change requests and tasks.
--
-- A translation already set for intake_record_id is kept, so a word changed in the
-- language data survives a reseed. A second run changes nothing.
UPDATE "public"."registry_languages"
   SET "domain_translation" = (jsonb_build_object('intake_record_id', 'ID')
                               || COALESCE("domain_translation"::jsonb, '{}'::jsonb))::json
 WHERE "language_code" IN ('en', 'am', 'om', 'ti')
   AND NOT (COALESCE("domain_translation"::jsonb, '{}'::jsonb) ? 'intake_record_id');
