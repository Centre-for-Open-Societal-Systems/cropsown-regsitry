"""Decimal number fields keep their decimals (0.5 ha is not saved as 1).

The staff UI's number input defaults format.decimalPlaces to 0, so a decimal
widget without places rounded every typed value. The overlay gives every
decimal number widget two places and makes Land area decimal. These tests read
the overlay, the New Dev metadata and the domain models: every number widget
bound to a Numeric column must end up decimal with places, and integer widgets
must stay integers.
"""
import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension"
SITE_CONFIGURATION = PACKAGE / "meta_data/site-configuration"
OVERLAY = SITE_CONFIGURATION / "97q_decimal_places.sql"
MODELS = PACKAGE / "register_domain/models"
METADATA = ROOT / "reference/new-dev/metadata.json"


def sql():
    return OVERLAY.read_text(encoding="utf-8")


def made_decimal():
    """Columns the overlay turns decimal when they declare no numeric type."""
    match = re.search(r"IN \(([^)]*)\) THEN\s+fmt := fmt \|\| '\{\"numericType\":\"decimal\"\}'", sql())
    assert match, "the land-area rule is missing"
    return set(re.findall(r"'([a-z_]+)'", match.group(1)))


def default_places():
    return int(re.search(r'\{"decimalPlaces":(\d+)\}', sql()).group(1))


def apply(node):
    """The overlay's rule, applied to a section UI schema."""
    if isinstance(node, list):
        return [apply(v) for v in node]
    if not isinstance(node, dict):
        return node
    result = {k: apply(v) for k, v in node.items()}
    if node.get("widget") == "number":
        fmt = dict(result.get("widget-data-format") or {})
        key = node.get("widget-data-path") or node.get("column-key")
        if fmt.get("numericType") is None and key in made_decimal():
            fmt["numericType"] = "decimal"
        if fmt.get("numericType") == "decimal" and "decimalPlaces" not in fmt:
            fmt["decimalPlaces"] = default_places()
        result["widget-data-format"] = fmt
    return result


def number_widgets(node):
    if isinstance(node, dict):
        if node.get("widget") == "number":
            yield node
        for value in node.values():
            yield from number_widgets(value)
    elif isinstance(node, list):
        for value in node:
            yield from number_widgets(value)


def schemas():
    data = json.loads(METADATA.read_text(encoding="utf-8"))
    found = []

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("section_ui_schema"), (dict, list)):
                found.append(node["section_ui_schema"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(data)
    assert found
    return found


def numeric_columns():
    columns = set()
    for model in MODELS.glob("*.py"):
        columns |= set(re.findall(r"^\s+([a-z_]+): Mapped\[[^\]]*\] = mapped_column\(\s*Numeric",
                                  model.read_text(encoding="utf-8"), re.MULTILINE))
    assert "area_sown" in columns and "land_area" in columns
    return columns


def test_every_number_widget_on_a_numeric_column_keeps_decimals():
    numeric = numeric_columns()
    checked = set()
    for schema in schemas():
        for widget in number_widgets(apply(copy.deepcopy(schema))):
            key = widget.get("widget-data-path") or widget.get("column-key")
            fmt = widget["widget-data-format"]
            if key in numeric:
                assert fmt.get("numericType") == "decimal", key
                assert fmt.get("decimalPlaces", 0) >= 2, key
                checked.add(key)
    assert {"area_sown", "planned_area", "land_area", "area_harvested", "qty_harvested"} <= checked


def test_integer_widgets_stay_integers_and_declared_places_are_kept():
    before = {"widget": "number", "widget-data-path": "growth_duration_days",
              "widget-data-format": {"numericType": "integer"}}
    assert "decimalPlaces" not in apply(before)["widget-data-format"]
    day = {"widget": "number", "widget-data-path": "start_day", "widget-data-format": {}}
    assert apply(day)["widget-data-format"] == {}
    declared = {"widget": "number", "widget-data-path": "estimated_damage_pct",
                "widget-data-format": {"numericType": "decimal", "decimalPlaces": 1}}
    assert apply(declared)["widget-data-format"]["decimalPlaces"] == 1


def test_the_overlay_runs_after_the_land_rows_and_before_the_dates():
    names = sorted(p.name for p in SITE_CONFIGURATION.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql"
    for earlier in ("92_number_alignment.sql", "97f_cultivation_land_details.sql", "97g_sowing_harvest_land_rows.sql"):
        assert names.index(OVERLAY.name) > names.index(earlier)
    assert len({n.split("_")[0] for n in names}) == len(names)


def test_the_overlay_only_adds_and_never_overwrites():
    text = sql()
    assert "NOT fmt ? 'decimalPlaces'" in text
    assert "fmt->>'numericType' IS NULL" in text
    assert "UPDATE public.g2p_register_sections" in text
