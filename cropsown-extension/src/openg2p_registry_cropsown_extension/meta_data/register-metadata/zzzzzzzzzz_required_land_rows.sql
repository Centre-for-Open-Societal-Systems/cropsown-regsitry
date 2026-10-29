-- Each Crop Sown intake form needs at least one land row, and the sowing and
-- harvest rows need their dates, quantities and crop. The intake service
-- (required_intake.py) enforces `widget-required` on save and submit for every
-- channel, so this file only marks the widgets.
--
-- Land table of each form (dialog-table widget id): planning, cultivation,
-- sowing and harvest. Cluster and infestation tables stay optional.
--   cs_planning_details_table      section cropsown_planning_details_section_01
--   cs_cultivation_details_table   section cropsown_cultivation_details_section_01
--   cs_sowing_details_table        section cropsown_sowing_details_section_01
--   cs_harvest_details_table       section cropsown_harvest_details_section_01
-- Required columns added: sowing_date, area_sown, commodity (sowing);
-- harvest_date, qty_harvested, commodity (harvest). Land ID (and Season and
-- Commodity of planning and cultivation) are already required by the base file.
--
-- Sorts after every earlier file that rewrites the section JSON (the base
-- upsert, field rules, identity overlays); no later file touches these sections.
-- Idempotent: it only sets flags to true, so every install and upgrade can re-run it.
CREATE OR REPLACE FUNCTION pg_temp.coss_require_land_rows(node jsonb, table_id text, required_columns text[])
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE result jsonb;
BEGIN
  IF jsonb_typeof(node) = 'array' THEN
    SELECT COALESCE(jsonb_agg(pg_temp.coss_require_land_rows(value, table_id, required_columns) ORDER BY position), '[]'::jsonb)
      INTO result FROM jsonb_array_elements(node) WITH ORDINALITY AS item(value, position);
  ELSIF jsonb_typeof(node) = 'object' THEN
    SELECT COALESCE(jsonb_object_agg(key, pg_temp.coss_require_land_rows(value, table_id, required_columns)), '{}'::jsonb)
      INTO result FROM jsonb_each(node);
    IF node->>'widget-id' = table_id AND node->>'widget' IN ('table', 'dialog-table')
       AND jsonb_typeof(node->'widget-data-columns') = 'array' THEN
      result := result || '{"widget-required": true}'::jsonb;
      result := jsonb_set(result, '{widget-data-columns}', (
        SELECT COALESCE(jsonb_agg(
          CASE WHEN jsonb_typeof(column_node) = 'object' AND column_node->>'column-key' = ANY (required_columns)
               THEN column_node || '{"widget-required": true}'::jsonb ELSE column_node END
          ORDER BY position), '[]'::jsonb)
        FROM jsonb_array_elements(node->'widget-data-columns') WITH ORDINALITY AS item(column_node, position)));
    END IF;
  ELSE
    result := node;
  END IF;
  RETURN result;
END $$;

UPDATE g2p_register_sections
SET section_ui_schema = pg_temp.coss_require_land_rows(section_ui_schema::jsonb, 'cs_planning_details_table', ARRAY[]::text[])
WHERE section_id = 'cropsown_planning_details_section_01' AND section_ui_schema IS NOT NULL;

UPDATE g2p_register_sections
SET section_ui_schema = pg_temp.coss_require_land_rows(section_ui_schema::jsonb, 'cs_cultivation_details_table', ARRAY[]::text[])
WHERE section_id = 'cropsown_cultivation_details_section_01' AND section_ui_schema IS NOT NULL;

UPDATE g2p_register_sections
SET section_ui_schema = pg_temp.coss_require_land_rows(section_ui_schema::jsonb, 'cs_sowing_details_table',
  ARRAY['sowing_date', 'area_sown', 'commodity'])
WHERE section_id = 'cropsown_sowing_details_section_01' AND section_ui_schema IS NOT NULL;

UPDATE g2p_register_sections
SET section_ui_schema = pg_temp.coss_require_land_rows(section_ui_schema::jsonb, 'cs_harvest_details_table',
  ARRAY['harvest_date', 'qty_harvested', 'commodity'])
WHERE section_id = 'cropsown_harvest_details_section_01' AND section_ui_schema IS NOT NULL;

-- Checks: fail the seed loudly if a land table is not required, or a named
-- column is missing or not required.
DO $$
DECLARE expected record; table_node jsonb; missing text;
BEGIN
  FOR expected IN SELECT * FROM (VALUES
      ('cropsown_planning_details_section_01', 'cs_planning_details_table', ARRAY['land_id', 'season', 'commodity']),
      ('cropsown_cultivation_details_section_01', 'cs_cultivation_details_table', ARRAY['land_id', 'season', 'commodity']),
      ('cropsown_sowing_details_section_01', 'cs_sowing_details_table', ARRAY['land_id', 'sowing_date', 'area_sown', 'commodity']),
      ('cropsown_harvest_details_section_01', 'cs_harvest_details_table', ARRAY['land_id', 'harvest_date', 'qty_harvested', 'commodity'])
    ) AS v(section_id, table_id, required_columns)
  LOOP
    SELECT w INTO table_node FROM g2p_register_sections s,
      jsonb_path_query(s.section_ui_schema::jsonb, 'strict $.**') w
      WHERE s.section_id = expected.section_id AND jsonb_typeof(w) = 'object' AND w->>'widget-id' = expected.table_id;
    IF table_node IS NULL OR table_node->'widget-required' IS DISTINCT FROM 'true'::jsonb THEN
      RAISE EXCEPTION 'land table % of % must be widget-required', expected.table_id, expected.section_id;
    END IF;
    SELECT string_agg(k, ', ') INTO missing FROM unnest(expected.required_columns) AS k
      WHERE NOT EXISTS (SELECT 1 FROM jsonb_array_elements(table_node->'widget-data-columns') c
        WHERE c->>'column-key' = k AND c->'widget-required' = 'true'::jsonb);
    IF missing IS NOT NULL THEN
      RAISE EXCEPTION 'columns of % must be widget-required: %', expected.table_id, missing;
    END IF;
  END LOOP;
END $$;
