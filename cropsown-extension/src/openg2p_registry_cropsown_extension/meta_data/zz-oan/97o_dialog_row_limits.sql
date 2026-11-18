-- Table rows are checked in the row dialog, on Save, before they reach the table, by
-- comparing two fields of the same row:
--   Crop planning        Planned crop area <= Total land area; End date >= Start date;
--                        Planned date between Start date and End date
--   Cultivation          Actual crop area <= Total land area; End date >= Start date;
--                        Cultivation date between Start date and End date
--   Cluster information  Planned area and Collected land <= Total cultivated area
--   and Cultivation      (timad x 0.25); Area collected by combine harvester <= Planned
--   cluster              area; End date >= Start date; Establishing date between Start
--                        date and End date
--   Sowing               Area sown <= Total land area; Area sown, cluster <= Total
--                        cultivated area
--   Harvest              Area harvested <= Total land area; Quantity stored + sold <=
--                        Quantity harvested (Independent and Clustered)
--
-- Each column gets marks the staff UI's dialog table reads
-- (ui/staff-ui/overrides/src/oan/widgets/RowLimitDialogTable.tsx):
--   "oan-max-column"       not more than that column (times "oan-max-factor" if given)
--   "oan-plus-column"      added to this column's value before that comparison
--   "oan-min-column"       a date not earlier than that column
--   "oan-max-date-column"  a date not later than that column
--   "oan-limit-message"    the translation key of the message
-- Blank values, and a column hidden in that row (for example Total land area when
-- "Is planning record created?" is Yes), are not compared. The server keeps the same
-- rules on Next and submit for every channel; totals of a Land ID across rows and the
-- checks against earlier stages stay there. Widgets, data paths, stored values, ODK and
-- file imports are unchanged.
--
-- To undo on a database: run the UPDATE below with
--   node - 'oan-max-column' - 'oan-max-factor' - 'oan-plus-column' - 'oan-min-column'
--        - 'oan-max-date-column' - 'oan-limit-message'
-- in place of the node || (marks -> ...) branch (or reseed without this file).
-- A second run changes nothing.
CREATE OR REPLACE FUNCTION pg_temp.dialog_row_limits(node jsonb, marks jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN
            CASE
                WHEN node->>'widget' IN ('number', 'date') AND marks ? (node->>'column-key')
                    THEN node || (marks -> (node->>'column-key'))
                ELSE (SELECT COALESCE(jsonb_object_agg(key, pg_temp.dialog_row_limits(value, marks)), '{}'::jsonb)
                        FROM jsonb_each(node))
            END
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.dialog_row_limits(element, marks) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position))
        ELSE node
    END
$$;

CREATE TEMP TABLE oan_dialog_row_limits (section_id text PRIMARY KEY, marks jsonb NOT NULL);
INSERT INTO oan_dialog_row_limits VALUES
('cropsown_planning_details_section_01', '{
  "planned_area": {"oan-max-column": "land_area", "oan-limit-message": "validation_planned_area_above_land_area"},
  "end_gc": {"oan-min-column": "start_gc", "oan-limit-message": "validation_end_date_before_start_date"},
  "planned_date": {"oan-min-column": "start_gc", "oan-max-date-column": "end_gc", "oan-limit-message": "validation_planned_date_outside_season"}}'),
('cropsown_cultivation_details_section_01', '{
  "actual_crop_area": {"oan-max-column": "land_area", "oan-limit-message": "validation_actual_crop_area_above_land_area"},
  "end_gc": {"oan-min-column": "start_gc", "oan-limit-message": "validation_end_date_before_start_date"},
  "actual_cultivation_date": {"oan-min-column": "start_gc", "oan-max-date-column": "end_gc", "oan-limit-message": "validation_cultivation_date_outside_season"}}'),
('cropsown_cluster_details_section_01', '{
  "cluster_plan": {"oan-max-column": "cluster_area_timad", "oan-max-factor": 0.25, "oan-limit-message": "validation_cluster_plan_above_total_area"},
  "collected_land": {"oan-max-column": "cluster_area_timad", "oan-max-factor": 0.25, "oan-limit-message": "validation_collected_land_above_total_area"},
  "collected_by_combiner": {"oan-max-column": "cluster_plan", "oan-limit-message": "validation_combiner_above_planned_area"},
  "end_gc": {"oan-min-column": "start_gc", "oan-limit-message": "validation_end_date_before_start_date"},
  "establishing_date": {"oan-min-column": "start_gc", "oan-max-date-column": "end_gc", "oan-limit-message": "validation_establishing_date_outside_season"}}'),
