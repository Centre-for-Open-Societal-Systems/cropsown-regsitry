-- Preserve complete original configuration before any seed upserts.
INSERT INTO public.coss_approval_binding_archive (binding_id,content_hash,original_binding,reason,archived_at)
SELECT c.awe_policy_config_id,md5(to_jsonb(c)::text),to_jsonb(c),'OpenG2P default approval reset',CURRENT_TIMESTAMP
FROM public.g2p_registry_awe_policy_configurations c
WHERE c.register_id IN ('6b06a95a-9a6c-5a33-a33d-c1625716c59c','fa120001-0000-4000-8000-000000000001') AND c.policy_type IN ('registry.change_request','change_request','registry.intake_form','intake_form') AND (c.policy_key NOT LIKE '%.default' OR c.context_field_names IS NOT NULL)
ON CONFLICT (binding_id,content_hash) DO NOTHING;
