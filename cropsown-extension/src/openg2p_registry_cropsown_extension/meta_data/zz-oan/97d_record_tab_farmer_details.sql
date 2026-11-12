-- The Crop sown record's first tab (cropsown_cropsown_tab, label key
-- cropsown_record_tab) is named "Farmer details" instead of "Crop sown".
--
-- English text in all four languages for now, as the Farmer tab already is; a
-- translation can replace it per language here. Sorts after
-- 30_label_casing.sql, which set "Crop sown". A second run changes nothing.
UPDATE "public"."registry_languages"
   SET "domain_translation" = (COALESCE("domain_translation"::jsonb, '{}'::jsonb)
                               || jsonb_build_object('cropsown_record_tab', 'Farmer details'))::json
 WHERE "language_code" IN ('en', 'am', 'om', 'ti')
   AND COALESCE("domain_translation"::jsonb->>'cropsown_record_tab', '') <> 'Farmer details';
