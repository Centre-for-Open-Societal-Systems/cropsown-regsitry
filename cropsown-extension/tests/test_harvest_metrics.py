"""The five read-only performance figures on a Harvest row (harvest_metrics.py)."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_cropsown_extension.register_domain.services import harvest_metrics as hm
from openg2p_registry_cropsown_extension.register_domain.services.domain_compute_utils import (
    compute_harvest_yield,
)

PLANNING = {"land_id": "L1", "commodity": "CROP_TEFF", "expected_yield": 40, "planned_area": 2}
CULTIVATION = {"land_id": "L1", "commodity": "CROP_TEFF", "actual_crop_area": 1.5,
               "actual_seed_qty": 50, "actual_fertilizer_qty": 200}
HARVEST = {"land_id": "L1", "commodity": "CROP_TEFF", "qty_harvested": 30, "area_harvested": 1.5}


def test_the_five_figures_follow_the_agreed_formulas():
    values = hm.harvest_metrics(HARVEST, PLANNING, CULTIVATION)
    assert values == {
        "yield_kg_ha": 2000.0,             # 30 quintal = 3000 kg / 1.5 ha
        "yield_performance_pct": 75.0,     # 30 / 40 quintal x 100
        "land_utilization_rate": 0.75,     # 1.5 ha actual crop area / 2 ha planned
        "seed_productivity": 60.0,         # 3000 kg / 50 kg seed
        "fertilizer_efficiency": 15.0,     # 3000 kg / 200 kg fertilizer
    }


def test_missing_inputs_or_zero_denominators_leave_the_figure_blank():
    values = hm.harvest_metrics({"land_id": "L1", "qty_harvested": 30, "area_harvested": 0})
    assert set(values.values()) == {None}
    assert hm.harvest_metrics({"qty_harvested": 0, "area_harvested": 2})["yield_kg_ha"] == 0.0


def test_a_cluster_row_uses_its_cluster_quantity_and_area():
    row = {"land_id": "L1", "cluster_qty_harvested": 10, "cluster_area_harvested": 4}
    assert hm.harvest_metrics(row)["yield_kg_ha"] == 250.0


def test_planning_and_cultivation_rows_match_on_land_id_and_crop():
    other_crop = dict(PLANNING, commodity="CROP_MAIZE", expected_yield=10)
    other_land = dict(PLANNING, land_id="L2", expected_yield=20)
    assert hm.matching_row([other_crop, other_land, PLANNING], HARVEST) is PLANNING
    assert hm.matching_row([other_crop, other_land], HARVEST) is None
    # a cluster harvest row names no crop: Land ID alone
    assert hm.matching_row([other_land, other_crop], {"land_id": "L1"}) is other_crop
    assert hm.matching_row([PLANNING], {"commodity": "CROP_TEFF"}) is None


def test_the_saved_harvest_row_carries_its_yield_under_the_column_it_has():
    record = dict(HARVEST)
    compute_harvest_yield(record)
    assert record["yield_kg_ha"] == 2000.0 and "yield_per_ha" not in record


class Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


def test_refresh_sets_the_figures_on_every_active_harvest_row_of_the_record():
    harvest = SimpleNamespace(**HARVEST, **{f: None for f in hm.FIELDS})
    unmatched = SimpleNamespace(land_id="L9", commodity="CROP_TEFF", qty_harvested=5, area_harvested=1,
                                **{f: 99 for f in hm.FIELDS})
    planning = SimpleNamespace(**PLANNING)
    cultivation = SimpleNamespace(**CULTIVATION)
    session = SimpleNamespace(execute=AsyncMock(side_effect=[
        Result([harvest, unmatched]), Result([planning]), Result([cultivation])]))
    changed = asyncio.run(hm.refresh_harvest_metrics(session, "record-1"))
    assert (harvest.yield_kg_ha, harvest.yield_performance_pct, harvest.land_utilization_rate,
            harvest.seed_productivity, harvest.fertilizer_efficiency) == (2000.0, 75.0, 0.75, 60.0, 15.0)
    # no Planning / Cultivation on L9: only the yield, the rest cleared
    assert unmatched.yield_kg_ha == 500.0 and unmatched.yield_performance_pct is None
    assert changed == 10


def test_harvest_planning_and_cultivation_recalculate_after_ingest_and_approval():
    from openg2p_registry_cropsown_extension.register_domain.services import (
        g2p_register_domain_service_cultivation as cultivation,
        g2p_register_domain_service_harvest as harvest,
        g2p_register_domain_service_planning as planning,
    )

    services = (harvest.G2PRegisterDomainServiceHarvest(), planning.G2PRegisterDomainServicePlanning(),
                cultivation.G2PRegisterDomainServiceCultivation())
    for service in services:
        with patch.object(hm, "refresh_after_change", new=AsyncMock()) as refresh:
            asyncio.run(service.post_ingest("reg", SimpleNamespace(link_internal_record_id="rec-1"), "s"))
            asyncio.run(service.post_approve(SimpleNamespace(internal_record_id="rec-2"), "s"))
        assert [c.args for c in refresh.await_args_list] == [("s", "rec-1"), ("s", "rec-2")]


def test_the_five_figures_show_next_to_their_label():
    from pathlib import Path

    zz_oan = Path(hm.__file__).resolve().parents[2] / "meta_data" / "zz-oan"
    sql = (zz_oan / "97a_harvest_results_left_aligned.sql").read_text(encoding="utf-8")
    assert "'cropsown_harvest_details_section_01'" in sql and '{"textAlign": "left"}' in sql
    for field in hm.FIELDS:
        assert f"'{field}'" in sql
    names = sorted(p.name for p in zz_oan.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql"
    assert names.index("97a_harvest_results_left_aligned.sql") > names.index("41_crop_record_tab_layout.sql")


def test_a_failed_recalculation_never_blocks_the_save():
    class Nested:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    session = SimpleNamespace(begin_nested=lambda: Nested(),
                              execute=AsyncMock(side_effect=RuntimeError("database down")))
    asyncio.run(hm.refresh_after_change(session, "rec-1"))  # logged, not raised
