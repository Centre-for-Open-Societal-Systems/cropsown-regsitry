-- Cultivation rows ask "Is planning record created?" and take the land details only
-- when they were not given in Planning.
--
-- Cultivation section (cropsown_cultivation_details_section_01), its table only:
--   Is planning record created?  first in the row; Yes stores true, No false.
--   Yes (or not answered: older rows, ODK, file import): only Land ID and Total land
--       area, as before. On save, a Yes is checked against this farmer's Planning
--       rows of the same crop year and season (g2p_register_domain_service_cultivation.py).
--   No: also Is plot registered?, Plot category, Ownership type, Soil fertility,
--       Region, Zone, Woreda, Kebele, Map location, Latitude and Longitude, copied
--       from the Crop planning table (so the Master Data lists, the cascade of
--       97b_cascading_location.sql and the map of 97c_planning_map_location.sql are
--       the same), each shown only when the answer is No.
--   Always (whatever the answer): Crop location map, Crop latitude and Crop longitude
--       after Actual crop area, copied from the Crop planning table.
-- A hidden field is not saved, so a Yes row keeps only Land ID and land area.
-- Not required yet: ODK and file import do not send the answer.
--
-- The added columns are taken out and written again on every run, so a second run
-- changes nothing. Sorts after 97c, whose Planning columns it copies.
CREATE OR REPLACE FUNCTION pg_temp.cultivation_land_details(node jsonb, planning jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    result jsonb;
    columns jsonb := '[]'::jsonb;
    col jsonb;
    key text;
    asked boolean := false;
    when_no jsonb := '{"widget-data-options": {"action": "show", "condition":
                       {"field": "is_planning_record_created", "operator": "equals", "value": false}}}'::jsonb;
    question jsonb := jsonb_build_object(
        'widget', 'select', 'widget-type', 'input', 'column-key', 'is_planning_record_created',
        'column-group', 'Land details', 'widget-label', 'Is planning record created?', 'widget-readonly', false,
        'widget-data-path', 'is_planning_record_created',
        'widget-data-source', jsonb_build_object('type', 'static', 'options', jsonb_build_array(
            jsonb_build_object('label', 'Yes', 'value', true),
            jsonb_build_object('label', 'No', 'value', false))));
    added text[] := ARRAY['is_planning_record_created', 'plot_category', 'ownership_type', 'soil_fertility_type',
                          'region', 'zone', 'woreda', 'kebele', 'map_location', 'latitude', 'longitude',
                          'crop_map_location', 'crop_latitude', 'crop_longitude'];
BEGIN
    IF jsonb_typeof(node) = 'array' THEN
        SELECT COALESCE(jsonb_agg(pg_temp.cultivation_land_details(value, planning) ORDER BY ord), '[]'::jsonb)
          INTO result FROM jsonb_array_elements(node) WITH ORDINALITY AS a(value, ord);
        RETURN result;
    ELSIF jsonb_typeof(node) <> 'object' THEN
        RETURN node;
    END IF;
    IF jsonb_typeof(node->'widget-data-columns') = 'array'
       AND EXISTS (SELECT 1 FROM jsonb_array_elements(node->'widget-data-columns') c WHERE c->>'column-key' = 'land_id') THEN
        FOR col IN SELECT value FROM jsonb_array_elements(node->'widget-data-columns') WITH ORDINALITY AS a(value, ord) ORDER BY ord LOOP
            CONTINUE WHEN col->>'column-key' = ANY (added);
            IF NOT asked THEN
                columns := columns || jsonb_build_array(question);
                asked := true;
            END IF;
            IF col->>'column-key' = 'is_plot_not_registered' THEN
                columns := columns || jsonb_build_array(col || when_no);
            ELSE
                columns := columns || jsonb_build_array(col);
            END IF;
            IF col->>'column-key' = 'land_id' THEN
                FOREACH key IN ARRAY ARRAY['plot_category', 'ownership_type'] LOOP
                    IF planning ? key THEN columns := columns || jsonb_build_array((planning->key) || when_no); END IF;
                END LOOP;
            ELSIF col->>'column-key' = 'land_area' THEN
                FOREACH key IN ARRAY ARRAY['soil_fertility_type', 'region', 'zone', 'woreda', 'kebele',
                                           'map_location', 'latitude', 'longitude'] LOOP
                    IF planning ? key THEN columns := columns || jsonb_build_array((planning->key) || when_no); END IF;
                END LOOP;
            ELSIF col->>'column-key' = 'actual_crop_area' THEN
                -- the crop's own location: shown on every row
                FOREACH key IN ARRAY ARRAY['crop_map_location', 'crop_latitude', 'crop_longitude'] LOOP
                    IF planning ? key THEN columns := columns || jsonb_build_array(planning->key); END IF;
                END LOOP;
            END IF;
        END LOOP;
        RETURN node || jsonb_build_object('widget-data-columns', columns);
    END IF;
    SELECT COALESCE(jsonb_object_agg(k, pg_temp.cultivation_land_details(v, planning)), '{}'::jsonb)
      INTO result FROM jsonb_each(node) AS e(k, v);
    RETURN result;
END
$$;

DO $$
DECLARE
    planning jsonb;
    keys text[];
    missing text;
BEGIN
    -- the Crop planning table's columns, by column key
    SELECT jsonb_object_agg(c->>'column-key', c)
      INTO planning
      FROM "public"."g2p_register_sections" s,
           jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-columns" != null)') t,
           jsonb_array_elements(t->'widget-data-columns') c
     WHERE s."section_id" = 'cropsown_planning_details_section_01';
    IF planning IS NULL THEN
        RAISE EXCEPTION 'Crop planning table not found';
    END IF;

    UPDATE "public"."g2p_register_sections"
       SET "section_ui_schema" = pg_temp.cultivation_land_details("section_ui_schema"::jsonb, planning)::json
     WHERE "section_id" = 'cropsown_cultivation_details_section_01';

    SELECT array_agg(c->>'column-key' ORDER BY ord)
      INTO keys
      FROM "public"."g2p_register_sections" s,
           jsonb_path_query(s."section_ui_schema"::jsonb, 'strict $.** ? (@."widget-data-columns" != null)') t,
           jsonb_array_elements(t->'widget-data-columns') WITH ORDINALITY AS x(c, ord)
     WHERE s."section_id" = 'cropsown_cultivation_details_section_01';
    SELECT string_agg(k, ', ') INTO missing
      FROM unnest(ARRAY['is_planning_record_created', 'is_plot_not_registered', 'land_id', 'plot_category',
                        'ownership_type', 'land_area', 'soil_fertility_type', 'region', 'zone', 'woreda',
                        'kebele', 'map_location', 'latitude', 'longitude',
                        'crop_map_location', 'crop_latitude', 'crop_longitude']) k
     WHERE NOT k = ANY (keys);
    IF missing IS NOT NULL OR keys[1] <> 'is_planning_record_created' THEN
        RAISE EXCEPTION 'Cultivation land details not in place (missing: %, first: %)', missing, keys[1];
    END IF;
END
$$;
