-- OpenG2P Farmer 1.2 default approval pattern. Domain-specific keys keep
-- old policies and in-flight tasks intact; no role/grant/task mutation.
-- Each stage is satisfied by one decision (any-n, 1): the named officer or admin.
INSERT INTO public.approval_stage (id,policy_id,stage_order,name,mode,mode_value,sla_hours,parallel_group,skip_if,on_empty,on_breach,escalation_rules_json,created_at,updated_at)
SELECT v.id,p.id,v.stage_order,v.name,'any-n',1,CAST(NULL AS integer),CAST(NULL AS integer),'null','block',CAST(NULL AS integer),'null',NOW(),NOW()
FROM (VALUES
('8d585afa-4c07-5d3c-b2c6-250476b64f95','registry.change_request.cropsown.default',1,'Stage 1 officers'),
('cbe6cd87-08c3-519a-b857-6c37cb625d52','registry.change_request.cropsown.default',2,'Stage 2 officers'),
('7e7b6cd3-21ae-5fcf-9f39-aa8f8dd73264','registry.change_request.cropsown-farmer.default',1,'Stage 1 officers'),
('01e246a2-432c-51f0-8d0c-a3884cb02b16','registry.change_request.cropsown-farmer.default',2,'Stage 2 officers'),
('d06c1b3f-ee31-5b79-9f82-73333c701806','registry.intake_form.cropsown.default',1,'Stage 1 officers'),
('b3cf7122-ecff-5338-a6d9-40ed4fe02614','registry.intake_form.cropsown.default',2,'Stage 2 officers')) AS v(id,policy_key,stage_order,name)
JOIN public.approval_policy p ON p.policy_key=v.policy_key AND p.version=1
WHERE NOT EXISTS (SELECT 1 FROM public.approval_stage s WHERE s.policy_id=p.id AND s.stage_order=v.stage_order)
ON CONFLICT (id) DO NOTHING;
