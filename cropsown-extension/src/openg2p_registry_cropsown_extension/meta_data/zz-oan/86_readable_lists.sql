-- Readable lists: the words staff read in lists, tasks and field labels.
--
-- 1. Planning record names read "Maize, Meher 2026" instead of the stored codes,
--    and the commodity and season columns of the lists show Master Data words.
-- 2. Gender, change action, and the intake list's source and form status read as
--    words; the register name is sentence case.
-- 3. The Fayda number has one name everywhere: "Fayda FAN ID" for the 16-digit
--    number and "Fayda FIN" for the 12-digit one; the farmer status field is
--    "Farmer registry status".
-- 4. The four intake forms lose their numbering and their Title Case.
-- 5. The unclear planning labels say what they are.
--
-- Only display text and stored record names change. Widget ids, data paths,
-- codes, mnemonics ids and translation keys stay. Every statement names its rows
-- or matches the exact old text, so a second run changes nothing, and the file
-- sorts after the earlier overlays, so a fresh install gets the same result.
-- Fayda verification widgets are not touched: that belongs to the overlay that
-- removes them (70_no_fayda_verification_widget.sql).

-- Field labels. A label is replaced only inside the widget that holds the named
-- data path: a jsonb text keeps the label before the data path and no object
-- braces lie between them.
UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = regexp_replace(regexp_replace(regexp_replace(regexp_replace(
    section_ui_schema::text,
    '("widget-label": )"Is plot not registered\?"([^{}]*"widget-data-path": "is_plot_not_registered")', '\1"Plot is not yet registered"\2', 'g'),
    '("widget-label": )"Method"([^{}]*"widget-data-path": "water_source_method")', '\1"Water application method"\2', 'g'),
    '("widget-label": )"Frequency"([^{}]*"widget-data-path": "water_source_frequency")', '\1"Watering frequency"\2', 'g'),
    '("widget-label": )"Reference"([^{}]*"widget-data-path": "reference")', '\1"Cluster reference"\2', 'g')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c'
  AND "section_id" IN ('cropsown_planning_details_section_01', 'cropsown_cultivation_details_section_01',
                       'cropsown_cluster_details_section_01', 'cropsown_cultivation_cluster_details_section_01')
  AND (section_ui_schema::text ~ '"widget-label": "(Is plot not registered\?|Method|Frequency|Reference)"');

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = regexp_replace(regexp_replace(regexp_replace(
    section_ui_schema::text,
    '"widget-label": "(Fayda FAN \(16 digits\)|Fayda ID \(FAN\))"', '"widget-label": "Fayda FAN ID"', 'g'),
    '"widget-label": "Fayda FIN \(from verification\)"', '"widget-label": "Fayda FIN"', 'g'),
    '("widget-label": )"Farmer reference"([^{}]*"widget-data-path": "[^"]*farmer_reference_status")', '\1"Farmer registry status"\2', 'g')::jsonb
WHERE "register_id" IN ('6b06a95a-9a6c-5a33-a33d-c1625716c59c', 'fa120001-0000-4000-8000-000000000001')
  AND "section_id" IN ('cropsown_intake_record_section_01', 'cropsown_common_intake_record_section_01',
                       'cropsown_production_details_section_01', 'cropsown_cropsown_record_section_01',
                       'cropsown_farmer_identity_section_01')
  AND (section_ui_schema::text ~ '"widget-label": "(Fayda FAN \(16 digits\)|Fayda ID \(FAN\)|Fayda FIN \(from verification\)|Farmer reference)"');

-- The search and filter label of the Fayda FAN ID column.
UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace("search_result_schema"::jsonb::text, '"display_label": "Fayda ID (FAN)"', '"display_label": "Fayda FAN ID"')::json
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "search_result_schema"::text LIKE '%"Fayda ID (FAN)"%';

UPDATE "public"."g2p_register_schemas"
SET "filter_schema" = replace("filter_schema"::jsonb::text, '"display_label": "Fayda ID (FAN)"', '"display_label": "Fayda FAN ID"')::json
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "filter_schema"::text LIKE '%"Fayda ID (FAN)"%';

