-- Farmer lookup: the first section of every Crop Sown intake form holds exactly two
-- fields, the Farmer ID and one typed Fayda ID (a 16-digit FAN or a 12-digit FIN).
-- Nothing else: no FIN display, no Verify with Fayda, no Farmer reference status.
-- The domain field rules split the typed Fayda ID by length into the stored
-- fayda_fan_id or fayda_fin column before the row is written, so stored data, the
-- dedup schema and the Farmer reference lookup are unchanged.
--
-- This folder sorts after register-metadata/, so this file runs after the older
-- identity overlays on every deploy and replaces what they re-apply. Idempotent.

INSERT INTO g2p_register_sections (register_id, section_id, section_register_id, is_core_section,
    section_mnemonic, section_description, documents_required, no_of_verifications_required, is_list,
    section_weightage, cr_auto_approve_for_bene_portal, cr_auto_approve_for_agent_portal,
    cr_auto_approve_for_staff_portal, cr_auto_approve_for_partner, section_ui_schema)
SELECT register_id, 'crop_farmer_lookup', section_register_id, FALSE,
    'crop_farmer_lookup', 'Farmer lookup', FALSE, 0, FALSE,
    section_weightage, cr_auto_approve_for_bene_portal, cr_auto_approve_for_agent_portal,
    cr_auto_approve_for_staff_portal, cr_auto_approve_for_partner,
    '{"section-id": "crop_farmer_lookup", "section-title": "Farmer lookup",
      "section-editable": true, "section-required-for-submit": true,
      "panels": [{"panel-id": "crop_farmer_lookup_fields", "panel-orientation": "horizontal",
        "panels": [
          {"panel-id": "crop_farmer_lookup_farmer_id", "panel-orientation": "vertical", "widgets": [
            {"widget": "text", "widget-id": "farmer_id", "widget-type": "input",
             "widget-label": "Farmer ID", "widget-readonly": false, "widget-required": true,
             "widget-data-path": "6b06a95a-9a6c-5a33-a33d-c1625716c59c.farmer_id",
             "widget-data-placeholder": "FR- followed by 12 digits",
             "widget-data-validation": {"pattern": "^\s*FR-[0-9]{12}\s*$", "patternMessage": "coss_input_farmer_id"}}]},
          {"panel-id": "crop_farmer_lookup_fayda_id", "panel-orientation": "vertical", "widgets": [
            {"widget": "text", "widget-id": "fayda_id", "widget-type": "input",
             "widget-label": "Fayda ID (FAN or FIN)", "widget-readonly": false, "widget-required": true,
             "widget-data-path": "6b06a95a-9a6c-5a33-a33d-c1625716c59c.fayda_id",
             "widget-data-placeholder": "16-digit FAN or 12-digit FIN",
             "widget-data-validation": {"pattern": "^\s*(?:[0-9]{12}|[0-9](?:\s*[0-9]){15})\s*$", "patternMessage": "coss_input_fayda_id"}}]}]}]}'::jsonb
FROM g2p_register_sections WHERE section_id = 'cropsown_intake_record_section_01'
ON CONFLICT (section_id) DO UPDATE SET
  section_mnemonic = EXCLUDED.section_mnemonic,
  section_description = EXCLUDED.section_description,
  section_ui_schema = EXCLUDED.section_ui_schema;

-- Bind Farmer lookup on each of the four intake tabs, then retire the old Farmer
-- Identity bindings by their explicit ids (the base file re-adds them on every
-- deploy; they are removed again here).
INSERT INTO g2p_intake_form_ui_tab_sections (tab_section_id, tab_id, section_id, section_order)
SELECT v.tab_id || '__crop_farmer_lookup', v.tab_id, 'crop_farmer_lookup', 0
FROM (VALUES ('8bd9fe3b-bb8c-4d5d-9f57-f7b5542050b8'), ('29ec34f5-24f7-4007-b8f0-32acc1bc1952'),
             ('56ce9d3d-eb8d-44b5-b175-ff9189ac1c3a'), ('01d306ec-d50e-4d73-9bc4-7199b6654eb4')) AS v(tab_id)
