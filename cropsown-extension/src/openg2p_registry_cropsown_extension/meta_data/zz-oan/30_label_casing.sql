-- Label casing: sentence case for everything staff read that OAN metadata defines.
-- Labels, section and tab titles, table headings, messages and dropdown filter
-- labels use sentence case; acronyms and proper nouns (ID, FAN, FIN, Fayda,
-- Kebele, Woreda, ODK, DA) keep their case, and raw codes are not shown as
-- labels. Only display text changes: translation keys, ids, codes and
-- mnemonics are untouched.
--
-- Every statement is an explicit-id UPDATE (or a merge of named translation
-- keys), so it is idempotent and a plain upgrade applies it to databases that
-- already hold the older text. It sorts after the older seed files of this
-- package, so it also wins on a fresh install.

-- Display labels: domain translations (English)
UPDATE "public"."registry_languages"
SET "domain_translation" = (COALESCE("domain_translation"::jsonb, '{}'::jsonb) ||
'{
 "2,4-D Amine": "2,4-D amine",
 "2_4_D_AMINE": "2 4 D amine",
 "2,4-D + Metsulfuron": "2,4-D + metsulfuron",
 "2_4_D_METSULFURON": "2 4 D metsulfuron",
 "action_taken": "Action taken / extension advice",
 "Action Taken / Extension Advice": "Action taken / extension advice",
 "actual_crop_area": "Actual crop area (ha)",
 "Actual Crop Area (ha)": "Actual crop area (ha)",
 "actual_cultivation_date": "Cultivation date",
 "actual_fertilizer_qty": "Actual fertilizer quantity (kg)",
 "Actual Fertilizer Quantity (kg)": "Actual fertilizer quantity (kg)",
 "actual_fertilizer_type": "Actual fertilizer type",
 "Actual Fertilizer Type": "Actual fertilizer type",
 "actual_growth_duration_days": "Actual growth duration (days)",
 "Actual Growth Duration (days)": "Actual growth duration (days)",
 "actual_seed_class": "Actual seed type",
 "actual_seed_qty": "Actual seed quantity (kg)",
 "Actual Seed Quantity (kg)": "Actual seed quantity (kg)",
 "actual_seed_source": "Actual seed source",
 "Actual Seed Source": "Actual seed source",
 "Actual Seed Type": "Actual seed type",
 "actual_yield": "Actual yield (quintal)",
 "Actual Yield (quintal)": "Actual yield (quintal)",
 "Add Cluster": "Add cluster",
 "add_cluster_line": "Add cluster",
 "Add Crop Planning": "Add crop planning",
 "Add Crop Production": "Add crop production",
 "Add Cultivation": "Add cultivation",
 "add_cultivation_line": "Add cultivation",
 "Add Harvest": "Add harvest",
 "add_harvest_line": "Add harvest",
 "Add Infestation Incident": "Add infestation incident",
 "add_infestation_line": "Add infestation incident",
 "add_planning_line": "Add crop planning",
 "add_production_line": "Add crop production",
 "address_line_1": "Address line 1",
 "address_line_2": "Address line 2",
 "Add Sowing": "Add sowing",
 "add_sowing_line": "Add sowing",
 "agro_ecological_zone": "Agro-ecological zone",
 "Agro-ecological Zone": "Agro-ecological zone",
 "Aluminium Phosphide": "Aluminium phosphide",
 "ALUMINIUM_PHOSPHIDE": "Aluminium phosphide",
 "Annual Crop": "Annual crop",
 "ANNUAL_CROP": "Annual crop",
 "ANNUAL_WEED": "Annual weed",
 "Approval Level 1": "Approval level 1",
 "APPROVAL_LEVEL_1": "Approval level 1",
 "Approval Level 2": "Approval level 2",
 "APPROVAL_LEVEL_2": "Approval level 2",
 "area_harvested": "Area harvested (ha)",
 "Area Harvested (ha)": "Area harvested (ha)",
 "area_sown": "Area sown (ha)",
 "Area Sown (ha)": "Area sown (ha)",
 "area_under_production": "Area under production (ha)",
 "Area Under Production (ha)": "Area under production (ha)",
 "As Needed": "As needed",
 "Biennial Crop": "Biennial crop",
 "BIENNIAL_CROP": "Biennial crop",
 "BIENNIAL_WEED": "Biennial weed",
 "Biological Mulching": "Biological mulching",
 "BIOLOGICAL_MULCHING": "Biological mulching",
 "Bispyribac Sodium": "Bispyribac sodium",
 "BISPYRIBAC_SODIUM": "Bispyribac sodium",
 "Bordeaux Mixture": "Bordeaux mixture",
 "BORDEAUX_MIXTURE": "Bordeaux mixture",
 "chemical_used": "Chemical used",
 "Chemical Used": "Chemical used",
 "CLIMATE_SHOCK": "Climate shock",
 "cluster_area_hectare": "Total cultivated area (ha)",
 "Cluster": "Cluster information",
 "Cluster Information": "Cluster information",
 "Cluster Information Details": "Cluster information details",
 "cluster_name": "Cluster name",
 "Cluster Name": "Cluster name",
 "cluster_status": "Cluster status",
 "Cluster Status": "Cluster status",
 "collected_land": "Collected land (ha)",
 "Collected Land (ha)": "Collected land (ha)",
 "collected_quintal": "Collected quintal",
 "Collected Quintal": "Collected quintal",
 "Combine Harvester": "Combine harvester",
 "COMBINE_HARVESTER": "Combine harvester",
 "Copper Hydroxide": "Copper hydroxide",
 "COPPER_HYDROXIDE": "Copper hydroxide",
 "Copper Oxychloride": "Copper oxychloride",
 "COPPER_OXYCHLORIDE": "Copper oxychloride",
 "Copper Sulphate": "Copper sulphate",
 "COPPER_SULPHATE": "Copper sulphate",
 "coss_input_actual_cultivation_date_min": "Actual cultivation date: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_cluster_harvest_date_min": "Cluster harvest date: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_da_name": "DA name: use 1-100 letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_date_of_birth_min": "Date of birth: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_end_gc_min": "End GC: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_establishing_date_min": "Establishing date: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_farmer_name": "Farmer name: use 1-100 letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_first_name_amh": "First name Amharic: use 1-100 Ethiopic letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_first_name": "First name: use 1-100 letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_first_name_other": "First name other: use 1-100 letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_harvest_date_min": "Harvest date: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_last_name_amh": "Last name Amharic: use 1-100 Ethiopic letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_last_name": "Last name: use 1-100 letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_last_name_other": "Last name other: use 1-100 letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_middle_name_amh": "Middle name Amharic: use 1-100 Ethiopic letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_middle_name": "Middle name: use 1-100 letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_middle_name_other": "Middle name other: use 1-100 letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_observation_date_min": "Observation date: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_planned_date_min": "Planned date: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_registration_date_min": "Registration date: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_sowing_date_min": "Sowing date: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_start_gc_min": "Start GC: the date is before 1900. Enter a date on or after 1900-01-01.",
 "coss_input_supervisor_name": "Supervisor name: use 1-100 letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "coss_input_surveyor_name": "DA name: use 1-100 letters, spaces, hyphens or apostrophes. Remove digits and other symbols.",
 "country_code": "Country code",
 "created_at": "Created at",
 "created_by": "Created by",
 "crop_category": "Crop category",
 "Crop Category": "Crop category",
 "crop_maturity_status": "Crop maturity status",
 "Crop Maturity Status": "Crop maturity status",
 "cropping_system": "Cropping system",
 "Cropping System": "Cropping system",
 "Crop Planning": "Crop planning",
 "Crop Planning Details": "Crop planning details",
 "Crop Production": "Crop production",
 "Crop Production Details": "Crop production details",
 "Crop Sharing": "Crop sharing",
 "CROP_SHARING": "Crop sharing",
 "cropsown_cluster_tab": "Cluster information",
 "crop_sown": "Crop sown",
 "cropsown": "Crop sown",
 "CropSown": "Crop sown registries",
 "cropsown_cultivation_tab": "Cultivation / land preparation",
 "Crop Sown ID": "Crop sown ID",
 "cropsown_infestation_tab": "Infestation incident",
 "cropsown_intake": "Crop Sown Registry intake form",
 "cropsown_intake_tab": "Crop Sown Registry intake form",
 "cropsown_record_tab": "Crop sown",
 "cropsown_registry": "Crop sown",
 "crop_variety": "Crop variety",
 "Crop Variety": "Crop variety",
 "cs_cluster_details_table": "Cluster information",
 "cs_cropsown_record": "Farmer identity",
 "cs_cultivation_details_table": "Cultivation / land preparation",
 "cs_infestation_details_table": "Infestation incidents",
 "cs_planning_details_table": "Crop planning",
 "cs_production_details_table": "Crop production",
 "cultivated_by": "Cultivated by",
 "Cultivated By": "Cultivated by",
 "Cultivation - Approved": "Cultivation - approved",
 "Cultivation": "Cultivation / land preparation",
 "Cultivation Date": "Cultivation date",
 "Cultivation / Land Preparation": "Cultivation / land preparation",
 "Cultivation / Land Preparation Details": "Cultivation / land preparation details",
 "Cultivation - Pending Approval": "Cultivation - pending approval",
 "Cultivation - Rejected": "Cultivation - rejected",
 "cultivation_type": "Cultivation type",
 "Cultivation Type": "Cultivation type",
 "DA Mobile Number": "DA mobile number",
 "DA Name": "DA name",
 "Date of Observation": "Date of observation",
 "DOWNY_MILDEW": "Downy mildew",
 "Edit Cluster": "Edit cluster",
 "Edit Crop Planning": "Edit crop planning",
 "Edit Crop Production": "Edit crop production",
 "Edit Cultivation": "Edit cultivation",
 "Edit Harvest": "Edit harvest",
 "Edit Infestation Incident": "Edit infestation incident",
 "Edit Sowing": "Edit sowing",
 "Equine/Other Animals": "Equine/other animals",
 "EQUINE_OTHER_ANIMALS": "Equine other animals",
 "Estimated Crop Damage (%)": "Estimated crop damage (%)",
 "estimated_damage_pct": "Estimated crop damage (%)",
 "expected_yield": "Expected yield (quintal)",
 "Expected Yield (quintal)": "Expected yield (quintal)",
 "FABA_BEAN": "Faba bean",
 "Family Gift": "Family gift",
 "FAMILY_GIFT": "Family gift",
 "Family Labor": "Family labor",
 "FAMILY_LABOR": "Family labor",
 "Farmer Identity": "Farmer identity",
 "farmer_name": "Farmer name",
 "fertilizer_efficiency": "Fertilizer efficiency",
 "Fertilizer Efficiency": "Fertilizer efficiency",
 "fertilizer_qty": "Fertilizer quantity (kg)",
 "Fertilizer Quantity (kg)": "Fertilizer quantity (kg)",
 "fertilizer_type": "Fertilizer type",
 "Fertilizer Type": "Fertilizer type",
 "FIELD_MOUSE": "Field mouse",
 "FIELD_PEA": "Field pea",
 "Fully Sown": "Fully sown",
 "FULLY_SOWN": "Fully sown",
 "functional_record_id": "Crop sown ID",
 "geo_tagged_photo_document_id": "Geo-tagged photo",
 "Geo-tagged Photo": "Geo-tagged photo",
 "gps_coordinate": "GPS coordinate",
 "GPS Coordinate": "GPS coordinate",
 "growth_duration_days": "Growth duration (days)",
 "Growth Duration (days)": "Growth duration (days)",
 "growth_stage": "Growth stage",
 "Growth Stage": "Growth stage",
 "Halosulfuron Methyl": "Halosulfuron methyl",
 "HALOSULFURON_METHYL": "Halosulfuron methyl",
 "HARICOT_BEAN": "Haricot bean",
 "harvest_date": "Harvest date",
 "Harvest Date": "Harvest date",
 "Harvest Details": "Harvest details",
 "harvested_by": "Harvested by",
 "Harvested By": "Harvested by",
 "Harvesting - Approved": "Harvesting - approved",
 "Harvesting - Pending Approval": "Harvesting - pending approval",
 "Harvesting - Rejected": "Harvesting - rejected",
 "has_pest_disease": "Pest / disease occurrence",
 "Hired Labor": "Hired labor",
 "HIRED_LABOR": "Hired labor",
 "Infestation Incident Details": "Infestation incident details",
 "Infestation Incidents": "Infestation incidents",
 "Infestation": "Infestation incident",
 "infestation_type": "Infestation type",
 "Infestation Type": "Infestation type",
 "Inter Cropping": "Inter cropping",
 "INTER_CROPPING": "Inter cropping",
 "Iron Phosphate": "Iron phosphate",
 "IRON_PHOSPHATE": "Iron phosphate",
 "Irrigation Scheme": "Irrigation scheme",
 "IRRIGATION_SCHEME": "Irrigation scheme",
 "is_land_registered": "Plot registered",
 "Kharif / Summer": "Kharif / summer",
 "KHARIF_SUMMER": "Kharif summer",
 "LAMBDA_CYHALOTHRIN": "Lambda cyhalothrin",
 "land_area": "Total land area (ha)",
 "Land Preparation Method": "Land preparation method",
 "land_prep_method": "Land preparation method",
 "Land Utilisation Rate (%)": "Land utilisation rate (%)",
 "land_utilization_rate": "Land utilisation rate (%)",
 "last_approved_at": "Last approved at",
 "last_approved_by": "Last approved by",
 "Leafhopper (Jassids)": "Leafhopper (jassids)",
 "LEAFHOPPER_JASSIDS": "Leafhopper jassids",
 "LEAF_MINER": "Leaf miner",
 "LEAF_SPOT": "Leaf spot",
 "lifecycle_stage": "Lifecycle stage",
 "Lifecycle Stage": "Lifecycle stage",
 "link_internal_record_id": "Parent record",
 "local_name": "Local name",
 "Local Name": "Local name",
 "Manual Digging": "Manual digging",
 "MANUAL_DIGGING": "Manual digging",
 "MANUAL_LEVELING": "Manual leveling",
 "Metsulfuron Methyl": "Metsulfuron methyl",
 "METSULFURON_METHYL": "Metsulfuron methyl",
 "Minimum Tillage": "Minimum tillage",
 "MINIMUM_TILLAGE": "Minimum tillage",
 "Mixed Cropping": "Mixed cropping",
 "MIXED_CROPPING": "Mixed cropping",
 "Mono Cropping": "Mono cropping",
 "MONO_CROPPING": "Mono cropping",
 "MOSAIC_VIRUS": "Mosaic virus",
 "Neem Oil": "Neem oil",
 "NEEM_OIL": "Neem oil",
 "Not Sown": "Not sown",
 "NOT_SOWN": "Not sown",
 "number_of_smallholders": "Number of smallholders",
 "Number of Smallholders": "Number of smallholders",
 "NUTRIENT_DEFICIENCY": "Nutrient deficiency",
 "observation_date": "Date of observation",
 "OIL_SEEDS": "Oil seeds",
 "ownership_type": "Ownership type",
 "Ownership Type": "Ownership type",
 "Own Saved": "Own saved",
 "OWN_SAVED": "Own saved",
 "Oxen Ploughing + Manual Row Seeding": "Oxen ploughing + manual row seeding",
 "OXEN_PLOUGHING_MANUAL_ROW_SEEDING": "Oxen ploughing manual row seeding",
 "Oxen Tillage": "Oxen tillage",
 "OXEN_TILLAGE": "Oxen tillage",
 "Partially Sown": "Partially sown",
 "PARTIALLY_SOWN": "Partially sown",
 "participant_farmers": "Participant farmers",
 "Participant Farmers": "Participant farmers",
 "Perennial Crop": "Perennial crop",
 "PERENNIAL_CROP": "Perennial crop",
 "PERENNIAL_WEED": "Perennial weed",
 "Pest / Disease Occurrence": "Pest / disease occurrence",
 "Planned Area (ha)": "Planned area (ha)",
 "planned_area": "Planned area (ha)",
 "planned_date": "Planned date",
 "Planned Date": "Planned date",
 "planned_fertilizer_qty": "Planned fertilizer quantity (kg)",
 "Planned Fertilizer Quantity (kg)": "Planned fertilizer quantity (kg)",
 "planned_fertilizer_type": "Planned fertilizer type",
 "Planned Fertilizer Type": "Planned fertilizer type",
 "planned_labor": "Planned labour",
 "Planned Labour": "Planned labour",
 "planned_seed_qty": "Planned seed quantity (kg)",
 "Planned Seed Quantity (kg)": "Planned seed quantity (kg)",
 "Planning - Approved": "Planning - approved",
 "Planning": "Crop planning",
 "Planning - Pending Approval": "Planning - pending approval",
 "Planning - Rejected": "Planning - rejected",
 "plot_category": "Plot category",
 "Plot Category": "Plot category",
 "plus_code": "Plus code",
 "postal_code": "Postal code",
 "post_harvest_loss_pct": "Post-harvest loss (%)",
 "Post-harvest Loss (%)": "Post-harvest loss (%)",
 "POWDERY_MILDEW": "Powdery mildew",
 "Power Tiller": "Power tiller",
 "POWER_TILLER": "Power tiller",
 "Production": "Crop production",
 "production_year": "Production year",
 "Production Year": "Production year",
 "qty_harvested": "Quantity harvested (quintal)",
 "qty_sold": "Quantity sold (quintal)",
 "qty_stored": "Quantity stored (quintal)",
 "Quantity Harvested (quintal)": "Quantity harvested (quintal)",
 "Quantity Sold (quintal)": "Quantity sold (quintal)",
 "Quantity Stored (quintal)": "Quantity stored (quintal)",
 "Rabi / Winter": "Rabi / winter",
 "RABI_WINTER": "Rabi winter",
 "Ready For Harvest": "Ready for harvest",
 "READY_FOR_HARVEST": "Ready for harvest",
 "record_status_reason": "Status reason",
 "record_status": "Record status",
 "registration_date": "Registration date",
 "Relay Cropping": "Relay cropping",
 "RELAY_CROPPING": "Relay cropping",
 "Re Sown": "Re sown",
 "RE_SOWN": "Re sown",
 "Ridging / Furrowing": "Ridging / furrowing",
 "RIDGING_FURROWING": "Ridging furrowing",
 "ROOT_CROPS": "Root crops",
 "ROOT_ROT": "Root rot",
 "Salicylic Acid": "Salicylic acid",
 "SALICYLIC_ACID": "Salicylic acid",
 "scientific_name": "Scientific name",
 "Scientific Name": "Scientific name",
 "seed_class": "Seed type",
 "SEED_CROP": "Seed crop",
 "seed_productivity": "Seed productivity",
 "Seed Productivity": "Seed productivity",
 "Seed Quantity (kg)": "Seed quantity (kg)",
 "seed_source": "Seed source",
 "Seed Source": "Seed source",
 "Seed Type": "Seed type",
 "seed_variety": "Seed variety",
 "Seed Variety": "Seed variety",
 "SEED_VARIETY": "Seed variety",
 "severity_level": "Severity level",
 "Severity Level": "Severity level",
 "shape_data": "Shape data",
 "shape_type": "Shape type",
 "Soil Fertility": "Soil fertility",
 "soil_fertility_type": "Soil fertility",
 "Soil & Water Conservation Structures": "Soil & water conservation structures",
 "SOIL_WATER_CONSERVATION_STRUCTURES": "Soil water conservation structures",
 "Sowing - Approved": "Sowing - approved",
 "sowing_date": "Sowing date",
 "Sowing Date": "Sowing date",
 "Sowing Details": "Sowing details",
 "Sowing - Pending Approval": "Sowing - pending approval",
 "Sowing - Rejected": "Sowing - rejected",
 "sowing_status": "Sowing status",
 "Sowing Status": "Sowing status",
 "SQUARE_METER": "Square meter",
 "STEM_BORER": "Stem borer",
 "supervisor_mobile_number": "Supervisor mobile number",
 "Supervisor Mobile Number": "Supervisor mobile number",
 "supervisor_name": "Supervisor name",
 "Supervisor Name": "Supervisor name",
 "Surface / Flood": "Surface / flood",
 "surveyor_mobile_number": "DA mobile number",
 "surveyor_name": "DA name",
 "Survey Personnel": "Survey personnel",
 "Thrashing Machine": "Thrashing machine",
 "THRASHING_MACHINE": "Thrashing machine",
 "Total Cultivated Area (ha)": "Total cultivated area (ha)",
 "Total Land Area (ha)": "Total land area (ha)",
 "Tractor Disc/Moldboard Ploughing": "Tractor disc/moldboard ploughing",
 "TRACTOR_DISC_MOLDBOARD_PLOUGHING": "Tractor disc moldboard ploughing",
 "Tractor Ploughing": "Tractor ploughing",
 "TRACTOR_PLOUGHING": "Tractor ploughing",
 "Tractor Primary Tillage + Oxen Secondary Tillage": "Tractor primary tillage + oxen secondary tillage",
 "TRACTOR_PRIMARY_TILLAGE_OXEN_SECONDARY_TILLAGE": "Tractor primary tillage oxen secondary tillage",
 "Traditional Maresha Ploughing": "Traditional Maresha ploughing",
 "TRADITIONAL_MARESHA_PLOUGHING": "Traditional Maresha ploughing",
 "Update Requested": "Update requested",
 "UPDATE_REQUESTED": "Update requested",
 "Upload Photo": "Upload photo",
 "Water Harvesting Structure": "Water harvesting structure",
 "WATER_HARVESTING_STRUCTURE": "Water harvesting structure",
 "water_source": "Water source",
 "Water Source": "Water source",
 "YEAR_ROUND": "Year round",
 "yield_per_ha": "Yield per hectare (quintal/ha)",
 "Yield per Hectare (quintal/ha)": "Yield per hectare (quintal/ha)",
 "Zinc Phosphide": "Zinc phosphide",
 "ZINC_PHOSPHIDE": "Zinc phosphide"
}'::jsonb)::json
WHERE "language_code" = 'en';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"message": "Land ID in Cluster must match Land ID specified in Crop Planning"', '"message": "Land ID in cluster must match land ID specified in crop planning"'), '"widget-label": "FPC Name"', '"widget-label": "FPC name"'), '"column-group": "Season Details"', '"column-group": "Season details"'), '"widget-label": "Start Month"', '"widget-label": "Start month"'), '"widget-label": "Start Day"', '"widget-label": "Start day"'), '"widget-label": "End Month"', '"widget-label": "End month"'), '"widget-label": "End Day"', '"widget-label": "End day"'), '"column-group": "Establishing Date"', '"column-group": "Establishing date"'), '"widget-label": "Establishing Date (GC)"', '"widget-label": "Establishing date (GC)"'), '"widget-label": "Establishing Date (EC)"', '"widget-label": "Establishing date (EC)"'), '"column-group": "Location Details"', '"column-group": "Location details"'), '"widget-label": "Plot Latitude"', '"widget-label": "Plot latitude"'), '"widget-label": "Plot Longitude"', '"widget-label": "Plot longitude"'), '"widget-label": "Primary Commodity"', '"widget-label": "Primary commodity"'), '"widget-label": "Secondary Commodity"', '"widget-label": "Secondary commodity"'), '"widget-label": "FPC Type"', '"widget-label": "FPC type"'), '"widget-label": "Co-Leader"', '"widget-label": "Co-leader"'), '"column-group": "Cultivation Details"', '"column-group": "Cultivation details"'), '"widget-label": "Total Cultivated Area (Timad)"', '"widget-label": "Total cultivated area (Timad)"'), '"widget-label": "Collected Land (Quintial)"', '"widget-label": "Collected land (Quintial)"'), '"widget-label": "Collected by Combiner (ha)"', '"widget-label": "Collected by combiner (ha)"'), '"column-group": "Water Details"', '"column-group": "Water details"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cluster_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "First Name"', '"widget-label": "First name"'), '"widget-label": "Middle Name"', '"widget-label": "Middle name"'), '"widget-label": "Last Name"', '"widget-label": "Last name"'), '"label": "MALE"', '"label": "Male"'), '"label": "FEMALE"', '"label": "Female"'), '"widget-label": "Date of Birth"', '"widget-label": "Date of birth"'), '"widget-label": "Mobile Number"', '"widget-label": "Mobile number"'), '"widget-label": "Registration Date"', '"widget-label": "Registration date"')::jsonb
WHERE "register_id" = 'fa120001-0000-4000-8000-000000000001' AND "section_id" = 'cropsown_farmer_identity_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"column-group": "Land Details"', '"column-group": "Land details"'), '"widget-label": "Is Plot Not Registered?"', '"widget-label": "Is plot not registered?"'), '"column-group": "Season Details"', '"column-group": "Season details"'), '"widget-label": "Start Month"', '"widget-label": "Start month"'), '"widget-label": "Start Day"', '"widget-label": "Start day"'), '"widget-label": "End Month"', '"widget-label": "End month"'), '"widget-label": "End Day"', '"widget-label": "End day"'), '"column-group": "Crop Details"', '"column-group": "Crop details"'), '"widget-label": "Planned Date (GC)"', '"widget-label": "Planned date (GC)"'), '"widget-label": "Planned Date (EC)"', '"widget-label": "Planned date (EC)"'), '"column-group": "Crop Planned Inputs"', '"column-group": "Crop planned inputs"'), '"widget-label": "Average Growth Duration (days)"', '"widget-label": "Average growth duration (days)"'), '"widget-label": "Planned Crop Area (ha)"', '"widget-label": "Planned crop area (ha)"'), '"message": "Planned Crop Area cannot be greater than Total Land Area"', '"message": "Planned crop area cannot be greater than total land area"'), '"widget-label": "Expected Yield (quintals)"', '"widget-label": "Expected yield (quintals)"'), '"column-group": "Seed Planned Inputs"', '"column-group": "Seed planned inputs"'), '"label": "Government / Woreda Agriculture Office"', '"label": "Government / Woreda agriculture office"'), '"label": "Agriculture Cooperative / Union"', '"label": "Agriculture cooperative / union"'), '"label": "Private Seed Enterprise"', '"label": "Private seed enterprise"'), '"label": "Farmer-to-Farmer Exchange / Saved Seed"', '"label": "Farmer-to-farmer exchange / saved seed"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_planning_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"column-group": "Land Details"', '"column-group": "Land details"'), '"widget-label": "Is Plot Not Registered?"', '"widget-label": "Is plot not registered?"'), '"column-group": "Season Details"', '"column-group": "Season details"'), '"widget-label": "Start Month"', '"widget-label": "Start month"'), '"widget-label": "Start Day"', '"widget-label": "Start day"'), '"widget-label": "End Month"', '"widget-label": "End month"'), '"widget-label": "End Day"', '"widget-label": "End day"'), '"column-group": "Crop Details"', '"column-group": "Crop details"'), '"widget-label": "Actual Cultivation Date (GC)"', '"widget-label": "Actual cultivation date (GC)"'), '"widget-label": "Actual Cultivation Date (EC)"', '"widget-label": "Actual cultivation date (EC)"'), '"column-group": "Seed Details"', '"column-group": "Seed details"'), '"label": "Government / Woreda Agriculture Office"', '"label": "Government / Woreda agriculture office"'), '"label": "Agriculture Cooperative / Union"', '"label": "Agriculture cooperative / union"'), '"label": "Private Seed Enterprise"', '"label": "Private seed enterprise"'), '"label": "Farmer-to-Farmer Exchange / Saved Seed"', '"label": "Farmer-to-farmer exchange / saved seed"'), '"column-group": "Water Source Details"', '"column-group": "Water source details"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cultivation_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "Cultivation Cluster Information"', '"widget-label": "Cultivation cluster information"'), '"message": "Land ID in Cultivation Cluster must match Land ID specified in Crop Planning"', '"message": "Land ID in cultivation cluster must match land ID specified in crop planning"'), '"widget-label": "FPC Name"', '"widget-label": "FPC name"'), '"column-group": "Season Details"', '"column-group": "Season details"'), '"widget-label": "Start Month"', '"widget-label": "Start month"'), '"widget-label": "Start Day"', '"widget-label": "Start day"'), '"widget-label": "End Month"', '"widget-label": "End month"'), '"widget-label": "End Day"', '"widget-label": "End day"'), '"column-group": "Establishing Date"', '"column-group": "Establishing date"'), '"widget-label": "Establishing Date (GC)"', '"widget-label": "Establishing date (GC)"'), '"widget-label": "Establishing Date (EC)"', '"widget-label": "Establishing date (EC)"'), '"column-group": "Address Details"', '"column-group": "Address details"'), '"widget-label": "Plot Latitude"', '"widget-label": "Plot latitude"'), '"widget-label": "Plot Longitude"', '"widget-label": "Plot longitude"'), '"widget-label": "Primary Commodity"', '"widget-label": "Primary commodity"'), '"widget-label": "Secondary Commodity"', '"widget-label": "Secondary commodity"'), '"widget-label": "FPC Type"', '"widget-label": "FPC type"'), '"widget-label": "Co-Leader"', '"widget-label": "Co-leader"'), '"column-group": "Cluster Metrics"', '"column-group": "Cluster metrics"'), '"widget-label": "Total Cultivated Area (Timad)"', '"widget-label": "Total cultivated area (Timad)"'), '"widget-label": "Actual Plan (ha)"', '"widget-label": "Actual plan (ha)"'), '"widget-label": "Actual Collected Land (Quintal)"', '"widget-label": "Actual collected land (quintal)"'), '"widget-label": "Actual Collected Quintal"', '"widget-label": "Actual collected quintal"'), '"widget-label": "Actual Collected by Combiner (ha)"', '"widget-label": "Actual collected by combiner (ha)"'), '"column-group": "Water Source Details"', '"column-group": "Water source details"'), '"widget-data-dialog-title-add": "Add Cultivation Cluster"', '"widget-data-dialog-title-add": "Add cultivation cluster"'), '"widget-data-dialog-title-edit": "Edit Cultivation Cluster"', '"widget-data-dialog-title-edit": "Edit cultivation cluster"'), '"section-title": "Cultivation Cluster Information Details"', '"section-title": "Cultivation cluster information details"')::jsonb, "section_description" = 'Cultivation cluster information details'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cultivation_cluster_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "Cluster / Non Cluster Status"', '"widget-label": "Cluster / non cluster status"'), '"column-group": "Cluster Details"', '"column-group": "Cluster details"'), '"widget-label": "FPC Name"', '"widget-label": "FPC name"'), '"widget-label": "Season (Cluster)"', '"widget-label": "Season (cluster)"'), '"widget-label": "Area Sown (ha) (Cluster)"', '"widget-label": "Area sown (ha) (cluster)"'), '"widget-label": "Actual Crop Name"', '"widget-label": "Actual crop name"'), '"widget-label": "Sowing Date (GC)"', '"widget-label": "Sowing date (GC)"'), '"widget-label": "Sowing Date (EC)"', '"widget-label": "Sowing date (EC)"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_sowing_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(section_ui_schema::text, '"widget-label": "Crop Year"', '"widget-label": "Crop year"'), '"widget-label": "Production Season"', '"widget-label": "Production season"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cropsown_record_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(section_ui_schema::text, '"widget-label": "Production Season"', '"widget-label": "Production season"'), '"section-title": "Production Summary"', '"section-title": "Production summary"')::jsonb, "section_description" = 'Production summary'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_production_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "Cluster / Non Cluster Status"', '"widget-label": "Cluster / non cluster status"'), '"column-group": "Cluster Details"', '"column-group": "Cluster details"'), '"widget-label": "FPC Name"', '"widget-label": "FPC name"'), '"label": "Not Yet Ready For Harvest"', '"label": "Not yet ready for harvest"'), '"column-group": "Crop Details"', '"column-group": "Crop details"'), '"widget-label": "Actual Crop Name"', '"widget-label": "Actual crop name"'), '"column-group": "Production Result"', '"column-group": "Production result"'), '"widget-label": "Yield Performance (%)"', '"widget-label": "Yield performance (%)"'), '"widget-label": "Land Utilization Rate"', '"widget-label": "Land utilization rate"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_harvest_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(section_ui_schema::text, '"widget-label": "Crop Year"', '"widget-label": "Crop year"'), '"widget-label": "Production Season"', '"widget-label": "Production season"'), '"section-title": "Production Season"', '"section-title": "Production season"')::jsonb, "section_description" = 'Production season'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_intake_season_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(section_ui_schema::text, '"widget-label": "Incident Record ID"', '"widget-label": "Incident record ID"'), '"widget-label": "Cluster / Non Cluster Status"', '"widget-label": "Cluster / non cluster status"'), '"widget-label": "FPC Name"', '"widget-label": "FPC name"'), '"widget-label": "Type of Infestation"', '"widget-label": "Type of infestation"'), '"widget-label": "Pest Type"', '"widget-label": "Pest type"'), '"widget-label": "Pest Name"', '"widget-label": "Pest name"'), '"widget-label": "Method of Control (Pest)"', '"widget-label": "Method of control (pest)"'), '"label": "Chemical Spray"', '"label": "Chemical spray"'), '"label": "Hand Picking"', '"label": "Hand picking"'), '"label": "Early Harvesting"', '"label": "Early harvesting"'), '"widget-label": "Pesticide Type"', '"widget-label": "Pesticide type"'), '"label": "Acaricide / Miticide"', '"label": "Acaricide / miticide"'), '"widget-label": "Pesticide Name"', '"widget-label": "Pesticide name"'), '"widget-label": "Frequency of Application"', '"widget-label": "Frequency of application"'), '"widget-label": "Weed Type"', '"widget-label": "Weed type"'), '"widget-label": "Weed Name"', '"widget-label": "Weed name"'), '"widget-label": "Method of Control (Weed)"', '"widget-label": "Method of control (weed)"'), '"widget-label": "Weedicides Type"', '"widget-label": "Weedicides type"'), '"label": "Pre-emergent Herbicide"', '"label": "Pre-emergent herbicide"'), '"label": "Post-emergent Herbicide"', '"label": "Post-emergent herbicide"'), '"label": "Systemic Herbicide"', '"label": "Systemic herbicide"'), '"label": "Contact Herbicide"', '"label": "Contact herbicide"'), '"label": "Broadleaf Herbicide"', '"label": "Broadleaf herbicide"'), '"label": "Sedge Herbicide"', '"label": "Sedge herbicide"'), '"label": "Aquatic Herbicide"', '"label": "Aquatic herbicide"'), '"label": "Foliar Herbicide"', '"label": "Foliar herbicide"'), '"label": "Soil Herbicide"', '"label": "Soil herbicide"'), '"widget-label": "Weedicides Name"', '"widget-label": "Weedicides name"'), '"widget-label": "Disease Type"', '"widget-label": "Disease type"'), '"widget-label": "Disease Name"', '"widget-label": "Disease name"'), '"widget-label": "Method of Control (Disease)"', '"widget-label": "Method of control (disease)"'), '"widget-label": "Fungicide/Bactericide Type"', '"widget-label": "Fungicide/bactericide type"'), '"widget-label": "Fungicide/Bactericide Name"', '"widget-label": "Fungicide/bactericide name"'), '"widget-label": "Nutrient Type"', '"widget-label": "Nutrient type"'), '"label": "Secondary Nutrient"', '"label": "Secondary nutrient"'), '"widget-label": "Nutrient Name"', '"widget-label": "Nutrient name"'), '"widget-label": "Method of Control (Nutrient)"', '"widget-label": "Method of control (nutrient)"'), '"label": "Soil Application"', '"label": "Soil application"'), '"label": "Foliar Spray"', '"label": "Foliar spray"'), '"label": "Organic Amendment"', '"label": "Organic amendment"'), '"label": "Cultural (e.g. Liming, Crop Rotation)"', '"label": "Cultural (e.g. liming, crop rotation)"'), '"widget-label": "Fertilizer/Amendment Type"', '"widget-label": "Fertilizer/amendment type"'), '"widget-label": "Fertilizer/Amendment Name"', '"widget-label": "Fertilizer/amendment name"'), '"widget-label": "Shock Type"', '"widget-label": "Shock type"'), '"widget-label": "Shock Event Name/Description"', '"widget-label": "Shock event name/description"'), '"widget-label": "Method of Control (Climate)"', '"widget-label": "Method of control (climate)"'), '"label": "Shelter/Covering"', '"label": "Shelter/covering"'), '"widget-label": "Recovery Input Type"', '"widget-label": "Recovery input type"'), '"label": "Soil Conditioner"', '"label": "Soil conditioner"'), '"label": "Replanting Material"', '"label": "Replanting material"'), '"label": "Irrigation Equipment"', '"label": "Irrigation equipment"'), '"widget-label": "Recovery Input Name"', '"widget-label": "Recovery input name"'), '"widget-label": "Date of Observation(GC)"', '"widget-label": "Date of observation(GC)"'), '"widget-label": "Date of Observation(EC)"', '"widget-label": "Date of observation(EC)"'), '"column-group": "Damage Metrics"', '"column-group": "Damage metrics"'), '"widget-label": "Estimated Crop Damage (%) or (ha)"', '"widget-label": "Estimated crop damage (%) or (ha)"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_infestation_details_section_01';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(section_ui_schema::text, '"widget-label": "Location Hierarchy"', '"widget-label": "Location hierarchy"'), '"widget-label": "Geo Latitude"', '"widget-label": "Geo latitude"'), '"widget-label": "Geo Longitude"', '"widget-label": "Geo longitude"')::jsonb
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_cropsown_location_section_03';

UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = replace(replace(replace(section_ui_schema::text, '"widget-label": "Crop Year"', '"widget-label": "Crop year"'), '"widget-label": "Production Season"', '"widget-label": "Production season"'), '"section-title": "Production Season"', '"section-title": "Production season"')::jsonb, "section_description" = 'Production season'
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c' AND "section_id" = 'cropsown_common_intake_season_section_01';

UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace(replace("search_result_schema"::jsonb::text, '"display_label": "Planned Area"', '"display_label": "Planned area"'), '"display_label": "Expected Yield"', '"display_label": "Expected yield"')::json
WHERE "register_id" = '0c0343ca-bac1-5c41-ae5d-72476fa21033';

UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace(replace("search_result_schema"::jsonb::text, '"display_label": "Land Preparation"', '"display_label": "Land preparation"'), '"display_label": "Actual Crop Area"', '"display_label": "Actual crop area"')::json
WHERE "register_id" = 'c9ee1d48-93b5-52d5-a8fc-280266a39c10';

UPDATE "public"."g2p_register_schemas"
SET "filter_schema" = replace("filter_schema"::jsonb::text, '"display_label": "Land Preparation"', '"display_label": "Land preparation"')::json
WHERE "register_id" = 'c9ee1d48-93b5-52d5-a8fc-280266a39c10';

UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace("search_result_schema"::jsonb::text, '"display_label": "Area Sown"', '"display_label": "Area sown"')::json
WHERE "register_id" = 'ee41a5f0-a5b6-5a9c-a853-f5c728e4d4b2';

UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace("search_result_schema"::jsonb::text, '"display_label": "Actual Yield"', '"display_label": "Actual yield"')::json
WHERE "register_id" = 'b9beb11f-45a7-5ad0-adde-eace5e1b6b27';

UPDATE "public"."g2p_register_schemas"
SET "filter_schema" = replace("filter_schema"::jsonb::text, '"display_label": "Growth Stage"', '"display_label": "Growth stage"')::json
WHERE "register_id" = 'b9beb11f-45a7-5ad0-adde-eace5e1b6b27';

UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace(replace(replace("search_result_schema"::jsonb::text, '"display_label": "Harvest Date"', '"display_label": "Harvest date"'), '"display_label": "Area Harvested"', '"display_label": "Area harvested"'), '"display_label": "Quantity Harvested"', '"display_label": "Quantity harvested"')::json
WHERE "register_id" = 'c40d0a7c-9f31-5c89-9743-e83d6d6c7683';

UPDATE "public"."g2p_register_schemas"
SET "filter_schema" = replace("filter_schema"::jsonb::text, '"display_label": "Maturity Status"', '"display_label": "Maturity status"')::json
WHERE "register_id" = 'c40d0a7c-9f31-5c89-9743-e83d6d6c7683';

UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace(replace("search_result_schema"::jsonb::text, '"display_label": "Infestation Type"', '"display_label": "Infestation type"'), '"display_label": "Observed On"', '"display_label": "Observed on"')::json
WHERE "register_id" = '17cab427-590c-5db2-b6dc-5e224de97f65';

UPDATE "public"."g2p_register_schemas"
SET "filter_schema" = replace("filter_schema"::jsonb::text, '"display_label": "Infestation Type"', '"display_label": "Infestation type"')::json
WHERE "register_id" = '17cab427-590c-5db2-b6dc-5e224de97f65';

UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace(replace(replace("search_result_schema"::jsonb::text, '"display_label": "Cluster Name"', '"display_label": "Cluster name"'), '"display_label": "Cluster Area (ha)"', '"display_label": "Cluster area (ha)"'), '"display_label": "Cluster Status"', '"display_label": "Cluster status"')::json
WHERE "register_id" = '62098187-a3f7-517a-be6d-b25da981153e';

UPDATE "public"."g2p_register_schemas"
SET "filter_schema" = replace(replace("filter_schema"::jsonb::text, '"display_label": "Cluster Status"', '"display_label": "Cluster status"'), '"display_label": "Agro Ecological Zone"', '"display_label": "Agro ecological zone"')::json
WHERE "register_id" = '62098187-a3f7-517a-be6d-b25da981153e';