-- Intake form names. The picker, the task list and the ingestion list show the
-- name; forms already submitted are linked by form id, which does not change.
UPDATE "public"."g2p_intake_form_definitions" SET "form_mnemonic" = 'Crop planning intake'
WHERE "form_id" = '5bf0068c-ce19-46f8-874c-7147997f793b' AND "form_mnemonic" <> 'Crop planning intake';
UPDATE "public"."g2p_intake_form_definitions" SET "form_mnemonic" = 'Crop cultivation intake'
WHERE "form_id" = '6be15ab9-0f1b-4c38-995f-395d52a1b17a' AND "form_mnemonic" <> 'Crop cultivation intake';
UPDATE "public"."g2p_intake_form_definitions" SET "form_mnemonic" = 'Crop sowing intake'
WHERE "form_id" = '4a7c2c98-0ffb-41d8-8fea-f22349823675' AND "form_mnemonic" <> 'Crop sowing intake';
UPDATE "public"."g2p_intake_form_definitions" SET "form_mnemonic" = 'Crop harvesting intake'
WHERE "form_id" = '52150a37-153d-496d-9cd9-2a3815d6e13b' AND "form_mnemonic" <> 'Crop harvesting intake';

-- Register name: sentence case, only where it still holds the seeded text.
UPDATE "public"."g2p_register_definitions" SET "register_subject" = 'Crop sown registry'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "register_subject" = 'Crop Sown Registry';

UPDATE "public"."g2p_registry_configuration" SET "registry_name" = 'Crop sown registry'
WHERE "configuration_id" = '9a3f5c21-77d4-4b6e-8f10-2c5b9d4e6a73' AND "registry_name" = 'Crop Sown Registry';

