INSERT INTO "public"."g2p_registry_documents" ("document_id","document_store_id","bucket","source_filename","created_by","created_at") VALUES
('1f0953d4-f0fb-4336-a126-4d0519a74ffc','dci_commons_response.json.j2','templates','dci_commons_response.json.j2','seeder','2026-04-01 00:00:00'),
('3b7c1d20-5c0e-4c1b-9f2e-8a1c6d5e4f30','dci_to_openg2p_cropsown.json.j2','templates','dci_to_openg2p_cropsown.json.j2','seeder','2026-04-01 00:00:00'),
('4c8d2e31-6d1f-4d2c-a03f-9b2d7e6f5041','openg2p_cropsown_to_dci.json.j2','templates','openg2p_cropsown_to_dci.json.j2','seeder','2026-04-01 00:00:00')
ON CONFLICT (document_id) DO NOTHING;

-- Document row for the ODK Central transform template; upserted so a re-run keeps the file name current.
INSERT INTO "public"."g2p_registry_documents" ("document_id","document_store_id","bucket","source_filename","created_by","created_at") VALUES
('odk_to_crop_intake_document','odk_to_crop_intake.j2','templates','odk_to_crop_intake.j2','seeder','2026-04-01 00:00:00')
ON CONFLICT (document_id) DO UPDATE SET
    document_store_id = EXCLUDED.document_store_id,
    source_filename = EXCLUDED.source_filename;

-- FILE_IMPORT_TO_CROP_*_INTAKE: Jinja templates of the native file import (crop_ prefix: the registries share one templates bucket).
INSERT INTO "public"."g2p_registry_documents" ("document_id","document_store_id","bucket","source_filename","created_by","created_at") VALUES
('file_import_to_crop_planning_intake_document','crop_file_import_planning_intake.j2','templates','crop_file_import_planning_intake.j2','seeder','2026-10-29 00:00:00'),
('file_import_to_crop_cultivation_intake_document','crop_file_import_cultivation_intake.j2','templates','crop_file_import_cultivation_intake.j2','seeder','2026-10-29 00:00:00'),
('file_import_to_crop_sowing_intake_document','crop_file_import_sowing_intake.j2','templates','crop_file_import_sowing_intake.j2','seeder','2026-10-29 00:00:00'),
('file_import_to_crop_harvesting_intake_document','crop_file_import_harvesting_intake.j2','templates','crop_file_import_harvesting_intake.j2','seeder','2026-10-29 00:00:00')
ON CONFLICT ("document_id") DO UPDATE SET
    document_store_id = EXCLUDED.document_store_id,
    source_filename = EXCLUDED.source_filename;
