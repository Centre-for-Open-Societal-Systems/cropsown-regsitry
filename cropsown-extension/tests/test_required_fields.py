"""Tests for the required fields read from the section metadata (required_fields.py).

The module has no framework imports, so these run without the registry installed:

    uv run --no-project --with pytest pytest cropsown-extension/tests/test_required_fields.py
"""

import importlib.util
import json
import sys
from pathlib import Path

PACKAGE = Path(__file__).parents[1] / "src/openg2p_registry_cropsown_extension"
spec = importlib.util.spec_from_file_location("crop_required_fields_pure", PACKAGE / "required_fields.py")
rf = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rf
spec.loader.exec_module(rf)

ROOT = "6b06a95a-9a6c-5a33-a33d-c1625716c59c"
MESSAGES = {"Gender": "Gender", "farmer_details": "Farmer Details"}


def widget(widget_id, kind="text", required=False, options=None, label=None, **extra):
    found = {"widget": kind, "widget-id": widget_id, "widget-label": label or widget_id,
             "widget-required": required, "widget-data-path": f"{ROOT}.{widget_id}", **extra}
    if options:
        found["widget-data-options"] = options
    return found


def column(key, required=False, options=None, label=None):
    found = {"widget": "text", "column-key": key, "widget-label": label or key, "widget-required": required,
             "widget-data-path": key}
    if options:
        found["widget-data-options"] = options
    return found


def equals(field, value, prefix=True):
    return {"field": f"{ROOT}.{field}" if prefix else field, "operator": "equals", "value": value}


def section(title, *widgets):
    return {"section-title": title, "panels": [{"widgets": list(widgets)}]}


def table_section(title, columns, required=False):
    return {"section-title": title, "panels": [{"widgets": [
        {"widget": "table", "widget-id": "rows", "widget-required": required, "widget-data-columns": columns}]}]}


def problems(schema, record, *, is_list=False, messages=MESSAGES, files=None, records=None, values=None):
    rows = records if records is not None else ([record] if record is not None else [])
    return rf.section_problems(schema, is_list, rows, values if values is not None else {ROOT: rows[0] if rows else {}},
                               messages, files)


SEASON = section("Production Season",
                 widget("crop_year", "number", required=True, label="Crop Year"),
                 widget("production_season", "select", required=True, label="Production Season"),
                 widget("remarks"))


def test_an_empty_required_section_names_every_missing_field():
    assert problems(SEASON, {}) == ["Production Season: fill in Crop Year, Production Season"]


def test_a_field_left_out_of_the_record_is_missing_like_an_empty_one():
    assert problems(SEASON, {"crop_year": 2026, "production_season": ""}) == ["Production Season: fill in Production Season"]
    assert problems(SEASON, {"crop_year": 2026}) == ["Production Season: fill in Production Season"]


def test_a_complete_section_has_nothing_missing():
    assert problems(SEASON, {"crop_year": 2026, "production_season": "SEASON_MEHER"}) == []


def test_an_untranslated_name_reads_without_underscores():
    schema = section("farmer_details", widget("marital_status", required=True))
    result = problems(schema, {}, messages={})
    assert result == ["Farmer details: fill in Marital status"] and "_" not in result[0]


def test_blank_values_are_missing_but_false_and_zero_are_answers():
    schema = section("s", widget("flag", "boolean", required=True), widget("count", "number", required=True))
    assert problems(schema, {"flag": False, "count": 0}) == []
    assert problems(schema, {"flag": None, "count": "  "}) == ["S: fill in Flag, Count"]


def test_a_hidden_field_is_not_required():
    schema = section("s", widget("has_land", "boolean"),
                     widget("land_id", required=True, options={"actions": [{"action": "show", "condition": equals("has_land", True)}]}))
    assert problems(schema, {"has_land": False}) == []
    assert problems(schema, {"has_land": True}) == ["S: fill in Land id"]


def test_the_single_action_form_of_the_metadata_is_read_too():
    schema = section("s", widget("kind", "select"),
                     widget("detail", required=True, options={"action": "show", "condition": equals("kind", "OTHER")}))
    assert problems(schema, {"kind": "SEED"}) == []
    assert problems(schema, {"kind": "OTHER"}) == ["S: fill in Detail"]


def test_a_require_rule_makes_an_optional_field_required():
    schema = section("s", widget("infested", "boolean"),
                     widget("pest", "select", options={"actions": [{"action": "require", "condition": equals("infested", True)}]}))
    assert problems(schema, {"infested": False}) == []
    assert problems(schema, {"infested": True}) == ["S: fill in Pest"]


