"""The crop record's location section is the farmer's Address, copied from the approved Farmer."""
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_cropsown_extension.farmer_reference import projection

PACKAGE = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension"
ZZ_OAN = PACKAGE / "meta_data/zz-oan"
OVERLAY = ZZ_OAN / "97e_address_section.sql"


def record(**values):
    fields = dict.fromkeys(list(projection.ADDRESS_FIELDS.values())
                           + ["geo_lowest_level_value_id", "geo_code_hierarchy_json"])
    return SimpleNamespace(**{**fields, **values})


def farmer(**values):
    fields = dict.fromkeys(list(projection.ADDRESS_FIELDS) + ["geo_lowest_level_value_id", "geo_code_hierarchy_json"])
    return SimpleNamespace(**{**fields, **values})


def test_the_farmers_address_is_copied_onto_the_record():
    chain = {"hierarchy": [{"level_id": "l3", "level_value_id": "ET040101"}], "lowest_level_value_id": "ET040101"}
    source = farmer(region_id="ET04", zone_id="ET0401", woreda_id="ET040101", region_name="Oromia",
                    woreda_name="Ambo", latitude=8.98, longitude=37.85,
                    geo_lowest_level_value_id="ET040101", geo_code_hierarchy_json=chain)
    row = record(region="ET03", woreda="ET030303", woreda_name="Dabat")
    assert projection._mirror_address(row, source) is True
    assert (row.region, row.zone, row.woreda, row.kebele) == ("ET04", "ET0401", "ET040101", None)
    assert (row.region_name, row.woreda_name) == ("Oromia", "Ambo")
    assert (row.latitude, row.longitude) == ("8.98", "37.85")  # text, as the record keeps them
    assert row.geo_lowest_level_value_id == "ET040101" and row.geo_code_hierarchy_json == chain
    assert projection._mirror_address(row, source) is False  # nothing left to change


def test_a_farmer_without_an_address_leaves_the_record_as_it_is():
    row = record(region="ET03", woreda="ET030303", latitude="12.1")
    assert projection._mirror_address(row, farmer()) is False
    assert (row.region, row.woreda, row.latitude) == ("ET03", "ET030303", "12.1")


def test_a_record_without_address_columns_is_not_touched():
    assert projection._mirror_address(SimpleNamespace(farmer_id="FR-1"), farmer(woreda_id="ET040101")) is False


def test_the_section_is_the_read_only_address_and_off_the_planning_form():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "WHERE \"section_id\" = 'cropsown_cropsown_location_section_03'" in sql
    assert '{"section-title": "Address", "section-editable": false}' in sql
    assert "node->>'widget' IN ('geo-hierarchy', 'oan-geo-point')" in sql and '{"widget-readonly": true}' in sql
    assert 'DELETE FROM "public"."g2p_intake_form_ui_tab_sections"' in sql
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql"
    assert len({n.split("_")[0] for n in names}) == len(names)


def test_odk_and_file_import_no_longer_send_the_address_section():
    for template in ("odk_to_crop_intake.j2", "crop_file_import_planning_intake.j2"):
        text = (PACKAGE / "templates" / template).read_text(encoding="utf-8")
        assert "'cs_cropsown_location'" not in text and '"cs_cropsown_location"' not in text
