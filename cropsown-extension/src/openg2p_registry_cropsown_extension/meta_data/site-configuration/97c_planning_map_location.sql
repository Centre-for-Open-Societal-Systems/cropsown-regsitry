-- Crop planning rows take their position from a map, like the Crop location
-- section, instead of a typed "GPS coordinate".
--
-- Crop planning section (cropsown_planning_details_section_01), its table only:
-- the GPS coordinate column is removed, and two maps take its place:
--   after Kebele ("Land details"): Map location, Latitude, Longitude. A click
--     places the pin and fills the row's Latitude and Longitude, and Region, Zone
--     and Woreda from the woreda under the pin; the Kebele is still chosen.
--   after Expected yield ("Crop planned inputs"): Crop location, Crop latitude,
--     Crop longitude: the crop's own position, which fills nothing else.
-- Each map spans the row in the dialog; it is not a stored field (no column holds
-- "map_location" or "crop_map_location") and not shown in the table grid. The
-- latitude and longitude fields are filled by their map, or typed (which moves the
-- pin), and shown in the table grid. In a row the map draws no boxes of its own.
-- The widget reads the row's columns from "oan-row-paths"
-- (ui/staff-ui/overrides/src/oan/widgets/GeoPointWidget.tsx, table-row mode).
-- gps_coordinate stays in the database (retired in
-- reference/metadata-transitions.json); latitude, longitude, crop_latitude and
-- crop_longitude are new columns of the planning model.
--
-- The six columns are taken out wherever they stand and written again in place,
-- so a database where an earlier version of this file placed them elsewhere ends
-- up the same. A second run changes nothing. Sorts after
-- 97b_cascading_location.sql, which marks the same table's Zone, Woreda and Kebele.
CREATE OR REPLACE FUNCTION pg_temp.planning_map_location(node jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    result jsonb;
    columns jsonb := '[]'::jsonb;
    col jsonb;
    land_placed boolean := false;
    crop_placed boolean := false;
    land jsonb := jsonb_build_array(
        jsonb_build_object(
            'widget', 'oan-geo-point', 'widget-type', 'input', 'column-key', 'map_location',
            'column-group', 'Land details', 'widget-label', 'Map location', 'widget-readonly', false,
            'column-visible-in-table', false,
            'oan-row-paths', jsonb_build_object(
                'latitude', 'latitude', 'longitude', 'longitude',
                'levels', jsonb_build_object('l1', 'region', 'l2', 'zone', 'l3', 'woreda', 'l4', 'kebele')),
            'widget-data-format', jsonb_build_object(
                'bounds', '[[3.3, 32.9], [15.0, 48.1]]'::jsonb, 'height', 320, 'minZoom', 5,
                'boundaries', jsonb_build_object(
                    'url', '/api/master-data/geo-boundary?level=woreda',
                    'geoSource', jsonb_build_object(
                        'method', 'POST', 'service', 'master-data',
                        'levelsEndpoint', 'get-all-g2p-geo-levels', 'valuesEndpoint', 'geo-level-values')))),
        jsonb_build_object(
            'widget', 'text', 'widget-type', 'input', 'column-key', 'latitude', 'widget-data-path', 'latitude',
            'column-group', 'Land details', 'widget-label', 'Latitude', 'widget-readonly', false),
        jsonb_build_object(
            'widget', 'text', 'widget-type', 'input', 'column-key', 'longitude', 'widget-data-path', 'longitude',
            'column-group', 'Land details', 'widget-label', 'Longitude', 'widget-readonly', false));
    crop jsonb := jsonb_build_array(
        jsonb_build_object(
            'widget', 'oan-geo-point', 'widget-type', 'input', 'column-key', 'crop_map_location',
            'column-group', 'Crop planned inputs', 'widget-label', 'Crop location', 'widget-readonly', false,
            'column-visible-in-table', false,
            'oan-row-paths', jsonb_build_object('latitude', 'crop_latitude', 'longitude', 'crop_longitude'),
            'widget-data-format', jsonb_build_object(
                'bounds', '[[3.3, 32.9], [15.0, 48.1]]'::jsonb, 'height', 320, 'minZoom', 5)),
        jsonb_build_object(
            'widget', 'text', 'widget-type', 'input', 'column-key', 'crop_latitude', 'widget-data-path', 'crop_latitude',
            'column-group', 'Crop planned inputs', 'widget-label', 'Crop latitude', 'widget-readonly', false),
        jsonb_build_object(
            'widget', 'text', 'widget-type', 'input', 'column-key', 'crop_longitude', 'widget-data-path', 'crop_longitude',
            'column-group', 'Crop planned inputs', 'widget-label', 'Crop longitude', 'widget-readonly', false));
BEGIN
    IF jsonb_typeof(node) = 'array' THEN
        SELECT COALESCE(jsonb_agg(pg_temp.planning_map_location(value) ORDER BY ord), '[]'::jsonb)
          INTO result FROM jsonb_array_elements(node) WITH ORDINALITY AS a(value, ord);
        RETURN result;
    ELSIF jsonb_typeof(node) <> 'object' THEN
        RETURN node;
    END IF;
    IF jsonb_typeof(node->'widget-data-columns') = 'array'
       AND EXISTS (SELECT 1 FROM jsonb_array_elements(node->'widget-data-columns') c
                    WHERE c->>'column-key' IN ('gps_coordinate', 'map_location')) THEN
        FOR col IN SELECT value FROM jsonb_array_elements(node->'widget-data-columns') WITH ORDINALITY AS a(value, ord) ORDER BY ord LOOP
            -- the retired GPS column and the six columns (re-added below) are dropped here
            CONTINUE WHEN col->>'column-key' IN ('gps_coordinate', 'map_location', 'latitude', 'longitude',
                                                 'crop_map_location', 'crop_latitude', 'crop_longitude');
            columns := columns || jsonb_build_array(col);
            IF col->>'column-key' = 'kebele' THEN
                columns := columns || land;
                land_placed := true;
            ELSIF col->>'column-key' = 'expected_yield' THEN
                columns := columns || crop;
                crop_placed := true;
            END IF;
        END LOOP;
        IF NOT land_placed THEN
            columns := columns || land;
        END IF;
        IF NOT crop_placed THEN
            columns := columns || crop;
        END IF;
        RETURN node || jsonb_build_object('widget-data-columns', columns);
    END IF;
    SELECT COALESCE(jsonb_object_agg(key, pg_temp.planning_map_location(value)), '{}'::jsonb)
      INTO result FROM jsonb_each(node);
    RETURN result;
END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = pg_temp.planning_map_location("section_ui_schema"::jsonb)::json
 WHERE "section_id" = 'cropsown_planning_details_section_01';

DO $$
DECLARE keys text[];
BEGIN
    SELECT array_agg(c->>'column-key' ORDER BY ord)
      INTO keys
      FROM "public"."g2p_register_sections" s,
           jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-columns" != null)') t,
           jsonb_array_elements(t->'widget-data-columns') WITH ORDINALITY AS x(c, ord)
     WHERE s."section_id" = 'cropsown_planning_details_section_01';
    IF 'gps_coordinate' = ANY (keys)
       OR array_position(keys, 'map_location') IS DISTINCT FROM array_position(keys, 'kebele') + 1
       OR array_position(keys, 'latitude') IS DISTINCT FROM array_position(keys, 'map_location') + 1
       OR array_position(keys, 'longitude') IS DISTINCT FROM array_position(keys, 'latitude') + 1
       OR array_position(keys, 'crop_map_location') IS DISTINCT FROM array_position(keys, 'expected_yield') + 1
       OR array_position(keys, 'crop_latitude') IS DISTINCT FROM array_position(keys, 'crop_map_location') + 1
       OR array_position(keys, 'crop_longitude') IS DISTINCT FROM array_position(keys, 'crop_latitude') + 1 THEN
        RAISE EXCEPTION 'Crop planning maps not in place (after Kebele and after Expected yield): %', keys;
    END IF;
END
$$;
