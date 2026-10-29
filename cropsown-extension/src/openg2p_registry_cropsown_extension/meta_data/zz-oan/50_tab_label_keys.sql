-- Display text for the Farmer tab's label key.
-- The platform only accepts lowercase keys in g2p_register_ui_tabs.tab_label
-- (G2PRegisterUITab.validate_tab_label); the change request search rebuilds tabs
-- from the metadata cache, which runs that check, so a label such as 'Farmer'
-- fails every cached search with SYS-ERR-001. zz_farmer_register.sql seeds the
-- key cropsown_farmer_tab, like the other Crop tabs, and the text staff read
-- comes from the domain translations. A language that already translates the
-- key keeps its own text.

UPDATE "public"."registry_languages"
SET "domain_translation" = ('{"cropsown_farmer_tab": "Farmer"}'::jsonb
  || COALESCE("domain_translation"::jsonb, '{}'::jsonb))::json;
