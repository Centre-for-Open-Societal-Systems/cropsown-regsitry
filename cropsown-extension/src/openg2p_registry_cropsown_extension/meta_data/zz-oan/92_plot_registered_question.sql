-- Ask "Is Plot Registered?" instead of "Plot is not yet registered" on the crop
-- planning and cultivation forms.
--
-- The stored field stays is_plot_not_registered (true = the plot is not
-- registered). Asking the question the other way round therefore also swaps
-- the answers: Yes stores false (registered) and No stores true (not
-- registered). Stored data, ODK, file import and reports keep their meaning,
-- and saved records still show the right answer.
--
-- Only the label and the two options of this one select change, in the two
-- sections that carry it. A second run changes nothing. Sorts after
-- 86_readable_lists.sql, which sets the earlier label.
CREATE OR REPLACE FUNCTION pg_temp.crop_plot_registered(node jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN
            CASE WHEN node->>'widget-data-path' = 'is_plot_not_registered'
                 THEN node || jsonb_build_object(
                          'widget-label', 'Is Plot Registered?',
                          'widget-data-source', jsonb_build_object('type', 'static', 'options', jsonb_build_array(
                              jsonb_build_object('label', 'Yes', 'value', false),
                              jsonb_build_object('label', 'No', 'value', true))))
                 ELSE (SELECT COALESCE(jsonb_object_agg(key, pg_temp.crop_plot_registered(value)), '{}'::jsonb)
                         FROM jsonb_each(node))
            END
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.crop_plot_registered(element) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position))
        ELSE node
    END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.crop_plot_registered("section_ui_schema"::jsonb)::json
 WHERE "section_id" IN ('cropsown_planning_details_section_01', 'cropsown_cultivation_details_section_01');

DO $$
DECLARE missed text;
BEGIN
    SELECT string_agg(s."section_id", ', ')
      INTO missed
      FROM "public"."g2p_register_sections" s
     WHERE s."section_id" IN ('cropsown_planning_details_section_01', 'cropsown_cultivation_details_section_01')
       AND NOT EXISTS (
           SELECT 1 FROM jsonb_path_query(s."section_ui_schema"::jsonb,
                    'strict $.** ? (@."widget-data-path" == "is_plot_not_registered")') w
            WHERE w->>'widget-label' = 'Is Plot Registered?'
              AND w->'widget-data-source'->'options' = '[{"label": "Yes", "value": false}, {"label": "No", "value": true}]'::jsonb);
    IF missed IS NOT NULL THEN
        RAISE EXCEPTION 'Crop Sown plot question not set to "Is Plot Registered?" in: %', missed;
    END IF;
END
$$;