('cropsown_cultivation_cluster_details_section_01', '{
  "cluster_plan": {"oan-max-column": "cluster_area_timad", "oan-max-factor": 0.25, "oan-limit-message": "validation_cluster_plan_above_total_area"},
  "collected_land": {"oan-max-column": "cluster_area_timad", "oan-max-factor": 0.25, "oan-limit-message": "validation_collected_land_above_total_area"},
  "collected_by_combiner": {"oan-max-column": "cluster_plan", "oan-limit-message": "validation_combiner_above_planned_area"},
  "end_gc": {"oan-min-column": "start_gc", "oan-limit-message": "validation_end_date_before_start_date"},
  "establishing_date": {"oan-min-column": "start_gc", "oan-max-date-column": "end_gc", "oan-limit-message": "validation_establishing_date_outside_season"}}'),
('cropsown_sowing_details_section_01', '{
  "area_sown": {"oan-max-column": "land_area", "oan-limit-message": "validation_area_sown_above_land_area"},
  "cluster_area_sown": {"oan-max-column": "cluster_area_hectare", "oan-limit-message": "validation_cluster_area_sown_above_total_area"}}'),
('cropsown_harvest_details_section_01', '{
  "area_harvested": {"oan-max-column": "land_area", "oan-limit-message": "validation_area_harvested_above_land_area"},
  "qty_stored": {"oan-max-column": "qty_harvested", "oan-plus-column": "qty_sold", "oan-limit-message": "validation_disposal_above_harvested"},
  "qty_sold": {"oan-max-column": "qty_harvested", "oan-plus-column": "qty_stored", "oan-limit-message": "validation_disposal_above_harvested"},
  "cluster_qty_stored": {"oan-max-column": "cluster_qty_harvested", "oan-plus-column": "cluster_qty_sold", "oan-limit-message": "validation_disposal_above_harvested"},
  "cluster_qty_sold": {"oan-max-column": "cluster_qty_harvested", "oan-plus-column": "cluster_qty_stored", "oan-limit-message": "validation_disposal_above_harvested"}}');

UPDATE "public"."g2p_register_sections" s
   SET "section_ui_schema" = pg_temp.dialog_row_limits(s."section_ui_schema"::jsonb, l.marks)::json
  FROM oan_dialog_row_limits l
 WHERE s."section_id" = l.section_id;

-- The messages ({limit} is the other field's value). Merged by key, every language.
UPDATE "public"."registry_languages"
   SET "domain_translation" = (COALESCE("domain_translation"::jsonb, '{}'::jsonb) || jsonb_build_object(
       'validation_planned_area_above_land_area', 'Planned crop area cannot be more than Total land area ({limit} hectares).',
       'validation_actual_crop_area_above_land_area', 'Actual crop area cannot be more than Total land area ({limit} hectares).',
       'validation_end_date_before_start_date', 'End date cannot be earlier than Start date.',
       'validation_planned_date_outside_season', 'Planned date must be between Start date and End date.',
       'validation_cultivation_date_outside_season', 'Cultivation date must be between Start date and End date.',
       'validation_establishing_date_outside_season', 'Establishing date must be between Start date and End date.',
       'validation_cluster_plan_above_total_area', 'Planned area cannot be more than Total cultivated area ({limit} hectares).',
       'validation_collected_land_above_total_area', 'Collected land cannot be more than Total cultivated area ({limit} hectares).',
       'validation_combiner_above_planned_area', 'Area collected by combine harvester cannot be more than Planned area ({limit} hectares).',
       'validation_area_sown_above_land_area', 'Area sown cannot be more than Total land area ({limit} hectares).',
       'validation_cluster_area_sown_above_total_area', 'Area sown, cluster cannot be more than Total cultivated area ({limit} hectares).',
       'validation_area_harvested_above_land_area', 'Area harvested cannot be more than Total land area ({limit} hectares).',
       'validation_disposal_above_harvested', 'Quantity stored plus quantity sold cannot be more than Quantity harvested ({limit}).'))::json;

DO $$
DECLARE missing text;
BEGIN
    SELECT string_agg(l.section_id || ' ' || k.column_key, ', ')
      INTO missing
      FROM oan_dialog_row_limits l, jsonb_object_keys(l.marks) AS k(column_key)
     WHERE NOT EXISTS (
           SELECT 1
             FROM "public"."g2p_register_sections" s,
                  jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."column-key" != null)') c
            WHERE s."section_id" = l.section_id
              AND c->>'column-key' = k.column_key
              AND c->>'oan-limit-message' = l.marks -> k.column_key ->> 'oan-limit-message');
    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'Table columns without their dialog row limit: %', missing;
    END IF;
END
$$;

DROP TABLE oan_dialog_row_limits;
