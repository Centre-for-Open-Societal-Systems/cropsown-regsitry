-- Pest name (Infestation): typed text, not the PEST dropdown.
--
-- The Infestation table's Pest name (cropsown_infestation_details_section_01, column
-- pest_name) becomes a text box: the widget is "text" and has no data source, so the
-- platform's code-list check (which reads the widget's attribute_id) no longer applies
-- to it. Its label and its show rule (Pest infestations only) stay. Pest type stays the
-- PEST dropdown. The ODK Sowing form asks Pest name as text too (build_mds_forms.py).
--
-- Rewrites the one column the same way on every run, so a second run changes nothing.
CREATE OR REPLACE FUNCTION pg_temp.pest_name_text(node jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    result jsonb;
BEGIN
    IF jsonb_typeof(node) = 'array' THEN
        SELECT COALESCE(jsonb_agg(pg_temp.pest_name_text(value) ORDER BY ord), '[]'::jsonb)
          INTO result FROM jsonb_array_elements(node) WITH ORDINALITY AS a(value, ord);
        RETURN result;
    ELSIF jsonb_typeof(node) <> 'object' THEN
        RETURN node;
    END IF;
    IF node->>'column-key' = 'pest_name' THEN
        RETURN (node - 'widget-data-source') || '{"widget": "text"}'::jsonb;
    END IF;
    SELECT COALESCE(jsonb_object_agg(k, pg_temp.pest_name_text(v)), '{}'::jsonb)
      INTO result FROM jsonb_each(node) AS e(k, v);
    RETURN result;
END
$$;

DO $$
BEGIN
    UPDATE "public"."g2p_register_sections"
       SET "section_ui_schema" = pg_temp.pest_name_text("section_ui_schema"::jsonb)::json
     WHERE "section_id" = 'cropsown_infestation_details_section_01';
    IF EXISTS (
        SELECT 1 FROM "public"."g2p_register_sections" s,
               jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.**') c
         WHERE s."section_id" = 'cropsown_infestation_details_section_01' AND jsonb_typeof(c) = 'object'
           AND c->>'column-key' = 'pest_name' AND (c->>'widget' <> 'text' OR c ? 'widget-data-source')) THEN
        RAISE EXCEPTION 'Pest name is still a dropdown';
    END IF;
END
$$;
