-- OpenG2P Farmer 1.2 default approval pattern. Domain-specific keys keep
-- old policies and in-flight tasks intact; no role/grant/task mutation.
INSERT INTO public.approval_policy (id,policy_key,version,name,description,status,artifact_type,created_by,forbid_self_approval,forbid_repeat_approvers,created_at,updated_at) VALUES
('186b212a-6946-5fbe-806c-dd4fcd663e25','registry.change_request.cropsown.default',1,'Cropsown change request - OpenG2P defaults',NULL,'active','registry.change_request','seed',FALSE,FALSE,NOW(),NOW()),
('6c937042-8db6-53b4-b48c-fdcfb9f9e801','registry.change_request.cropsown-farmer.default',1,'Farmer reference change request - OpenG2P defaults',NULL,'active','registry.change_request','seed',FALSE,FALSE,NOW(),NOW()),
('39785d0d-d4f9-5f59-b149-ad50dc4497b5','registry.intake_form.cropsown.default',1,'Cropsown intake - OpenG2P defaults',NULL,'active','registry.intake_form','seed',FALSE,FALSE,NOW(),NOW())
ON CONFLICT (policy_key,version) DO NOTHING;