def test_the_last_show_or_hide_rule_wins():
    schema = section("s", widget("a", "boolean"), widget("b", "boolean"),
                     widget("x", required=True, options={"actions": [
                         {"action": "hide", "condition": equals("a", True)},
                         {"action": "show", "condition": equals("b", True)}]}))
    assert problems(schema, {"a": True, "b": False}) == []
    assert problems(schema, {"a": True, "b": True}) == ["S: fill in X"]


def test_conditions_with_in_not_in_and_or_not():
    def schema_with(condition):
        return section("s", widget("k"), widget("m"),
                       widget("x", required=True, options={"actions": [{"action": "show", "condition": condition}]}))

    listed = {"field": f"{ROOT}.k", "operator": "in", "value": ["A", "B"]}
    assert problems(schema_with(listed), {"k": "B"}) == ["S: fill in X"]
    assert problems(schema_with(listed), {"k": "C"}) == []
    assert problems(schema_with({**listed, "operator": "notIn"}), {"k": "C"}) == ["S: fill in X"]
    both = {"and": [equals("k", "A"), {"field": f"{ROOT}.m", "operator": "notEmpty"}]}
    assert problems(schema_with(both), {"k": "A", "m": "z"}) == ["S: fill in X"]
    assert problems(schema_with(both), {"k": "A", "m": ""}) == []
    either = {"or": [equals("k", "A"), equals("m", "z")]}
    assert problems(schema_with(either), {"k": "C", "m": "z"}) == ["S: fill in X"]
    assert problems(schema_with({"not": equals("k", "A")}), {"k": "A"}) == []
    assert problems(schema_with({"field": f"{ROOT}.k", "operator": "unknown"}), {"k": "A"}) == []


def test_a_condition_may_look_at_another_section_of_the_form():
    schema = section("s", widget("x", required=True, options={"actions": [{"action": "show", "condition": equals("has_id", True)}]}))
    shown = rf.section_problems(schema, False, [{}], {ROOT: {"has_id": True}}, {})
    hidden = rf.section_problems(schema, False, [{}], {ROOT: {"has_id": False}}, {})
    assert shown == ["S: fill in X"] and hidden == []


def test_readonly_lookups_and_display_widgets_are_left_alone():
    schema = section("s", widget("lookup", "register-lookup", required=True), widget("shown", "display", required=True),
                     widget("locked", required=True, **{"widget-readonly": True}))
    assert problems(schema, {}) == []


def test_a_required_table_needs_a_row():
    schema = table_section("Crop Planning Details", [column("land_id", required=True)], required=True)
    assert problems(schema, None, is_list=True, records=[]) == ["Crop Planning Details: add at least one row"]


def test_an_optional_table_may_be_empty():
    schema = table_section("Crop Planning Details", [column("land_id", required=True)])
    assert problems(schema, None, is_list=True, records=[]) == []


def test_each_row_needs_its_required_columns():
    schema = table_section("Crop Planning Details", [column("land_id", required=True, label="Land ID"),
                                                     column("season", required=True, label="Season")])
    rows = [{"land_id": "L1", "season": "MEHER"}, {"land_id": "L2", "season": ""}, {"season": None}]
    assert problems(schema, None, is_list=True, records=rows) == [
        "Crop Planning Details, row 2: fill in Season", "Crop Planning Details, row 3: fill in Land ID, Season"]


def test_a_hidden_column_is_not_required():
    schema = table_section("Crops", [
        column("is_diseased"),
        column("disease_type", required=True, label="Disease Type",
               options={"actions": [{"action": "show", "condition": equals("is_diseased", True, prefix=False)}]})])
    assert problems(schema, None, is_list=True, records=[{"is_diseased": False}]) == []
    assert problems(schema, None, is_list=True, records=[{"is_diseased": True}]) == ["Crops, row 1: fill in Disease Type"]


def test_a_required_document_is_a_file_to_add():
    schema = section("Documents", widget("permit", "file", required=True, options={"title": "Permit"}))
    assert problems(schema, {}) == ["Documents: add Permit"]
    assert problems(schema, {}, files={"permit"}) == []


def test_the_typed_fayda_id_counts_as_filled_when_the_fin_or_the_fan_is_stored():
    lookup = section("Farmer lookup", widget("farmer_id", required=True, label="Farmer ID"),
                     widget("fayda_id", required=True, label="Fayda ID (FAN or FIN)"))
    assert problems(lookup, {"farmer_id": "FR-000000000001"}) == ["Farmer lookup: fill in Fayda ID (FAN or FIN)"]
    assert problems(lookup, {"farmer_id": "FR-000000000001", "fayda_fin": "001234567890"}) == []
    assert problems(lookup, {"farmer_id": "FR-000000000001", "fayda_fan_id": "1234567890123456"}) == []
    # A typed value that was cleared is not rescued by the stored one.
    assert problems(lookup, {"farmer_id": "FR-000000000001", "fayda_id": "", "fayda_fin": "001234567890"}) == [
        "Farmer lookup: fill in Fayda ID (FAN or FIN)"]


