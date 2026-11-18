"""Sowing rows: Season (Independent) and Season (cluster) (Clustered) are required while
they are shown, by a `require` rule with the column's own show condition."""
from pathlib import Path

from openg2p_registry_cropsown_extension.required_fields import widget_state

ZZ_OAN = (Path(__file__).resolve().parents[1]
          / "src/openg2p_registry_cropsown_extension/meta_data/zz-oan")
OVERLAY = ZZ_OAN / "97p_sowing_season_required.sql"


def test_the_overlay_adds_a_require_rule_to_the_two_sowing_seasons_only():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "IF node->>'column-key' IN ('season', 'cluster_season') THEN" in sql
    assert "jsonb_build_object('action', 'require', 'condition', show_rule)" in sql
    assert "WHERE \"section_id\" = 'cropsown_sowing_details_section_01';" in sql
    assert "widget-required" not in sql.split("CREATE OR REPLACE FUNCTION")[1].split("$$;")[0]
    assert "RAISE EXCEPTION 'Sowing Season / Season (cluster) are not required while shown'" in sql


def test_the_overlay_sorts_after_the_cluster_status_list_and_before_the_dates():
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names.index("97k_cluster_status_list.sql") < names.index(OVERLAY.name) < names.index("98_ethiopian_dates.sql")
    assert len({n.split("_")[0] for n in names}) == len(names)


def column(value):
    rule = {"field": "cluster_status", "operator": "contains", "value": value}
    return {"widget": "select", "column-key": "x",
            "widget-data-options": {"actions": [{"action": "show", "condition": rule},
                                                {"action": "require", "condition": rule}]}}


def test_each_season_is_required_only_on_its_own_side():
    season, cluster_season = column("INDEPENDENT"), column("CLUSTERED")
    assert widget_state(season, {"cluster_status": ["INDEPENDENT"]}) == (True, True)
    assert widget_state(cluster_season, {"cluster_status": ["INDEPENDENT"]}) == (False, False)
    assert widget_state(cluster_season, {"cluster_status": ["CLUSTERED"]}) == (True, True)
    assert widget_state(season, {"cluster_status": ["INDEPENDENT", "CLUSTERED"]}) == (True, True)
    assert widget_state(cluster_season, {"cluster_status": ["INDEPENDENT", "CLUSTERED"]}) == (True, True)
    assert widget_state(season, {}) == (False, False)  # no status chosen: neither
