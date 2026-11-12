"""Sowing with no matching Cultivation is checked against Planning: the sowing date
against the Planned date, the area sown against the Planned crop area."""
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


def sow_area(rows, area):
    record = {"cluster_status": ["INDEPENDENT"], "land_id": "L1", "season": "SEASON_MEHER", "area_sown": area,
              "submission_id": "sub-1"}
    with patch.object(checks, "get_master_records_for_submission", new=AsyncMock(return_value=MASTER)):
        asyncio.run(G2PRegisterDomainServiceSowing()._validate_sowing_area_after_cultivation(record, Session(rows)))


def test_without_cultivation_the_area_sown_is_checked_against_the_planned_area():
    with pytest.raises(G2PRegistryException) as error:
        sow_area({"g2p_intake_form_plannings": [(2.0,)]}, 3)
    assert "cannot exceed Planned Crop Area in Planning (2.0 hectares)" in error.value.message
    sow_area({"g2p_intake_form_plannings": [(2.0,)]}, 2)
    sow_area({"g2p_register_plannings": [(2.0,)]}, 1.5)
    with pytest.raises(G2PRegistryException):
        sow_area({"g2p_register_plannings": [(2.0,)]}, 2.5)  # the farmer's Planning record
    sow_area({}, 9)  # neither: nothing to check


def test_cultivation_area_still_comes_first():
    with pytest.raises(G2PRegistryException) as error:
        sow_area({"g2p_intake_form_cultivations": [(1.0,)], "g2p_intake_form_plannings": [(5.0,)]}, 2)
    assert "Actual Crop Area in Cultivation (1.0 hectares)" in error.value.message


# Harvest: Sowing first, then Cultivation, then Planning.
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


def harvest_area(rows, area):
    record = {"cluster_status": ["INDEPENDENT"], "land_id": "L1", "area_harvested": area, "submission_id": "sub-1"}
    with patch.object(checks, "get_master_records_for_submission", new=AsyncMock(return_value=MASTER)):
        asyncio.run(G2PRegisterDomainServiceHarvest()._validate_harvest_area_after_sowing(record, Session(rows)))


def test_without_sowing_or_cultivation_the_area_harvested_is_checked_against_the_planned_area():
    with pytest.raises(G2PRegistryException) as error:
        harvest_area({"g2p_intake_form_plannings": [(2.0,)]}, 3)
    assert "cannot exceed Planned Crop Area in Planning (2.0 hectares)" in error.value.message
    harvest_area({"g2p_register_plannings": [(2.0,)]}, 2)
    harvest_area({}, 9)
    with pytest.raises(G2PRegistryException) as error:
        harvest_area({"g2p_intake_form_sowings": [(1.0,)], "g2p_intake_form_plannings": [(5.0,)]}, 2)
    assert "Area Sown in Sowing (1.0 hectares)" in error.value.message


def test_registered_cultivation_is_the_farmers_own():
    # The farmer's own registered Cultivation limits the area sown
    with pytest.raises(G2PRegistryException) as error:
        sow_area({"g2p_register_cultivations": [(1.0,)]}, 1.5)
    assert "Actual Crop Area in Cultivation (1.0 hectares)" in error.value.message
    sow_area({"g2p_register_cultivations": [(1.0,)]}, 0.9)


def test_another_farmers_land_of_the_same_name_is_not_used():
    # Without any of the farmer's crop sown records there is no registered Cultivation to compare with
    # (a "Plot 1" of another farmer must not limit this farmer's sowing)
    record = {"cluster_status": ["INDEPENDENT"], "land_id": "Plot 1", "season": "SEASON_IRRIGATION", "area_sown": 0.9,
              "submission_id": "sub-1"}
    rows = {"g2p_register_cultivations": [(0.75,)]}
    with patch.object(checks, "get_master_records_for_submission", new=AsyncMock(return_value=([], "", "", ""))):
        asyncio.run(G2PRegisterDomainServiceSowing()._validate_sowing_area_after_cultivation(record, Session(rows)))
