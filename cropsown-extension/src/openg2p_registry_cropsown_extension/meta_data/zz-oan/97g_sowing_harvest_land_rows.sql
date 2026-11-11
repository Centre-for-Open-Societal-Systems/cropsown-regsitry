-- Sowing and Harvest land rows, in two parts that run in this order:
--   Part 1: a Land ID for each Cluster status (Land ID / Land ID (cluster)).
--   Part 2: "Is planning record created?" for each Land ID, with the land fields for No.

-- ===================== Part 1: Land ID for each Cluster status =====================
-- Sowing and Harvest rows: a Land ID for each Cluster status.
--
-- Sowing (cropsown_sowing_details_section_01) and Harvest
-- (cropsown_harvest_details_section_01), their tables only:
--   A new row shows Cluster / non cluster status, then the Development agent and
--   Supervisor fields. Land ID (cluster) comes first among the cluster fields, Land ID
--   first among the Independent fields.
--   Independent ticked: Land ID (land_id), checked against Cultivation (Sowing) or
--       the independent Sowing (Harvest).
--   Clustered ticked: Land ID (cluster) (cluster_land_id), checked against
--       Cultivation cluster (Sowing) or the clustered Sowing (Harvest).
--   Both ticked: both Land IDs.
-- Each is required only while shown (a `require` rule, read by the row dialog and
-- by required_fields.py), not by `widget-required`: the table check asks for a
-- `widget-required` column even when it is hidden, which would block the other
-- side. The save (g2p_register_domain_service_sowing.py / _harvest.py) also asks
-- for Land ID when no status is given (ODK, file import), as before.
--
-- Land ID (cluster) is taken out and written again on every run, so a second run
-- changes nothing.
CREATE OR REPLACE FUNCTION pg_temp.sowing_harvest_land_ids(node jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    result jsonb;
    columns jsonb := '[]'::jsonb;
    land jsonb;
    land_cluster jsonb;
    rules jsonb;
    placed boolean := false;
    col jsonb;
    show_for text;
BEGIN
    IF jsonb_typeof(node) = 'array' THEN
        SELECT COALESCE(jsonb_agg(pg_temp.sowing_harvest_land_ids(value) ORDER BY ord), '[]'::jsonb)
          INTO result FROM jsonb_array_elements(node) WITH ORDINALITY AS a(value, ord);
        RETURN result;
    ELSIF jsonb_typeof(node) <> 'object' THEN
        RETURN node;
    END IF;
    IF jsonb_typeof(node->'widget-data-columns') = 'array'
       AND EXISTS (SELECT 1 FROM jsonb_array_elements(node->'widget-data-columns') c WHERE c->>'column-key' = 'land_id')
       AND EXISTS (SELECT 1 FROM jsonb_array_elements(node->'widget-data-columns') c WHERE c->>'column-key' = 'cluster_status') THEN
        SELECT c INTO land FROM jsonb_array_elements(node->'widget-data-columns') c WHERE c->>'column-key' = 'land_id';
        land := land - 'widget-required';
        land_cluster := land || jsonb_build_object('column-key', 'cluster_land_id', 'widget-data-path', 'cluster_land_id',
                                                   'widget-label', 'Land ID (cluster)');
        FOREACH show_for IN ARRAY ARRAY['INDEPENDENT', 'CLUSTER'] LOOP
            rules := jsonb_build_object('widget-data-options', jsonb_build_object('actions', jsonb_build_array(
                jsonb_build_object('action', 'show', 'condition', jsonb_build_object(
                    'field', 'cluster_status', 'operator', 'contains', 'value', show_for)),
                jsonb_build_object('action', 'require', 'condition', jsonb_build_object(
                    'field', 'cluster_status', 'operator', 'contains', 'value', show_for)))));
            IF show_for = 'INDEPENDENT' THEN land := land || rules; ELSE land_cluster := land_cluster || rules; END IF;
        END LOOP;
        -- Land ID (cluster) right after Cluster status, where the cluster fields start;
        -- Land ID just before the first Independent field.
        FOR col IN SELECT value FROM jsonb_array_elements(node->'widget-data-columns') WITH ORDINALITY AS a(value, ord) ORDER BY ord LOOP
            -- Part 2's question and land fields are set aside here and added back by Part 2,
            -- so a second run places the Land IDs exactly as the first.
            CONTINUE WHEN col->>'column-key' IN ('land_id', 'cluster_land_id', 'is_land_recorded',
                'is_cluster_land_recorded', 'is_plot_not_registered', 'plot_category', 'ownership_type',
                'land_area', 'soil_fertility_type', 'region', 'zone', 'woreda', 'kebele', 'map_location',
                'latitude', 'longitude', 'cluster_region', 'cluster_zone', 'cluster_woreda', 'cluster_kebele',
                'cluster_sub_kebele', 'cluster_latitude', 'cluster_longitude');
            IF NOT placed AND col->'widget-data-options'->'condition'->>'value' = 'INDEPENDENT' THEN
                columns := columns || jsonb_build_array(land);
                placed := true;
            END IF;
            columns := columns || jsonb_build_array(col);
            IF col->>'column-key' = 'cluster_status' THEN
                columns := columns || jsonb_build_array(land_cluster);
            END IF;
        END LOOP;
        IF NOT placed THEN
            columns := columns || jsonb_build_array(land);
        END IF;
        RETURN node || jsonb_build_object('widget-data-columns', columns);
    END IF;
    SELECT COALESCE(jsonb_object_agg(k, pg_temp.sowing_harvest_land_ids(v)), '{}'::jsonb)
      INTO result FROM jsonb_each(node) AS e(k, v);
    RETURN result;
END
$$;

DO $$
DECLARE
    section text;
    keys text[];
BEGIN
    UPDATE "public"."g2p_register_sections"
       SET "section_ui_schema" = pg_temp.sowing_harvest_land_ids("section_ui_schema"::jsonb)::json
     WHERE "section_id" IN ('cropsown_sowing_details_section_01', 'cropsown_harvest_details_section_01');

    FOREACH section IN ARRAY ARRAY['cropsown_sowing_details_section_01', 'cropsown_harvest_details_section_01'] LOOP
        SELECT array_agg(c->>'column-key' ORDER BY ord)
          INTO keys
          FROM "public"."g2p_register_sections" s,
               jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-columns" != null)') t,
               jsonb_array_elements(t->'widget-data-columns') WITH ORDINALITY AS x(c, ord)
         WHERE s."section_id" = section;
        IF keys[1:2] IS DISTINCT FROM ARRAY['cluster_status', 'cluster_land_id']
           OR keys[array_position(keys, 'land_id') + 1] NOT IN ('season', 'commodity') THEN
            RAISE EXCEPTION 'Land IDs not in place in % (%)', section, keys;
        END IF;
    END LOOP;
END
$$;

-- ======== Part 2: "Is planning record created?" and the land fields ========
-- Sowing and Harvest rows ask "Is planning record created?" for each Land ID.
--
-- Sowing (cropsown_sowing_details_section_01) and Harvest
-- (cropsown_harvest_details_section_01), their tables only:
--   Independent: "Is planning record created?" (is_land_recorded) just before Land ID.
--       No shows the Crop planning row's land fields after Land ID: Is plot registered?,
--       Plot category, Ownership type, Total land area, Soil fertility, Region, Zone,
--       Woreda, Kebele, Map location, Latitude, Longitude (same lists, cascade and map).
--   Clustered: "Is planning record created?" (is_cluster_land_recorded) just
--       before Land ID (cluster). No shows the Cluster section's location fields after
--       it, as cluster_region, cluster_zone, cluster_woreda, cluster_kebele,
--       cluster_sub_kebele, cluster_latitude, cluster_longitude.
-- Nothing here is required (ODK and file import do not send the answers yet). The
-- answers and land fields are stored on the Sowing / Harvest row; on save a Yes is
-- checked: Land ID against Planning or Cultivation, Land ID (cluster) against Cluster or
-- Cultivation cluster, of the same farmer, crop year and season
-- (cropsown_intake_validation_service.validate_land_recorded).
--
-- The added columns are taken out and written again on every run, so a second run
-- changes nothing. Runs after Part 1 above (Land ID / Land ID (cluster) placement)
-- and after 97c (the Planning map it copies).
CREATE OR REPLACE FUNCTION pg_temp.sowing_harvest_land_recorded(node jsonb, planning jsonb, cluster jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    result jsonb;
    columns jsonb := '[]'::jsonb;
    col jsonb;
    key text;
    copy jsonb;
    land_keys text[] := ARRAY['is_plot_not_registered', 'plot_category', 'ownership_type', 'land_area',
                              'soil_fertility_type', 'region', 'zone', 'woreda', 'kebele', 'map_location',
                              'latitude', 'longitude'];
    cluster_keys text[] := ARRAY['region', 'zone', 'woreda', 'kebele', 'sub_kebele', 'latitude', 'longitude'];
    added text[];
    land_no jsonb := '{"widget-data-options": {"action": "show", "condition":
                      {"field": "is_land_recorded", "operator": "equals", "value": false}}}'::jsonb;
    cluster_no jsonb := '{"widget-data-options": {"action": "show", "condition":
                         {"field": "is_cluster_land_recorded", "operator": "equals", "value": false}}}'::jsonb;
    yes_no jsonb := jsonb_build_object('type', 'static', 'options', jsonb_build_array(
                        jsonb_build_object('label', 'Yes', 'value', true),
                        jsonb_build_object('label', 'No', 'value', false)));