-- Display words. The staff portal looks a value up in the English domain
-- translations and falls back to the value itself, so the list columns show
-- these for the codes stored in the records. Master Data stays the source of
-- the dropdown labels; the commodity and season words below are the labels it
-- holds. CROP_TEFF reads "Teff" in lists.
UPDATE "public"."registry_languages"
SET "domain_translation" = (COALESCE("domain_translation"::jsonb, '{}'::jsonb) ||
'{
 "ADD": "Add",
 "Crop Sown Registry": "Crop sown registry",
 "FEMALE": "Female",
 "FINAL": "Final",
 "Fayda ID (FAN)": "Fayda FAN ID",
 "Is Plot Not Registered?": "Plot is not yet registered",
 "MALE": "Male",
 "OTHER": "Other",
 "PARTNER": "Partner",
 "STAFF_PORTAL": "Staff portal",
 "UPDATE": "Update",
 "coss_field_fan_format": "{label}: enter exactly 16 digits, optionally separated by spaces. Use the Fayda FIN field for a 12-digit number.",
 "coss_field_fin_format": "{label}: enter exactly 12 digits. Use the Fayda FAN ID field for a 16-digit number.",
 "coss_input_fayda_fan_id": "Fayda FAN ID: enter exactly 16 digits, optionally separated by spaces. Use the Fayda FIN field for a 12-digit number.",
 "coss_input_fayda_fin": "Fayda FIN: enter exactly 12 digits. Use the Fayda FAN ID field for a 16-digit number.",
 "cropsown_intake": "Crop sown registry intake form",
 "cropsown_intake_tab": "Crop sown registry intake form",
 "cs_farmer_identity": "Farmer identity",
 "fayda_fan_id": "Fayda FAN ID",
 "link_foundational_id": "Fayda FAN ID",
 "CROP_ADZUKI_BEAN": "Adzuki bean",
 "CROP_AFRICAN_MARIGOLD": "African marigold",
 "CROP_ALFALFA": "Alfalfa",
 "CROP_AMARANTH": "Amaranth",
 "CROP_ANCHOTE": "Anchote",
 "CROP_AVOCADO": "Avocado",
 "CROP_BANANA": "Banana",
 "CROP_BARLEY": "Barley",
 "CROP_BASIL": "Basil",
 "CROP_BLACK_CUMIN": "Black cumin",
 "CROP_BLACK_PEPPER": "Black pepper",
 "CROP_BRACHIARIA": "Brachiaria",
 "CROP_BREAD_WHEAT": "Bread wheat",
 "CROP_BROCCOLI": "Broccoli",
 "CROP_BUCKWHEAT": "Buckwheat",
 "CROP_CABBAGE": "Cabbage",
 "CROP_CACAO": "Cacao",
 "CROP_CAMELINA": "Camelina",
 "CROP_CARDAMOM": "Cardamom",
 "CROP_CARROT": "Carrot",
 "CROP_CASSAVA": "Cassava",
 "CROP_CASTOR": "Castor",
 "CROP_CAULIFLOWER": "Cauliflower",
 "CROP_CHAMOMILE": "Chamomile",
 "CROP_CHICKPEA": "Chickpea",
 "CROP_CITRONELLA_GRASS": "Citronella grass",
 "CROP_COFFEE": "Coffee",
 "CROP_COMMON_BEAN": "Common bean",
 "CROP_CORIANDER": "Coriander",
 "CROP_COTTON": "Cotton",
 "CROP_COWPEA": "Cowpea",
 "CROP_CUCUMBER": "Cucumber",
 "CROP_DATE_PALM": "Date palm",
 "CROP_DEKOKO": "Dekoko",
 "CROP_DURUM_WHEAT": "Durum wheat",
 "CROP_EGGPLANT": "Eggplant",
 "CROP_EMMER_WHEAT": "Emmer wheat",
 "CROP_ENSET": "Enset",
 "CROP_ETHIOPIAN_MUSTARD": "Ethiopian mustard",
 "CROP_FABA_BEAN": "Faba bean",
 "CROP_FENUGREEK": "Fenugreek",
 "CROP_FIELD_PEA": "Field pea",
 "CROP_FIG": "Fig",
 "CROP_FINE_BUSH_BEAN": "Fine bush bean",
 "CROP_FINGER_MILLET": "Finger millet",
 "CROP_FOXTAIL_MILLET": "Foxtail millet",
 "CROP_GARLIC": "Garlic",
 "CROP_GERANIUM": "Geranium",
 "CROP_GINGER": "Ginger",
 "CROP_GRASS_PEA": "Grass pea",
 "CROP_GREEN_COURGETTE": "Green courgette",
 "CROP_GROUNDNUT": "Groundnut",
 "CROP_HARICOT_BEAN": "Haricot bean",
 "CROP_HIBISCUS": "Hibiscus",
 "CROP_JAPANESE_MINT": "Japanese mint",
 "CROP_KENAF": "Kenaf",
 "CROP_KORARIMA": "Korarima",
 "CROP_LAVENDER": "Lavender",
 "CROP_LEMONGRASS": "Lemongrass",
 "CROP_LEMON_SCENTED_EUCALYPTUS": "Lemon-scented eucalyptus",
 "CROP_LEMON_VERBENA": "Lemon verbena",
 "CROP_LENTIL": "Lentil",
 "CROP_LETTUCE": "Lettuce",
 "CROP_LIMA_BEAN": "Lima bean",
 "CROP_LINSEED": "Linseed",
 "CROP_MAIZE": "Maize",
 "CROP_MALT_BARLEY": "Malt barley",
 "CROP_MANGO": "Mango",
 "CROP_MARJORAM_OREGANO": "Marjoram / oregano",
 "CROP_MUNG_BEAN": "Mung bean",
 "CROP_MUSKMELON": "Muskmelon",
 "CROP_NOUG": "Noug",
 "CROP_OAT": "Oat",
 "CROP_OKRA": "Okra",
 "CROP_ONION": "Onion",
 "CROP_OTHER": "Other",
 "CROP_PAK_CHOI": "Pak choi",
 "CROP_PALMAROSA": "Palmarosa",
 "CROP_PAPAYA": "Papaya",
 "CROP_PEACH": "Peach",
 "CROP_PEARL_MILLET": "Pearl millet",
 "CROP_PEPPER": "Pepper",
 "CROP_PEPPERMINT": "Peppermint",
 "CROP_PIGEON_PEA": "Pigeon pea",
 "CROP_PINEAPPLE": "Pineapple",
 "CROP_POTATO": "Potato",
 "CROP_PYRETHRUM": "Pyrethrum",
 "CROP_QUINOA": "Quinoa",
 "CROP_RAPESEED": "Rapeseed",
 "CROP_RED_BEET": "Red beet",
 "CROP_RICE": "Rice",
 "CROP_ROSE": "Rose",
 "CROP_ROSEMARY": "Rosemary",
 "CROP_SAFFLOWER": "Safflower",
 "CROP_SAGE": "Sage",
 "CROP_SESAME": "Sesame",
 "CROP_SHALLOT": "Shallot",
 "CROP_SNAP_BEAN": "Snap bean",
 "CROP_SNAP_PEA": "Snap pea",
 "CROP_SNOW_PEA": "Snow pea",
 "CROP_SORGHUM": "Sorghum",
 "CROP_SOYBEAN": "Soybean",
 "CROP_SPANISH_MINT": "Spanish mint",
 "CROP_SPEARMINT": "Spearmint",
 "CROP_STEVIA": "Stevia",
 "CROP_SUGARCANE": "Sugarcane",
 "CROP_SUMMER_SQUASH": "Summer squash",
 "CROP_SUNFLOWER": "Sunflower",
 "CROP_SWEET_ANNIE": "Sweet annie",
 "CROP_SWEET_CORN": "Sweet corn",
 "CROP_SWEET_POTATO": "Sweet potato",
 "CROP_TARO": "Taro",
 "CROP_TEFF": "Teff",
 "CROP_TOBACCO": "Tobacco",
 "CROP_TOMATO": "Tomato",
 "CROP_TRITICALE": "Triticale",
 "CROP_TURMERIC": "Turmeric",
 "CROP_VANILLA": "Vanilla",
 "CROP_VERNONIA": "Vernonia",
 "CROP_WATERMELON": "Watermelon",
 "CROP_WHITE_CUMIN": "White cumin",
 "CROP_WINE_GRAPE": "Wine grape",
 "CROP_YAM": "Yam",
 "CROP_YELLOW_COURGETTE": "Yellow courgette",
 "CROP_ZIZIPHUS": "Ziziphus",
 "SEASON_BELG": "Belg (short rains)",
 "SEASON_IRRIGATION": "Irrigation (dry season)",
 "SEASON_MEHER": "Meher (main rains)"
}'::jsonb)::json
WHERE "language_code" = 'en';

