# Crop Sown bulk import from a file

The Crop Sown registry takes intakes from a CSV or Excel file through the staff portal menu **Import from file**, one entry per intake form. This page is the column specification. The blank header files are in `import-templates/`.

## How an upload is handled

1. Staff with the intake-submission edit permission upload a `.csv` or `.xlsx` file for one form.
2. The platform import worker reads the first sheet and passes every row on as one flat record.
3. A Jinja incoming template (`templates/crop_file_import_<form>_intake.j2`) maps the columns to the sections of the form. There is no Python mapping.
4. Every row becomes an intake submission. It waits for its Farmer to be approved in the Farmer registry, then goes through the two-stage approval (an officer, then a second officer; an admin can act at either stage). Nothing is written to the register directly.

## File rules

- One file per form. The first row holds the column names exactly as below (letter case is ignored). A column not listed for that form fails the row, naming the column, so a file made for another form is not imported by mistake. Columns may be in any order.
- One row is one intake. A planning, cultivation or sowing row can also carry up to **three child rows** of its form (clusters, cultivation clusters or infestations) in numbered column groups, see each form below. More child rows: add them in the staff portal or by change request after the intake exists.
- A blank cell means "not given". Required columns are checked when the intake is saved and submitted.
- Numbers use a decimal point and no thousands separator. Dates are `YYYY-MM-DD` (a time after the date is dropped, as Excel writes it). Yes/no columns take `yes`, `no`, `true`, `false`, `1` or `0`.
- Dropdown columns take the Master Data **code**, never the label. Where a column takes several values, separate them with a semicolon.
- A row with a value the register cannot take (for example a letter in a number column) fails on its own, with the column named in the error; the other rows of the file continue. Check the row errors of the upload when the count of imported rows is lower than the count in the file.
- The farmer is named by the Farmer ID and one Fayda ID (FIN or FAN). Nothing else about the farmer is imported; the Farmer registry owns it.

## Planning intake (`crop_planning_intake_import_template.csv`)

Import configuration: `file_import_to_crop_planning_intake`.

| Column | Maps to | Required | Format or allowed codes |
|---|---|---|---|
| `farmer_id` | Farmer lookup (`crop_farmer_lookup`) | Yes | FR- followed by 12 digits, for example FR-000000000001 |
| `fayda_id` | Farmer lookup (`crop_farmer_lookup`) | Yes | A 12-digit FIN or a 16-digit FAN, digits only (spaces are dropped) |
| `crop_year` | Production Season (`cs_intake_season`) | Yes | Four-digit year, for example 2026 |
| `production_season` | Production Season (`cs_intake_season`) | Yes | Code from the CROP_SEASON list below. |
| `region` | Location (`cs_cropsown_location`) and the plot row | No | Master Data geo unit id (P-code), for example ET04 |
| `zone` | Location (`cs_cropsown_location`) and the plot row | No | Master Data geo unit id (P-code), for example ET0404 |
| `woreda` | Location (`cs_cropsown_location`) and the plot row | No | Master Data geo unit id (P-code), for example ET040404 |
| `kebele` | Location (`cs_cropsown_location`) and the plot row | No | Master Data geo unit id (P-code), for example ET040404888003 |
| `latitude` | Location (`cs_cropsown_location`) and the plot row | No | Decimal degrees; needs the longitude too |
| `longitude` | Location (`cs_cropsown_location`) and the plot row | No | Decimal degrees; needs the latitude too |
| `land_id` | `cs_planning_details` | Yes | Text |
| `plot_category` | `cs_planning_details` | No | Code from the PLOT_CATEGORY list below. |
| `ownership_type` | `cs_planning_details` | No | Code from the OWNERSHIP_TYPE list below. |
| `soil_fertility_type` | `cs_planning_details` | No | Code from the SOIL_FERTILITY list below. |
| `season` | `cs_planning_details` | No | Code from the CROP_SEASON list below. Blank means the production season. |
| `commodity` | `cs_planning_details` | Yes | Code from the CROP_COMMODITY list below. |
| `crop_category` | `cs_planning_details` | No | Code from the CROP_CATEGORY list below. |
| `local_name` | `cs_planning_details` | No | Text |
| `scientific_name` | `cs_planning_details` | No | Text |
| `seed_variety` | `cs_planning_details` | No | The variety (shown as "Variety"): code from the SEED_VARIETY list below. |
| `planned_fertilizer_type` | `cs_planning_details` | No | Code from the FERTILIZER_TYPE list below. |
| `water_source` | `cs_planning_details` | No | Code from the WATER_SOURCE list below. |
| `water_source_method` | `cs_planning_details` | No | Code from the WATER_SOURCE_METHOD list below. |
| `water_source_frequency` | `cs_planning_details` | No | Code from the WATER_SOURCE_FREQUENCY list below. |
| `da_name` | `cs_planning_details` | No | Text |
| `da_mobile_number` | `cs_planning_details` | No | Text |
| `supervisor_name` | `cs_planning_details` | No | Text |
| `supervisor_mobile_number` | `cs_planning_details` | No | Text |
| `land_area` | `cs_planning_details` | No | Number, digits and an optional decimal point. Required when `planned_area` is given. |
| `planned_area` | `cs_planning_details` | No | Number, digits and an optional decimal point |
| `expected_yield` | `cs_planning_details` | No | Number, digits and an optional decimal point |
| `crop_latitude` | `cs_planning_details` | No | The crop's latitude in decimal degrees. |
| `crop_longitude` | `cs_planning_details` | No | The crop's longitude in decimal degrees. |
| `planned_seed_qty` | `cs_planning_details` | No | Number, digits and an optional decimal point |
| `planned_fertilizer_qty` | `cs_planning_details` | No | Number, digits and an optional decimal point |
| `start_month` | `cs_planning_details` | No | Whole number |
| `start_day` | `cs_planning_details` | No | Whole number |
| `end_month` | `cs_planning_details` | No | Whole number |
| `end_day` | `cs_planning_details` | No | Whole number |
| `growth_duration_days` | `cs_planning_details` | No | Whole number |
| `planned_labor` | `cs_planning_details` | No | Whole number |
| `start_gc` | `cs_planning_details` | No | YYYY-MM-DD |
| `end_gc` | `cs_planning_details` | No | YYYY-MM-DD |
| `planned_date` | `cs_planning_details` | No | YYYY-MM-DD |
| `is_plot_not_registered` | `cs_planning_details` | No | yes or no (also true/false, 1/0) |
| `cropping_system` | `cs_planning_details` | No | Code from the CROPPING_SYSTEM list below. |
| `seed_class` | `cs_planning_details` | No | Code from the SEED_TYPE list below. |
| `seed_source` | `cs_planning_details` | No | Code from the SEED_SOURCE list below. |
| `cluster_<n>_land_id` | `cs_cluster_details` | No | Text. The Land ID; **required when the group has any value**. |
| `cluster_<n>_name` | `cs_cluster_details` | No | Text (Farmer production cluster name) |
| `cluster_<n>_reference` | `cs_cluster_details` | No | Text |
| `cluster_<n>_fpc_type` | `cs_cluster_details` | No | `GREEN` |
| `cluster_<n>_season` | `cs_cluster_details` | No | Code from the CROP_SEASON list below. Blank means the production season; another season is refused. |
| `cluster_<n>_start_gc` | `cs_cluster_details` | No | YYYY-MM-DD |
| `cluster_<n>_end_gc` | `cs_cluster_details` | No | YYYY-MM-DD |
| `cluster_<n>_establishing_date` | `cs_cluster_details` | No | YYYY-MM-DD, between `cluster_<n>_start_gc` and `cluster_<n>_end_gc`. |
| `cluster_<n>_region` | `cs_cluster_details` | No | Master Data geo unit id (P-code), for example ET04 |
| `cluster_<n>_zone` | `cs_cluster_details` | No | P-code, for example ET0404 |
| `cluster_<n>_woreda` | `cs_cluster_details` | No | P-code, for example ET040404 |
| `cluster_<n>_kebele` | `cs_cluster_details` | No | P-code, for example ET040404888003 |
| `cluster_<n>_sub_kebele` | `cs_cluster_details` | No | Text |
| `cluster_<n>_agro_ecological_zone` | `cs_cluster_details` | No | Code from the AGRO_ECOLOGICAL_ZONE list |
| `cluster_<n>_latitude` | `cs_cluster_details` | No | Latitude in decimal degrees |
| `cluster_<n>_longitude` | `cs_cluster_details` | No | Longitude in decimal degrees |
| `cluster_<n>_primary_commodity` | `cs_cluster_details` | No | Code from the CROP_COMMODITY list below. |
| `cluster_<n>_secondary_commodity` | `cs_cluster_details` | No | Code from the CROP_COMMODITY list below. |
| `cluster_<n>_area_timad` | `cs_cluster_details` | No | Number (timad, 0.25 hectares). The registry works out Total cultivated area (hectares) from it. |
| `cluster_<n>_plan` | `cs_cluster_details` | No | Number (planned area, hectares) |
| `cluster_<n>_collected_land` | `cs_cluster_details` | No | Number (hectares) |
| `cluster_<n>_collected_quintal` | `cs_cluster_details` | No | Number (quintal) |
| `cluster_<n>_collected_by_combiner` | `cs_cluster_details` | No | Number (hectares) |
| `cluster_<n>_number_of_smallholders` | `cs_cluster_details` | No | Whole number |
| `cluster_<n>_water_source` | `cs_cluster_details` | No | Code from the WATER_SOURCE list |
| `cluster_<n>_water_source_method` | `cs_cluster_details` | No | Code from the WATER_SOURCE_METHOD list |
| `cluster_<n>_water_source_frequency` | `cs_cluster_details` | No | Code from the WATER_SOURCE_FREQUENCY list |
| `cluster_<n>_leader` | `cs_cluster_details` | No | Text |
| `cluster_<n>_co_leader` | `cs_cluster_details` | No | Text |
| `cluster_<n>_coordinator` | `cs_cluster_details` | No | Text |
| `cluster_<n>_secretary` | `cs_cluster_details` | No | Text |
| `cluster_<n>_da_name` | `cs_cluster_details` | No | Text |
| `cluster_<n>_da_mobile_number` | `cs_cluster_details` | No | Text |
| `cluster_<n>_supervisor_name` | `cs_cluster_details` | No | Text |
| `cluster_<n>_supervisor_mobile_number` | `cs_cluster_details` | No | Text |

