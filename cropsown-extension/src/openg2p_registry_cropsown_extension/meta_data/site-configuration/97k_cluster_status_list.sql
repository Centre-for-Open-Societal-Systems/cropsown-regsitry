-- Sowing and Harvest rows take "Cluster / non cluster status" from the Master Data
-- list CLUSTER_STATUS (CLUSTERED, INDEPENDENT), as the Infestation rows already do,
-- instead of the form's own options (CLUSTER, INDEPENDENT).
--
-- Sowing (cropsown_sowing_details_section_01) and Harvest
-- (cropsown_harvest_details_section_01), their tables only:
--   * cluster_status stays a multi-select (a row may be both) and reads its options
--     from CLUSTER_STATUS;
--   * every show / require rule on cluster_status for CLUSTER now reads CLUSTERED
--     (Land ID (cluster), its "Is planning record created?" and the other cluster
--     fields). The INDEPENDENT rules are unchanged, as are the land and cluster
--     location fields, which follow "Is planning record created?", not the status.
--   * rows already stored with CLUSTER are rewritten to CLUSTERED (intake, register
--     and history), so they open with Clustered ticked.
-- The backend reads either value (cluster_sides in cropsown_intake_validation_service);
-- ODK (odk_to_crop_intake.j2) and file import send CLUSTERED, and file import still
-- takes CLUSTER from older files.
--
-- Runs after 97g_sowing_harvest_land_rows.sql, which writes the CLUSTER rules of
-- Land ID (cluster) and its "Is planning record created?" on every run; this file
-- turns them to CLUSTERED again. A second run changes nothing.

CREATE OR REPLACE FUNCTION pg_temp.cluster_status_rule(node jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN
            CASE
                WHEN node->>'field' = 'cluster_status' AND node->>'value' = 'CLUSTER'
                    THEN node || '{"value": "CLUSTERED"}'::jsonb
                ELSE (SELECT COALESCE(jsonb_object_agg(key, pg_temp.cluster_status_rule(value)), '{}'::jsonb)
                        FROM jsonb_each(node))
            END
        WHEN 'array' THEN
            (SELECT COALESCE(jsonb_agg(pg_temp.cluster_status_rule(value) ORDER BY ord), '[]'::jsonb)
               FROM jsonb_array_elements(node) WITH ORDINALITY AS a(value, ord))
        ELSE node
    END
$$;

CREATE OR REPLACE FUNCTION pg_temp.cluster_status_list(node jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    result jsonb;
    columns jsonb := '[]'::jsonb;
    col jsonb;
    list jsonb := '{"type": "api", "method": "POST", "params": {"page_size": 200, "attribute_id": "CLUSTER_STATUS"},
                    "service": "attributes", "endpoint": "values", "labelKey": "value_display",
                    "valueKey": "value_code"}'::jsonb;
BEGIN
    IF jsonb_typeof(node) = 'array' THEN
        SELECT COALESCE(jsonb_agg(pg_temp.cluster_status_list(value) ORDER BY ord), '[]'::jsonb)
          INTO result FROM jsonb_array_elements(node) WITH ORDINALITY AS a(value, ord);
        RETURN result;
    ELSIF jsonb_typeof(node) <> 'object' THEN
        RETURN node;
    END IF;
    IF jsonb_typeof(node->'widget-data-columns') = 'array'
       AND EXISTS (SELECT 1 FROM jsonb_array_elements(node->'widget-data-columns') c WHERE c->>'column-key' = 'cluster_status') THEN
        FOR col IN SELECT value FROM jsonb_array_elements(node->'widget-data-columns') WITH ORDINALITY AS a(value, ord) ORDER BY ord LOOP
            IF col->>'column-key' = 'cluster_status' THEN
                col := col || jsonb_build_object('widget-data-source', list);
            ELSIF col ? 'widget-data-options' THEN
                col := col || jsonb_build_object('widget-data-options', pg_temp.cluster_status_rule(col->'widget-data-options'));
            END IF;
            columns := columns || jsonb_build_array(col);
        END LOOP;
        RETURN node || jsonb_build_object('widget-data-columns', columns);
    END IF;
    SELECT COALESCE(jsonb_object_agg(k, pg_temp.cluster_status_list(v)), '{}'::jsonb)
      INTO result FROM jsonb_each(node) AS e(k, v);
    RETURN result;
END
$$;

-- A stored status: the list with CLUSTER written CLUSTERED; a lone "CLUSTER" string likewise.
CREATE OR REPLACE FUNCTION pg_temp.cluster_status_value(status jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(status)
        WHEN 'array' THEN
            (SELECT COALESCE(jsonb_agg(CASE WHEN value = '"CLUSTER"'::jsonb THEN '"CLUSTERED"'::jsonb ELSE value END
                                       ORDER BY ord), '[]'::jsonb)
               FROM jsonb_array_elements(status) WITH ORDINALITY AS a(value, ord))
        WHEN 'string' THEN
            CASE WHEN status = '"CLUSTER"'::jsonb THEN '"CLUSTERED"'::jsonb ELSE status END
        ELSE status
    END
$$;

DO $$
DECLARE
    tbl text;
    leftover int;
BEGIN
    UPDATE "public"."g2p_register_sections"
       SET "section_ui_schema" = pg_temp.cluster_status_list("section_ui_schema"::jsonb)::json
     WHERE "section_id" IN ('cropsown_sowing_details_section_01', 'cropsown_harvest_details_section_01');

    FOREACH tbl IN ARRAY ARRAY['g2p_intake_form_sowings', 'g2p_register_sowings', 'g2p_register_history_sowings',
                               'g2p_intake_form_harvests', 'g2p_register_harvests', 'g2p_register_history_harvests'] LOOP
        IF to_regclass('public.' || tbl) IS NOT NULL THEN
            EXECUTE format('UPDATE "public".%I SET "cluster_status" = pg_temp.cluster_status_value("cluster_status") '
                           'WHERE "cluster_status" @> ''["CLUSTER"]''::jsonb OR "cluster_status" = ''"CLUSTER"''::jsonb', tbl);
        END IF;
    END LOOP;

    SELECT count(*) INTO leftover
      FROM "public"."g2p_register_sections"
     WHERE "section_id" IN ('cropsown_sowing_details_section_01', 'cropsown_harvest_details_section_01')
       AND ("section_ui_schema"::jsonb @? '$.** ? (@.field == "cluster_status" && @.value == "CLUSTER")'
            OR NOT "section_ui_schema"::jsonb @? '$.** ? (@."column-key" == "cluster_status" && @."widget-data-source".params.attribute_id == "CLUSTER_STATUS")');
    IF leftover > 0 THEN
        RAISE EXCEPTION 'Sowing / Harvest cluster status not moved to CLUSTER_STATUS';
    END IF;
END
$$;