-- Planning record names stored before the change read "CROP_MAIZE SEASON_MEHER 1.5".
-- This rewrites them to the words the code now gives new records
-- (register_domain/services/plain_text.py, planning_record_name): the crop, the
-- season with the year of the planned date, then the planned area in hectares.
-- Only a name that still starts with its stored code is rewritten, so a second
-- run changes nothing. The intake form table keeps its application reference.
CREATE OR REPLACE FUNCTION pg_temp.list_code_words(code text, prefixes text[]) RETURNS text AS $$
DECLARE
    t text := btrim(coalesce(code, ''));
    prefix text;
    words text;
BEGIN
    IF t !~ '^[A-Z0-9]+(_[A-Z0-9]+)+$' THEN
        RETURN t;
    END IF;
    FOREACH prefix IN ARRAY prefixes LOOP
        IF left(t, length(prefix)) = prefix AND length(t) > length(prefix) THEN
            t := substr(t, length(prefix) + 1);
            EXIT;
        END IF;
    END LOOP;
    words := lower(replace(t, '_', ' '));
    RETURN upper(left(words, 1)) || substr(words, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION pg_temp.planning_name(commodity text, season text, planned_date date, planned_area numeric) RETURNS text AS $$
DECLARE
    crop text := CASE btrim(coalesce(commodity, ''))
        WHEN 'CROP_MARJORAM_OREGANO' THEN 'Marjoram / oregano'
        WHEN 'CROP_LEMON_SCENTED_EUCALYPTUS' THEN 'Lemon-scented eucalyptus'
        ELSE pg_temp.list_code_words(commodity, ARRAY['CROP_']) END;
    season_words text := pg_temp.list_code_words(season, ARRAY['CROP_SEASON_', 'SEASON_']);
    area text := CASE WHEN planned_area IS NULL THEN '' ELSE trim_scale(planned_area)::text || ' hectares' END;
BEGIN
    IF season_words <> '' AND planned_date IS NOT NULL THEN
        season_words := season_words || ' ' || to_char(planned_date, 'YYYY');
    END IF;
    RETURN concat_ws(', ', NULLIF(crop, ''), NULLIF(season_words, ''), NULLIF(area, ''));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

DO $$
DECLARE
    tbl text;
    required text[] := ARRAY['record_name', 'commodity', 'season', 'planned_date', 'planned_area'];
    reference_suffix text;
BEGIN
    FOREACH tbl IN ARRAY ARRAY['g2p_register_plannings', 'g2p_register_history_plannings', 'g2p_intake_form_plannings'] LOOP
        CONTINUE WHEN to_regclass(format('public.%I', tbl)) IS NULL;
        CONTINUE WHEN (SELECT count(*) FROM information_schema.columns c
                       WHERE c.table_schema = 'public' AND c.table_name = tbl AND c.column_name = ANY (required)) <> 5;
        reference_suffix := '';
        IF EXISTS (SELECT 1 FROM information_schema.columns c
                   WHERE c.table_schema = 'public' AND c.table_name = tbl AND c.column_name = 'application_reference') THEN
            reference_suffix := ' || CASE WHEN coalesce(application_reference, '''') = '''' THEN '''' ELSE '' '' || application_reference END';
        END IF;
        EXECUTE format(
            'UPDATE public.%1$I SET record_name = pg_temp.planning_name(commodity, season, planned_date, planned_area)%2$s'
            ' WHERE coalesce(nullif(btrim(commodity), ''''), nullif(btrim(season), '''')) ~ ''^[A-Z0-9]+(_[A-Z0-9]+)+$'''
            ' AND (record_name = coalesce(nullif(btrim(commodity), ''''), nullif(btrim(season), ''''))'
            ' OR left(record_name, length(coalesce(nullif(btrim(commodity), ''''), nullif(btrim(season), ''''))) + 1)'
            '    = coalesce(nullif(btrim(commodity), ''''), nullif(btrim(season), '''')) || '' '')',
            tbl, reference_suffix);
    END LOOP;
END;
$$;
