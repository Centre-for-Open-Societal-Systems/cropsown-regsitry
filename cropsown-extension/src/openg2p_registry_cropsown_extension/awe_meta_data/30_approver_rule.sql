-- OpenG2P Farmer 1.2 default approval pattern. Domain-specific keys keep
-- old policies and in-flight tasks intact; no role/grant/task mutation.
-- Every stage lists the named officer and admin; one decision from either completes it.
INSERT INTO public.approver_rule (id,stage_id,rule_type,rule_value,kind,required,created_at,updated_at)
SELECT v.id,s.id,'user',v.rule_value::json,'approver',FALSE,NOW(),NOW()
FROM (VALUES
('1bf98c6f-b183-5943-89c4-229765fa3818','registry.change_request.cropsown.default',1,'{"user_id": "alex.carter"}'),
('48935244-a09d-5964-8019-ed5c611ed8b9','registry.change_request.cropsown.default',1,'{"user_id": "admin"}'),
('76159a19-ce91-5040-9d12-05bacf13471b','registry.change_request.cropsown.default',2,'{"user_id": "nina.patel"}'),
('c4b6f65d-320c-5f8c-8723-370ab2e31f70','registry.change_request.cropsown.default',2,'{"user_id": "admin"}'),
('ddd102c8-a12e-54f8-a2f9-77bfe74ed5e5','registry.change_request.cropsown-farmer.default',1,'{"user_id": "alex.carter"}'),
('4b2376b0-7ab5-56b8-9554-5618c8d8c81f','registry.change_request.cropsown-farmer.default',1,'{"user_id": "admin"}'),
('a708f8f7-19a6-5b86-9d4d-e6afb0a87d73','registry.change_request.cropsown-farmer.default',2,'{"user_id": "nina.patel"}'),
('41324804-fbd9-563e-b35e-bc1db64a5dc0','registry.change_request.cropsown-farmer.default',2,'{"user_id": "admin"}'),
('168f739b-9e0e-5f2c-8fcf-22c39b1a9f52','registry.intake_form.cropsown.default',1,'{"user_id": "alex.carter"}'),
('751c2f50-4866-594e-89e4-b74d2dacbae6','registry.intake_form.cropsown.default',1,'{"user_id": "admin"}'),
('65c33af6-875f-5d72-96a0-e9f19d33eafc','registry.intake_form.cropsown.default',2,'{"user_id": "nina.patel"}'),
('d90a75af-cdf4-5cc7-af1c-5a46136b9d30','registry.intake_form.cropsown.default',2,'{"user_id": "admin"}')) AS v(id,policy_key,stage_order,rule_value)
JOIN public.approval_policy p ON p.policy_key=v.policy_key AND p.version=1
JOIN public.approval_stage s ON s.policy_id=p.id AND s.stage_order=v.stage_order
WHERE NOT EXISTS (SELECT 1 FROM public.approver_rule r WHERE r.stage_id=s.id AND r.rule_type='user' AND r.rule_value::text=v.rule_value)
ON CONFLICT (id) DO NOTHING;
