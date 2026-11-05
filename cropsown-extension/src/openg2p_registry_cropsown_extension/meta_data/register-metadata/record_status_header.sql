-- Record header with the record status, as the OpenG2P reference and farmer
-- registries have it (header-section widget with status and statusReason). It
-- shows the record's status (Active, Inactive, Archived) and the reason, and it
-- is the section a change request uses to close a record: an approved UPDATE
-- of record_status and record_status_reason on this section. Search and export
-- show only ACTIVE records (platform default), so a closed record leaves the
-- lists but keeps its history. The platform accepts those two fields in a
-- change request only from a section that binds them, which no other section
-- does.
--
-- Sorts after the base section and tab-section files; no later file touches
-- these sections. Idempotent: the section upsert and the tab-section insert
-- re-run safely on every install and upgrade.
-- Crop Sown register, first section of the Crop Sown tab.
INSERT INTO "public"."g2p_register_sections" ("register_id","section_id","section_register_id","is_core_section","section_mnemonic","section_description","documents_required","no_of_verifications_required","is_list","section_weightage","section_ui_schema","cr_auto_approve_for_bene_portal","cr_auto_approve_for_agent_portal","cr_auto_approve_for_staff_portal","cr_auto_approve_for_partner") VALUES
('6b06a95a-9a6c-5a33-a33d-c1625716c59c','cropsown_record_header','6b06a95a-9a6c-5a33-a33d-c1625716c59c','FALSE','cs_record_header','Record status','FALSE',0,'FALSE',0,'{"panels": [{"panels": [{"widgets": [{"widget": "header-section", "widget-id": "registry-header", "widget-type": "group", "widget-data-path": {"name": "6b06a95a-9a6c-5a33-a33d-c1625716c59c.record_name", "status": "6b06a95a-9a6c-5a33-a33d-c1625716c59c.record_status", "createdAt": "6b06a95a-9a6c-5a33-a33d-c1625716c59c.created_at", "createdBy": "6b06a95a-9a6c-5a33-a33d-c1625716c59c.created_by", "functionalId": "6b06a95a-9a6c-5a33-a33d-c1625716c59c.functional_record_id", "statusReason": "6b06a95a-9a6c-5a33-a33d-c1625716c59c.record_status_reason", "lastApprovedAt": "6b06a95a-9a6c-5a33-a33d-c1625716c59c.last_approved_at", "lastApprovedBy": "6b06a95a-9a6c-5a33-a33d-c1625716c59c.last_approved_by"}, "widget-data-format": {"nameColor": "#ED7C22", "statusColors": {"ACTIVE": "#16A34A", "ARCHIVED": "#6B7280", "INACTIVE": "#D97706"}}, "widget-field-config": {"status": {"data-source": {"type": "static", "options": [{"label": "Active", "value": "ACTIVE"}, {"label": "Inactive", "value": "INACTIVE"}, {"label": "Archived", "value": "ARCHIVED"}]}}}}], "panel-id": "cropsown_record_header_inside_panel", "panel-orientation": "vertical"}], "panel-id": "cropsown_record_header_outside_panel", "panel-orientation": "horizontal"}], "section-id": "cropsown_record_header", "section-title": "", "section-editable": true}','FALSE','FALSE','FALSE','FALSE')
ON CONFLICT ("section_id") DO UPDATE SET
  "section_ui_schema"   = EXCLUDED."section_ui_schema",
  "section_description" = EXCLUDED."section_description";

INSERT INTO "public"."g2p_register_ui_tab_sections" ("tab_section_id","register_id","tab_id","section_id","section_order") VALUES
('01c06663-4a5f-5ac4-bc47-b77d8a3d57d9','6b06a95a-9a6c-5a33-a33d-c1625716c59c','cropsown_cropsown_tab','cropsown_record_header',5)
ON CONFLICT DO NOTHING;
