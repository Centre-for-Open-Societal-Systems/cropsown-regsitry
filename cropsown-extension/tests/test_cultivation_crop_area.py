"""Cultivation: Actual crop area within Total land area, per row and per Land ID, as Planning
checks its planned area. Runs on save and submit for every channel (validate_domain_attributes)."""
import inspect

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException  # noqa: E402

from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_cultivation import (  # noqa: E402
    G2PRegisterDomainServiceCultivation,
)

SERVICE = G2PRegisterDomainServiceCultivation()


@pytest.mark.parametrize("record", [
    {"actual_crop_area": 0.5, "land_area": 2},
    {"actual_crop_area": "2", "land_area": "2"},          # equal is allowed
    {"actual_crop_area": 3, "land_area": None},           # no land area: not compared
    {"actual_crop_area": 3, "land_area": 0},
    {"actual_crop_area": None, "land_area": 1},
])
def test_a_crop_area_within_the_land_area_or_without_one_passes(record):
    SERVICE._validate_actual_crop_area(record)


def test_a_crop_area_above_the_land_area_is_refused():
    with pytest.raises(G2PRegistryException) as error:
        SERVICE._validate_actual_crop_area({"actual_crop_area": "2.5", "land_area": "2"})
    assert "Actual crop area (2.5 hectares) cannot be greater than Total land area (2 hectares)" in error.value.message


def test_the_crop_areas_of_one_land_together_may_not_exceed_its_land_area():
    rows = [{"land_id": "L1", "actual_crop_area": 1.5, "land_area": 2},
            {"land_id": "L1", "actual_crop_area": 1, "land_area": 2},
            {"land_id": "L2", "actual_crop_area": 5, "land_area": 6}]
    with pytest.raises(G2PRegistryException) as error:
        SERVICE._validate_cumulative_actual_crop_area(rows)
    assert ("Total actual crop area (2.5 hectares) across all records for Land ID 'L1' "
            "exceeds Total land area (2 hectares)") in error.value.message


def test_separate_lands_and_rows_without_a_land_area_are_not_added_together():
    SERVICE._validate_cumulative_actual_crop_area([
        {"land_id": "L1", "actual_crop_area": 1, "land_area": 2},
        {"land_id": "L1", "actual_crop_area": 1, "land_area": None},
        {"land_id": "L2", "actual_crop_area": 3, "land_area": 3},
        {"land_id": "", "actual_crop_area": 9, "land_area": 1},
        {"land_id": "L3", "actual_crop_area": 9, "land_area": None},
    ])


def test_both_checks_run_on_save_and_submit():
    source = inspect.getsource(G2PRegisterDomainServiceCultivation.validate_domain_attributes)
    assert "self._validate_actual_crop_area(record)" in source
    assert "self._validate_cumulative_actual_crop_area(active_records)" in source
