-- Sowing rows: Season (Independent) and Season (cluster) (Clustered) are required while
-- they are shown, as Land ID and Land ID (cluster) are (97g_sowing_harvest_land_rows.sql):
-- each column's show rule ("Cluster / non cluster status" contains INDEPENDENT or
-- CLUSTERED, 97k_cluster_status_list.sql) gets a `require` rule with the same condition.
-- The row dialog and the save check (required_fields.py, every channel) read it; a
-- `widget-required` flag would ask for the hidden one too and block the other side.
-- ODK fills both from the production season; the file import fills `season`, and a
-- Clustered row needs its `cluster_season`.
--
-- Sorts after 97k (which sets the CLUSTERED / INDEPENDENT conditions). Only the
-- widget-data-options of these two columns change; a second run changes nothing.
CREATE OR REPLACE FUNCTION pg_temp.sowing_season_required(node jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    result jsonb;
    show_rule jsonb;
BEGIN
    IF jsonb_typeof(node) = 'array' THEN
        SELECT COALESCE(jsonb_agg(pg_temp.sowing_season_required(value) ORDER BY ord), '[]'::jsonb)
          INTO result FROM jsonb_array_elements(node) WITH ORDINALITY AS a(value, ord);
        RETURN result;
    ELSIF jsonb_typeof(node) <> 'object' THEN
        RETURN node;
    END IF;
    IF node->>'column-key' IN ('season', 'cluster_season') THEN
        show_rule := CASE
            WHEN node->'widget-data-options'->>'action' = 'show' THEN node->'widget-data-options'->'condition'
            ELSE (SELECT a->'condition' FROM jsonb_array_elements(node->'widget-data-options'->'actions') a
                   WHERE a->>'action' = 'show' LIMIT 1)
        END;
        IF show_rule IS NULL THEN
            RAISE EXCEPTION 'Sowing % has no show rule to require it by', node->>'column-key';
        END IF;
        RETURN node || jsonb_build_object('widget-data-options', jsonb_build_object('actions', jsonb_build_array(
            jsonb_build_object('action', 'show', 'condition', show_rule),
            jsonb_build_object('action', 'require', 'condition', show_rule))));
    END IF;
    SELECT COALESCE(jsonb_object_agg(key, pg_temp.sowing_season_required(value)), '{}'::jsonb)
      INTO result FROM jsonb_each(node);
    RETURN result;
END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.sowing_season_required("section_ui_schema"::jsonb)::json
 WHERE "section_id" = 'cropsown_sowing_details_section_01';

DO $$
DECLARE found int;
BEGIN
    SELECT count(*) INTO found
      FROM "public"."g2p_register_sections" s,
           jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."column-key" != null)') c
     WHERE s."section_id" = 'cropsown_sowing_details_section_01'
       AND (c->>'column-key', c->'widget-data-options'->'actions'->1->'condition'->>'value') IN
           (('season', 'INDEPENDENT'), ('cluster_season', 'CLUSTERED'))
       AND c->'widget-data-options'->'actions'->1->>'action' = 'require'
       AND c->'widget-data-options'->'actions'->0->'condition' = c->'widget-data-options'->'actions'->1->'condition';
    IF found <> 2 THEN
        RAISE EXCEPTION 'Sowing Season / Season (cluster) are not required while shown';
    END IF;
END
$$;