Each `cluster_<n>_*` column exists for n = 1, 2 and 3 (for example `cluster_1_land_id`, `cluster_2_land_id`, `cluster_3_land_id`): up to three Clusters (Cluster information details) in the same intake as the planning row. A group with any value becomes one row and needs its Land ID; leave a group blank to skip it. `cluster_<n>_land_id` is the cluster's Land ID; `cluster_name`, `cluster_area_timad` and `cluster_plan` become `cluster_<n>_name`, `cluster_<n>_area_timad` and `cluster_<n>_plan`. Cluster ID and Total cultivated area (hectares) are filled by the registry. More than three: add them in the staff portal or by change request.


## Cultivation intake (`crop_cultivation_intake_import_template.csv`)

Import configuration: `file_import_to_crop_cultivation_intake`.

| Column | Maps to | Required | Format or allowed codes |
|---|---|---|---|
| `farmer_id` | Farmer lookup (`crop_farmer_lookup`) | Yes | FR- followed by 12 digits, for example FR-000000000001 |
| `fayda_id` | Farmer lookup (`crop_farmer_lookup`) | Yes | A 12-digit FIN or a 16-digit FAN, digits only (spaces are dropped) |
| `crop_year` | Production Season (`cs_common_intake_season`) | Yes | Four-digit year, for example 2026 |
| `production_season` | Production Season (`cs_common_intake_season`) | Yes | Code from the CROP_SEASON list below. |
| `land_id` | `cs_cultivation_details` | Yes | Text |
| `season` | `cs_cultivation_details` | No | Code from the CROP_SEASON list below. Blank means the production season. |
| `commodity` | `cs_cultivation_details` | Yes | Code from the CROP_COMMODITY list below. |
| `crop_category` | `cs_cultivation_details` | No | Code from the CROP_CATEGORY list below. |
| `local_name` | `cs_cultivation_details` | No | Text |
| `scientific_name` | `cs_cultivation_details` | No | Text |
| `cultivation_type` | `cs_cultivation_details` | No | Code from the MACHINERY list below. |
| `seed_variety` | `cs_cultivation_details` | No | The variety (shown as "Variety"): code from the SEED_VARIETY list below. |
| `actual_fertilizer_type` | `cs_cultivation_details` | No | Code from the FERTILIZER_TYPE list below. |
| `water_source` | `cs_cultivation_details` | No | Code from the WATER_SOURCE list below. |
| `water_source_method` | `cs_cultivation_details` | No | Code from the WATER_SOURCE_METHOD list below. |
| `water_source_frequency` | `cs_cultivation_details` | No | Code from the WATER_SOURCE_FREQUENCY list below. |
| `da_name` | `cs_cultivation_details` | No | Text |
| `da_mobile_number` | `cs_cultivation_details` | No | Text |
| `supervisor_name` | `cs_cultivation_details` | No | Text |
| `supervisor_mobile_number` | `cs_cultivation_details` | No | Text |
| `land_area` | `cs_cultivation_details` | No | Number, digits and an optional decimal point. Required when `actual_crop_area` is given. |
| `actual_crop_area` | `cs_cultivation_details` | No | Number, digits and an optional decimal point |
| `actual_yield` | `cs_cultivation_details` | No | Number, digits and an optional decimal point |
| `actual_seed_qty` | `cs_cultivation_details` | No | Number, digits and an optional decimal point |
| `actual_fertilizer_qty` | `cs_cultivation_details` | No | Number, digits and an optional decimal point |
| `start_month` | `cs_cultivation_details` | No | Whole number |
| `start_day` | `cs_cultivation_details` | No | Whole number |
| `end_month` | `cs_cultivation_details` | No | Whole number |
| `end_day` | `cs_cultivation_details` | No | Whole number |
| `actual_growth_duration_days` | `cs_cultivation_details` | No | Whole number |
| `start_gc` | `cs_cultivation_details` | No | YYYY-MM-DD |
| `end_gc` | `cs_cultivation_details` | No | YYYY-MM-DD |
| `actual_cultivation_date` | `cs_cultivation_details` | No | YYYY-MM-DD |
| `is_plot_not_registered` | `cs_cultivation_details` | No | yes or no (also true/false, 1/0) |
| `cropping_system` | `cs_cultivation_details` | No | Code from the CROPPING_SYSTEM list below. |
| `actual_seed_class` | `cs_cultivation_details` | No | Code from the SEED_TYPE list below. |
| `actual_seed_source` | `cs_cultivation_details` | No | Code from the SEED_SOURCE list below. |
| `land_prep_method` | `cs_cultivation_details` | No | Code from the LAND_PREP_METHOD list below. Several values separated by a semicolon. |
| `is_planning_record_created` | `cs_cultivation_details` | No | yes or no (also true/false, 1/0). yes: the land is in Planning, so only `land_id` and `land_area` are kept and the Land ID must be in the farmer's Planning of the same crop year and season. no: the land columns below are kept. |
| `plot_category` | `cs_cultivation_details` | No | Code from the PLOT_CATEGORY list. Read when `is_planning_record_created` is not yes. |
| `ownership_type` | `cs_cultivation_details` | No | Code from the OWNERSHIP_TYPE list. Read when `is_planning_record_created` is not yes. |
| `soil_fertility_type` | `cs_cultivation_details` | No | Code from the SOIL_FERTILITY list. Read when `is_planning_record_created` is not yes. |
| `region` | `cs_cultivation_details` | No | The land's Region: Master Data geo unit id (P-code), for example ET04. Read when `is_planning_record_created` is not yes. |
| `zone` | `cs_cultivation_details` | No | The land's Zone: P-code, for example ET0404. Read when `is_planning_record_created` is not yes. |
| `woreda` | `cs_cultivation_details` | No | The land's Woreda: P-code, for example ET040404. Read when `is_planning_record_created` is not yes. |
| `kebele` | `cs_cultivation_details` | No | The land's Kebele: P-code, for example ET040404888003. Read when `is_planning_record_created` is not yes. |
| `latitude` | `cs_cultivation_details` | No | The land's latitude in decimal degrees, for example 9.0301. Read when `is_planning_record_created` is not yes. |
| `longitude` | `cs_cultivation_details` | No | The land's longitude in decimal degrees, for example 38.7469. Read when `is_planning_record_created` is not yes. |
| `crop_latitude` | `cs_cultivation_details` | No | The crop's latitude in decimal degrees. |
| `crop_longitude` | `cs_cultivation_details` | No | The crop's longitude in decimal degrees. |
| `cluster_<n>_land_id` | `cs_cultivation_cluster_details` | No | Text. The Land ID; **required when the group has any value**. |
| `cluster_<n>_name` | `cs_cultivation_cluster_details` | No | Text (Farmer production cluster name) |
| `cluster_<n>_reference` | `cs_cultivation_cluster_details` | No | Text |
| `cluster_<n>_fpc_type` | `cs_cultivation_cluster_details` | No | `GREEN` |
| `cluster_<n>_season` | `cs_cultivation_cluster_details` | No | Code from the CROP_SEASON list below. Blank means the production season; another season is refused. |
| `cluster_<n>_start_gc` | `cs_cultivation_cluster_details` | No | YYYY-MM-DD |
| `cluster_<n>_end_gc` | `cs_cultivation_cluster_details` | No | YYYY-MM-DD |
| `cluster_<n>_establishing_date` | `cs_cultivation_cluster_details` | No | YYYY-MM-DD, between `cluster_<n>_start_gc` and `cluster_<n>_end_gc`. |
| `cluster_<n>_region` | `cs_cultivation_cluster_details` | No | Master Data geo unit id (P-code), for example ET04 |
| `cluster_<n>_zone` | `cs_cultivation_cluster_details` | No | P-code, for example ET0404 |
| `cluster_<n>_woreda` | `cs_cultivation_cluster_details` | No | P-code, for example ET040404 |
| `cluster_<n>_kebele` | `cs_cultivation_cluster_details` | No | P-code, for example ET040404888003 |
| `cluster_<n>_sub_kebele` | `cs_cultivation_cluster_details` | No | Text |
| `cluster_<n>_agro_ecological_zone` | `cs_cultivation_cluster_details` | No | Code from the AGRO_ECOLOGICAL_ZONE list |
| `cluster_<n>_latitude` | `cs_cultivation_cluster_details` | No | Latitude in decimal degrees |
| `cluster_<n>_longitude` | `cs_cultivation_cluster_details` | No | Longitude in decimal degrees |
| `cluster_<n>_primary_commodity` | `cs_cultivation_cluster_details` | No | Code from the CROP_COMMODITY list below. |
| `cluster_<n>_secondary_commodity` | `cs_cultivation_cluster_details` | No | Code from the CROP_COMMODITY list below. |
| `cluster_<n>_area_timad` | `cs_cultivation_cluster_details` | No | Number (timad, 0.25 hectares). The registry works out Total cultivated area (hectares) from it. |
| `cluster_<n>_plan` | `cs_cultivation_cluster_details` | No | Number (planned area, hectares) |
| `cluster_<n>_collected_land` | `cs_cultivation_cluster_details` | No | Number (hectares) |
| `cluster_<n>_collected_quintal` | `cs_cultivation_cluster_details` | No | Number (quintal) |
| `cluster_<n>_collected_by_combiner` | `cs_cultivation_cluster_details` | No | Number (hectares) |
| `cluster_<n>_number_of_smallholders` | `cs_cultivation_cluster_details` | No | Whole number |
| `cluster_<n>_water_source` | `cs_cultivation_cluster_details` | No | Code from the WATER_SOURCE list |
| `cluster_<n>_water_source_method` | `cs_cultivation_cluster_details` | No | Code from the WATER_SOURCE_METHOD list |
| `cluster_<n>_water_source_frequency` | `cs_cultivation_cluster_details` | No | Code from the WATER_SOURCE_FREQUENCY list |
| `cluster_<n>_leader` | `cs_cultivation_cluster_details` | No | Text |
| `cluster_<n>_co_leader` | `cs_cultivation_cluster_details` | No | Text |
| `cluster_<n>_coordinator` | `cs_cultivation_cluster_details` | No | Text |
| `cluster_<n>_secretary` | `cs_cultivation_cluster_details` | No | Text |
| `cluster_<n>_da_name` | `cs_cultivation_cluster_details` | No | Text |
| `cluster_<n>_da_mobile_number` | `cs_cultivation_cluster_details` | No | Text |
| `cluster_<n>_supervisor_name` | `cs_cultivation_cluster_details` | No | Text |
| `cluster_<n>_supervisor_mobile_number` | `cs_cultivation_cluster_details` | No | Text |