WHERE EXISTS (SELECT 1 FROM g2p_intake_form_ui_tabs t WHERE t.tab_id = v.tab_id)
ON CONFLICT (tab_section_id) DO NOTHING;

DELETE FROM g2p_intake_form_ui_tab_sections
WHERE tab_section_id IN ('f0fb088a-277f-471d-a9b9-fcceba0a1a8d', 'c3b6dfdb-80c5-45e4-864b-71f89899b443',
                         '1040a5ec-755e-412a-ad8e-18993a3989ad', '8a9dd89a-2bb8-4efd-aea9-c769bae3d183');

-- Farmer lookup first, Production Season second, then every other section in its
-- existing order.
UPDATE g2p_intake_form_ui_tab_sections ts SET section_order = ordered.position
FROM (
  SELECT x.tab_section_id, row_number() OVER (PARTITION BY x.tab_id ORDER BY
      CASE x.section_id WHEN 'crop_farmer_lookup' THEN 0
        WHEN 'cropsown_intake_season_section_01' THEN 1
        WHEN 'cropsown_common_intake_season_section_01' THEN 1 ELSE 2 END,
      x.section_order, x.section_id) AS position
  FROM g2p_intake_form_ui_tab_sections x
  WHERE EXISTS (SELECT 1 FROM g2p_intake_form_ui_tab_sections l
    WHERE l.tab_id = x.tab_id AND l.section_id = 'crop_farmer_lookup')
) ordered
WHERE ts.tab_section_id = ordered.tab_section_id AND ts.section_order <> ordered.position;

-- English defaults for the new message; translations already stored win.
UPDATE registry_languages SET domain_translation = ('{"coss_input_fayda_id": "Fayda ID: enter the 16-digit FAN or the 12-digit FIN, digits only.", "coss_field_fayda_id_format": "{label}: enter the 16-digit FAN or the 12-digit FIN, digits only.", "crop_farmer_lookup": "Farmer lookup"}'::jsonb
  || COALESCE(domain_translation::jsonb, '{}'::jsonb))::json;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM g2p_register_sections WHERE section_id = 'crop_farmer_lookup') THEN
    RAISE EXCEPTION 'The Crop Sown Farmer lookup section is missing';
  END IF;
  IF (SELECT count(*) FROM g2p_register_sections s,
        jsonb_path_query(s.section_ui_schema, 'strict $.** ? (exists (@."widget"))') w
      WHERE s.section_id = 'crop_farmer_lookup') <> 2
     OR EXISTS (SELECT 1 FROM g2p_register_sections s,
        jsonb_path_query(s.section_ui_schema, 'strict $.** ? (exists (@."widget"))') w
      WHERE s.section_id = 'crop_farmer_lookup' AND w->>'widget-id' NOT IN ('farmer_id', 'fayda_id')) THEN
    RAISE EXCEPTION 'Farmer lookup must hold exactly the Farmer ID and the Fayda ID';
  END IF;
  IF EXISTS (SELECT 1 FROM g2p_intake_form_ui_tabs t
      WHERE t.tab_id IN ('8bd9fe3b-bb8c-4d5d-9f57-f7b5542050b8', '29ec34f5-24f7-4007-b8f0-32acc1bc1952',
                         '56ce9d3d-eb8d-44b5-b175-ff9189ac1c3a', '01d306ec-d50e-4d73-9bc4-7199b6654eb4')
        AND NOT EXISTS (SELECT 1 FROM g2p_intake_form_ui_tab_sections ts
          WHERE ts.tab_id = t.tab_id AND ts.section_id = 'crop_farmer_lookup' AND ts.section_order = 1)) THEN
    RAISE EXCEPTION 'Every Crop Sown intake tab must start with Farmer lookup';
  END IF;
  IF EXISTS (SELECT 1 FROM g2p_intake_form_ui_tab_sections
      WHERE section_id IN ('cropsown_intake_record_section_01', 'cropsown_common_intake_record_section_01')) THEN
    RAISE EXCEPTION 'An old Farmer Identity section is still bound to an intake form';
  END IF;
END $$;
