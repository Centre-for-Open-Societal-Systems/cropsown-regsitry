-- The multi-select list (for example the cluster status on a sowing row) shows
-- the core translations common.selectedCount, common.selectAll,
-- common.deselectAll and common.clearAll. The English seed holds the raw keys
-- ("SelectedCount", "SelectAll", ...), so the list read "SelectedCount" instead
-- of how many items are chosen. The widget passes the number as {count}.
-- The keys are merged inside "common", so its other keys stay as they are; the
-- other languages already have their own text and are not touched. Idempotent.
UPDATE "public"."registry_languages"
SET "core_translation" = jsonb_set(
    COALESCE("core_translation"::jsonb, '{}'::jsonb),
    '{common}',
    COALESCE("core_translation"::jsonb -> 'common', '{}'::jsonb) ||
    '{
     "selectedCount": "{count} selected",
     "selectAll": "Select all",
     "deselectAll": "Deselect all",
     "clearAll": "Clear all"
    }'::jsonb
)::json
WHERE "language_code" = 'en';
