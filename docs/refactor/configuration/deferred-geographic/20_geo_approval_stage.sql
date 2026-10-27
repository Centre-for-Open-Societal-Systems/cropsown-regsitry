INSERT INTO "public"."approval_stage" ("id","policy_id","stage_order","name","mode","mode_value","sla_hours","parallel_group","skip_if","on_empty","on_breach","escalation_rules_json","created_at","updated_at")
SELECT v.id, p.id, v.stage_order, v.name, 'any-n', 1, CAST(NULL AS integer), CAST(NULL AS integer),
       'null', 'block', CAST(NULL AS integer), 'null', NOW(), NOW()
FROM (VALUES
    ('5796eb80-b9a8-5fb3-9f51-5e0916efdd4f','registry.change_request.cropsown',1,'Woreda approval'),
    ('32bbca53-7d4f-5ea2-9492-a410367ffca5','registry.change_request.cropsown-farmer',1,'Woreda approval'),
    ('0f614560-3330-5eb9-9410-3e1d23c39689','registry.intake_form.cropsown',1,'Woreda approval')
) AS v(id, policy_key, stage_order, name)
INNER JOIN approval_policy p ON p.policy_key = v.policy_key AND p.version = 1
WHERE NOT EXISTS (SELECT 1 FROM approval_stage s WHERE s.policy_id = p.id AND s.stage_order = v.stage_order)
ON CONFLICT ("id") DO NOTHING;
