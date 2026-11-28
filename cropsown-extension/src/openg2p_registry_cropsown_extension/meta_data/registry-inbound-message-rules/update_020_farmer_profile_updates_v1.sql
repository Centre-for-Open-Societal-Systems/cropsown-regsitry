-- FARMER_PROFILE_UPDATES_V1: the Farmer registry's change notice under
-- its readable name (event type and WebSub topic farmer.profile.updates.v1;
-- the hub derives the Kafka topic farmer_profile_updates_v1). It is
-- received next to FARMER_CHANGED_V1 and FARMER_REFERENCE_CHANGED_V1, whose patterns do
-- not match this event type, so exactly one data model answers each notice. The two
-- older names stay accepted until every sender has moved over. Same key path, routing,
-- response and update templates as FARMER_CHANGED_V1.
-- Ids are uuid5 over the URL namespace of
-- https://oan.invalid/seed/inbound/farmer.profile.updates.v1/<row kind>.
INSERT INTO public.data_models ("data_model_id","data_model_mnemonic","pattern_for_data_model","response_template_document_id","is_active") VALUES
('8cceae40-aa16-5d0a-a0b6-31e2e3ccbfb0','FARMER_PROFILE_UPDATES_V1','$.body.message.payload.event_type=>^farmer[.]profile[.]updates[.]v1$','crop_farmer_changed_v1_response_document',TRUE)
ON CONFLICT ("data_model_id") DO UPDATE SET "data_model_mnemonic" = EXCLUDED."data_model_mnemonic", "pattern_for_data_model" = EXCLUDED."pattern_for_data_model", "response_template_document_id" = EXCLUDED."response_template_document_id", "is_active" = EXCLUDED."is_active";

INSERT INTO public.incoming_model_key_paths ("key_path_id","data_model_id","key_path_for_message_id","key_path_for_sender","key_path_for_signature","key_path_for_signature_payload","is_list","key_path_for_list_elements") VALUES
('b6a3dd3c-f8c2-522a-96dd-5e426a6b5b32','8cceae40-aa16-5d0a-a0b6-31e2e3ccbfb0','$.body.header.message_id','$.body.header.sender_id','$.body.header.signature','$.body.message.payload',FALSE,'')
ON CONFLICT ("key_path_id") DO NOTHING;

INSERT INTO public.incoming_model_register_semantic_patterns ("register_semantic_pattern_id","data_model_id","register_id","pattern_for_register","key_path_for_record_identifier") VALUES
('ca8c46ce-9b7e-52ba-9164-2e1b1e590187','8cceae40-aa16-5d0a-a0b6-31e2e3ccbfb0','fa120001-0000-4000-8000-000000000001','$.body.message.payload.event_type=>^farmer[.]profile[.]updates[.]v1$','$.body.message.payload.farmer_id')
ON CONFLICT ("register_semantic_pattern_id") DO UPDATE SET "pattern_for_register" = EXCLUDED."pattern_for_register";

INSERT INTO public.incoming_model_semantic_patterns ("semantic_pattern_id","data_model_id","register_id","intake_form_id","section_id","pattern_for_register","pattern_for_intake_form","pattern_for_section","key_path_for_business_payload","raw_payload_enricher_class") VALUES
('c010db6d-d518-5da0-b077-959fa483d088','8cceae40-aa16-5d0a-a0b6-31e2e3ccbfb0','fa120001-0000-4000-8000-000000000001',NULL,'cropsown_farmer_identity_section_01','$.body.message.payload.event_type=>^farmer[.]profile[.]updates[.]v1$','$.body.message.payload.event_type=>^NEVER_ADD$','$.body.message.payload.event_type=>^farmer[.]profile[.]updates[.]v1$','$.body.message.payload','FarmerChangedEnricher')
ON CONFLICT ("semantic_pattern_id") DO UPDATE SET "pattern_for_register" = EXCLUDED."pattern_for_register", "pattern_for_section" = EXCLUDED."pattern_for_section", "raw_payload_enricher_class" = EXCLUDED."raw_payload_enricher_class";

INSERT INTO public.incoming_templates ("template_id","register_id","data_model_id","template_document_id","jsonld_expansion_required","created_at") VALUES
('6c1854ac-282d-57cd-8331-43d22354402f','fa120001-0000-4000-8000-000000000001','8cceae40-aa16-5d0a-a0b6-31e2e3ccbfb0','crop_farmer_changed_v1_update_document',FALSE,'2026-11-06 00:00:00')
ON CONFLICT ("template_id") DO NOTHING;
