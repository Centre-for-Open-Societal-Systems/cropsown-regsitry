-- The response template is upserted: rows created before it was set kept an
-- empty one, and with no template the Partner API cannot serialise its reply
-- (a datetime in the header), answers 500, and the ODK connector resends the
-- same submission on every poll.
INSERT INTO "public"."data_models" ("data_model_id","data_model_mnemonic","pattern_for_data_model","response_template_document_id","is_active") VALUES
('c331ba96-ac35-4014-9d13-4ef327f6b79b','DCI','*','1f0953d4-f0fb-4336-a126-4d0519a74ffc','TRUE'),
('e442ca96-ac35-4014-9d13-4ef327f6b79c','CSR_DATA_MODEL','*','1f0953d4-f0fb-4336-a126-4d0519a74ffc','TRUE')
ON CONFLICT (data_model_mnemonic) DO UPDATE SET "response_template_document_id" = EXCLUDED."response_template_document_id";

-- DCI response template: dci_commons_response.json.j2
