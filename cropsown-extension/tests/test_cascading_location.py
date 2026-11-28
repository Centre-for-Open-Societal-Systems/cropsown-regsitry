"""Planning, Cluster and Cultivation cluster rows pick Region -> Zone -> Woreda -> Kebele as a cascade.

The overlay marks only those sections' Zone, Woreda and Kebele columns with the column
above them; the staff UI's select reads the mark in the row dialog. Stored values, the
Master Data list and every other section are unchanged.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE_CONFIGURATION = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/meta_data/site-configuration"
OVERLAY = SITE_CONFIGURATION / "97b_cascading_location.sql"
WIDGETS = ROOT / "ui/staff-ui/overrides/src/oan/widgets"
SECTIONS = ("cropsown_planning_details_section_01", "cropsown_cluster_details_section_01",
            "cropsown_cultivation_cluster_details_section_01")


def test_only_the_three_sections_location_columns_get_their_parent():
    sql = OVERLAY.read_text(encoding="utf-8")
    update = sql.split('UPDATE "public"')[1].split("DO $$")[0]
    for section in SECTIONS:
        assert f"'{section}'" in update
    for other in ("cropsown_cultivation_details_section_01", "cropsown_cropsown_location_section_03"):
        assert other not in sql
    assert "IN ('zone', 'woreda', 'kebele') AND node->>'widget' = 'select'" in sql
    assert "WHEN 'zone' THEN 'region' WHEN 'woreda' THEN 'zone' ELSE 'woreda'" in sql
    # the columns stay selects on the same list; only the stock dependsOn is added, a
    # placeholder never set, so the platform's own load of the cell waits for the select
    function = sql.split("CREATE OR REPLACE FUNCTION")[1].split('UPDATE "public"')[0]
    assert "'{widget-data-source,dependsOn}', '\"oan-parent-cell\"')" in function
    assert "AND c->'widget-data-source'->>'dependsOn' = 'oan-parent-cell'" in sql


def test_the_overlay_sorts_after_the_section_rewrites_and_before_the_dates():
    names = sorted(p.name for p in SITE_CONFIGURATION.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql"
    for earlier in ("41_crop_record_tab_layout.sql", "89_master_data_dropdowns.sql", "93_plot_registered_question.sql"):
        assert names.index(OVERLAY.name) > names.index(earlier)
    assert len({n.split("_")[0] for n in names}) == len(names)


def test_the_ui_select_reads_the_mark_and_is_registered():
    widget = (WIDGETS / "CascadingSelectWidget.tsx").read_text(encoding="utf-8")
    assert "const PARENT_COLUMN = 'oan-parent-column';" in widget
    assert "dependsOn: parentId" in widget and "-dlg-" in widget
    assert "<SelectWidget config={effective as never} />" in widget
    # until the level above is chosen, the level offers nothing ("Select" only)
    assert "if (!parentChosen) return { ...config, 'widget-data-source': { type: 'static', options: [] } };" in widget
    # the placeholder dependsOn is replaced in a row dialog and dropped anywhere else
    assert "const PARENT_PLACEHOLDER = 'oan-parent-cell';" in widget
    assert "dependsOn === PARENT_PLACEHOLDER ? { ...config, 'widget-data-source': source } : config" in widget
    register = (WIDGETS / "register.ts").read_text(encoding="utf-8")
    assert "widgetRegistry.register({ widget: 'select', component: CascadingSelectWidget as never });" in register
