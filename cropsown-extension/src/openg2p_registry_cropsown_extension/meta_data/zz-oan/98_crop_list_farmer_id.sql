-- Add farmer_id column to the Crop Sown register search result schema
UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = '[{"field_name": "farmer_id", "display_label": "Farmer ID", "order": 1}, {"field_name": "fayda_fan_id", "display_label": "Fayda FAN ID", "order": 2}, {"field_name": "region_name", "display_label": "Region", "order": 3}, {"field_name": "zone_name", "display_label": "Zone", "order": 4}, {"field_name": "woreda_name", "display_label": "Woreda", "order": 5}, {"field_name": "kebele_name", "display_label": "Kebele", "order": 6}, {"field_name": "crop_year", "display_label": "Crop year", "order": 7}, {"field_name": "status", "display_label": "Status", "order": 8}]'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c';
