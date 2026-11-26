-- Crop planning, Cluster information and Cultivation cluster rows pick their
-- location like the Crop location section: Zone lists only the zones of the chosen
-- Region, Woreda only the woredas of the chosen Zone, Kebele only the kebeles of
-- the chosen Woreda, and changing a level clears the levels below it.
--
-- Sections cropsown_planning_details_section_01,
-- cropsown_cluster_details_section_01 and
-- cropsown_cultivation_cluster_details_section_01 only. Their Zone, Woreda and
-- Kebele columns get "oan-parent-column" naming the column above them; the staff
-- UI's select (ui/staff-ui/overrides/src/oan/widgets/CascadingSelectWidget.tsx)
-- reads it inside the row dialog. The widgets stay selects on the same Master Data
-- list, so the stored values (level_value_id), the table grid, ODK and imports are
-- unchanged.
--
-- Their data source also gets the stock "dependsOn": "oan-parent-cell", a value that
-- is never set. The platform loads a cell's list itself, from the column as given,
-- before the select runs; with this it waits instead of loading every zone, woreda or
-- kebele (which would replace the select's list). The select points dependsOn at the
-- parent cell of the open row, so only one list is loaded.
--
-- To undo on a database: run the UPDATE below with
--   (node - 'oan-parent-column') #- '{widget-data-source,dependsOn}'
-- in place of the jsonb_set(...) branch (or reseed without this file).
-- A second run changes nothing.
CREATE OR REPLACE FUNCTION pg_temp.cascading_location(node jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN
            CASE
                WHEN node->>'column-key' IN ('zone', 'woreda', 'kebele') AND node->>'widget' = 'select'
                    THEN jsonb_set(node || jsonb_build_object('oan-parent-column',
                             CASE node->>'column-key' WHEN 'zone' THEN 'region' WHEN 'woreda' THEN 'zone' ELSE 'woreda' END),
                         '{widget-data-source,dependsOn}', '"oan-parent-cell"')
                ELSE (SELECT COALESCE(jsonb_object_agg(key, pg_temp.cascading_location(value)), '{}'::jsonb)
                        FROM jsonb_each(node))
            END
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.cascading_location(element) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position))
        ELSE node
    END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.cascading_location("section_ui_schema"::jsonb)::json
 WHERE "section_id" IN ('cropsown_planning_details_section_01',
                        'cropsown_cluster_details_section_01',
                        'cropsown_cultivation_cluster_details_section_01');

DO $$
DECLARE missing text;
BEGIN
    SELECT string_agg(sections.id || ' ' || expected.level, ', ')
      INTO missing
      FROM (VALUES ('cropsown_planning_details_section_01'),
                   ('cropsown_cluster_details_section_01'),
                   ('cropsown_cultivation_cluster_details_section_01')) AS sections(id),
           (VALUES ('zone', 'region'), ('woreda', 'zone'), ('kebele', 'woreda')) AS expected(level, parent)
     WHERE NOT EXISTS (
           SELECT 1
             FROM "public"."g2p_register_sections" s,
                  jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."column-key" != null)') c
            WHERE s."section_id" = sections.id
              AND c->>'column-key' = expected.level
              AND c->>'oan-parent-column' = expected.parent
              AND c->'widget-data-source'->>'dependsOn' = 'oan-parent-cell');
    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'Location columns without their parent: %', missing;
    END IF;
END
$$;
