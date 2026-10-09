"""The forms' location lists are the registry's location hierarchy.

docs/odk/media/{region,zone,woreda,kebele1}.csv are generated from the crop
sown registry's geo attribute values by docs/odk/build_location_media.py. If
they drift, field agents can pick a place the registry does not know (or cannot
pick one it does), and the transform sends an id nothing resolves.
"""

import copy
import csv
import importlib.util
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
ODK = REPO / "docs" / "odk"
TEMPLATE = REPO / "cropsown-extension/src/openg2p_registry_cropsown_extension/templates/csr_odk_transform.j2"

spec = importlib.util.spec_from_file_location("build_location_media", ODK / "build_location_media.py")
build_location_media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_location_media)

HIERARCHY = build_location_media.load_hierarchy()
IDS = {f"{level.upper()}_{code}" for level, rows in HIERARCHY.items() for code, _, _ in rows}


def _csv(name):
    return list(csv.DictReader((ODK / "media" / name).open(encoding="utf-8")))


def test_committed_lists_are_what_the_generator_builds():
    for name, text in build_location_media.build(HIERARCHY).items():
        assert (ODK / "media" / name).read_bytes().decode("utf-8") == text, (
            f"{name} is stale: run python docs/odk/build_location_media.py"
        )


def test_every_place_is_offered_once_under_its_parent():
    counts = {level: len(rows) for level, rows in HIERARCHY.items()}
    assert counts == {"region": 14, "zone": 125, "woreda": 1379, "kebele": 19535}
    zones, woredas, kebeles = _csv("zone.csv"), _csv("woreda.csv"), _csv("kebele1.csv")
    assert (len(zones), len(woredas), len(kebeles)) == (125, 1379, 19535)
    regions = {row["name"] for row in _csv("region.csv")}
    assert {z["region"] for z in zones} <= regions
    assert {w["zone"] for w in woredas} <= {z["name"] for z in zones}
    assert {k["woreda"] for k in kebeles} <= {w["name"] for w in woredas}


@pytest.mark.parametrize("kebele_index", [0, 7000, 19534])
def test_a_pick_from_the_lists_becomes_registry_ids(kebele_index):
    jinja2 = pytest.importorskip("jinja2")
    kebele = _csv("kebele1.csv")[kebele_index]
    woreda = {w["name"]: w for w in _csv("woreda.csv")}[kebele["woreda"]]
    zone = {z["name"]: z for z in _csv("zone.csv")}[woreda["zone"]]
    submission = {
        "farmer_identity": {"farmer_id": "FR-1", "fayda_fan_id": "1234567890123456", "crop_year": 2026, "production_season": "belg"},
        "address": {
            "region_display_id": zone["region"], "zone_display_id": zone["name"],
            "woreda_display_id": woreda["name"], "kebele_display_id": kebele["name"],
        },
        "planning": [{"land_info_id": "LND-1", "season_id": "belg", "cluster_information": []}],
        "__system": {"submissionDate": "2026-10-08T06:00:00.000Z"},
    }
    record = json.loads(jinja2.Template(TEMPLATE.read_text(encoding="utf-8")).render(expanded=copy.deepcopy(submission)))[
        "cs_intake_record"
    ][0]
    for field in ("region", "zone", "woreda", "kebele", "geo_lowest_level_value_id"):
        assert record[field] in IDS, (field, record[field])
    assert record["kebele"] == f"KEBELE_{kebele['name']}"
