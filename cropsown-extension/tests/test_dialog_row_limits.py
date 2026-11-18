"""Table rows are checked in the row dialog on Save by comparing two fields of the same row
(Planning, Cultivation, Cluster, Cultivation cluster, Sowing, Harvest). The overlay marks the
columns, the staff UI's dialog table reads the marks, and the server keeps the same rules on
Next and submit for every channel."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ZZ_OAN = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/meta_data/zz-oan"
OVERLAY = ZZ_OAN / "97o_dialog_row_limits.sql"
WIDGETS = ROOT / "ui/staff-ui/overrides/src/oan/widgets"

EXPECTED = {
    "cropsown_planning_details_section_01": {
        "planned_area": ("oan-max-column", "land_area"), "end_gc": ("oan-min-column", "start_gc"),
        "planned_date": ("oan-max-date-column", "end_gc")},
    "cropsown_cultivation_details_section_01": {
        "actual_crop_area": ("oan-max-column", "land_area"), "end_gc": ("oan-min-column", "start_gc"),
        "actual_cultivation_date": ("oan-max-date-column", "end_gc")},
    "cropsown_cluster_details_section_01": {
        "cluster_plan": ("oan-max-column", "cluster_area_timad"), "collected_land": ("oan-max-column", "cluster_area_timad"),
        "collected_by_combiner": ("oan-max-column", "cluster_plan"), "end_gc": ("oan-min-column", "start_gc"),
        "establishing_date": ("oan-max-date-column", "end_gc")},
    "cropsown_cultivation_cluster_details_section_01": {
        "cluster_plan": ("oan-max-column", "cluster_area_timad"), "collected_land": ("oan-max-column", "cluster_area_timad"),
        "collected_by_combiner": ("oan-max-column", "cluster_plan"), "end_gc": ("oan-min-column", "start_gc"),
        "establishing_date": ("oan-max-date-column", "end_gc")},
    "cropsown_sowing_details_section_01": {
        "area_sown": ("oan-max-column", "land_area"), "cluster_area_sown": ("oan-max-column", "cluster_area_hectare")},
    "cropsown_harvest_details_section_01": {
        "area_harvested": ("oan-max-column", "land_area"), "qty_stored": ("oan-max-column", "qty_harvested"),
        "qty_sold": ("oan-max-column", "qty_harvested"), "cluster_qty_stored": ("oan-max-column", "cluster_qty_harvested"),
        "cluster_qty_sold": ("oan-max-column", "cluster_qty_harvested")},
}


def marks():
    sql = OVERLAY.read_text(encoding="utf-8")
    rows = re.findall(r"\('(cropsown_\w+)', '(\{.*?\})'\)", sql.split("INSERT INTO oan_dialog_row_limits VALUES")[1], re.S)
    return {section: json.loads(text) for section, text in rows}


def test_each_section_marks_exactly_its_same_row_rules():
    found = marks()
    assert set(found) == set(EXPECTED)
    for section, columns in EXPECTED.items():
        assert set(found[section]) == set(columns), section
        for column, (mark, other) in columns.items():
            assert found[section][column][mark] == other, (section, column)
            assert found[section][column]["oan-limit-message"].startswith("validation_")
    # the area of a cluster is its timad x 0.25; stored + sold are added up
    for section in ("cropsown_cluster_details_section_01", "cropsown_cultivation_cluster_details_section_01"):
        assert found[section]["cluster_plan"]["oan-max-factor"] == 0.25
        assert found[section]["collected_land"]["oan-max-factor"] == 0.25
    harvest = found["cropsown_harvest_details_section_01"]
    assert harvest["qty_stored"]["oan-plus-column"] == "qty_sold" and harvest["qty_sold"]["oan-plus-column"] == "qty_stored"
    assert harvest["cluster_qty_stored"]["oan-plus-column"] == "cluster_qty_sold"
    for between in (("cropsown_planning_details_section_01", "planned_date"),
                    ("cropsown_cultivation_details_section_01", "actual_cultivation_date"),
                    ("cropsown_cluster_details_section_01", "establishing_date"),
                    ("cropsown_cultivation_cluster_details_section_01", "establishing_date")):
        assert found[between[0]][between[1]]["oan-min-column"] == "start_gc"


def test_the_overlay_only_adds_marks_and_checks_them():
    sql = OVERLAY.read_text(encoding="utf-8")
    function = sql.split("CREATE OR REPLACE FUNCTION")[1].split("CREATE TEMP TABLE")[0]
    assert "WHEN node->>'widget' IN ('number', 'date') AND marks ? (node->>'column-key')" in function
    assert "THEN node || (marks -> (node->>'column-key'))" in function
    for untouched in ("widget-data-source", "widget-data-path", "widget-data-validation", "'widget',"):
        assert untouched not in function
    assert "RAISE EXCEPTION 'Table columns without their dialog row limit" in sql


def test_every_message_is_readable_and_in_every_language():
    sql = OVERLAY.read_text(encoding="utf-8")
    messages = sql.split('UPDATE "public"."registry_languages"')[1].split(";")[0]
    assert "WHERE" not in messages  # every language
    texts = dict(re.findall(r"'(validation_\w+)', '([^']+)'", messages))
    used = {m["oan-limit-message"] for section in marks().values() for m in section.values()}
    assert used <= set(texts)
    assert texts["validation_end_date_before_start_date"] == "End date cannot be earlier than Start date."
    assert texts["validation_area_sown_above_land_area"] == "Area sown cannot be more than Total land area ({limit} hectares)."
    assert texts["validation_establishing_date_outside_season"] == "Establishing date must be between Start date and End date."


def test_the_overlay_sorts_after_the_section_overlays_and_before_the_dates():
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql"
    for earlier in ("90_season_window_from_dates.sql", "97b_cascading_location.sql", "97f_cultivation_land_details.sql",
                    "97g_sowing_harvest_land_rows.sql"):
        assert names.index(OVERLAY.name) > names.index(earlier)
    assert len({n.split("_")[0] for n in names}) == len(names)


def test_the_ui_dialog_table_reads_the_marks_and_is_registered():
    widget = (WIDGETS / "RowLimitDialogTable.tsx").read_text(encoding="utf-8")
    for constant in ("const MAX_COLUMN = 'oan-max-column';", "const MAX_FACTOR = 'oan-max-factor';",
                     "const PLUS_COLUMN = 'oan-plus-column';", "const MIN_COLUMN = 'oan-min-column';",
                     "const MAX_DATE_COLUMN = 'oan-max-date-column';", "const MESSAGE = 'oan-limit-message';"):
        assert constant in widget
    assert "`${tableId}-dlg-`" in widget and "store.getState()" in widget
    assert "if (!MARKS.some((mark) => col?.[mark])) return col;" in widget  # unmarked columns unchanged
    assert "visible(maxColumn)" in widget  # a hidden other column is not compared
    assert "'widget-data-validation': { ...(col['widget-data-validation'] ?? {}), zodSchema: schema }" in widget
    assert "<DialogTableWidget config={effective as never} />" in widget
    # Location levels: nothing to choose until the level above is chosen, then its children
    # (set on the column, which the platform loads the list from).
    assert "const PARENT_COLUMN = 'oan-parent-column';" in widget
    assert "? { ...col, 'widget-data-source': { type: 'static', options: [] } }" in widget
    assert "dependsOn: `${tableId}-dlg-${session}-${parent}`" in widget
    register = (WIDGETS / "register.ts").read_text(encoding="utf-8")
    assert "widgetRegistry.register({ widget: 'dialog-table', component: RowLimitDialogTable as never });" in register
    assert "widgetRegistry.register({ widget: 'select', component: CascadingSelectWidget as never });" in register


# --- the same rules on the server (Next, submit, ODK, file import, change requests) --------------

def helpers():
    pytest.importorskip("openg2p_registry_core")
    from openg2p_registry_cropsown_extension.register_domain.services import domain_validation_utils
    from openg2p_registry_core.errors import G2PRegistryException
    return domain_validation_utils, G2PRegistryException


@pytest.mark.parametrize("start,end", [("2026-06-01", "2026-06-01"), ("2026-06-01", "2026-10-30"),
                                       ("2026-06-01", None), (None, "2026-06-01"), ("", "")])
def test_an_end_date_on_or_after_the_start_or_a_blank_date_passes(start, end):
    utils, _ = helpers()
    utils.validate_season_window({"start_gc": start, "end_gc": end})


def test_an_end_date_before_the_start_is_refused():
    utils, error_class = helpers()
    with pytest.raises(error_class) as error:
        utils.validate_season_window({"start_gc": "2026-06-01", "end_gc": "2026-05-31"})
    assert error.value.message == "End date cannot be earlier than Start date."


@pytest.mark.parametrize("day", ["2026-06-01", "2026-08-15", "2026-10-30", None, ""])
def test_an_establishing_date_inside_the_window_or_blank_passes(day):
    utils, _ = helpers()
    utils.validate_date_in_window({"start_gc": "2026-06-01", "end_gc": "2026-10-30", "establishing_date": day},
                                  "establishing_date", "Establishing date")
    utils.validate_date_in_window({"establishing_date": "2026-01-01"}, "establishing_date", "Establishing date")


@pytest.mark.parametrize("day", ["2026-05-31", "2026-10-31"])
def test_an_establishing_date_outside_the_window_is_refused(day):
    utils, error_class = helpers()
    with pytest.raises(error_class) as error:
        utils.validate_date_in_window({"start_gc": "2026-06-01", "end_gc": "2026-10-30", "establishing_date": day},
                                      "establishing_date", "Establishing date")
    assert error.value.message == "Establishing date must be between Start date and End date."


def test_not_more_than_compares_only_given_values():
    utils, error_class = helpers()
    message = "Area sown ({value} hectares) cannot be more than Total land area ({limit} hectares)."
    for record in ({"area_sown": 2, "land_area": 2}, {"area_sown": 9, "land_area": None}, {"area_sown": None, "land_area": 1},
                   {"area_sown": 9, "land_area": 0}):
        utils.validate_not_more_than(record, "area_sown", "land_area", message)
    with pytest.raises(error_class) as error:
        utils.validate_not_more_than({"area_sown": "2.5", "land_area": "2"}, "area_sown", "land_area", message)
    assert error.value.message == "Area sown (2.5 hectares) cannot be more than Total land area (2 hectares)."


@pytest.mark.parametrize("module,method", [
    ("g2p_register_domain_service_planning", "self._validate_season_window(record)"),
    ("g2p_register_domain_service_cultivation", "validate_season_window(record)"),
    ("g2p_register_domain_service_cluster", "validate_season_window(record)"),
    ("g2p_register_domain_service_cultivation_cluster", "validate_season_window(record)"),
    ("g2p_register_domain_service_cluster", 'validate_date_in_window(record, "establishing_date", "Establishing date")'),
    ("g2p_register_domain_service_cultivation_cluster", 'validate_date_in_window(record, "establishing_date", "Establishing date")'),
    ("g2p_register_domain_service_sowing", 'validate_not_more_than(record, "area_sown", "land_area",'),
    ("g2p_register_domain_service_sowing", 'validate_not_more_than(record, "cluster_area_sown", "cluster_area_hectare",'),
    ("g2p_register_domain_service_harvest", 'validate_not_more_than(record, "area_harvested", "land_area",'),
    ("g2p_register_domain_service_harvest", "self._validate_cluster_disposal_quantities(record)"),
])
def test_each_service_runs_its_rule_on_save_and_submit(module, method):
    source = (ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services"
              / f"{module}.py").read_text(encoding="utf-8")
    body = source.split("async def validate_domain_attributes")[1].split("\n    def ")[0].split("\n    async def ")[0]
    assert method in body


def test_land_area_rules_skip_a_yes_row():
    for module in ("g2p_register_domain_service_sowing", "g2p_register_domain_service_harvest"):
        source = (ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services"
                  / f"{module}.py").read_text(encoding="utf-8")
        assert 'if as_bool(record.get("is_land_recorded")) is not True:' in source


def test_clustered_harvest_quantities():
    pytest.importorskip("openg2p_registry_core")
    from openg2p_registry_core.errors import G2PRegistryException
    from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_harvest import (
        G2PRegisterDomainServiceHarvest,
    )
    service = G2PRegisterDomainServiceHarvest()
    service._validate_cluster_disposal_quantities({"cluster_qty_harvested": 10, "cluster_qty_stored": 6, "cluster_qty_sold": 4})
    service._validate_cluster_disposal_quantities({"cluster_qty_harvested": None, "cluster_qty_stored": 6})
    with pytest.raises(G2PRegistryException, match=r"\(cluster\) must not be more than the quantity harvested \(cluster\)"):
        service._validate_cluster_disposal_quantities({"cluster_qty_harvested": 10, "cluster_qty_stored": 7, "cluster_qty_sold": 4})
