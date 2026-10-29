-- The sentence shown when a coded value (crop, season, variety ...) is not on its
-- Master Data list: "Crop: choose a crop from the list." The server builds the
-- label and noun per field; this key only holds the wording. The merge adds the
-- one key and keeps every other translation. Safe to run on every deploy.
UPDATE "public"."registry_languages"
SET "domain_translation" = (COALESCE("domain_translation"::jsonb, '{}'::jsonb) ||
'{
 "coss_code_choice": "{label}: choose {noun} from the list."
}'::jsonb)::json
WHERE "language_code" = 'en';
