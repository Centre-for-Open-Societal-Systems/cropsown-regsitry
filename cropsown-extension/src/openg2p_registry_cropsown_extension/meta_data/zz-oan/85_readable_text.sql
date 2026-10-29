-- Readable text: everything staff read in the Crop Sown registry is plain English.
-- Sentence case, no underscores or internal keys, no unexplained abbreviations:
-- dates say Gregorian or Ethiopian instead of GC and EC, "DA" is "Development
-- agent", "FPC" is "Farmer production cluster", areas say hectares, the local
-- timad unit is explained, and the raw codes YES, NO and OTHER become Yes, No
-- and Other. Validation messages (name, date and format rules), register
-- names, search and filter labels, and the intake form tab names that had no
-- text at all are covered too.
--
-- Only display text changes; widget ids, column keys, data paths, codes,
-- mnemonics and translation keys stay as they are. Every statement is an
-- explicit-id UPDATE (or a merge of named translation keys), so it is
-- idempotent: a plain upgrade applies it to databases that hold the older text,
-- and it sorts after the casing overlay, so it also wins on a fresh install.

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "Total Land Area (ha)"', '"widget-label": "Total land area (hectares)"'), '"widget-label": "Start GC"', '"widget-label": "Start date (Gregorian)"'), '"widget-label": "End GC"', '"widget-label": "End date (Gregorian)"'), '"widget-label": "Planned date (GC)"', '"widget-label": "Planned date (Gregorian)"'), '"widget-data-placeholder": "dd_mm_yyyy"', '"widget-data-placeholder": "Day/month/year"'), '"widget-label": "Planned date (EC)"', '"widget-label": "Planned date (Ethiopian)"'), '"widget-label": "Planned crop area (ha)"', '"widget-label": "Planned crop area (hectares)"'), '"widget-label": "DA Name"', '"widget-label": "Development agent name"'), '"widget-label": "DA Mobile Number"', '"widget-label": "Development agent mobile number"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_planning_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "Total Land Area (ha)"', '"widget-label": "Total land area (hectares)"'), '"widget-label": "Start GC"', '"widget-label": "Start date (Gregorian)"'), '"widget-label": "End GC"', '"widget-label": "End date (Gregorian)"'), '"widget-label": "Actual cultivation date (GC)"', '"widget-label": "Actual cultivation date (Gregorian)"'), '"widget-data-placeholder": "dd_mm_yyyy"', '"widget-data-placeholder": "Day/month/year"'), '"widget-label": "Actual cultivation date (EC)"', '"widget-label": "Actual cultivation date (Ethiopian)"'), '"widget-label": "Actual Crop Area (ha)"', '"widget-label": "Actual crop area (hectares)"'), '"widget-label": "DA Name"', '"widget-label": "Development agent name"'), '"widget-label": "DA Mobile Number"', '"widget-label": "Development agent mobile number"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cultivation_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "FPC name"', '"widget-label": "Farmer production cluster name"'), '"widget-label": "Start GC"', '"widget-label": "Start date (Gregorian)"'), '"widget-label": "End GC"', '"widget-label": "End date (Gregorian)"'), '"widget-label": "Establishing date (GC)"', '"widget-label": "Establishing date (Gregorian)"'), '"widget-data-placeholder": "dd_mm_yyyy"', '"widget-data-placeholder": "Day/month/year"'), '"widget-label": "Establishing date (EC)"', '"widget-label": "Establishing date (Ethiopian)"'), '"widget-label": "Sub Kebele"', '"widget-label": "Sub-kebele"'), '"widget-label": "FPC type"', '"widget-label": "Farmer production cluster type"'), '"widget-label": "Total cultivated area (Timad)"', '"widget-label": "Total cultivated area (timad, a local unit of 0.25 hectares)"'), '"widget-label": "Total Cultivated Area (ha)"', '"widget-label": "Total cultivated area (hectares)"'), '"widget-label": "Actual plan (ha)"', '"widget-label": "Actual planned area (hectares)"'), '"widget-label": "Actual collected land (quintal)"', '"widget-label": "Actual collected land (hectares)"'), '"widget-label": "Actual collected quintal"', '"widget-label": "Actual quantity collected (quintal)"'), '"widget-label": "Actual collected by combiner (ha)"', '"widget-label": "Actual area collected by combine harvester (hectares)"'), '"widget-label": "DA Name"', '"widget-label": "Development agent name"'), '"widget-label": "DA Mobile Number"', '"widget-label": "Development agent mobile number"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cultivation_cluster_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "FPC name"', '"widget-label": "Farmer production cluster name"'), '"widget-label": "Area Harvested (ha)"', '"widget-label": "Area harvested (hectares)"'), '"widget-data-placeholder": "dd_mm_yyyy"', '"widget-data-placeholder": "Day/month/year"'), '"widget-label": "Yield (kg/ha)"', '"widget-label": "Yield (kg per hectare)"'), '"widget-label": "DA Name"', '"widget-label": "Development agent name"'), '"widget-label": "DA Mobile Number"', '"widget-label": "Development agent mobile number"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_harvest_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "FPC name"', '"widget-label": "Farmer production cluster name"'), '"widget-label": "Start GC"', '"widget-label": "Start date (Gregorian)"'), '"widget-label": "End GC"', '"widget-label": "End date (Gregorian)"'), '"widget-label": "Establishing date (GC)"', '"widget-label": "Establishing date (Gregorian)"'), '"widget-data-placeholder": "dd_mm_yyyy"', '"widget-data-placeholder": "Day/month/year"'), '"widget-label": "Establishing date (EC)"', '"widget-label": "Establishing date (Ethiopian)"'), '"widget-label": "Sub Kebele"', '"widget-label": "Sub-kebele"'), '"widget-label": "FPC type"', '"widget-label": "Farmer production cluster type"'), '"widget-label": "Total cultivated area (Timad)"', '"widget-label": "Total cultivated area (timad, a local unit of 0.25 hectares)"'), '"widget-label": "Total Cultivated Area (ha)"', '"widget-label": "Total cultivated area (hectares)"'), '"widget-label": "Plan (ha)"', '"widget-label": "Planned area (hectares)"'), '"widget-label": "Collected land (Quintial)"', '"widget-label": "Collected land (hectares)"'), '"widget-label": "Collected Quintal"', '"widget-label": "Quantity collected (quintal)"'), '"widget-label": "Collected by combiner (ha)"', '"widget-label": "Area collected by combine harvester (hectares)"'), '"widget-label": "DA Name"', '"widget-label": "Development agent name"'), '"widget-label": "DA Mobile Number"', '"widget-label": "Development agent mobile number"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cluster_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(section_ui_schema::text, '"label": "OTHER"', '"label": "Other"')::jsonb
WHERE "register_id" = 'fa120001-0000-4000-8000-000000000001' AND "section_id" = 'cropsown_farmer_identity_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "FPC name"', '"widget-label": "Farmer production cluster name"'), '"widget-label": "Total Cultivated Area (ha)"', '"widget-label": "Total cultivated area (hectares)"'), '"widget-label": "Area sown (ha) (cluster)"', '"widget-label": "Area sown, cluster (hectares)"'), '"label": "YES"', '"label": "Yes"'), '"label": "NO"', '"label": "No"'), '"widget-label": "Area Sown (ha)"', '"widget-label": "Area sown (hectares)"'), '"widget-label": "Sowing date (GC)"', '"widget-label": "Sowing date (Gregorian)"'), '"widget-label": "Sowing date (EC)"', '"widget-label": "Sowing date (Ethiopian)"'), '"widget-data-placeholder": "dd_mm_yyyy"', '"widget-data-placeholder": "Day/month/year"'), '"widget-label": "DA Name"', '"widget-label": "Development agent name"'), '"widget-label": "DA Mobile Number"', '"widget-label": "Development agent mobile number"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_sowing_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "FPC name"', '"widget-label": "Farmer production cluster name"'), '"widget-label": "Weedicides type"', '"widget-label": "Weedicide type"'), '"widget-label": "Weedicides name"', '"widget-label": "Weedicide name"'), '"widget-label": "Date of observation(GC)"', '"widget-label": "Date of observation (Gregorian)"'), '"widget-data-placeholder": "dd_mm_yyyy"', '"widget-data-placeholder": "Day/month/year"'), '"widget-label": "Date of observation(EC)"', '"widget-label": "Date of observation (Ethiopian)"'), '"widget-label": "Estimated crop damage (%) or (ha)"', '"widget-label": "Estimated crop damage (percent or hectares)"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_infestation_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(section_ui_schema::text, '"widget-label": "Geo latitude"', '"widget-label": "Latitude"'), '"widget-label": "Geo longitude"', '"widget-label": "Longitude"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cropsown_location_section_03';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Crop planning details'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_planning_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Survey personnel'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_survey_personnel_section_02';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Cultivation / land preparation details'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cultivation_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Harvest details'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_harvest_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Cluster information details'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cluster_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Farmer identity'
WHERE "register_id" = 'fa120001-0000-4000-8000-000000000001' AND "section_id" = 'cropsown_farmer_identity_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Sowing details'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_sowing_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Farmer identity'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cropsown_record_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Farmer identity'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_common_intake_record_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Infestation incident details'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_infestation_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_description" = 'Farmer identity'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_intake_record_section_01';

