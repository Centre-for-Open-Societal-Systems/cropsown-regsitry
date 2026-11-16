-- "Import from file": the message shown after a file is uploaded, and the menu labels.
-- The platform shows the core translation import_successful as soon as the file
-- is queued, before any row is read. Each row is then checked on its own, and a
-- row that fails (for example a file made for another form's import) creates no
-- intake; its reason is in Incoming Messages. So the message says the file was
-- uploaded and where to see each row's result, not that the import succeeded.
-- The Import from file menu shows an import configuration's translation when a
-- key named after its import_file_template_mnemonic exists, else the mnemonic
-- itself; the four keys below give each crop import a readable label (the
-- mnemonic, which data models and templates use, stays as it is).
-- Display text only, merged by key, so keys not named stay as they are; every
-- language, because none of them has its own text for these keys yet.
UPDATE "public"."registry_languages"
SET "core_translation" = (COALESCE("core_translation"::jsonb, '{}'::jsonb) ||
'{
 "import_successful": "File uploaded. Check Incoming Messages for the result of each row.",
 "file_import_to_crop_planning_intake": "Planning (with clusters)",
 "file_import_to_crop_cultivation_intake": "Cultivation (with cultivation clusters)",
 "file_import_to_crop_sowing_intake": "Sowing (with infestations)",
 "file_import_to_crop_harvesting_intake": "Harvest"
}'::jsonb)::json;
