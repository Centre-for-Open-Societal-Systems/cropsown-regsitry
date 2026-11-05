-- OpenG2P Farmer 1.2 default approval pattern. Domain-specific keys keep
-- old policies and in-flight tasks intact; no role/grant/task mutation.
INSERT INTO g2p_registry_awe_policy_configurations
(awe_policy_config_id,policy_scope,register_id,intake_form_id,section_id,policy_type,policy_key,context_field_names) VALUES
('45cbfacb-532e-5553-90b0-1c040222cda7','REGISTER','6b06a95a-9a6c-5a33-a33d-c1625716c59c',NULL,NULL,'registry.change_request','registry.change_request.cropsown.default',NULL),
('b268668d-3091-5529-9508-38fe67bdea73','REGISTER','fa120001-0000-4000-8000-000000000001',NULL,NULL,'registry.change_request','registry.change_request.cropsown-farmer.default',NULL),
('34e0fb1a-ca18-5a5e-a5d7-b80181daf491','INTAKE_FORM','6b06a95a-9a6c-5a33-a33d-c1625716c59c','5bf0068c-ce19-46f8-874c-7147997f793b',NULL,'registry.intake_form','registry.intake_form.cropsown.default',NULL),
('536d68b8-c1d9-5d08-b778-9e99b46bc1cc','INTAKE_FORM','6b06a95a-9a6c-5a33-a33d-c1625716c59c','6be15ab9-0f1b-4c38-995f-395d52a1b17a',NULL,'registry.intake_form','registry.intake_form.cropsown.default',NULL),
('443011c9-9669-54b1-a610-048d7cbf2a9e','INTAKE_FORM','6b06a95a-9a6c-5a33-a33d-c1625716c59c','4a7c2c98-0ffb-41d8-8fea-f22349823675',NULL,'registry.intake_form','registry.intake_form.cropsown.default',NULL),
('7152f77c-ec06-5b48-80b1-3aa387a66810','INTAKE_FORM','6b06a95a-9a6c-5a33-a33d-c1625716c59c','52150a37-153d-496d-9cd9-2a3815d6e13b',NULL,'registry.intake_form','registry.intake_form.cropsown.default',NULL)
ON CONFLICT (awe_policy_config_id) DO UPDATE SET
  policy_key=EXCLUDED.policy_key, context_field_names=NULL;
