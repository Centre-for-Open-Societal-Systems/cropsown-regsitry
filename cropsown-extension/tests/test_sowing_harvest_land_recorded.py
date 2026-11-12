"""Sowing and Harvest rows ask whether the land is already recorded (web form only, for now)."""
from pathlib import Path

ZZ_OAN = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension/meta_data/zz-oan"
OVERLAY = ZZ_OAN / "97g_sowing_harvest_land_rows.sql"


def test_each_status_gets_its_own_question_and_land_fields():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "'cropsown_sowing_details_section_01', 'cropsown_harvest_details_section_01'" in sql
    assert sql.count("'widget-label', 'Is planning record created?'") == 2
    assert '{"field": "is_land_recorded", "operator": "equals", "value": false}' in sql
    assert '{"field": "is_cluster_land_recorded", "operator": "equals", "value": false}' in sql
    assert "WHERE s.\"section_id\" = 'cropsown_planning_details_section_01'" in sql  # Independent land fields
    assert "WHERE s.\"section_id\" = 'cropsown_cluster_details_section_01'" in sql  # cluster location fields
    assert "'cluster_' || key" in sql and "'oan-parent-column', 'cluster_'" in sql  # no clash, cascade kept
    assert "widget-required\" = true" not in sql and "- 'widget-required'" in sql  # nothing required


def test_the_questions_come_after_the_land_ids_and_before_the_dates():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert sql.index("Part 1: Land ID for each Cluster status") < sql.index("pg_temp.sowing_harvest_land_recorded")
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names.index(OVERLAY.name) > names.index("97c_planning_map_location.sql")
    assert names[-1] == "98_ethiopian_dates.sql"
    assert len({n.split("_")[0] for n in names}) == len(names)


def test_sowing_and_harvest_records_store_the_answers_and_land_fields():
    from openg2p_registry_cropsown_extension.register_domain.models.harvest import G2PRegisterHarvest
    from openg2p_registry_cropsown_extension.register_domain.models.sowing import G2PRegisterSowing
    for model in (G2PRegisterSowing, G2PRegisterHarvest):
        columns = model.__table__.columns
        for key in ("is_land_recorded", "is_cluster_land_recorded", "plot_category", "land_area", "region",
                    "kebele", "latitude", "cluster_region", "cluster_sub_kebele", "cluster_longitude"):
            assert key in columns, (model.__name__, key)


import asyncio  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

import pytest  # noqa: E402


class Session:
    """Answers "SELECT 1 ... FROM <table>": a hit when the table is listed."""

    def __init__(self, *tables):
        self.tables, self.calls = tables, []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append(sql)
        hit = any(f" {t} " in sql for t in self.tables)
        return SimpleNamespace(first=lambda: (1,) if hit else None)


def check(record, session):
    pytest.importorskip("openg2p_registry_core")
    from openg2p_registry_cropsown_extension.register_domain.services import cropsown_intake_validation_service as v
    with patch.object(v, "get_master_records_for_submission",
                      new=AsyncMock(return_value=(["rec-1"], "fan", "2026", "SEASON_MEHER"))):
        asyncio.run(v.validate_land_recorded({"submission_id": "sub-1", **record}, session))


def test_yes_passes_when_planning_or_cultivation_has_the_land():
    for table in ("g2p_intake_form_plannings", "g2p_intake_form_cultivations", "g2p_register_plannings",
                  "g2p_register_cultivations"):
        check({"is_land_recorded": True, "land_id": "56"}, Session(table))


def test_yes_is_refused_when_neither_has_the_land():
    from openg2p_registry_core.errors import G2PRegistryException
    with pytest.raises(G2PRegistryException) as error:
        check({"is_land_recorded": True, "land_id": "56"}, Session())
    assert "No planning or cultivation record found for Land ID '56'" in error.value.message


def test_clustered_yes_is_checked_against_cluster_and_cultivation_cluster():
    from openg2p_registry_core.errors import G2PRegistryException
    check({"is_cluster_land_recorded": True, "cluster_land_id": "C1"}, Session("g2p_register_clusters"))
    check({"is_cluster_land_recorded": True, "cluster_land_id": "C1"}, Session("g2p_intake_form_cultivation_clusters"))
    with pytest.raises(G2PRegistryException) as error:
        check({"is_cluster_land_recorded": True, "cluster_land_id": "C1"}, Session("g2p_register_plannings"))
    assert "No cluster planning or cultivation cluster record found for Land ID (cluster) 'C1'" in error.value.message


def test_no_or_no_answer_is_never_checked():
    for answer in (False, None):
        session = Session()
        check({"is_land_recorded": answer, "land_id": "56", "is_cluster_land_recorded": answer,
               "cluster_land_id": "C1"}, session)
        assert session.calls == []