UPDATE "public"."g2p_register_schemas"
SET "search_result_schema" = replace("search_result_schema"::jsonb::text, '"display_label": "Crop Year"', '"display_label": "Crop year"')::json
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c';

UPDATE "public"."g2p_register_schemas"
SET "filter_schema" = replace(replace(replace(replace("filter_schema"::jsonb::text, '"display_label": "Crop Year"', '"display_label": "Crop year"'), '"display_label": "Lifecycle Stage"', '"display_label": "Lifecycle stage"'), '"display_label": "Ownership Type"', '"display_label": "Ownership type"'), '"display_label": "Plot Category"', '"display_label": "Plot category"')::json
WHERE "register_id" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c';

UPDATE "public"."g2p_register_definitions"
SET "register_subject" = 'Crop planning lines'
WHERE "register_id" = '0c0343ca-bac1-5c41-ae5d-72476fa21033';

UPDATE "public"."g2p_register_definitions"
SET "register_subject" = 'Crop infestation incidents'
WHERE "register_id" = '17cab427-590c-5db2-b6dc-5e224de97f65';

UPDATE "public"."g2p_register_definitions"
SET "register_subject" = 'Crop cluster info'
WHERE "register_id" = '62098187-a3f7-517a-be6d-b25da981153e';

UPDATE "public"."g2p_register_definitions"
SET "register_subject" = 'Crop production lines'
WHERE "register_id" = 'b9beb11f-45a7-5ad0-adde-eace5e1b6b27';

