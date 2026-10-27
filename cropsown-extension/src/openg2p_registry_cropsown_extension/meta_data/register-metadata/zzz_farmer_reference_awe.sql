-- OpenG2P Farmer 1.2 default approval pattern. Domain-specific keys keep
-- old policies and in-flight tasks intact; no role/grant/task mutation.
INSERT INTO g2p_registry_awe_policy_configurations
(awe_policy_config_id,policy_scope,register_id,intake_form_id,section_id,policy_type,policy_key,context_field_names)
VALUES ('d7114c08-d44a-5977-a6b7-e3ca91ad582d','SECTION','fa120001-0000-4000-8000-000000000001',NULL,'cropsown_farmer_identity_section_01',
'registry.change_request','registry.change_request.cropsown-farmer.default',NULL)
ON CONFLICT (awe_policy_config_id) DO UPDATE SET
  policy_key=EXCLUDED.policy_key, context_field_names=NULL;
