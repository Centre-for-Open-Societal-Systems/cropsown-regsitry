"""Sowing with no matching Cultivation is checked against Planning: the sowing date
against the Planned date. Areas are not compared across sections (see test_area_total_land_only)."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException

from openg2p_registry_cropsown_extension.register_domain.services import cropsown_intake_validation_service as checks
from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_sowing import (
    G2PRegisterDomainServiceSowing,
)

MASTER = (["rec-1"], "fan", "2026", "SEASON_MEHER")


class Session:
    """Rows by table name; the first table named in the statement answers."""

    def __init__(self, rows):
        self.rows = rows

    async def execute(self, statement, params=None):
        sql = str(statement)
        table = next((t for t in self.rows if t in sql), None)
        hit = self.rows.get(table, [])
        return SimpleNamespace(fetchall=lambda: hit, fetchone=lambda: hit[0] if hit else None)


def sow_dates(rows, sowing_date):
    row = {"cluster_status": ["INDEPENDENT"], "land_id": "L1", "commodity": "CROP_TEFF", "season": "SEASON_MEHER",
           "sowing_date": sowing_date}
    with patch.object(checks, "get_master_records_for_submission", new=AsyncMock(return_value=MASTER)):
        asyncio.run(checks.validate_sowing_against_cultivation(Session(rows), [row], "sub-1"))


PLAN = {"g2p_intake_form_plannings": [("L1", "CROP_TEFF", "SEASON_MEHER", "2026-07-01")]}


def test_without_cultivation_the_sowing_date_is_checked_against_the_planned_date():
    with pytest.raises(G2PRegistryException) as error:
        sow_dates(PLAN, "2026-06-01")
    assert "Planned Date (01/07/2026) in Planning for Land ID 'L1'" in error.value.message
    sow_dates(PLAN, "2026-07-15")  # on or after the planned date
    sow_dates({}, "2026-06-01")  # neither Cultivation nor Planning: nothing to check


def test_cultivation_still_comes_first():
    rows = {**PLAN, "g2p_intake_form_cultivations": [("L1", "CROP_TEFF", "SEASON_MEHER", "2026-05-01", None)]}
    sow_dates(rows, "2026-06-01")  # after cultivation; the later planned date is not used


# Harvest date: Sowing first, then Cultivation, then Planning.
from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_harvest import (  # noqa: E402
    G2PRegisterDomainServiceHarvest,
)


def harvest_dates(rows, harvest_date):
    row = {"cluster_status": ["INDEPENDENT"], "land_id": "L1", "commodity": "CROP_TEFF", "harvest_date": harvest_date}
    with patch.object(checks, "get_master_records_for_submission", new=AsyncMock(return_value=MASTER)):
        asyncio.run(checks.validate_harvest_against_sowing(Session(rows), [row], "sub-1"))


CULT = {"g2p_intake_form_cultivations": [("L1", "CROP_TEFF", "SEASON_MEHER", "2026-08-01")]}


def test_without_sowing_the_harvest_date_is_checked_against_cultivation_then_planning():
    with pytest.raises(G2PRegistryException) as error:
        harvest_dates(CULT, "2026-07-01")
    assert "after Cultivation Date (01/08/2026)" in error.value.message
    with pytest.raises(G2PRegistryException) as error:
        harvest_dates({"g2p_intake_form_plannings": [("L1", "CROP_TEFF", "SEASON_MEHER", "2026-08-01")]}, "2026-07-01")
    assert "after Planned Date in Planning (01/08/2026)" in error.value.message
    harvest_dates(CULT, "2026-10-01")
    harvest_dates({}, "2026-01-01")  # nothing earlier: nothing to check


def test_sowing_still_comes_first_for_the_harvest_date():
    rows = {**CULT, "g2p_intake_form_sowings": [("L1", "CROP_TEFF", None, "SEASON_MEHER", None, "2026-06-01",
                                                  ["INDEPENDENT"], None)]}
    harvest_dates(rows, "2026-07-01")  # after sowing; the later cultivation date is not used
