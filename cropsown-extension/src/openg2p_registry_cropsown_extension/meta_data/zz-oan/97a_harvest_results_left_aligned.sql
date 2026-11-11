-- The five calculated Harvest figures show their value next to the label.
--
-- Harvest section (cropsown_harvest_details_section_01), "Production result"
-- group only: Yield (kg per hectare), Yield performance (%), Fertilizer
-- efficiency, Land utilization rate and Seed productivity. They are read-only
-- (register_domain/services/harvest_metrics.py fills them), and right-aligned
-- they sat at the far edge of their column, against the next field's label.
-- Their textAlign becomes "left"; every other number field keeps "right".
--
-- Only these five widgets change. A second run changes nothing.
CREATE OR REPLACE FUNCTION pg_temp.harvest_results_left_aligned(node jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN
            CASE
                WHEN COALESCE(node->>'widget-data-path', node->>'column-key') IN (
                        'yield_kg_ha', 'yield_performance_pct', 'fertilizer_efficiency',
                        'land_utilization_rate', 'seed_productivity')
                     AND node->>'widget' = 'number'
                    THEN jsonb_set(node, '{widget-data-format}',
                                   COALESCE(node->'widget-data-format', '{}'::jsonb) || '{"textAlign": "left"}'::jsonb)
                ELSE (SELECT COALESCE(jsonb_object_agg(key, pg_temp.harvest_results_left_aligned(value)), '{}'::jsonb)
                        FROM jsonb_each(node))
            END
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.harvest_results_left_aligned(element) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position))
        ELSE node
    END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.harvest_results_left_aligned("section_ui_schema"::jsonb)::json
 WHERE "section_id" = 'cropsown_harvest_details_section_01';

DO $$
DECLARE still_right text;
BEGIN
    SELECT string_agg(COALESCE(w->>'widget-data-path', w->>'column-key'), ', ')
      INTO still_right
      FROM "public"."g2p_register_sections" s,
           jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget" == "number")') w
     WHERE s."section_id" = 'cropsown_harvest_details_section_01'
       AND COALESCE(w->>'widget-data-path', w->>'column-key') IN (
               'yield_kg_ha', 'yield_performance_pct', 'fertilizer_efficiency',
               'land_utilization_rate', 'seed_productivity')
       AND COALESCE(w->'widget-data-format'->>'textAlign', '') <> 'left';
    IF still_right IS NOT NULL THEN
        RAISE EXCEPTION 'Harvest result fields not left-aligned: %', still_right;
    END IF;
END
$$;
