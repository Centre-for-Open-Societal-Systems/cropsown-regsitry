-- Pre-configured "Import from file" entries for the CropSown Registry intake forms.
-- Each of the 4 intake forms has its own file-import data model (file_import_to_crop_<form>_intake),
-- whose key paths, pattern and Jinja template take one flat CSV/Excel row per intake. The ODK data
-- model (odk_to_crop_intake) belongs to the ODK connector and is not used here. The configuration
-- ids are kept, so a database that already holds these rows is updated in place on upgrade.
-- Columns: docs/file-import.md.

INSERT INTO g2p_registry_import_file_configurations (
    import_file_configuration_id,
    register_id,
    form_id,
    data_model_id,
    import_file_template_mnemonic,
    import_file_template_description
) VALUES
(
    '9ad583e8-b792-48f2-aeab-749156903a1f',
    '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
    '5bf0068c-ce19-46f8-874c-7147997f793b',
    'file_import_to_crop_planning_intake',
    'file_import_to_crop_planning_intake',
    'Import planning intakes from a CSV or Excel file, one row per intake'
),
(
    'c0755be4-bcea-4d8e-9bdf-f91f41bf1e42',
    '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
    '6be15ab9-0f1b-4c38-995f-395d52a1b17a',
    'file_import_to_crop_cultivation_intake',
    'file_import_to_crop_cultivation_intake',
    'Import cultivation intakes from a CSV or Excel file, one row per intake'
),
(
    'be46f3fd-b78d-4308-bf86-91f8d665a9ab',
    '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
    '4a7c2c98-0ffb-41d8-8fea-f22349823675',
    'file_import_to_crop_sowing_intake',
    'file_import_to_crop_sowing_intake',
    'Import sowing intakes from a CSV or Excel file, one row per intake'
),
(
    '8fb0d6f0-8c6d-42df-99c3-6147390d6413',
    '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
    '52150a37-153d-496d-9cd9-2a3815d6e13b',
    'file_import_to_crop_harvesting_intake',
    'file_import_to_crop_harvesting_intake',
    'Import harvesting intakes from a CSV or Excel file, one row per intake'
)
ON CONFLICT (import_file_configuration_id) DO UPDATE SET
    register_id = EXCLUDED.register_id,
    form_id = EXCLUDED.form_id,
    data_model_id = EXCLUDED.data_model_id,
    import_file_template_mnemonic = EXCLUDED.import_file_template_mnemonic,
    import_file_template_description = EXCLUDED.import_file_template_description;
