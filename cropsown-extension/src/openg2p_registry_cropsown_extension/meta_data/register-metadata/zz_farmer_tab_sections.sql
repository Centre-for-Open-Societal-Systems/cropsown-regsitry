-- The Farmer tab of a Crop Sown record shows what the Livestock registry's does:
-- the record status header first, then the farmer's identity, then the
-- farmer's location (the geography copied from the Farmer Registry).
--
-- The header is the section an approved change request uses to close the farmer
-- copy (record_status / record_status_reason, see record_status_header.sql).
-- Change requests on both sections go through the Farmer register's
-- REGISTER-level approval policy (registry.change_request.cropsown-farmer.default).
--
-- Sorts after zz_farmer_register.sql, which creates the register and the tab.
-- Idempotent: section upserts and tab-section inserts re-run safely.

INSERT INTO "public"."g2p_register_sections" ("register_id","section_id","section_register_id","is_core_section","section_mnemonic","section_description","documents_required","no_of_verifications_required","is_list","section_weightage","section_ui_schema","cr_auto_approve_for_bene_portal","cr_auto_approve_for_agent_portal","cr_auto_approve_for_staff_portal","cr_auto_approve_for_partner") VALUES
('fa120001-0000-4000-8000-000000000001','cropsown_farmer_record_header','fa120001-0000-4000-8000-000000000001','FALSE','cs_farmer_record_header','Record status','FALSE',0,'FALSE',0,'{"panels": [{"panels": [{"widgets": [{"widget": "header-section", "widget-id": "registry-header", "widget-type": "group", "widget-data-path": {"name": "fa120001-0000-4000-8000-000000000001.record_name", "status": "fa120001-0000-4000-8000-000000000001.record_status", "createdAt": "fa120001-0000-4000-8000-000000000001.created_at", "createdBy": "fa120001-0000-4000-8000-000000000001.created_by", "functionalId": "fa120001-0000-4000-8000-000000000001.functional_record_id", "statusReason": "fa120001-0000-4000-8000-000000000001.record_status_reason", "lastApprovedAt": "fa120001-0000-4000-8000-000000000001.last_approved_at", "lastApprovedBy": "fa120001-0000-4000-8000-000000000001.last_approved_by"}, "widget-data-format": {"nameColor": "#ED7C22", "statusColors": {"ACTIVE": "#16A34A", "ARCHIVED": "#6B7280", "INACTIVE": "#D97706"}}, "widget-field-config": {"status": {"data-source": {"type": "static", "options": [{"label": "Active", "value": "ACTIVE"}, {"label": "Inactive", "value": "INACTIVE"}, {"label": "Archived", "value": "ARCHIVED"}]}}}}], "panel-id": "cropsown_farmer_record_header_inside_panel", "panel-orientation": "vertical"}], "panel-id": "cropsown_farmer_record_header_outside_panel", "panel-orientation": "horizontal"}], "section-id": "cropsown_farmer_record_header", "section-title": "", "section-editable": true}','FALSE','FALSE','FALSE','FALSE')
ON CONFLICT ("section_id") DO UPDATE SET
  "section_ui_schema"   = EXCLUDED."section_ui_schema",
  "section_description" = EXCLUDED."section_description";

INSERT INTO "public"."g2p_register_ui_tab_sections" ("tab_section_id","register_id","tab_id","section_id","section_order") VALUES
('2ad4eefa-2e60-5c23-8944-278a38ac9a0b','fa120001-0000-4000-8000-000000000001','cropsown_farmer_tab','cropsown_farmer_record_header',5)
ON CONFLICT DO NOTHING;

INSERT INTO "public"."g2p_register_sections" ("register_id","section_id","section_register_id","is_core_section","section_mnemonic","section_description","documents_required","no_of_verifications_required","is_list","section_weightage","section_ui_schema","cr_auto_approve_for_bene_portal","cr_auto_approve_for_agent_portal","cr_auto_approve_for_staff_portal","cr_auto_approve_for_partner") VALUES
('fa120001-0000-4000-8000-000000000001','cropsown_farmer_location_section_02','fa120001-0000-4000-8000-000000000001','FALSE','cs_farmer_location','Farmer location','FALSE',0,'FALSE',10,'{"panels": [{"panels": [{"widgets": [{"widget": "geo-hierarchy", "widget-id": "farmer_geo_hierarchy", "widget-type": "input", "widget-label": "Administrative hierarchy", "widget-readonly": false, "widget-required": false, "widget-data-path": {"value": "fa120001-0000-4000-8000-000000000001.geo_lowest_level_value_id", "hierarchy": "fa120001-0000-4000-8000-000000000001.geo_code_hierarchy_json"}, "widget-geo-layout": {"columnSpan": 1}, "widget-data-source": {"type": "api", "method": "POST", "service": "master-data", "levelsEndpoint": "get-all-g2p-geo-levels", "valuesEndpoint": "geo-level-values"}}], "panel-id": "vp_cs_farmer_location_1", "panel-orientation": "vertical"}], "panel-id": "hp_cs_farmer_location", "panel-orientation": "horizontal"}], "section-id": "cropsown_farmer_location_section_02", "section-title": "Farmer location", "section-editable": true}','FALSE','FALSE','FALSE','FALSE')
ON CONFLICT ("section_id") DO UPDATE SET
  "section_ui_schema"   = EXCLUDED."section_ui_schema",
  "section_description" = EXCLUDED."section_description";

INSERT INTO "public"."g2p_register_ui_tab_sections" ("tab_section_id","register_id","tab_id","section_id","section_order") VALUES
('984897ff-cc36-5c77-9694-e60fee385532','fa120001-0000-4000-8000-000000000001','cropsown_farmer_tab','cropsown_farmer_location_section_02',20)
ON CONFLICT DO NOTHING;