# ---------------------------------------------------- the real Crop Sown metadata --
META = PACKAGE / "meta_data"


def _sections_in_base_file():
    found = {}
    text = (META / "register-metadata/g2p_register_sections.sql").read_text(encoding="utf8")
    for line in text.split("\n"):
        if line.startswith("('") and "{" in line:
            line = line.replace("''", "'")
            section_id = line.split("','")[1]
            ui, _ = json.JSONDecoder().raw_decode(line[line.index("{"):])
            found[section_id] = ui
    return found


def _lookup_section():
    text = (META / "zz-oan/10_farmer_lookup.sql").read_text(encoding="utf8")
    start = text.index("'{\"section-id\": \"crop_farmer_lookup\"") + 1
    ui, _ = json.JSONDecoder().raw_decode(text[start:])
    return ui


def test_the_farmer_lookup_section_requires_the_farmer_id_and_one_fayda_id():
    lookup = _lookup_section()
    assert problems(lookup, {}, messages={}) == ["Farmer lookup: fill in Farmer ID, Fayda ID (FAN or FIN)"]
    assert problems(lookup, {"farmer_id": "FR-000000000001", "fayda_id": "001234567890"}, messages={}) == []
    stored = {"farmer_id": "FR-000000000001", "fayda_fin": "001234567890"}
    assert problems(lookup, stored, messages={}) == []


def test_the_farmer_reference_status_display_is_never_required():
    for ui in _sections_in_base_file().values():
        for found in rf.widgets_of(ui):
            if found["widget-id"] in {"farmer_reference_status", "farmer_reference_fin"}:
                assert found.get("widget-required") is not True


def test_the_production_season_fields_come_from_the_record_section_metadata():
    ui = _sections_in_base_file()["cropsown_intake_record_section_01"]
    season = [w for w in rf.widgets_of(ui) if w["widget-id"] in {"crop_year", "production_season"}]
    assert {w["widget-id"] for w in season} == {"crop_year", "production_season"}
    assert all(w.get("widget-required") is True for w in season)
    schema = {"section-title": "Production Season", "panels": [{"widgets": season}]}
    assert problems(schema, {}, messages={}) == ["Production Season: fill in Crop Year, Production Season"]


def test_the_list_sections_ask_for_their_required_columns_and_no_row_is_demanded():
    sections = _sections_in_base_file()
    for section_id in ("cropsown_planning_details_section_01", "cropsown_cultivation_details_section_01",
                       "cropsown_sowing_details_section_01", "cropsown_harvest_details_section_01"):
        ui = sections[section_id]
        table = rf.table_of(ui)
        assert table is not None and table.get("widget-required") is not True
        required = [c["column-key"] for c in table["widget-data-columns"] if c.get("widget-required")]
        assert "land_id" in required
        assert problems(ui, None, is_list=True, records=[], messages={}) == []
        assert problems(ui, None, is_list=True, records=[{}], messages={})[0].startswith(
            ui.get("section-title", "") + ", row 1: fill in ")


def test_the_land_row_overlay_sorts_after_every_file_that_rewrites_a_section():
    register_metadata = sorted((META / "register-metadata").glob("*.sql"))
    overlay = META / "register-metadata/zzzzzzzzzz_required_land_rows.sql"
    assert register_metadata[-1] == overlay
    # Files outside register-metadata that sort after it never touch these sections.
    text = overlay.read_text(encoding="utf8")
    later = [p for p in sorted(META.rglob("*.sql")) if p > overlay]
    for path in later:
        # Translation files name the sections for their labels; no other later file may.
        if path.parent.name == "registry-configurations":
            continue
        # The label casing, readable text and readable lists overlays only reword display text (labels and titles);
        # it never adds, removes or reorders a row.
        if path.name.endswith(("_label_casing.sql", "_readable_text.sql", "_readable_lists.sql")):
            continue
        body = path.read_text(encoding="utf8")
        for section_id in ("cropsown_planning_details_section_01", "cropsown_cultivation_details_section_01",
                           "cropsown_sowing_details_section_01", "cropsown_harvest_details_section_01"):
            assert section_id not in body, f"{path.name} rewrites {section_id}"
    for expected in ("sowing_date", "area_sown", "harvest_date", "qty_harvested", "commodity"):
        assert f"'{expected}'" in text
