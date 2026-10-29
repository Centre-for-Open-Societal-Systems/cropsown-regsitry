"""The Crop Sown record's first tab reads as a crop record, a farmer and Fayda IDs.

41_crop_record_tab_layout.sql rewrites two sections in full; it must keep every
widget and data path and only change the labels and titles it names.
"""

import json
import re
from pathlib import Path

META = Path(__file__).resolve().parents[1] / "src" / "openg2p_registry_cropsown_extension" / "meta_data"
OVERLAY = META / "zz-oan" / "41_crop_record_tab_layout.sql"
REGISTER = "6b06a95a-9a6c-5a33-a33d-c1625716c59c"


def sections():
    text = OVERLAY.read_text(encoding="utf-8")
    found = {}
    for schema, sid in re.findall(
            r"SET \"section_ui_schema\" = '(.*?)'::jsonb.*?\"section_id\" = '([a-z0-9_]+)';", text, re.S):
        found[sid] = json.loads(schema.replace("''", "'"))
    return found


def widgets(node):
    if isinstance(node, dict):
        if "widget-id" in node:
            yield node
        for value in node.values():
            yield from widgets(value)
    elif isinstance(node, list):
        for value in node:
            yield from widgets(value)


def test_record_section_columns_and_labels():
    record = sections()["cropsown_cropsown_record_section_01"]
    assert record["section-title"] == "Crop record"
    columns = [[w["widget-id"] for w in panel["widgets"]] for panel in record["panels"][0]["panels"]]
    assert columns == [["functional_record_id", "crop_year", "production_season"],
                       ["farmer_id", "farmer_name", "farmer_reference_status"],
                       ["fayda_fan_id", "fayda_fin", "identity_verification"]]
    labels = {w["widget-id"]: w["widget-label"] for w in widgets(record)}
    assert labels["fayda_fan_id"] == "Fayda FAN ID"
    assert labels["fayda_fin"] == "Fayda FIN"
    assert labels["farmer_name"] == "Farmer name"


def test_location_section_labels():
    location = sections()["cropsown_cropsown_location_section_03"]
    assert location["section-title"] == "Crop location"
    labels = {w["widget-id"]: w["widget-label"] for w in widgets(location)}
    assert labels == {"cropsown_geo_hierarchy": "Location", "latitude": "Latitude",
                      "longitude": "Longitude", "cropsown_geo_point": "Map location"}


def test_no_label_carries_a_hint_and_paths_stay_on_the_register():
    for section in sections().values():
        for widget in widgets(section):
            assert "(" not in widget["widget-label"], widget["widget-label"]
            paths = widget.get("widget-data-path")
            for path in (paths.values() if isinstance(paths, dict) else [paths] if paths else []):
                if isinstance(path, str):
                    assert path.startswith(REGISTER + "."), path
