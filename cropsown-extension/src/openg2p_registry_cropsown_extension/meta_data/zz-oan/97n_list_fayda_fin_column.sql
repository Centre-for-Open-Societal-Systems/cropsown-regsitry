-- Crop Sown register list: a "Fayda FIN ID" column next to "Fayda FAN ID", so a farmer
-- registered with a FIN no longer shows a blank Fayda value. Each row shows its FAN in
-- one column and its FIN in the other (field fayda_fin, a stored column of the record).
--
-- The new column goes right after Fayda FAN ID; the columns after it move one place
-- along. Crop Sown register only; stored values, search, filters, the record page and the
-- Farmer register are unchanged. Sorts after 86_readable_lists.sql, which names the FAN
-- column. A second run changes nothing (the column is added only when it is missing).
-- The register is found by its mnemonic (CropSown), not by its id.
UPDATE "public"."g2p_register_schemas" s
   SET "search_result_schema" = (
       SELECT jsonb_agg(x.item ORDER BY (x.item->>'order')::int)
         FROM (SELECT CASE WHEN (e->>'order')::int > f.fan_order
                           THEN e || jsonb_build_object('order', (e->>'order')::int + 1)
                           ELSE e END AS item
                 FROM jsonb_array_elements(s."search_result_schema"::jsonb) e
               UNION ALL
               SELECT jsonb_build_object('order', f.fan_order + 1, 'field_name', 'fayda_fin',
                                         'display_label', 'Fayda FIN ID')) x)::json
  FROM (SELECT (c->>'order')::int AS fan_order
          FROM "public"."g2p_register_schemas" s2, jsonb_array_elements(s2."search_result_schema"::jsonb) c
         WHERE s2."register_id" = (SELECT "register_id" FROM "public"."g2p_register_definitions" WHERE "register_mnemonic" = 'CropSown') AND c->>'field_name' = 'fayda_fan_id') f
 WHERE s."register_id" = (SELECT "register_id" FROM "public"."g2p_register_definitions" WHERE "register_mnemonic" = 'CropSown')
   AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(s."search_result_schema"::jsonb) c
                    WHERE c->>'field_name' = 'fayda_fin');

-- The column's label, also on a list that already has the column.
UPDATE "public"."g2p_register_schemas"
   SET "search_result_schema" = (
       SELECT jsonb_agg(CASE WHEN item->>'field_name' = 'fayda_fin'
                             THEN item || '{"display_label": "Fayda FIN ID"}'::jsonb ELSE item END ORDER BY position)
         FROM jsonb_array_elements("search_result_schema"::jsonb) WITH ORDINALITY AS a(item, position))::json
 WHERE "register_id" = (SELECT "register_id" FROM "public"."g2p_register_definitions" WHERE "register_mnemonic" = 'CropSown');

-- The list's column headers are the domain translations of the field names (as for
-- fayda_fan_id), not display_label. English as asked; the other languages follow their own
-- wording of the FAN column, with FIN. Merged by key.
UPDATE "public"."registry_languages"
   SET "domain_translation" = (COALESCE("domain_translation"::jsonb, '{}'::jsonb) || jsonb_build_object('fayda_fin',
       CASE "language_code" WHEN 'am' THEN 'የፋይዳ መለያ (FIN)' WHEN 'om' THEN 'Lakkoofsa Fayidaa (FIN)'
                            WHEN 'ti' THEN 'መለለዪ ፋይዳ (FIN)' ELSE 'Fayda FIN ID' END))::json;

DO $$
DECLARE fan int; fin int;
BEGIN
    SELECT max(CASE WHEN c->>'field_name' = 'fayda_fan_id' THEN (c->>'order')::int END),
           max(CASE WHEN c->>'field_name' = 'fayda_fin' THEN (c->>'order')::int END)
      INTO fan, fin
      FROM "public"."g2p_register_schemas" s, jsonb_array_elements(s."search_result_schema"::jsonb) c
     WHERE s."register_id" = (SELECT "register_id" FROM "public"."g2p_register_definitions" WHERE "register_mnemonic" = 'CropSown');
    IF fan IS NULL OR fin IS NULL OR fin <> fan + 1 THEN
        RAISE EXCEPTION 'Crop Sown list: the Fayda FIN ID column is not next to Fayda FAN ID';
    END IF;
END
$$;
