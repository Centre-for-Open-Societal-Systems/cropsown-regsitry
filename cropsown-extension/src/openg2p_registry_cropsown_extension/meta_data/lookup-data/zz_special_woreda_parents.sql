-- The three special woredas hang under their special zones.
--
-- g2p_attribute_values.sql seeded Kebena, Mareko and Tembaro SP woreda with no
-- parent, so a location cascade could never reach them (pick the zone, the
-- woreda is not offered). The shared location hierarchy every registry now
-- uses places them under Kebena, Mareko and Tembaro Special; the seed file has
-- that parent too, but it is a plain INSERT and leaves existing rows alone, so
-- this sets it where it is still missing. Never overwrites a parent that is set.

UPDATE "public"."g2p_attribute_values" AS v
SET "parent_value_id" = p.parent
FROM (VALUES
    ('WOREDA_ET070001', 'ZONE_ET0705'),
    ('WOREDA_ET072501', 'ZONE_ET0706'),
    ('WOREDA_ET072601', 'ZONE_ET0707')
) AS p(value_id, parent)
WHERE v."value_id" = p.value_id
  AND v."parent_value_id" IS NULL;
