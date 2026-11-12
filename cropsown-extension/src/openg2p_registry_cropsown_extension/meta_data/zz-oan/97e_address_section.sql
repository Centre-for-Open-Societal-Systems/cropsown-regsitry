-- The crop record's location section is the farmer's address, from the Farmer
-- Registry, like the farmer's name.
--
-- Section cropsown_cropsown_location_section_03 (Farmer details tab):
--   * titled "Address" instead of "Crop location";
--   * read-only: no Edit Details, and the location picker and the map do not
--     take input. farmer_reference/projection.py fills region, zone, woreda,
--     kebele (and their names), the location hierarchy, latitude and longitude
--     from the approved Farmer when the record is written;
--   * no longer on the Planning intake form, which therefore does not ask for it
--     (ODK and file import stopped sending it; their farmer lookup keeps the
--     location, used when the Farmer has no address).
-- The plot's own location (the Planning rows' Region to Kebele and Map location)
-- is unchanged.
--
-- A second run changes nothing.
CREATE OR REPLACE FUNCTION pg_temp.address_section_readonly(node jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE jsonb_typeof(node)
        WHEN 'object' THEN
            CASE
                WHEN node->>'widget' IN ('geo-hierarchy', 'oan-geo-point')
                    THEN node || '{"widget-readonly": true}'::jsonb
                ELSE (SELECT COALESCE(jsonb_object_agg(key, pg_temp.address_section_readonly(value)), '{}'::jsonb)
                        FROM jsonb_each(node))
            END
        WHEN 'array' THEN (
            SELECT COALESCE(jsonb_agg(pg_temp.address_section_readonly(element) ORDER BY position), '[]'::jsonb)
              FROM jsonb_array_elements(node) WITH ORDINALITY AS item(element, position))
        ELSE node
    END
$$;

UPDATE "public"."g2p_register_sections"
   SET "section_ui_schema" = (pg_temp.address_section_readonly("section_ui_schema"::jsonb)
                              || '{"section-title": "Address", "section-editable": false}'::jsonb)::json,
       "section_description" = 'Address'
 WHERE "section_id" = 'cropsown_cropsown_location_section_03';

DELETE FROM "public"."g2p_intake_form_ui_tab_sections"
 WHERE "section_id" = 'cropsown_cropsown_location_section_03';

-- Close the gap the Address left: each intake tab's sections are numbered 1, 2, 3, ...
-- in the order they already have.
UPDATE "public"."g2p_intake_form_ui_tab_sections" t
   SET "section_order" = r.position
  FROM (SELECT "tab_section_id",
               row_number() OVER (PARTITION BY "tab_id" ORDER BY "section_order", "tab_section_id") AS position
          FROM "public"."g2p_intake_form_ui_tab_sections") r
 WHERE t."tab_section_id" = r."tab_section_id"
   AND t."section_order" IS DISTINCT FROM r.position;

DO $$
DECLARE problem text;
BEGIN
    SELECT CASE
             WHEN s."section_ui_schema"::jsonb->>'section-title' <> 'Address' THEN 'title'
             WHEN (s."section_ui_schema"::jsonb->>'section-editable')::boolean THEN 'editable'
             WHEN EXISTS (SELECT 1 FROM jsonb_path_query(s."section_ui_schema"::jsonb,
                                  'strict $.** ? (@."widget" == "geo-hierarchy" || @."widget" == "oan-geo-point")') w
                           WHERE COALESCE((w->>'widget-readonly')::boolean, false) IS NOT TRUE) THEN 'input widget'
             WHEN EXISTS (SELECT 1 FROM "public"."g2p_intake_form_ui_tab_sections"
                           WHERE "section_id" = 'cropsown_cropsown_location_section_03') THEN 'on an intake form'
           END
      INTO problem
      FROM "public"."g2p_register_sections" s
     WHERE s."section_id" = 'cropsown_cropsown_location_section_03';
    IF problem IS NOT NULL THEN
        RAISE EXCEPTION 'Address section not in place: %', problem;
    END IF;
END
$$;
