-- Crop Sown approvals by the record's place (geo_approval/): one stage, the
-- Woreda Approvers of the record's own woreda (Oct 2026 decision). The registry
-- computes them; the rule reads them with "var".
-- Fresh install: existing policies, stages and rules are never changed.
INSERT INTO "public"."approval_policy" ("id","policy_key","version","name","description","status","artifact_type","created_by","forbid_self_approval","forbid_repeat_approvers","created_at","updated_at") VALUES
('67a96592-9ddd-547a-a129-51c9bb877c58','registry.change_request.cropsown',1,'Crop Sown change request','Woreda approval at the record''s approved place','active','registry.change_request','seed','TRUE','TRUE',NOW(),NOW()),
('f202f9aa-4b9e-5613-a3b5-f7d931c77664','registry.change_request.cropsown-farmer',1,'Crop Sown Farmer change request','Woreda approval at the record''s approved place','active','registry.change_request','seed','TRUE','TRUE',NOW(),NOW()),
('f65b31e0-5b1a-5561-9360-d356529f9bd1','registry.intake_form.cropsown',1,'Crop Sown intake','Woreda approval at the submitted place','active','registry.intake_form','seed','TRUE','TRUE',NOW(),NOW())
ON CONFLICT ("policy_key","version") DO NOTHING;
