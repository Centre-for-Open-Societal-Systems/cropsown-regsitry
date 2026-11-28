-- Validation message keys and the location panel id lose their old implementer
-- prefix. The seeds upsert and never delete, so a database that was seeded earlier
-- still holds the old names; this file moves them to the new names and leaves none
-- behind. It reads only the old names, so it is a no-op once they are gone and is
-- safe to run on every deploy, before or after the files that write the new keys.
--
--   coss_input_<x>        -> validation_<x>
--   coss_field_<x>        -> validation_rule_<x>
--   coss_code_choice      -> validation_code_choice
--   panel coss_location_widgets -> location_widgets

-- 1. Saved section schemas: the message keys named by patternMessage / minDateMessage.
UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = regexp_replace(regexp_replace(regexp_replace(
    section_ui_schema::text,
    'coss_input_', 'validation_', 'g'),
    'coss_field_', 'validation_rule_', 'g'),
    'coss_code_choice', 'validation_code_choice', 'g')::jsonb
WHERE section_ui_schema::text ~ 'coss_(input_|field_|code_choice)';

-- 2. Saved location panel id (the seed that appends the panel checks the new id).
UPDATE "public"."g2p_register_sections"
SET "section_ui_schema" = regexp_replace(section_ui_schema::text,
    '("panel-id": ?)"coss_location_widgets"', '\1"location_widgets"', 'g')::jsonb
WHERE section_ui_schema::text ~ '"panel-id": ?"coss_location_widgets"';

-- 3. Translations: an old key hands its text to the new key when the new key is
-- missing (a local edit survives), then every old key is removed. The new keys win
-- when both exist.
UPDATE "public"."registry_languages"
SET "domain_translation" = (
    SELECT COALESCE(jsonb_object_agg(
        regexp_replace(regexp_replace(regexp_replace(key,
            '^coss_input_', 'validation_'),
            '^coss_field_', 'validation_rule_'),
            '^coss_code_choice$', 'validation_code_choice'), value), '{}'::jsonb)
    FROM jsonb_each("domain_translation"::jsonb) WHERE key ~ '^coss_'
  ) || (
    SELECT COALESCE(jsonb_object_agg(key, value), '{}'::jsonb)
    FROM jsonb_each("domain_translation"::jsonb) WHERE key !~ '^coss_'
  )
WHERE "domain_translation"::jsonb::text ~ '"coss_';
