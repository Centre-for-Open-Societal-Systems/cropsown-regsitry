-- Decimal number fields keep their decimals.
--
-- The staff UI's number input formats a value with format.decimalPlaces and
-- defaults it to 0, so a widget marked numericType "decimal" without places
-- rounded every value to a whole number as it was typed: 0.5 ha was saved as 1.
-- The columns behind these widgets are Numeric, and ODK submissions keep the
-- decimals, so only the form lost them.
--
-- Every number widget, including table columns, that is decimal and declares
-- no places gets two. Land area ("Total land area (hectares)", Numeric) had no
-- numeric type at all and becomes decimal first. A widget that already declares
-- its places, and every integer widget, are left as they are. Applied after the
-- overlays that add land rows (97f, 97g), so their columns are covered too.
CREATE OR REPLACE FUNCTION pg_temp.oan_decimal_places(node jsonb)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
  result jsonb;
  fmt jsonb;
BEGIN
  IF jsonb_typeof(node) = 'array' THEN
    SELECT COALESCE(jsonb_agg(pg_temp.oan_decimal_places(value) ORDER BY ord), '[]'::jsonb)
      INTO result FROM jsonb_array_elements(node) WITH ORDINALITY AS a(value, ord);
  ELSIF jsonb_typeof(node) = 'object' THEN
    SELECT COALESCE(jsonb_object_agg(key, pg_temp.oan_decimal_places(value)), '{}'::jsonb)
      INTO result FROM jsonb_each(node);
    IF node->>'widget' = 'number' THEN
      fmt := COALESCE(result->'widget-data-format', '{}'::jsonb);
      IF fmt->>'numericType' IS NULL
         AND COALESCE(node->>'widget-data-path', node->>'column-key') IN ('land_area') THEN
        fmt := fmt || '{"numericType":"decimal"}'::jsonb;
      END IF;
      IF fmt->>'numericType' = 'decimal' AND NOT fmt ? 'decimalPlaces' THEN
        fmt := fmt || '{"decimalPlaces":2}'::jsonb;
      END IF;
      result := jsonb_set(result, '{widget-data-format}', fmt);
    END IF;
  ELSE
    result := node;
  END IF;
  RETURN result;
END $$;

UPDATE public.g2p_register_sections
SET section_ui_schema = pg_temp.oan_decimal_places(section_ui_schema)
WHERE section_ui_schema IS NOT NULL
  AND section_ui_schema::text LIKE '%"widget": "number"%';
