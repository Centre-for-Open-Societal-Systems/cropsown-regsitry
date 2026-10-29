-- The seven ATI brand themes are retired: the staff-portal theme is data in
-- openg2p-data (oan_theme, rendered into 90_oan_theme.sql), and its crop entry
-- carries the ATI-Green palette. Seed upserts never delete, so long-lived
-- databases drop the rows here, by explicit id. A theme the registry
-- configuration still points at is left in place.
DELETE FROM "public"."registry_theme_values" v
 WHERE v."theme_id" IN (
       '9d109f28-ab6a-5617-bf27-649b0f92aa5a',
       'b6df9c20-df62-549c-8147-2f872c4fced0',
       '00e923a7-7be6-581d-867b-7fcfc102b369',
       '4d35d365-c019-593b-98ed-1f7f1b0f474c',
       '2f041a25-8abe-5fd6-819d-0361e72be31e',
       '9921ddc0-4f7e-56bb-9b6e-b8dbca186e7f',
       '3b1faa01-0060-545c-8a68-22fb5b35525c')
   AND NOT EXISTS (SELECT 1 FROM "public"."g2p_registry_configuration" c
                    WHERE c."registry_theme_id" = v."theme_id");

DELETE FROM "public"."registry_themes" t
 WHERE t."theme_id" IN (
       '9d109f28-ab6a-5617-bf27-649b0f92aa5a',
       'b6df9c20-df62-549c-8147-2f872c4fced0',
       '00e923a7-7be6-581d-867b-7fcfc102b369',
       '4d35d365-c019-593b-98ed-1f7f1b0f474c',
       '2f041a25-8abe-5fd6-819d-0361e72be31e',
       '9921ddc0-4f7e-56bb-9b6e-b8dbca186e7f',
       '3b1faa01-0060-545c-8a68-22fb5b35525c')
   AND NOT EXISTS (SELECT 1 FROM "public"."g2p_registry_configuration" c
                    WHERE c."registry_theme_id" = t."theme_id");
