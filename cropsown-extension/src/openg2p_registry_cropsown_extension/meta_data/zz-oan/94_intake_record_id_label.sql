-- "ID" instead of "Name" for an intake's record name.
--
-- An intake only carries the Farmer ID and Fayda ID (no farmer name), so its
-- record name is the Farmer ID. The staff UI overrides of the intake submission
-- card, the intake list column and the submission header
-- (ui/staff-ui/overrides/src/...) label it with the key intake_record_id. The
-- shared record_name key ("Name") stays for registers, change requests and tasks.
--
-- A translation already set for intake_record_id is kept, so a word changed in the
-- language data survives a reseed. A second run changes nothing.
UPDATE "public"."registry_languages"
   SET "domain_translation" = (jsonb_build_object('intake_record_id', 'ID')
                               || COALESCE("domain_translation"::jsonb, '{}'::jsonb))::json
 WHERE "language_code" IN ('en', 'am', 'om', 'ti')
   AND NOT (COALESCE("domain_translation"::jsonb, '{}'::jsonb) ? 'intake_record_id');
