"""Crop Sown register list: a "Fayda FIN ID" column right after "Fayda FAN ID", so a row shows
its FAN in one column and its FIN in the other."""
from pathlib import Path

OVERLAY = (Path(__file__).resolve().parents[1]
           / "src/openg2p_registry_cropsown_extension/meta_data/zz-oan/97n_list_fayda_fin_column.sql")


def test_the_fin_column_goes_after_the_fan_column_of_the_crop_sown_list_only():
    sql = OVERLAY.read_text(encoding="utf-8")
    update = sql.split('UPDATE "public"."g2p_register_schemas" s')[1].split(";")[0]
    assert "WHERE s.\"register_id\" = '6b06a95a-9a6c-5a33-a33d-c1625716c59c'" in update  # Crop Sown only
    assert "jsonb_build_object('order', f.fan_order + 1, 'field_name', 'fayda_fin',\n" in update
    assert "'display_label', 'Fayda FIN ID')" in update
    assert 'THEN item || \'{"display_label": "Fayda FIN ID"}\'::jsonb' in sql  # also on an existing column
    assert "Fayda Fin" not in sql  # the text check refuses Title Case; FIN is an allowed acronym
    # the header is the field's domain translation, in every language
    translation = sql.split('UPDATE "public"."registry_languages"')[1].split(";")[0]
    assert "WHERE" not in translation and "jsonb_build_object('fayda_fin'," in translation
    assert "ELSE 'Fayda FIN ID' END" in translation
    assert "THEN e || jsonb_build_object('order', (e->>'order')::int + 1)" in update  # later columns move along
    assert update.rstrip().endswith("WHERE c->>'field_name' = 'fayda_fin')")  # added only once
    assert "fayda_fan_id' THEN" in sql and "RAISE EXCEPTION" in sql
    assert "filter_schema" not in sql and "fayda_fan_or_fin" not in sql


def test_the_overlay_sorts_after_the_list_labels_and_before_the_dates():
    names = sorted(p.name for p in OVERLAY.parent.glob("*.sql"))
    assert names.index("86_readable_lists.sql") < names.index(OVERLAY.name) < names.index("98_ethiopian_dates.sql")
    assert len({n.split("_")[0] for n in names}) == len(names)
