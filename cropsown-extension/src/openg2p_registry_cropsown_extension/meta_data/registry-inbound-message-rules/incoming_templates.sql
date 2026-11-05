INSERT INTO "public"."incoming_templates" ("template_id","register_id","data_model_id","template_document_id","jsonld_expansion_required","created_at","updated_at") VALUES
('IN-TMPL-1','6b06a95a-9a6c-5a33-a33d-c1625716c59c','c331ba96-ac35-4014-9d13-4ef327f6b79b','3b7c1d20-5c0e-4c1b-9f2e-8a1c6d5e4f30','FALSE','2026-05-07 04:31:27.828397',NULL)
ON CONFLICT (template_id) DO NOTHING;

-- ODK_TO_CROP_INTAKE: odk_to_crop_intake.j2
INSERT INTO "public"."incoming_templates" ("template_id","register_id","data_model_id","template_document_id","jsonld_expansion_required","created_at","updated_at") VALUES
('odk_to_crop_intake_template','6b06a95a-9a6c-5a33-a33d-c1625716c59c','odk_to_crop_intake','odk_to_crop_intake_document','FALSE','2026-10-12 00:00:00',NULL)
ON CONFLICT (template_id) DO UPDATE SET
    "register_id" = EXCLUDED."register_id",
    "data_model_id" = EXCLUDED."data_model_id",
    "template_document_id" = EXCLUDED."template_document_id";

-- DCI: dci_to_openg2p_cropsown.json.j2

-- FILE_IMPORT_TO_CROP_*_INTAKE: crop_file_import_<form>_intake.j2
INSERT INTO "public"."incoming_templates" ("template_id","register_id","data_model_id","template_document_id","jsonld_expansion_required","created_at","updated_at") VALUES
('file_import_to_crop_planning_intake_template','6b06a95a-9a6c-5a33-a33d-c1625716c59c','file_import_to_crop_planning_intake','file_import_to_crop_planning_intake_document','FALSE','2026-10-29 00:00:00',NULL),
('file_import_to_crop_cultivation_intake_template','6b06a95a-9a6c-5a33-a33d-c1625716c59c','file_import_to_crop_cultivation_intake','file_import_to_crop_cultivation_intake_document','FALSE','2026-10-29 00:00:00',NULL),
('file_import_to_crop_sowing_intake_template','6b06a95a-9a6c-5a33-a33d-c1625716c59c','file_import_to_crop_sowing_intake','file_import_to_crop_sowing_intake_document','FALSE','2026-10-29 00:00:00',NULL),
('file_import_to_crop_harvesting_intake_template','6b06a95a-9a6c-5a33-a33d-c1625716c59c','file_import_to_crop_harvesting_intake','file_import_to_crop_harvesting_intake_document','FALSE','2026-10-29 00:00:00',NULL)
ON CONFLICT (template_id) DO UPDATE SET
    "register_id" = EXCLUDED."register_id",
    "data_model_id" = EXCLUDED."data_model_id",
    "template_document_id" = EXCLUDED."template_document_id",
    "jsonld_expansion_required" = EXCLUDED."jsonld_expansion_required";