UPDATE "public"."g2p_register_definitions"
SET "register_subject" = 'Crop harvesting lines'
WHERE "register_id" = 'c40d0a7c-9f31-5c89-9743-e83d6d6c7683';

UPDATE "public"."g2p_register_definitions"
SET "register_subject" = 'Crop cultivation lines'
WHERE "register_id" = 'c9ee1d48-93b5-52d5-a8fc-280266a39c10';

UPDATE "public"."g2p_register_definitions"
SET "register_subject" = 'Crop sowing lines'
WHERE "register_id" = 'ee41a5f0-a5b6-5a9c-a853-f5c728e4d4b2';

UPDATE "public"."g2p_register_definitions"
SET "register_subject" = 'Cultivation cluster lines'
WHERE "register_id" = '3392fa94-39fa-5eb7-891d-e593ab973e21';

UPDATE "public"."g2p_intake_form_definitions"
SET "form_description" = 'Cultivation intake form'
WHERE "form_id" = '6be15ab9-0f1b-4c38-995f-395d52a1b17a';

UPDATE "public"."g2p_intake_form_definitions"
SET "form_description" = 'Planning intake form'
WHERE "form_id" = '5bf0068c-ce19-46f8-874c-7147997f793b';

UPDATE "public"."g2p_intake_form_definitions"
SET "form_description" = 'Sowing intake form'
WHERE "form_id" = '4a7c2c98-0ffb-41d8-8fea-f22349823675';

UPDATE "public"."g2p_intake_form_definitions"
SET "form_description" = 'Harvesting intake form'
WHERE "form_id" = '52150a37-153d-496d-9cd9-2a3815d6e13b';

UPDATE "public"."registry_languages"
SET "core_translation" = (COALESCE("core_translation"::jsonb, '{}'::jsonb) ||
'{
 "functional_record_id": "Crop sown ID",
 "id": "Crop sown ID"
}'::jsonb)::json
WHERE "language_code" = 'en';
