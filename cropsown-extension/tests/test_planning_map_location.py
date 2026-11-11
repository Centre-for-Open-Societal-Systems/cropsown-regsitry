"""Crop planning rows take their position from a map instead of a typed GPS coordinate.

The overlay replaces the Planning table's GPS coordinate column with Map location,
Latitude and Longitude; the map fills the row's Latitude, Longitude, Region, Zone and
Woreda (GeoPointWidget table-row mode). gps_coordinate stays in the database.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension"
ZZ_OAN = PACKAGE / "meta_data/zz-oan"
OVERLAY = ZZ_OAN / "97c_planning_map_location.sql"
WIDGETS = ROOT / "ui/staff-ui/overrides/src/oan/widgets"


def test_only_the_planning_table_swaps_gps_for_the_map():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "WHERE \"section_id\" = 'cropsown_planning_details_section_01'" in sql
    for other in ("cropsown_cluster_details_section_01", "cropsown_cultivation_cluster_details_section_01",
                  "cropsown_cropsown_location_section_03"):
        assert other not in sql
    # the land map after Kebele (Land details), the crop map after Expected yield (Crop planned inputs)
    assert "IF col->>'column-key' = 'kebele' THEN" in sql and "ELSIF col->>'column-key' = 'expected_yield' THEN" in sql
    assert sql.count("'column-group', 'Land details'") == 3 and sql.count("'column-group', 'Crop planned inputs'") == 3
    assert "'oan-row-paths', jsonb_build_object('latitude', 'crop_latitude', 'longitude', 'crop_longitude')" in sql
    assert sql.count("'levels'") == 1  # only the land map fills Region, Zone and Woreda
    for key in ("'map_location'", "'latitude'", "'longitude'", "'oan-geo-point'", "'oan-row-paths'"):
        assert key in sql
    assert "'l1', 'region', 'l2', 'zone', 'l3', 'woreda', 'l4', 'kebele'" in sql
    assert "'column-visible-in-table', false" in sql
    # typed in the row's own columns, not in boxes of the map
    assert "'Latitude', 'widget-readonly', false" in sql and "'Longitude', 'widget-readonly', false" in sql


def test_the_overlay_runs_after_the_cascade_and_before_the_dates():
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql"
    assert names.index(OVERLAY.name) > names.index("97b_cascading_location.sql")
    assert len({n.split("_")[0] for n in names}) == len(names)


def test_the_planning_model_keeps_gps_and_adds_latitude_and_longitude():
    model = (PACKAGE / "register_domain/models/planning.py").read_text(encoding="utf-8")
    for column in ("gps_coordinate", "latitude", "longitude", "crop_latitude", "crop_longitude"):
        assert f"    {column}: Mapped[str] = mapped_column(String, nullable=True)" in model
    transitions = json.loads((ROOT / "reference/metadata-transitions.json").read_text(encoding="utf-8"))
    assert {"from_section": "cropsown_planning_details_section_01", "path": "gps_coordinate",
            "mechanism": "retired_field", "replaced_by": "latitude"}.items() <= next(
        t for t in transitions["transitions"] if t.get("path") == "gps_coordinate").items()


def test_odk_and_file_import_fill_the_planning_latitude_and_longitude():
    odk = (PACKAGE / "templates/odk_to_crop_intake.j2").read_text(encoding="utf-8")
    planning = odk.split('"cs_planning_details"')[1]
    assert '"latitude": "{{ p_lat }}"' in planning and '"longitude": "{{ p_lon }}"' in planning
    assert "p_gps_str" not in odk
    imported = (PACKAGE / "templates/crop_file_import_planning_intake.j2").read_text(encoding="utf-8")
    assert "record.update({'latitude': latitude | string, 'longitude': longitude | string})" in imported


def test_the_map_has_a_table_row_mode():
    widget = (WIDGETS / "GeoPointWidget.tsx").read_text(encoding="utf-8")
    assert "export function rowMode(config: Config): RowMode | null" in widget
    assert "config['oan-row-paths']" in widget and "'-dlg-'" in widget
    assert "rowPatch[cell] = entry ? entry.level_value_id : null;" in widget
    assert "{!row && (" in widget  # no coordinate boxes of its own in a table row
    assert ".dialog-table-field:has(.oan-geo-row) { grid-column: 1 / -1; }" in widget  # full row
    cascade = (WIDGETS / "CascadingSelectWidget.tsx").read_text(encoding="utf-8")
    # a level set together with its parent (by the map) is kept
    assert "before.own === ownValue" in cascade