BEGIN
    IF jsonb_typeof(node) = 'array' THEN
        SELECT COALESCE(jsonb_agg(pg_temp.sowing_harvest_land_recorded(value, planning, cluster) ORDER BY ord), '[]'::jsonb)
          INTO result FROM jsonb_array_elements(node) WITH ORDINALITY AS a(value, ord);
        RETURN result;
    ELSIF jsonb_typeof(node) <> 'object' THEN
        RETURN node;
    END IF;
    IF jsonb_typeof(node->'widget-data-columns') = 'array'
       AND EXISTS (SELECT 1 FROM jsonb_array_elements(node->'widget-data-columns') c WHERE c->>'column-key' = 'cluster_land_id') THEN
        added := ARRAY['is_land_recorded', 'is_cluster_land_recorded'] || land_keys
                 || ARRAY(SELECT 'cluster_' || k FROM unnest(cluster_keys) k);
        FOR col IN SELECT value FROM jsonb_array_elements(node->'widget-data-columns') WITH ORDINALITY AS a(value, ord) ORDER BY ord LOOP
            CONTINUE WHEN col->>'column-key' = ANY (added);
            IF col->>'column-key' = 'land_id' THEN
                columns := columns || jsonb_build_array(jsonb_build_object(
                    'widget', 'select', 'widget-type', 'input', 'column-key', 'is_land_recorded',
                    'widget-data-path', 'is_land_recorded', 'widget-label', 'Is planning record created?',
                    'widget-readonly', false, 'widget-data-source', yes_no,
                    'widget-data-options', jsonb_build_object('action', 'show', 'condition', jsonb_build_object(
                        'field', 'cluster_status', 'operator', 'contains', 'value', 'INDEPENDENT'))));
            ELSIF col->>'column-key' = 'cluster_land_id' THEN
                columns := columns || jsonb_build_array(jsonb_build_object(
                    'widget', 'select', 'widget-type', 'input', 'column-key', 'is_cluster_land_recorded',
                    'widget-data-path', 'is_cluster_land_recorded', 'widget-label', 'Is planning record created?',
                    'widget-readonly', false, 'widget-data-source', yes_no,
                    'widget-data-options', jsonb_build_object('action', 'show', 'condition', jsonb_build_object(
                        'field', 'cluster_status', 'operator', 'contains', 'value', 'CLUSTER'))));
            END IF;
            columns := columns || jsonb_build_array(col);
            IF col->>'column-key' = 'land_id' THEN
                FOREACH key IN ARRAY land_keys LOOP
                    IF planning ? key THEN
                        columns := columns || jsonb_build_array(((planning->key) - 'widget-required') || land_no);
                    END IF;
                END LOOP;
            ELSIF col->>'column-key' = 'cluster_land_id' THEN
                FOREACH key IN ARRAY cluster_keys LOOP
                    IF cluster ? key THEN
                        copy := ((cluster->key) - 'widget-required') || jsonb_build_object(
                            'column-key', 'cluster_' || key, 'widget-data-path', 'cluster_' || key);
                        IF copy ? 'oan-parent-column' THEN
                            copy := copy || jsonb_build_object('oan-parent-column', 'cluster_' || (copy->>'oan-parent-column'));
                        END IF;
                        columns := columns || jsonb_build_array(copy || cluster_no);
                    END IF;
                END LOOP;
            END IF;
        END LOOP;
        RETURN node || jsonb_build_object('widget-data-columns', columns);
    END IF;
    SELECT COALESCE(jsonb_object_agg(k, pg_temp.sowing_harvest_land_recorded(v, planning, cluster)), '{}'::jsonb)
      INTO result FROM jsonb_each(node) AS e(k, v);
    RETURN result;
