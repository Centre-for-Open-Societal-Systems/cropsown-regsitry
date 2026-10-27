-- Native policy resolution requires exactly one binding per effective scope.
-- Preserve full snapshots/IDs before retiring duplicate metadata only. AWE
-- policies, requests, tasks, decisions, IAM grants and domain rows are untouched.
INSERT INTO public.coss_approval_binding_archive (binding_id,content_hash,original_binding,reason,archived_at)
SELECT c.awe_policy_config_id,md5(to_jsonb(c)::text),to_jsonb(c),'OpenG2P default approval reset',CURRENT_TIMESTAMP
FROM public.g2p_registry_awe_policy_configurations c
WHERE c.register_id IN ('6b06a95a-9a6c-5a33-a33d-c1625716c59c','fa120001-0000-4000-8000-000000000001') AND c.policy_type IN ('registry.change_request','change_request','registry.intake_form','intake_form') AND (c.policy_key NOT LIKE '%.default' OR c.context_field_names IS NOT NULL)
ON CONFLICT (binding_id,content_hash) DO NOTHING;

UPDATE public.g2p_registry_awe_policy_configurations c
SET policy_key=m.policy_key,context_field_names=NULL
FROM (VALUES
('6b06a95a-9a6c-5a33-a33d-c1625716c59c','change_request','registry.change_request.cropsown.default'),
('fa120001-0000-4000-8000-000000000001','change_request','registry.change_request.cropsown-farmer.default'),
('6b06a95a-9a6c-5a33-a33d-c1625716c59c','intake_form','registry.intake_form.cropsown.default')) m(register_id,artifact,policy_key)
WHERE c.register_id=m.register_id AND regexp_replace(c.policy_type,'^registry[.]','')=m.artifact
  AND (c.policy_key IS DISTINCT FROM m.policy_key OR c.context_field_names IS NOT NULL);

WITH ranked AS (SELECT c.awe_policy_config_id,row_number() OVER (PARTITION BY c.register_id,regexp_replace(c.policy_type,'^registry[.]',''),c.policy_scope,CASE WHEN c.policy_scope='SECTION' THEN coalesce(c.section_id,'') WHEN c.policy_scope='INTAKE_FORM' THEN coalesce(c.intake_form_id,'') ELSE '' END ORDER BY CASE WHEN c.awe_policy_config_id IN ('45cbfacb-532e-5553-90b0-1c040222cda7','b268668d-3091-5529-9508-38fe67bdea73','34e0fb1a-ca18-5a5e-a5d7-b80181daf491','536d68b8-c1d9-5d08-b778-9e99b46bc1cc','443011c9-9669-54b1-a610-048d7cbf2a9e','7152f77c-ec06-5b48-80b1-3aa387a66810','d7114c08-d44a-5977-a6b7-e3ca91ad582d') THEN 0 ELSE 1 END,c.awe_policy_config_id) AS position FROM public.g2p_registry_awe_policy_configurations c WHERE c.register_id IN ('6b06a95a-9a6c-5a33-a33d-c1625716c59c','fa120001-0000-4000-8000-000000000001') AND c.policy_type IN ('registry.change_request','change_request','registry.intake_form','intake_form'))
INSERT INTO public.coss_approval_binding_archive (binding_id,content_hash,original_binding,reason,archived_at)
SELECT c.awe_policy_config_id,md5(to_jsonb(c)::text),to_jsonb(c),'Duplicate native approval binding',CURRENT_TIMESTAMP
FROM public.g2p_registry_awe_policy_configurations c JOIN ranked r ON r.awe_policy_config_id=c.awe_policy_config_id
WHERE r.position>1 ON CONFLICT (binding_id,content_hash) DO NOTHING;

WITH ranked AS (SELECT c.awe_policy_config_id,row_number() OVER (PARTITION BY c.register_id,regexp_replace(c.policy_type,'^registry[.]',''),c.policy_scope,CASE WHEN c.policy_scope='SECTION' THEN coalesce(c.section_id,'') WHEN c.policy_scope='INTAKE_FORM' THEN coalesce(c.intake_form_id,'') ELSE '' END ORDER BY CASE WHEN c.awe_policy_config_id IN ('45cbfacb-532e-5553-90b0-1c040222cda7','b268668d-3091-5529-9508-38fe67bdea73','34e0fb1a-ca18-5a5e-a5d7-b80181daf491','536d68b8-c1d9-5d08-b778-9e99b46bc1cc','443011c9-9669-54b1-a610-048d7cbf2a9e','7152f77c-ec06-5b48-80b1-3aa387a66810','d7114c08-d44a-5977-a6b7-e3ca91ad582d') THEN 0 ELSE 1 END,c.awe_policy_config_id) AS position FROM public.g2p_registry_awe_policy_configurations c WHERE c.register_id IN ('6b06a95a-9a6c-5a33-a33d-c1625716c59c','fa120001-0000-4000-8000-000000000001') AND c.policy_type IN ('registry.change_request','change_request','registry.intake_form','intake_form'))
DELETE FROM public.g2p_registry_awe_policy_configurations c USING ranked r
WHERE c.awe_policy_config_id=r.awe_policy_config_id AND r.position>1
  AND EXISTS (SELECT 1 FROM public.coss_approval_binding_archive a
    WHERE a.binding_id=c.awe_policy_config_id AND a.content_hash=md5(to_jsonb(c)::text));
