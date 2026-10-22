INSERT INTO "public"."g2p_registry_awe_policy_configurations" (
    "awe_policy_config_id",
    "policy_scope",
    "register_id",
    "intake_form_id",
    "section_id",
    "policy_type",
    "policy_key",
    "context_field_names"
) VALUES
    ('7c1f8a92-4b3d-4e15-9a26-5d8e0f3b71a4', 'REGISTER', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', NULL, NULL, 'registry.change_request', 'registry.change_request.cropsown', 'null'),
    ('16c5eaa0-d7d4-4d2a-9516-5a973f85dc21', 'REGISTER', 'fa120001-0000-4000-8000-000000000001', NULL, NULL, 'registry.change_request', 'registry.change_request.cropsown', 'null'),
    ('509fdb5f-e2ac-46b6-8f9f-3efae6215655', 'INTAKE_FORM', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', '5bf0068c-ce19-46f8-874c-7147997f793b', NULL, 'registry.intake_form', 'registry.intake_form.planning_cropsown', 'null'),
    ('8ea3ecc5-2661-48ed-8340-222dfed66bbc', 'INTAKE_FORM', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', '6be15ab9-0f1b-4c38-995f-395d52a1b17a', NULL, 'registry.intake_form', 'registry.intake_form.cultivation_cropsown', 'null'),
    ('01865048-59f3-4d32-ad26-c44f4c78bfc8', 'INTAKE_FORM', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', '4a7c2c98-0ffb-41d8-8fea-f22349823675', NULL, 'registry.intake_form', 'registry.intake_form.sowing_cropsown', 'null'),
    ('548e358d-2be7-44b7-8a97-18f882d32de2', 'INTAKE_FORM', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', '52150a37-153d-496d-9cd9-2a3815d6e13b', NULL, 'registry.intake_form', 'registry.intake_form.harvesting_cropsown', 'null')
ON CONFLICT ("awe_policy_config_id") DO UPDATE SET
    policy_scope = EXCLUDED.policy_scope,
    register_id = EXCLUDED.register_id,
    intake_form_id = EXCLUDED.intake_form_id,
    section_id = EXCLUDED.section_id,
    policy_type = EXCLUDED.policy_type,
    policy_key = EXCLUDED.policy_key,
    context_field_names = EXCLUDED.context_field_names;

-- Older dev deployments inserted parallel bindings under these known IDs.
-- Keep the canonical mappings above, existing AWE policies/tasks and their
-- approvers. Remove a legacy mapping only when its expected replacement exists.
DELETE FROM "public"."g2p_registry_awe_policy_configurations" AS legacy
WHERE legacy.register_id = '6b06a95a-9a6c-5a33-a33d-c1625716c59c'
  AND legacy.awe_policy_config_id IN (
    '71e1e9f4-4cf5-48eb-a7bc-a98610b47e05',
    'd126d7ff-8fb9-48e2-ab71-a48db3bf261a',
    '1a9c8b0a-99ef-4153-8b72-7690aef04ae1',
    'f298d42a-bc83-48a6-83b7-81abe09f303f',
    'aa82e48c-eef9-4f62-babb-109c95046a47')
  AND legacy.policy_key IN ('registry.change_request.devcropsown',
    'registry.intake_form.devplanning_cropsown', 'registry.intake_form.devcultivation_cropsown',
    'registry.intake_form.devsowing_cropsown', 'registry.intake_form.devharvesting_cropsown')
  AND EXISTS (
    SELECT 1 FROM "public"."g2p_registry_awe_policy_configurations" AS canonical
    WHERE canonical.register_id = legacy.register_id
      AND canonical.policy_scope = legacy.policy_scope
      AND canonical.policy_type = legacy.policy_type
      AND COALESCE(canonical.intake_form_id, '') = COALESCE(legacy.intake_form_id, '')
      AND COALESCE(canonical.section_id, '') = COALESCE(legacy.section_id, '')
      AND canonical.policy_key = REPLACE(legacy.policy_key, '.dev', '.'));

