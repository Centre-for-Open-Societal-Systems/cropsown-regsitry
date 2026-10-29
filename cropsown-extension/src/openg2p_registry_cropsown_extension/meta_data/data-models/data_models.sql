-- When a request does not name its data model, the platform tries every row's
-- pattern, so each pattern must be "<jsonpath>=><regex>": a bare "*" makes the
-- matcher raise "Invalid pattern format" and every such ingest fails with
-- SYS-ERR-001. Both patterns are therefore valid and part of the upsert, so
-- databases seeded with the old pattern are repaired by a plain upgrade.
-- The ODK connectors send sender_id CropSown (data model ODK_TO_CROP_INTAKE), so
-- the ODK model is keyed on the sender, as the Livestock one is.
-- The response template is upserted: rows created before it was set kept an
-- empty one, and with no template the Partner API cannot serialise its reply
-- (a datetime in the header), answers 500, and the ODK connector resends the
-- same submission on every poll.
INSERT INTO "public"."data_models" ("data_model_id","data_model_mnemonic","pattern_for_data_model","response_template_document_id","is_active") VALUES
('c331ba96-ac35-4014-9d13-4ef327f6b79b','DCI','$.body.header.data_model=>^DCI$','1f0953d4-f0fb-4336-a126-4d0519a74ffc','TRUE'),
('odk_to_crop_intake','ODK_TO_CROP_INTAKE','$.body.header.sender_id=>^CropSown$','1f0953d4-f0fb-4336-a126-4d0519a74ffc','TRUE')
ON CONFLICT (data_model_mnemonic) DO UPDATE SET "pattern_for_data_model" = EXCLUDED."pattern_for_data_model",
  "response_template_document_id" = EXCLUDED."response_template_document_id";

-- DCI response template: dci_commons_response.json.j2

-- FILE_IMPORT_TO_CROP_*_INTAKE: the data models of the native "Import from file" menu, one per intake form
-- (a data model holds one incoming template per register, so the template cannot tell the forms apart).
-- The import worker names the data model itself; the pattern is only the one the worker's sender matches.
-- The ODK model above is not used by file import.
INSERT INTO "public"."data_models" ("data_model_id","data_model_mnemonic","pattern_for_data_model","response_template_document_id","is_active") VALUES
('file_import_to_crop_planning_intake','FILE_IMPORT_TO_CROP_PLANNING_INTAKE','$.headers.sender_id=>^Staff Portal$',NULL,TRUE),
('file_import_to_crop_cultivation_intake','FILE_IMPORT_TO_CROP_CULTIVATION_INTAKE','$.headers.sender_id=>^Staff Portal$',NULL,TRUE),
('file_import_to_crop_sowing_intake','FILE_IMPORT_TO_CROP_SOWING_INTAKE','$.headers.sender_id=>^Staff Portal$',NULL,TRUE),
('file_import_to_crop_harvesting_intake','FILE_IMPORT_TO_CROP_HARVESTING_INTAKE','$.headers.sender_id=>^Staff Portal$',NULL,TRUE)
ON CONFLICT ("data_model_id") DO UPDATE SET "data_model_mnemonic" = EXCLUDED."data_model_mnemonic", "pattern_for_data_model" = EXCLUDED."pattern_for_data_model", "is_active" = EXCLUDED."is_active";