Each `cluster_<n>_*` column exists for n = 1, 2 and 3 (for example `cluster_1_land_id`, `cluster_2_land_id`, `cluster_3_land_id`): up to three Cultivation clusters (Cultivation cluster details) in the same intake as the cultivation row. A group with any value becomes one row and needs its Land ID; leave a group blank to skip it. Same columns as the Planning clusters. Cluster ID and Total cultivated area (hectares) are filled by the registry. More than three: add them in the staff portal or by change request.

## Sowing intake (`crop_sowing_intake_import_template.csv`)

Import configuration: `file_import_to_crop_sowing_intake`.

| Column | Maps to | Required | Format or allowed codes |
|---|---|---|---|
| `farmer_id` | Farmer lookup (`crop_farmer_lookup`) | Yes | FR- followed by 12 digits, for example FR-000000000001 |
| `fayda_id` | Farmer lookup (`crop_farmer_lookup`) | Yes | A 12-digit FIN or a 16-digit FAN, digits only (spaces are dropped) |
| `crop_year` | Production Season (`cs_common_intake_season`) | Yes | Four-digit year, for example 2026 |
| `production_season` | Production Season (`cs_common_intake_season`) | Yes | Code from the CROP_SEASON list below. |
| `land_id` | `cs_sowing_details` | Yes | Text |
| `season` | `cs_sowing_details` | No | Code from the CROP_SEASON list below. Blank means the production season. |
| `commodity` | `cs_sowing_details` | Yes | Code from the CROP_COMMODITY list below. |
| `fertilizer_type` | `cs_sowing_details` | No | Code from the FERTILIZER_TYPE list below. |
| `cluster_name` | `cs_sowing_details` | No | Text |
| `cluster_season` | `cs_sowing_details` | No | Code from the CROP_SEASON list below. Required when `cluster_status` has CLUSTERED. |
| `da_name` | `cs_sowing_details` | No | Text |
| `da_mobile_number` | `cs_sowing_details` | No | Text |
| `supervisor_name` | `cs_sowing_details` | No | Text |
| `supervisor_mobile_number` | `cs_sowing_details` | No | Text |
| `area_sown` | `cs_sowing_details` | Yes | Number, digits and an optional decimal point |
| `fertilizer_qty` | `cs_sowing_details` | No | Number, digits and an optional decimal point |
| `cluster_area_hectare` | `cs_sowing_details` | No | Number, digits and an optional decimal point. Required when `cluster_area_sown` is given on a Clustered row. |
| `cluster_area_sown` | `cs_sowing_details` | No | Number, digits and an optional decimal point |
| `sowing_date` | `cs_sowing_details` | Yes | YYYY-MM-DD |
| `has_pest_disease` | `cs_sowing_details` | No | yes or no (also true/false, 1/0) |
| `cluster_has_pest_disease` | `cs_sowing_details` | No | yes or no (also true/false, 1/0) |
| `agro_ecological_zone` | `cs_sowing_details` | No | Code from the AGRO_ECOLOGICAL_ZONE list below. |
| `cluster_status` | `cs_sowing_details` | No | `CLUSTERED`, `INDEPENDENT`, or both separated by a semicolon (`CLUSTER` is read as `CLUSTERED`) |
| `cluster_land_id` | `cs_sowing_details` | No | Land ID (cluster) of a Clustered row. Blank: the row's `land_id` is used. |
| `is_land_recorded` | `cs_sowing_details` | No | "Is planning record created?" for the Independent Land ID: yes or no (also true/false, 1/0). yes keeps only the Land ID, which must be in the farmer's Planning or Cultivation of the same crop year and season; no keeps the land columns below. |
| `is_plot_not_registered` | `cs_sowing_details` | No | yes or no (also true/false, 1/0). Read when `is_land_recorded` is not yes. |
| `plot_category` | `cs_sowing_details` | No | Code from the PLOT_CATEGORY list. Read when `is_land_recorded` is not yes. |
| `ownership_type` | `cs_sowing_details` | No | Code from the OWNERSHIP_TYPE list. Read when `is_land_recorded` is not yes. |
| `land_area` | `cs_sowing_details` | No | Number, digits and an optional decimal point. Read when `is_land_recorded` is not yes. |
| `soil_fertility_type` | `cs_sowing_details` | No | Code from the SOIL_FERTILITY list. Read when `is_land_recorded` is not yes. |
| `region` | `cs_sowing_details` | No | The land's Region: Master Data geo unit id (P-code), for example ET04. Read when `is_land_recorded` is not yes. |
| `zone` | `cs_sowing_details` | No | The land's Zone: P-code, for example ET0404. Read when `is_land_recorded` is not yes. |
| `woreda` | `cs_sowing_details` | No | The land's Woreda: P-code, for example ET040404. Read when `is_land_recorded` is not yes. |
| `kebele` | `cs_sowing_details` | No | The land's Kebele: P-code, for example ET040404888003. Read when `is_land_recorded` is not yes. |
| `latitude` | `cs_sowing_details` | No | The land's latitude in decimal degrees. Read when `is_land_recorded` is not yes. |
| `longitude` | `cs_sowing_details` | No | The land's longitude in decimal degrees. Read when `is_land_recorded` is not yes. |
| `is_cluster_land_recorded` | `cs_sowing_details` | No | "Is planning record created?" for the Land ID (cluster): yes or no (also true/false, 1/0). yes keeps only the Land ID (cluster), which must be in the farmer's Cluster or Cultivation cluster records of the same crop year and season; no keeps the cluster location columns below. |
| `cluster_region` | `cs_sowing_details` | No | The cluster land's Region: P-code. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_zone` | `cs_sowing_details` | No | The cluster land's Zone: P-code. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_woreda` | `cs_sowing_details` | No | The cluster land's Woreda: P-code. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_kebele` | `cs_sowing_details` | No | The cluster land's Kebele: P-code. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_sub_kebele` | `cs_sowing_details` | No | Text. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_latitude` | `cs_sowing_details` | No | The cluster land's latitude in decimal degrees. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_longitude` | `cs_sowing_details` | No | The cluster land's longitude in decimal degrees. Read when `is_cluster_land_recorded` is not yes. |
| `infestation_<n>_land_id` | `cs_infestation_details` | No | Text. The Land ID; **required when the group has any value**. |
| `infestation_<n>_cluster_status` | `cs_infestation_details` | No | `CLUSTERED` or `INDEPENDENT` (`CLUSTER` is read as `CLUSTERED`) |
| `infestation_<n>_cluster_name` | `cs_infestation_details` | No | Text. Read for a Clustered row. |
| `infestation_<n>_commodity` | `cs_infestation_details` | No | Code from the CROP_COMMODITY list below. Read for an Independent row. |
| `infestation_<n>_type` | `cs_infestation_details` | No | Infestation type: `INFT_PEST`, `INFT_WEED` or `INFT_DISEASE` (INFESTATION_TYPE list) |
| `infestation_<n>_pest_type` | `cs_infestation_details` | No | Code from the PEST list. Pest rows. |
| `infestation_<n>_pest_name` | `cs_infestation_details` | No | Text. Pest rows. |
| `infestation_<n>_pesticide_method` | `cs_infestation_details` | No | Code from the PEST_CONTROL_ACTION list. Pest rows. |
| `infestation_<n>_pesticide_type` | `cs_infestation_details` | No | `insecticide`, `fungicide`, `herbicide`, `rodenticide`, `bactericide`, `nematicide`, `acaricide`, `molluscicide`, `termiticide`, `avicide`, `piscicide`, `algicide`, `virucide`. Pest rows. |
| `infestation_<n>_pesticide_name` | `cs_infestation_details` | No | Text. Pest rows. |
| `infestation_<n>_pesticide_frequency` | `cs_infestation_details` | No | Text. Pest rows. |
| `infestation_<n>_weed_type` | `cs_infestation_details` | No | Code from the WEED list. Weed rows. |
| `infestation_<n>_weed_name` | `cs_infestation_details` | No | Text. Weed rows. |
| `infestation_<n>_weed_control_method` | `cs_infestation_details` | No | `chemical_spray`, `hand_picking`, `early_harvesting`. Weed rows. |
| `infestation_<n>_weedicide_type` | `cs_infestation_details` | No | `pre_emergent`, `post_emergent`, `systemic`, `contact`, `graminicide`, `broadleaf`, `sedge`, `aquatic`, `foliar`, `soil`. Weed rows. |
| `infestation_<n>_weedicide_name` | `cs_infestation_details` | No | Text. Weed rows. |
| `infestation_<n>_weedicide_frequency` | `cs_infestation_details` | No | Text. Weed rows. |
| `infestation_<n>_disease_type` | `cs_infestation_details` | No | Code from the CROP_DISEASE list. Disease rows. |
| `infestation_<n>_disease_name` | `cs_infestation_details` | No | Text. Disease rows. |
| `infestation_<n>_disease_control_method` | `cs_infestation_details` | No | `chemical_spray`, `hand_picking`, `early_harvesting`. Disease rows. |
| `infestation_<n>_fungicide_type` | `cs_infestation_details` | No | `fungicide`, `bactericide`. Disease rows. |
| `infestation_<n>_fungicide_name` | `cs_infestation_details` | No | Text. Disease rows. |
| `infestation_<n>_disease_frequency_of_application` | `cs_infestation_details` | No | Text. Disease rows. |
| `infestation_<n>_growth_stage` | `cs_infestation_details` | No | Code from the CROP_GROWTH_STAGE list |
| `infestation_<n>_observation_date` | `cs_infestation_details` | No | YYYY-MM-DD, today or earlier |
| `infestation_<n>_severity_level` | `cs_infestation_details` | No | Code from the INFESTATION_SEVERITY list |
| `infestation_<n>_estimated_damage_pct` | `cs_infestation_details` | No | Estimated crop damage (%): a number from 0 to 100, without the `%` sign, for example `15` |

Each `infestation_<n>_*` column exists for n = 1, 2 and 3 (for example `infestation_1_land_id`, `infestation_2_land_id`, `infestation_3_land_id`): up to three Infestations (Infestation details) in the same intake as the sowing row. A group with any value becomes one row and needs its Land ID; leave a group blank to skip it. `infestation_type` becomes `infestation_<n>_type`. Fill the columns of the row's type (pest, weed or disease); the nutrient and climate fields are not on the form and not imported. More than three: add them in the staff portal or by change request.

## Harvesting intake (`crop_harvesting_intake_import_template.csv`)

Import configuration: `file_import_to_crop_harvesting_intake`.

| Column | Maps to | Required | Format or allowed codes |
|---|---|---|---|
| `farmer_id` | Farmer lookup (`crop_farmer_lookup`) | Yes | FR- followed by 12 digits, for example FR-000000000001 |
| `fayda_id` | Farmer lookup (`crop_farmer_lookup`) | Yes | A 12-digit FIN or a 16-digit FAN, digits only (spaces are dropped) |
| `crop_year` | Production Season (`cs_common_intake_season`) | Yes | Four-digit year, for example 2026 |
| `production_season` | Production Season (`cs_common_intake_season`) | Yes | Code from the CROP_SEASON list below. |
| `land_id` | `cs_harvest_details` | Yes | Text |
| `commodity` | `cs_harvest_details` | Yes | Code from the CROP_COMMODITY list below. |
| `cluster_name` | `cs_harvest_details` | No | Text |
| `da_name` | `cs_harvest_details` | No | Text |
| `da_mobile_number` | `cs_harvest_details` | No | Text |
| `supervisor_name` | `cs_harvest_details` | No | Text |
| `supervisor_mobile_number` | `cs_harvest_details` | No | Text |
| `area_harvested` | `cs_harvest_details` | No | Number, digits and an optional decimal point |
| `qty_harvested` | `cs_harvest_details` | Yes | Number, digits and an optional decimal point |
| `post_harvest_loss_pct` | `cs_harvest_details` | No | Number, digits and an optional decimal point |
| `qty_stored` | `cs_harvest_details` | No | Number, digits and an optional decimal point |
| `qty_sold` | `cs_harvest_details` | No | Number, digits and an optional decimal point |
| `cluster_area_harvested` | `cs_harvest_details` | No | Number, digits and an optional decimal point |
| `cluster_qty_harvested` | `cs_harvest_details` | No | Number, digits and an optional decimal point |
| `cluster_post_harvest_loss_pct` | `cs_harvest_details` | No | Number, digits and an optional decimal point |
| `cluster_qty_stored` | `cs_harvest_details` | No | Number, digits and an optional decimal point |
| `cluster_qty_sold` | `cs_harvest_details` | No | Number, digits and an optional decimal point |
| `harvest_date` | `cs_harvest_details` | Yes | YYYY-MM-DD |
| `cluster_harvest_date` | `cs_harvest_details` | No | YYYY-MM-DD |
| `crop_maturity_status` | `cs_harvest_details` | No | `READY_FOR_HARVEST`, `NOT_YET_READY_FOR_HARVEST` |
| `cluster_crop_maturity_status` | `cs_harvest_details` | No | `READY_FOR_HARVEST`, `NOT_YET_READY_FOR_HARVEST` |
| `cluster_status` | `cs_harvest_details` | No | `CLUSTERED`, `INDEPENDENT`, or both separated by a semicolon (`CLUSTER` is read as `CLUSTERED`) |
| `cluster_land_id` | `cs_harvest_details` | No | Land ID (cluster) of a Clustered row. Blank: the row's `land_id` is used. |
| `is_land_recorded` | `cs_harvest_details` | No | "Is planning record created?" for the Independent Land ID: yes or no (also true/false, 1/0). yes keeps only the Land ID, which must be in the farmer's Planning or Cultivation of the same crop year and season; no keeps the land columns below. |
| `is_plot_not_registered` | `cs_harvest_details` | No | yes or no (also true/false, 1/0). Read when `is_land_recorded` is not yes. |
| `plot_category` | `cs_harvest_details` | No | Code from the PLOT_CATEGORY list. Read when `is_land_recorded` is not yes. |
| `ownership_type` | `cs_harvest_details` | No | Code from the OWNERSHIP_TYPE list. Read when `is_land_recorded` is not yes. |
| `land_area` | `cs_harvest_details` | No | Number, digits and an optional decimal point. Read when `is_land_recorded` is not yes. |
| `soil_fertility_type` | `cs_harvest_details` | No | Code from the SOIL_FERTILITY list. Read when `is_land_recorded` is not yes. |
| `region` | `cs_harvest_details` | No | The land's Region: Master Data geo unit id (P-code), for example ET04. Read when `is_land_recorded` is not yes. |
| `zone` | `cs_harvest_details` | No | The land's Zone: P-code, for example ET0404. Read when `is_land_recorded` is not yes. |
| `woreda` | `cs_harvest_details` | No | The land's Woreda: P-code, for example ET040404. Read when `is_land_recorded` is not yes. |
| `kebele` | `cs_harvest_details` | No | The land's Kebele: P-code, for example ET040404888003. Read when `is_land_recorded` is not yes. |
| `latitude` | `cs_harvest_details` | No | The land's latitude in decimal degrees. Read when `is_land_recorded` is not yes. |
| `longitude` | `cs_harvest_details` | No | The land's longitude in decimal degrees. Read when `is_land_recorded` is not yes. |
| `is_cluster_land_recorded` | `cs_harvest_details` | No | "Is planning record created?" for the Land ID (cluster): yes or no (also true/false, 1/0). yes keeps only the Land ID (cluster), which must be in the farmer's Cluster or Cultivation cluster records of the same crop year and season; no keeps the cluster location columns below. |
| `cluster_region` | `cs_harvest_details` | No | The cluster land's Region: P-code. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_zone` | `cs_harvest_details` | No | The cluster land's Zone: P-code. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_woreda` | `cs_harvest_details` | No | The cluster land's Woreda: P-code. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_kebele` | `cs_harvest_details` | No | The cluster land's Kebele: P-code. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_sub_kebele` | `cs_harvest_details` | No | Text. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_latitude` | `cs_harvest_details` | No | The cluster land's latitude in decimal degrees. Read when `is_cluster_land_recorded` is not yes. |
| `cluster_longitude` | `cs_harvest_details` | No | The cluster land's longitude in decimal degrees. Read when `is_cluster_land_recorded` is not yes. |

## Code lists

The codes below are what Master Data serves (the `value_code` of each value, never the label). The template does not translate them; the registry checks every dropdown code against Master Data when the intake is saved (setting `validate_attribute_values`, on in the developer stack), so a code that Master Data does not hold fails the row with the column named. Only the yes/no columns, crop maturity status and the fixed infestation choices are listed in the tables above instead.

### CROP_SEASON

Master Data list `CROP_SEASON` as the ETH-OAN pack seeds it.

`SEASON_MEHER`, `SEASON_BELG`, `SEASON_IRRIGATION`

### CROP_CATEGORY

Master Data list `CROP_CATEGORY` as the ETH-OAN pack seeds it.

`CROPCAT_CEREAL`, `CROPCAT_FOOD_LEGUME`, `CROPCAT_OILSEED`, `CROPCAT_FRUIT_VEGETABLE`, `CROPCAT_ROOT_TUBER`, `CROPCAT_STIMULANT`, `CROPCAT_INDUSTRIAL`, `CROPCAT_SPICE_MEDICINAL_AROMATIC`, `CROPCAT_OTHER`

### CROP_COMMODITY

Master Data list `CROP_COMMODITY` as the ETH-OAN pack seeds it.

`CROP_TEFF`, `CROP_QUINOA`, `CROP_BREAD_WHEAT`, `CROP_DURUM_WHEAT`, `CROP_TRITICALE`, `CROP_EMMER_WHEAT`, `CROP_BUCKWHEAT`, `CROP_BARLEY`, `CROP_MALT_BARLEY`, `CROP_SORGHUM`, `CROP_FINGER_MILLET`, `CROP_PEARL_MILLET`, `CROP_FOXTAIL_MILLET`, `CROP_MAIZE`, `CROP_RICE`, `CROP_FABA_BEAN`, `CROP_CHICKPEA`, `CROP_LENTIL`, `CROP_FIELD_PEA`, `CROP_DEKOKO`, `CROP_COWPEA`, `CROP_HARICOT_BEAN`, `CROP_GRASS_PEA`, `CROP_MUNG_BEAN`, `CROP_ADZUKI_BEAN`, `CROP_LIMA_BEAN`, `CROP_COMMON_BEAN`, `CROP_NOUG`, `CROP_LINSEED`, `CROP_RAPESEED`, `CROP_ETHIOPIAN_MUSTARD`, `CROP_SUNFLOWER`, `CROP_SAFFLOWER`, `CROP_SOYBEAN`, `CROP_SESAME`, `CROP_GROUNDNUT`, `CROP_WINE_GRAPE`, `CROP_PEACH`, `CROP_BANANA`, `CROP_MANGO`, `CROP_PINEAPPLE`, `CROP_AVOCADO`, `CROP_ZIZIPHUS`, `CROP_FIG`, `CROP_PAPAYA`, `CROP_DATE_PALM`, `CROP_GARLIC`, `CROP_SHALLOT`, `CROP_CARROT`, `CROP_LETTUCE`, `CROP_SNAP_BEAN`, `CROP_CAULIFLOWER`, `CROP_SNOW_PEA`, `CROP_PEPPER`, `CROP_TOMATO`, `CROP_ONION`, `CROP_CABBAGE`, `CROP_WATERMELON`, `CROP_MUSKMELON`, `CROP_GREEN_COURGETTE`, `CROP_YELLOW_COURGETTE`, `CROP_BROCCOLI`, `CROP_SNAP_PEA`, `CROP_SWEET_CORN`, `CROP_FINE_BUSH_BEAN`, `CROP_OKRA`, `CROP_ANCHOTE`, `CROP_AMARANTH`, `CROP_PAK_CHOI`, `CROP_EGGPLANT`, `CROP_CUCUMBER`, `CROP_SUMMER_SQUASH`, `CROP_POTATO`, `CROP_SWEET_POTATO`, `CROP_RED_BEET`, `CROP_TARO`, `CROP_CASSAVA`, `CROP_ENSET`, `CROP_YAM`, `CROP_COFFEE`, `CROP_COTTON`, `CROP_KENAF`, `CROP_VERNONIA`, `CROP_CASTOR`, `CROP_CAMELINA`, `CROP_SUGARCANE`, `CROP_TOBACCO`, `CROP_CACAO`, `CROP_SWEET_ANNIE`, `CROP_PYRETHRUM`, `CROP_AFRICAN_MARIGOLD`, `CROP_CHAMOMILE`, `CROP_STEVIA`, `CROP_HIBISCUS`, `CROP_CITRONELLA_GRASS`, `CROP_LEMONGRASS`, `CROP_PEPPERMINT`, `CROP_SPEARMINT`, `CROP_JAPANESE_MINT`, `CROP_SPANISH_MINT`, `CROP_GERANIUM`, `CROP_LEMON_VERBENA`, `CROP_LAVENDER`, `CROP_MARJORAM_OREGANO`, `CROP_SAGE`, `CROP_ROSEMARY`, `CROP_LEMON_SCENTED_EUCALYPTUS`, `CROP_PALMAROSA`, `CROP_BLACK_PEPPER`, `CROP_GINGER`, `CROP_TURMERIC`, `CROP_CARDAMOM`, `CROP_VANILLA`, `CROP_CORIANDER`, `CROP_BLACK_CUMIN`, `CROP_WHITE_CUMIN`, `CROP_FENUGREEK`, `CROP_BASIL`, `CROP_KORARIMA`, `CROP_ROSE`, `CROP_OTHER`, `CROP_OAT`, `CROP_PIGEON_PEA`, `CROP_ALFALFA`, `CROP_BRACHIARIA`

### SEED_VARIETY

Master Data list `SEED_VARIETY`.

Too long to repeat here: use the `value_code` of each value in `packs/ETH-OAN/domains/agriculture/seed_variety.json` of the openg2p-data repository (for example `VAR_TEFF_QUNCHO`).

### SOIL_FERTILITY

Master Data list `SOIL_FERTILITY` as the ETH-OAN pack seeds it.

`SF_HIGH`, `SF_MEDIUM`, `SF_LOW`

### FERTILIZER_TYPE

Master Data list `FERTILIZER_TYPE` as the ETH-OAN pack seeds it.

`FERT_UREA`, `FERT_DAP`, `FERT_NPS`, `FERT_NPSB`, `FERT_NPSZNB`, `FERT_COMPOST`, `FERT_MANURE`, `FERT_BIO_RHIZO`, `FERT_ZINC_BORON`, `FERT_LIME`

### WATER_SOURCE

Master Data list `WATER_SOURCE` as the ETH-OAN pack seeds it.

`WS_RAINFED`, `WS_IRRIGATION_GROUND`, `WS_IRRIGATION_SURFACE`, `WS_WELL_GROUND`, `WS_WATER_HARVESTING`, `WS_SURFACE_WATER`

### PLOT_CATEGORY

Master Data list `PLOT_CATEGORY` as the ETH-OAN pack seeds it.

`ANNUAL_CROP`, `PERENNIAL_CROP`, `BIENNIAL_CROP`

### OWNERSHIP_TYPE

Master Data list `OWNERSHIP_TYPE` as the ETH-OAN pack seeds it.

`OWNER`, `TENANT`, `CROP_SHARING`, `FAMILY_GIFT`

### WATER_SOURCE_METHOD

Master Data list `WATER_SOURCE_METHOD` as the ETH-OAN pack seeds it.

`SURFACE`, `SPRINKLER`, `DRIP`, `MANUAL`, `OTHER`

### WATER_SOURCE_FREQUENCY

Master Data list `WATER_SOURCE_FREQUENCY` as the ETH-OAN pack seeds it.

`DAILY`, `WEEKLY`, `BIWEEKLY`, `MONTHLY`, `AS_NEEDED`, `OTHER`

### MACHINERY

Master Data list `MACHINERY` as the ETH-OAN pack seeds it.

`OXEN_TILLAGE`, `EQUINE_OTHER`, `TRACTOR_PLOUGHING`, `POWER_TILLER`, `COMBINE_HARVESTER`, `THRASHING_MACHINE`, `FAMILY_LABOR`, `DEBO_JIGI`, `HIRED_LABOR`, `TRACTOR_OXEN`, `OXEN_MANUAL`

### LAND_PREP_METHOD

Master Data list `LAND_PREP_METHOD` as the ETH-OAN pack seeds it.

`TRADITIONAL_MARESHA_PLOUGHING`, `TRACTOR_DISC_MOLDBOARD_PLOUGHING`, `MANUAL_DIGGING`, `SHILSHALO`, `RIDGING_FURROWING`, `MANUAL_LEVELING`, `MINIMUM_TILLAGE`, `SOIL_WATER_CONSERVATION_STRUCTURES`, `BIOLOGICAL_MULCHING`

### CROPPING_SYSTEM

Master Data list `CROPPING_SYSTEM` as the ETH-OAN pack seeds it.

`CSYS_PURE`, `CSYS_MIXED`, `CSYS_INTERCROPPED`

### SEED_TYPE

Master Data list `SEED_TYPE` as the ETH-OAN pack seeds it.

`SEED_IMPROVED`, `SEED_LOCAL`, `SEED_HYBRID`

### SEED_SOURCE

Master Data list `SEED_SOURCE` as the ETH-OAN pack seeds it.

`SEEDSRC_COOPERATIVE`, `SEEDSRC_GOVERNMENT`, `SEEDSRC_MARKET`, `SEEDSRC_OWN_SAVED`, `SEEDSRC_NGO`, `SEEDSRC_NEIGHBOUR`

### AGRO_ECOLOGICAL_ZONE

Master Data list `AGRO_ECOLOGICAL_ZONE` as the ETH-OAN pack seeds it.

`AEZ_BEREHA`, `AEZ_KOLLA`, `AEZ_WEYNA_DEGA`, `AEZ_DEGA`, `AEZ_WURCH`

### CLUSTER_STATUS

Master Data list `CLUSTER_STATUS` as the ETH-OAN pack seeds it.

`CLUSTERED`, `INDEPENDENT`

### INFESTATION_TYPE

Master Data list `INFESTATION_TYPE` as the ETH-OAN pack seeds it.

`INFT_PEST`, `INFT_DISEASE`, `INFT_WEED`

### PEST

Master Data list `PEST` as the ETH-OAN pack seeds it.

`APHIDS`, `WHITEFLIES`, `THRIPS`, `STEM_BORER`, `LEAF_MINER`, `ARMYWORM`, `CUTWORM`, `BOLLWORM`, `BEETLES`, `MEALYBUGS`, `GRASSHOPPERS`, `LEAFHOPPER_JASSIDS`, `RATS`, `FIELD_MOUSE`, `SNAILS`, `SLUGS`, `LEAF_SPOT`, `POWDERY_MILDEW`, `DOWNY_MILDEW`, `RUST`, `BLIGHT`, `WILT`, `MOSAIC_VIRUS`

### PEST_CONTROL_ACTION

Master Data list `PEST_CONTROL_ACTION` as the ETH-OAN pack seeds it.

`CTRL_CHEMICAL`, `CTRL_BIOLOGICAL`, `CTRL_CULTURAL`, `CTRL_NONE`

### WEED

Master Data list `WEED` as the ETH-OAN pack seeds it.

`ANNUAL`, `BIENNIAL`, `PERENNIAL`, `KHARIF_SUMMER`, `RABI_WINTER`, `YEAR_ROUND`, `GRASSY`, `SEDGE`, `BROADLEAF`, `AQUATIC`, `TERRESTRIAL`, `PARASITIC`, `EPIPHYTIC`, `NOXIOUS`, `POISONOUS`, `ALLELOPATHIC`, `INVASIVE`, `CLIMBING`, `ROSETTE`, `CREEPING`, `ERECT`

### CROP_DISEASE

Master Data list `CROP_DISEASE` as the ETH-OAN pack seeds it.

`LEAF_SPOT`, `POWDERY_MILDEW`, `DOWNY_MILDEW`, `RUST`, `BLIGHT`, `WILT`, `MOSAIC_VIRUS`, `SMUT`, `ANTHRACNOSE`, `ROOT_ROT`

### CROP_GROWTH_STAGE

Master Data list `CROP_GROWTH_STAGE` as the ETH-OAN pack seeds it.

`GS_EMERGENCE`, `GS_VEGETATIVE`, `GS_FLOWERING`, `GS_GRAIN_FILLING`, `GS_MATURITY`

### INFESTATION_SEVERITY

Master Data list `INFESTATION_SEVERITY` as the ETH-OAN pack seeds it.

`SEV_LOW`, `SEV_MEDIUM`, `SEV_HIGH`

## Where the pieces live

| Piece | Where |
|---|---|
| Import configuration (one row per form) | `meta_data/registry-configurations/g2p_registry_import_file_configurations.sql` |
| Data models `file_import_to_crop_<form>_intake` | `meta_data/data-models/data_models.sql` |
| Key paths (`$.headers.*`, payload `$.body`) | `meta_data/registry-inbound-message-rules/incoming_model_key_paths.sql` |
| Semantic patterns (pass-through enricher) | `meta_data/registry-inbound-message-rules/incoming_model_semantic_patterns.sql` |
| Incoming templates and their documents | `incoming_templates.sql`, `meta_data/register-metadata/g2p_registry_documents.sql` |
| Jinja templates | `templates/crop_file_import_<form>_intake.j2` |
| Tests | `cropsown-extension/tests/test_file_import.py` |

The ODK connector keeps its own data model `odk_to_crop_intake`; file import does not touch it.

## Operating notes

- The import worker sends rows as the sender `Staff Portal`. That sender must exist as an active partner in Partner Management, or the first row aborts the whole file.
- The worker supplies the service token for the approval workflow itself (the Crop Sown extension requests one from the approval engine when a worker has no user token), so the worker needs the `REGISTRY_FARMER_REFERENCE_AWE_*` settings.
- Sample rows are not kept here. Sample import files belong in the openg2p-data repository.