END
$$;

DO $$
DECLARE
    planning jsonb;
    cluster jsonb;
    section text;
    keys text[];
BEGIN
    -- the Crop planning and Cluster tables' columns, by column key
    SELECT jsonb_object_agg(c->>'column-key', c) INTO planning
      FROM "public"."g2p_register_sections" s,
           jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-columns" != null)') t,
           jsonb_array_elements(t->'widget-data-columns') c
     WHERE s."section_id" = 'cropsown_planning_details_section_01';
    SELECT jsonb_object_agg(c->>'column-key', c) INTO cluster
      FROM "public"."g2p_register_sections" s,
           jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-columns" != null)') t,
           jsonb_array_elements(t->'widget-data-columns') c
     WHERE s."section_id" = 'cropsown_cluster_details_section_01';
    IF planning IS NULL OR cluster IS NULL THEN
        RAISE EXCEPTION 'Crop planning or Cluster table not found';
    END IF;

    UPDATE "public"."g2p_register_sections"
       SET "section_ui_schema" = pg_temp.sowing_harvest_land_recorded("section_ui_schema"::jsonb, planning, cluster)::json
     WHERE "section_id" IN ('cropsown_sowing_details_section_01', 'cropsown_harvest_details_section_01');

    FOREACH section IN ARRAY ARRAY['cropsown_sowing_details_section_01', 'cropsown_harvest_details_section_01'] LOOP
        SELECT array_agg(c->>'column-key' ORDER BY ord) INTO keys
          FROM "public"."g2p_register_sections" s,
               jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-columns" != null)') t,
               jsonb_array_elements(t->'widget-data-columns') WITH ORDINALITY AS x(c, ord)
         WHERE s."section_id" = section;
        IF keys[array_position(keys, 'land_id') - 1] IS DISTINCT FROM 'is_land_recorded'
           OR keys[array_position(keys, 'land_id') + 1] IS DISTINCT FROM 'is_plot_not_registered'
           OR keys[array_position(keys, 'cluster_land_id') - 1] IS DISTINCT FROM 'is_cluster_land_recorded'
           OR keys[array_position(keys, 'cluster_land_id') + 1] IS DISTINCT FROM 'cluster_region'
           OR NOT keys @> ARRAY['map_location', 'cluster_kebele', 'cluster_longitude'] THEN
            RAISE EXCEPTION 'Land recorded questions not in place in % (%)', section, keys;
        END IF;
    END LOOP;
END
$$;