-- Display labels: English domain translations (plain words, sentence case)
UPDATE "public"."registry_languages"
SET "domain_translation" = (COALESCE("domain_translation"::jsonb, '{}'::jsonb) ||
'{
 "2_4_D": "2,4-D",
 "AGRO_CHEMICAL_PESTICIDE_ALUMINIUM_PHOSPHIDE": "Aluminium phosphide",
 "AGRO_CHEMICAL_PESTICIDE_BORDEAUX_MIXTURE": "Bordeaux mixture",
 "AGRO_CHEMICAL_PESTICIDE_COPPER_HYDROXIDE": "Copper hydroxide",
 "AGRO_CHEMICAL_PESTICIDE_COPPER_OXYCHLORIDE": "Copper oxychloride",
 "AGRO_CHEMICAL_PESTICIDE_COPPER_SULPHATE": "Copper sulphate",
 "AGRO_CHEMICAL_PESTICIDE_IRON_PHOSPHATE": "Iron phosphate",
 "AGRO_CHEMICAL_PESTICIDE_NEEM_OIL": "Neem oil",
 "AGRO_CHEMICAL_PESTICIDE_SALICYLIC_ACID": "Salicylic acid",
 "AGRO_CHEMICAL_PESTICIDE_ZINC_PHOSPHIDE": "Zinc phosphide",
 "AGRO_CHEMICAL_WEEDICIDE_2_4_D_AMINE": "2,4-D amine",
 "AGRO_CHEMICAL_WEEDICIDE_2_4_D_METSULFURON": "2,4-D + metsulfuron",
 "AGRO_CHEMICAL_WEEDICIDE_BISPYRIBAC_SODIUM": "Bispyribac sodium",
 "AGRO_CHEMICAL_WEEDICIDE_COPPER_SULPHATE": "Copper sulphate",
 "AGRO_CHEMICAL_WEEDICIDE_HALOSULFURON_METHYL": "Halosulfuron methyl",
 "AGRO_CHEMICAL_WEEDICIDE_METSULFURON_METHYL": "Metsulfuron methyl",
 "APPROVAL_STATUS_APPROVAL_LEVEL_1": "Approval level 1",
 "APPROVAL_STATUS_APPROVAL_LEVEL_2": "Approval level 2",
 "APPROVAL_STATUS_UPDATE_REQUESTED": "Update requested",
 "Actual Collected Land (Quintal)": "Actual collected land (hectares)",
 "Actual Collected Quintal": "Actual quantity collected (quintal)",
 "Actual Collected by Combiner (ha)": "Actual area collected by combine harvester (hectares)",
 "Actual Crop Area (ha)": "Actual crop area (hectares)",
 "Actual Crop Name": "Actual crop name",
 "Actual Cultivated Date": "Actual cultivated date",
 "Actual Cultivated Date (EC)": "Actual cultivated date (Ethiopian)",
 "Actual Cultivated Date (GC)": "Actual cultivated date (Gregorian)",
 "Actual Cultivation Date (EC)": "Actual cultivation date (Ethiopian)",
 "Actual Cultivation Date (GC)": "Actual cultivation date (Gregorian)",
 "Actual Plan (ha)": "Actual planned area (hectares)",
 "Add Cultivation Cluster": "Add cultivation cluster",
 "Address Details": "Address details",
 "Area Harvested (ha)": "Area harvested (hectares)",
 "Area Sown (ha)": "Area sown (hectares)",
 "Area Sown (ha) (Cluster)": "Area sown, cluster (hectares)",
 "Area Under Production (ha)": "Area under production (hectares)",
 "Average Growth Duration (days)": "Average growth duration (days)",
 "CROP_SEASON_BEGA": "Bega",
 "Climate Shock": "Climate shock",
 "Cluster / Non Cluster Status": "Cluster / non cluster status",
 "Cluster Details": "Cluster details",
 "Cluster Metrics": "Cluster metrics",
 "Collected Land (Quintial)": "Collected land (hectares)",
 "Collected Land (ha)": "Collected land (hectares)",
 "Collected Quintal": "Quantity collected (quintal)",
 "Collected by Combiner (ha)": "Area collected by combine harvester (hectares)",
 "Crop Details": "Crop details",
 "Crop Planned Inputs": "Crop planned inputs",
 "Crop Year": "Crop year",
 "Cultivation Cluster Information": "Cultivation cluster information",
 "Cultivation Cluster Information Details": "Cultivation cluster information details",
 "Cultivation Date (EC)": "Cultivation date (Ethiopian)",
 "Cultivation Date (GC)": "Cultivation date (Gregorian)",
 "Cultivation Details": "Cultivation details",
 "CultivationCluster": "Cultivation cluster information",
 "DA Mobile Number": "Development agent mobile number",
 "DA Name": "Development agent name",
 "DEBO_JIGI": "Debo / Jigi",
 "Damage Metrics": "Damage metrics",
 "Date of Observation(EC)": "Date of observation (Ethiopian)",
 "Date of Observation(GC)": "Date of observation (Gregorian)",
 "Disease Name": "Disease name",
 "Disease Type": "Disease type",
 "Edit Cultivation Cluster": "Edit cultivation cluster",
 "End Day": "End day",
 "End GC": "End date (Gregorian)",
 "End Month": "End month",
 "Estimated Crop Damage (%) or (ha)": "Estimated crop damage (percent or hectares)",
 "Expected Yield (quintals)": "Expected yield (quintals)",
 "FERTILIZER_TYPE_BIO": "Bio fertilizer",
 "Farmer Name": "Farmer name",
 "Fertilizer/Amendment Name": "Fertilizer/amendment name",
 "Fertilizer/Amendment Type": "Fertilizer/amendment type",
 "Frequency of Application": "Frequency of application",
 "Fungicide/Bactericide Name": "Fungicide/bactericide name",
 "Fungicide/Bactericide Type": "Fungicide/bactericide type",
 "GPS Location": "GPS location",
 "INFESTATION_TYPE_CLIMATE": "Climate shock",
 "INFESTATION_TYPE_NUTRIENT": "Nutrient deficiency",
 "Incident Record ID": "Incident record ID",
 "Is Plot Not Registered?": "Is plot not registered?",
 "LAND_PREP_METHOD_BIOLOGICAL_MULCHING": "Biological mulching",
 "LAND_PREP_METHOD_MANUAL_DIGGING": "Manual digging",
 "LAND_PREP_METHOD_MINIMUM_TILLAGE": "Minimum tillage",
 "LAND_PREP_METHOD_RIDGING_FURROWING": "Ridging / furrowing",
 "LAND_PREP_METHOD_SOIL_WATER_CONSERVATION_STRUCTURES": "Soil & water conservation structures",
 "LAND_PREP_METHOD_TRACTOR_DISC_MOLDBOARD_PLOUGHING": "Tractor disc/moldboard ploughing",
 "LAND_PREP_METHOD_TRADITIONAL_MARESHA_PLOUGHING": "Traditional Maresha ploughing",
 "Land Details": "Land details",
 "Land Utilization Rate": "Land utilization rate",
 "Location Details": "Location details",
 "Location Hierarchy": "Location hierarchy",
 "MACHINERY_COMBINE_HARVESTER": "Combine harvester",
 "MACHINERY_EQUINE_OTHER": "Equine/other animals",
 "MACHINERY_FAMILY_LABOR": "Family labor",
 "MACHINERY_HIRED_LABOR": "Hired labor",
 "MACHINERY_MULTI_CROP_TRASHER": "Multi-crop trasher",
 "MACHINERY_OXEN_MANUAL": "Oxen ploughing + manual row seeding",
 "MACHINERY_OXEN_TILLAGE": "Oxen tillage",
 "MACHINERY_POWER_TILLER": "Power tiller",
 "MACHINERY_THRASHING_MACHINE": "Thrashing machine",
 "MACHINERY_TRACTOR_OXEN": "Tractor primary tillage + oxen secondary tillage",
 "MACHINERY_TRACTOR_PLOUGHING": "Tractor ploughing",
 "Method of Control (Climate)": "Method of control (climate)",
 "Method of Control (Disease)": "Method of control (disease)",
 "Method of Control (Nutrient)": "Method of control (nutrient)",
 "Method of Control (Pest)": "Method of control (pest)",
 "Method of Control (Weed)": "Method of control (weed)",
 "NO": "No",
 "NOT_YET_READY_FOR_HARVEST": "Not yet ready for harvest",
 "Nutrient Deficiency": "Nutrient deficiency",
 "Nutrient Name": "Nutrient name",
 "Nutrient Type": "Nutrient type",
 "OWNERSHIP_TYPE_CROP_SHARING": "Crop sharing",
 "OWNERSHIP_TYPE_FAMILY_GIFT": "Family gift",
 "PEST_LEAFHOPPER_JASSIDS": "Leafhopper (jassids)",
 "PLOT_CATEGORY_ANNUAL_CROP": "Annual crop",
 "PLOT_CATEGORY_BIENNIAL_CROP": "Biennial crop",
 "PLOT_CATEGORY_PERENNIAL_CROP": "Perennial crop",
 "Pest Name": "Pest name",
 "Pest Type": "Pest type",
 "Pesticide Name": "Pesticide name",
 "Pesticide Type": "Pesticide type",
 "Plan (ha)": "Planned area (hectares)",
 "Planned Area (ha)": "Planned area (hectares)",
 "Planned Crop Area (ha)": "Planned crop area (hectares)",
 "Planned Date (EC)": "Planned date (Ethiopian)",
 "Planned Date (GC)": "Planned date (Gregorian)",
 "Production Result": "Production result",
 "Production Season": "Production season",
 "Production Summary": "Production summary",
 "Recovery Input Name": "Recovery input name",
 "Recovery Input Type": "Recovery input type",
 "Season (Cluster)": "Season (cluster)",
 "Season Details": "Season details",
 "Seed Details": "Seed details",
 "Seed Planned Inputs": "Seed planned inputs",
 "Shock Event Name/Description": "Shock event name/description",
 "Shock Type": "Shock type",
 "Sowing Date (EC)": "Sowing date (Ethiopian)",
 "Sowing Date (GC)": "Sowing date (Gregorian)",
 "Start Day": "Start day",
 "Start GC": "Start date (Gregorian)",
 "Start Month": "Start month",
 "Sub Kebele": "Sub-kebele",
 "TIMAD": "Timad (0.25 hectares)",
 "Total Cultivated Area (Timad)": "Total cultivated area (timad, a local unit of 0.25 hectares)",
 "Total Cultivated Area (ha)": "Total cultivated area (hectares)",
 "Total Land Area (ha)": "Total land area (hectares)",
 "Type of Infestation": "Type of infestation",
 "WATER_SOURCE_FREQUENCY_AS_NEEDED": "As needed",
 "WATER_SOURCE_IRRIGATION_GROUND": "Irrigation - ground water",
 "WATER_SOURCE_IRRIGATION_SURFACE": "Irrigation - surface water",
 "WATER_SOURCE_METHOD_SURFACE": "Surface / flood",
 "WATER_SOURCE_SURFACE_WATER": "Surface water",
 "WATER_SOURCE_WATER_HARVESTING": "Water harvesting",
 "WATER_SOURCE_WELL_WATER": "Well water (groundwater)",
 "WEED_KHARIF_SUMMER": "Kharif / summer",
 "WEED_RABI_WINTER": "Rabi / winter",
 "Water Details": "Water details",
 "Water Source Details": "Water source details",
 "Weed Name": "Weed name",
 "Weed Type": "Weed type",
 "Weedicides Name": "Weedicide name",
 "Weedicides Type": "Weedicide type",
 "YES": "Yes",
 "Yield (kg/ha)": "Yield (kg per hectare)",
 "Yield Performance (%)": "Yield performance (%)",
 "Yield per Hectare (quintal/ha)": "Yield per hectare (quintal per hectare)",
 "actual_crop_area": "Actual crop area (hectares)",
 "area_harvested": "Area harvested (hectares)",
 "area_sown": "Area sown (hectares)",
 "area_under_production": "Area under production (hectares)",
 "cluster_area_hectare": "Total cultivated area (hectares)",
 "collected_land": "Collected land (hectares)",
 "collected_quintal": "Quantity collected (quintal)",
 "common.clearAll": "Clear all",
 "common.deselectAll": "Deselect all",
 "common.selectAll": "Select all",
 "coss_field_amharic_name_format": "{label}: use 1 to 100 Ethiopic letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_field_date_format": "{label}: enter a real date. In imported files, write dates as year-month-day in the Gregorian calendar, for example 2018-12-25.",
 "coss_field_date_future": "{label}: the date is in the future. Enter today''s date or an earlier date.",
 "coss_field_date_min": "{label}: the date is too early. Enter a date in 1900 or later.",
 "coss_field_name_format": "{label}: use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_actual_cultivation_date_min": "Actual cultivation date: the date is too early. Enter a date in 1900 or later.",
 "coss_input_cluster_harvest_date_min": "Cluster harvest date: the date is too early. Enter a date in 1900 or later.",
 "coss_input_da_name": "Development agent name: use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_date_of_birth_min": "Date of birth: the date is too early. Enter a date in 1900 or later.",
 "coss_input_end_gc_min": "End date (Gregorian): the date is too early. Enter a date in 1900 or later.",
 "coss_input_establishing_date_min": "Establishing date: the date is too early. Enter a date in 1900 or later.",
 "coss_input_farmer_name": "Farmer name: use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_first_name": "First name: use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_first_name_amh": "First name (Amharic): use 1 to 100 Ethiopic letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_first_name_other": "First name (other language): use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_harvest_date_min": "Harvest date: the date is too early. Enter a date in 1900 or later.",
 "coss_input_last_name": "Last name: use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_last_name_amh": "Last name (Amharic): use 1 to 100 Ethiopic letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_last_name_other": "Last name (other language): use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_middle_name": "Middle name: use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_middle_name_amh": "Middle name (Amharic): use 1 to 100 Ethiopic letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_middle_name_other": "Middle name (other language): use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_observation_date_min": "Observation date: the date is too early. Enter a date in 1900 or later.",
 "coss_input_planned_date_min": "Planned date: the date is too early. Enter a date in 1900 or later.",
 "coss_input_registration_date_min": "Registration date: the date is too early. Enter a date in 1900 or later.",
 "coss_input_sowing_date_min": "Sowing date: the date is too early. Enter a date in 1900 or later.",
 "coss_input_start_gc_min": "Start date (Gregorian): the date is too early. Enter a date in 1900 or later.",
 "coss_input_supervisor_name": "Supervisor name: use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "coss_input_surveyor_name": "Development agent name: use 1 to 100 letters, spaces, hyphens or apostrophes. Do not use digits or other symbols.",
 "crop_year": "Crop year",
 "cropsown_cultivation_intake_tab": "Cultivation intake",
 "cropsown_harvesting_intake_tab": "Harvesting intake",
 "cropsown_planning_intake_tab": "Planning intake",
 "cropsown_sowing_intake_tab": "Sowing intake",
 "dd_mm_yyyy": "Day/month/year",
 "land_area": "Total land area (hectares)",
 "planned_area": "Planned area (hectares)",
 "surveyor_mobile_number": "Development agent mobile number",
 "surveyor_name": "Development agent name",
 "yield_per_ha": "Yield per hectare (quintal per hectare)"
}'::jsonb)::json
WHERE "language_code" = 'en';

