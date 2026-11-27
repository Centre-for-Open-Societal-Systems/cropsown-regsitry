"""Option B: Area sown and Area harvested are checked only against Total land area on the same row
(Area sown, cluster against Total cultivated area). They are not compared with the area of an
earlier section (Planning, Cultivation or Sowing), so a farmer may sow or harvest more than an
earlier section recorded, but never more than the land."""
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException  # noqa: E402

from openg2p_registry_cropsown_extension.register_domain.services import (  # noqa: E402
    cropsown_intake_validation_service as checks,
)
from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_harvest import (  # noqa: E402
    G2PRegisterDomainServiceHarvest,
)
from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_sowing import (  # noqa: E402
    G2PRegisterDomainServiceSowing,
)

SERVICES = Path(checks.__file__).resolve().parent
EARLIER_AREAS = ("planned_area", "actual_crop_area", "area_sown", "cluster_area_hectare", "cluster_plan")


class Session:
    """Every earlier section on this land holds 0.5 ha (Planning, Cultivation, Sowing and their
    cluster tables); nothing else is found. Keeps every statement it is asked."""

    def __init__(self):
        self.queries = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.queries.append(sql)
        hit = [(0.5,)] if any(sql.lstrip().startswith(f"SELECT {column} FROM") for column in EARLIER_AREAS) else []
        return SimpleNamespace(fetchall=lambda: hit, fetchone=lambda: hit[0] if hit else None, scalar=lambda: None,
                               scalars=lambda: SimpleNamespace(all=lambda: [], first=lambda: None))


def sowing(**row):
    record = {"cluster_status": ["INDEPENDENT"], "land_id": "L1", "commodity": "CROP_TEFF",
              "season": "SEASON_MEHER", "is_land_recorded": False, "submission_id": "sub-1", **row}
    session = Session()
    asyncio.run(G2PRegisterDomainServiceSowing().validate_domain_attributes([record], session=session))
    return session


def harvest(**row):
    record = {"cluster_status": ["INDEPENDENT"], "land_id": "L1", "commodity": "CROP_TEFF",
              "season": "SEASON_MEHER", "is_land_recorded": False, "submission_id": "sub-1", **row}
    session = Session()
    asyncio.run(G2PRegisterDomainServiceHarvest().validate_domain_attributes([record], session=session))
    return session


def no_earlier_area_read(session):
    for sql in session.queries:
        selected = sql.split("FROM", 1)[0]
        assert not any(f"SELECT {column} " in selected + " " for column in EARLIER_AREAS), sql


def test_area_sown_up_to_total_land_area_is_accepted_whatever_earlier_sections_say():
    no_earlier_area_read(sowing(area_sown=1.8, land_area=2.0))
    sowing(area_sown=2.0, land_area=2.0)


def test_area_sown_more_than_total_land_area_is_refused():
    with pytest.raises(G2PRegistryException) as error:
        sowing(area_sown=2.5, land_area=2.0)
    assert "Area sown (2.5 hectares) cannot be more than Total land area (2 hectares)." in error.value.message


def test_clustered_area_sown_is_checked_against_total_cultivated_area():
    row = {"cluster_status": ["CLUSTERED"], "cluster_land_id": "C1", "cluster_name": "FPC 1",
           "cluster_season": "SEASON_MEHER", "cluster_area_hectare": 3.0}
    no_earlier_area_read(sowing(**row, cluster_area_sown=3.0))
    with pytest.raises(G2PRegistryException) as error:
        sowing(**row, cluster_area_sown=3.5)
    assert "cannot be more than Total cultivated area (3 hectares)" in error.value.message


def test_area_harvested_up_to_total_land_area_is_accepted_and_more_is_refused():
    no_earlier_area_read(harvest(area_harvested=1.8, land_area=2.0))
    with pytest.raises(G2PRegistryException) as error:
        harvest(area_harvested=2.5, land_area=2.0)
    assert "Area harvested (2.5 hectares) cannot be more than Total land area (2 hectares)." in error.value.message


def test_the_comparison_across_sections_is_gone():
    for name in ("g2p_register_domain_service_sowing.py", "g2p_register_domain_service_harvest.py",
                 "cropsown_intake_validation_service.py"):
        source = (SERVICES / name).read_text(encoding="utf-8")
        for retired in ("_validate_sowing_area_after_cultivation", "_validate_harvest_area_after_sowing",
                        "earlier_stage_area"):
            assert retired not in source, (name, retired)
