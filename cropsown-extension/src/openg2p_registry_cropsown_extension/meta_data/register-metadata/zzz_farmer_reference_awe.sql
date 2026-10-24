-- Fresh-install binding only; no existing bindings or IAM assignments are removed.
-- The shared AWE policy is provisioned through its standard administration API
-- from docs/refactor/configuration/farmer-reference-awe-policy.json.
INSERT INTO g2p_registry_awe_policy_configurations
(awe_policy_config_id,policy_scope,register_id,intake_form_id,section_id,policy_type,policy_key,context_field_names)
VALUES ('d7114c08-d44a-5977-a6b7-e3ca91ad582d','SECTION','fa120001-0000-4000-8000-000000000001',NULL,'cropsown_farmer_identity_section_01',
'registry.change_request','coss.cropsown.farmer-reference.v1','["farmer_reference_woreda_id","farmer_reference_approver_ids"]')
ON CONFLICT (awe_policy_config_id) DO NOTHING;