UPDATE "public"."registry_languages"
SET "core_translation" = (COALESCE("core_translation"::jsonb, '{}'::jsonb) ||
'{
 "ACTIVE": "Active",
 "INACTIVE": "Inactive",
 "ARCHIVED": "Archived",
 "planted_date": "Cultivation date"
}'::jsonb)::json
WHERE "language_code" = 'en';

UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace("search_result_schema"::jsonb::text, '"display_label": "Cluster area (ha)"', '"display_label": "Cluster area (hectares)"')::json
WHERE "register_id" = '62098187-a3f7-517a-be6d-b25da981153e';

UPDATE "public"."g2p_register_schemas"
SET "filter_schema" = replace("filter_schema"::jsonb::text, '"display_label": "Agro ecological zone"', '"display_label": "Agro-ecological zone"')::json
WHERE "register_id" = '62098187-a3f7-517a-be6d-b25da981153e';

UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace("search_result_schema"::jsonb::text, '"display_label": "Yield per ha"', '"display_label": "Yield per hectare"')::json
WHERE "register_id" = 'b9beb11f-45a7-5ad0-adde-eace5e1b6b27';

UPDATE "public"."g2p_register_schemas"
SET "filter_schema" = replace(replace(replace(replace("filter_schema"::jsonb::text, '"display_label": "Production Season"', '"display_label": "Production season"'), '"label": "Annual Crop"', '"label": "Annual crop"'), '"label": "Perennial Crop"', '"label": "Perennial crop"'), '"label": "Biennial Crop"', '"label": "Biennial crop"')::json
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c';

