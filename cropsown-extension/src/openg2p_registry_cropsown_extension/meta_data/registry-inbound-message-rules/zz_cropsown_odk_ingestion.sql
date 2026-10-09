-- ODK submissions from the connector service become Crop Sown intakes.
--
-- The connector (openg2p-connector-service) runs one pipeline per stage form
-- and posts each submission to the Partner API as
--
--   POST /partner/ingest_data?data_model=CSR_DATA_MODEL
--   {"header":  {"message_id": "<form id>:<instance id>", "sender_id": ..., ...},
--    "message": {"payload": {<the ODK submission, repeat groups expanded>}}}
--
-- The Partner API wraps the request as {"body": <request>}, so every path below
-- starts at $.body. The form id at the front of message_id picks the stage's
-- intake form (planning, cultivation and land prep, sowing, harvest); the
-- celery worker then renders csr_odk_transform.j2 from the templates bucket.
--
-- These are the rows the dev environment was configured with by hand, with the
-- same ids, so a fresh environment comes up able to ingest without that manual
-- step. Every row is upserted on its fixed id, so a re-run changes nothing.
-- The partner the connector posts as (crop-partner) lives in Master Data, which
-- db-seed does not write: see ci/connector/README.md.

INSERT INTO "public"."data_models" (
    "data_model_id", "data_model_mnemonic", "pattern_for_data_model",
    "response_template_document_id", "is_active"
) VALUES (
    -- The DCI commons response template answers the connector.
    'CSR_DATA_MODEL', 'CSR_DATA_MODEL', '$.body.header.sender_id=>^.*$',
    '1f0953d4-f0fb-4336-a126-4d0519a74ffc', TRUE
) ON CONFLICT ("data_model_id") DO UPDATE SET
    "data_model_mnemonic" = EXCLUDED."data_model_mnemonic",
    "pattern_for_data_model" = EXCLUDED."pattern_for_data_model",
    "response_template_document_id" = EXCLUDED."response_template_document_id",
    "is_active" = EXCLUDED."is_active";

INSERT INTO "public"."incoming_model_key_paths" (
    "key_path_id", "data_model_id", "key_path_for_message_id", "key_path_for_sender",
    "key_path_for_signature", "key_path_for_signature_payload", "is_list",
    "key_path_for_list_elements"
) VALUES (
    'csr_key_path', 'CSR_DATA_MODEL',
    '$.body.header.message_id', '$.body.header.sender_id',
    '$.body.header.signature', '$.body.message', FALSE, ''
) ON CONFLICT ("key_path_id") DO UPDATE SET
    "data_model_id" = EXCLUDED."data_model_id",
    "key_path_for_message_id" = EXCLUDED."key_path_for_message_id",
    "key_path_for_sender" = EXCLUDED."key_path_for_sender",
    "key_path_for_signature" = EXCLUDED."key_path_for_signature",
    "key_path_for_signature_payload" = EXCLUDED."key_path_for_signature_payload",
    "is_list" = EXCLUDED."is_list",
    "key_path_for_list_elements" = EXCLUDED."key_path_for_list_elements";

-- One pattern per stage form, all on the CropSown register.
INSERT INTO "public"."incoming_model_semantic_patterns" (
    "semantic_pattern_id", "data_model_id", "register_id", "intake_form_id",
    "section_id", "pattern_for_register", "pattern_for_intake_form",
    "pattern_for_section", "key_path_for_business_payload",
    "raw_payload_enricher_class"
) VALUES
    ('SP-ODK-CROPSOWN-1', 'CSR_DATA_MODEL', '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
     '5bf0068c-ce19-46f8-874c-7147997f793b', NULL, NULL,
     '$.body.header.message_id=>^crop_sown_registry_plan:.*$', NULL,
     '$.body.message.payload', 'G2PDciCropSownCreateEnricherService'),
    ('SP-ODK-CROPSOWN-PREP', 'CSR_DATA_MODEL', '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
     '6be15ab9-0f1b-4c38-995f-395d52a1b17a', NULL, NULL,
     '$.body.header.message_id=>^crop_sown_registry_prep:.*$', NULL,
     '$.body.message.payload', 'G2PDciCropSownCreateEnricherService'),
    ('SP-ODK-CROPSOWN-SOWN', 'CSR_DATA_MODEL', '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
     '4a7c2c98-0ffb-41d8-8fea-f22349823675', NULL, NULL,
     '$.body.header.message_id=>^crop_sown_registry_sown:.*$', NULL,
     '$.body.message.payload', 'G2PDciCropSownCreateEnricherService'),
    ('SP-ODK-CROPSOWN-HARVEST', 'CSR_DATA_MODEL', '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
     '52150a37-153d-496d-9cd9-2a3815d6e13b', NULL, NULL,
     '$.body.header.message_id=>^crop_sown_registry_harvest:.*$', NULL,
     '$.body.message.payload', 'G2PDciCropSownCreateEnricherService')
ON CONFLICT ("semantic_pattern_id") DO UPDATE SET
    "data_model_id" = EXCLUDED."data_model_id",
    "register_id" = EXCLUDED."register_id",
    "intake_form_id" = EXCLUDED."intake_form_id",
    "pattern_for_intake_form" = EXCLUDED."pattern_for_intake_form",
    "key_path_for_business_payload" = EXCLUDED."key_path_for_business_payload",
    "raw_payload_enricher_class" = EXCLUDED."raw_payload_enricher_class";

-- The template catalogue row; db-seed uploads the object (LOAD_TEMPLATES)
-- under the same key.
INSERT INTO "public"."g2p_registry_documents" (
    "document_id", "document_store_id", "bucket", "source_filename",
    "created_by", "created_at"
) VALUES (
    '7e3c1a52-0d4b-4c1e-9a6f-c5d0d1a0c5a1', 'csr_odk_transform.j2', 'templates',
    'csr_odk_transform.j2', 'seeder', '2026-10-07 03:51:16'
) ON CONFLICT ("document_id") DO UPDATE SET
    "document_store_id" = EXCLUDED."document_store_id",
    "bucket" = EXCLUDED."bucket";

INSERT INTO "public"."incoming_templates" (
    "template_id", "register_id", "data_model_id", "template_document_id",
    "jsonld_expansion_required", "created_at", "updated_at"
) VALUES (
    'IN-TMPL-ODK-CSR-1', '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
    'CSR_DATA_MODEL', '7e3c1a52-0d4b-4c1e-9a6f-c5d0d1a0c5a1',
    FALSE, '2026-10-07 03:51:16', NULL
) ON CONFLICT ("template_id") DO UPDATE SET
    "register_id" = EXCLUDED."register_id",
    "data_model_id" = EXCLUDED."data_model_id",
    "template_document_id" = EXCLUDED."template_document_id",
    "jsonld_expansion_required" = EXCLUDED."jsonld_expansion_required";
