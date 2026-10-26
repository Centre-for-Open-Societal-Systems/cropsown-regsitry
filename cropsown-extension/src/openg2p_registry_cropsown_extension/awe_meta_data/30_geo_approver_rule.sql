INSERT INTO "public"."approver_rule" ("id","stage_id","rule_type","rule_value","kind","required","created_at","updated_at")
SELECT v.id, s.id, 'expression', v.rule_value::json, 'approver', FALSE, NOW(), NOW()
FROM (VALUES
    ('c740b903-b8d0-550b-b3ab-9604a6da12ce','registry.change_request.cropsown',1,'{"logic": {"var": "geo_woreda_approver_ids"}}'),
    ('4b9465b4-dca4-5197-b1d9-f6120fba909a','registry.change_request.cropsown-farmer',1,'{"logic": {"var": "geo_woreda_approver_ids"}}'),
    ('9f37a248-9e74-5d65-b21c-30b82b341dbc','registry.intake_form.cropsown',1,'{"logic": {"var": "geo_woreda_approver_ids"}}')
) AS v(id, policy_key, stage_order, rule_value)
INNER JOIN approval_policy p ON p.policy_key = v.policy_key AND p.version = 1
INNER JOIN approval_stage s ON s.policy_id = p.id AND s.stage_order = v.stage_order
WHERE NOT EXISTS (SELECT 1 FROM approver_rule r WHERE r.stage_id = s.id)
ON CONFLICT ("id") DO NOTHING;