UPDATE "public"."g2p_register_definitions"
SET "register_description" = 'Farmer register'
WHERE "register_id" = 'fa120001-0000-4000-8000-000000000001';

UPDATE "public"."g2p_register_definitions"
SET "register_description" = 'Crop sown register'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c';

UPDATE "public"."g2p_register_definitions"
SET "register_description" = 'Crop planning register'
WHERE "register_id" = '0c0343ca-bac1-5c41-ae5d-72476fa21033';

UPDATE "public"."g2p_register_definitions"
SET "register_description" = 'Infestation incident register'
WHERE "register_id" = '17cab427-590c-5db2-b6dc-5e224de97f65';

UPDATE "public"."g2p_register_definitions"
SET "register_description" = 'Cluster information register', "register_subject" = 'Crop cluster information'
WHERE "register_id" = '62098187-a3f7-517a-be6d-b25da981153e';

UPDATE "public"."g2p_register_definitions"
SET "register_description" = 'Crop production register'
WHERE "register_id" = 'b9beb11f-45a7-5ad0-adde-eace5e1b6b27';

UPDATE "public"."g2p_register_definitions"
SET "register_description" = 'Harvest register'
WHERE "register_id" = 'c40d0a7c-9f31-5c89-9743-e83d6d6c7683';

UPDATE "public"."g2p_register_definitions"
SET "register_description" = 'Cultivation / land preparation register'
WHERE "register_id" = 'c9ee1d48-93b5-52d5-a8fc-280266a39c10';

UPDATE "public"."g2p_register_definitions"
SET "register_description" = 'Sowing register'
WHERE "register_id" = 'ee41a5f0-a5b6-5a9c-a853-f5c728e4d4b2';

UPDATE "public"."g2p_register_definitions"
SET "register_description" = 'Cultivation cluster information register'
WHERE "register_id" = '3392fa94-39fa-5eb7-891d-e593ab973e21';
