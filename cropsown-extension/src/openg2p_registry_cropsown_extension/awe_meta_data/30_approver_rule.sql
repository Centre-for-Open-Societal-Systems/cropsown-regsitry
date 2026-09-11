INSERT INTO "public"."approver_rule" (
    "id",
    "stage_id",
    "rule_type",
    "rule_value",
    "kind",
    "required",
    "created_at",
    "updated_at"
) VALUES
    ('0a1b2c3d-7183-44c5-8ff6-7c8d9eafb0c7', 'c3e5071a-3d4f-4081-acb2-3e4f5a6b7c83', 'user', '{"user_id": "admin"}', 'approver', 'FALSE', NOW(), NOW()),
    ('2c3d4e5f-93a5-46e7-a1b8-9eafb0c1d2e9', 'e507293c-5f61-42a3-ced4-5a6b7c8d9ea5', 'user', '{"user_id": "admin"}', 'approver', 'FALSE', NOW(), NOW()),
    ('75357d4a-b9df-47c4-a681-b82741be09af', '10c248f8-1dd9-485c-9e20-7246c36ee560', 'user', '{"user_id": "admin"}', 'approver', 'FALSE', NOW(), NOW()),
    ('5a939bc8-4f34-49de-b65f-4374677c4c9d', 'a021b13a-bc3c-47ef-ba59-bf2309031cc2', 'user', '{"user_id": "admin"}', 'approver', 'FALSE', NOW(), NOW()),
    ('7812be37-3ee6-4ff4-9cec-07d3f7008369', 'a7382ebe-4f1e-48ec-a0de-ac4bc5a6898b', 'user', '{"user_id": "admin"}', 'approver', 'FALSE', NOW(), NOW()),
    ('cc5bd93d-9f1d-4999-a46f-eb46bd8dc3a7', '32e7925f-1d30-4e84-acf3-6a23a1b1809c', 'user', '{"user_id": "admin"}', 'approver', 'FALSE', NOW(), NOW())
ON CONFLICT ("id") DO NOTHING;

