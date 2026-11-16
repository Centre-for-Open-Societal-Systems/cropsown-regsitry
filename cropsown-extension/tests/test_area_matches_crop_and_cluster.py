"""Area sown and area harvested are compared only with the matching earlier-stage row:
Independent by Land ID + crop + season, Clustered by Land ID (cluster) + FPC name. Every lookup
names the row's land; there is no fallback to any row of the record."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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

MASTER = (["rec-1"], "fan", "2026", "SEASON_MEHER")


class Session:
    """Answers with the rows of the first table named in the statement and the given area column;
    keeps every statement so the match can be checked."""

    def __init__(self, rows):
        self.rows, self.queries = rows, []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.queries.append((sql, dict(params or {})))
        hit = next((v for (table, column), v in self.rows.items() if table in sql and f"SELECT {column} " in sql), [])
        return SimpleNamespace(fetchall=lambda: hit, fetchone=lambda: hit[0] if hit else None)


def run(service, method, record, rows):
    session = Session(rows)
    with patch.object(checks, "get_master_records_for_submission", new=AsyncMock(return_value=MASTER)):
        asyncio.run(getattr(service, method)({"submission_id": "sub-1", **record}, session))
    return session


def sow(record, rows):
    return run(G2PRegisterDomainServiceSowing(), "_validate_sowing_area_after_cultivation", record, rows)


def harvest(record, rows):
    return run(G2PRegisterDomainServiceHarvest(), "_validate_harvest_area_after_sowing", record, rows)


INDEPENDENT = {"cluster_status": ["INDEPENDENT"], "land_id": "Plot 1", "commodity": "CROP_TEFF", "season": "SEASON_MEHER"}
CLUSTERED = {"cluster_status": ["CLUSTERED"], "cluster_land_id": "C-1", "cluster_name": "Gara Cluster"}


def test_sowing_is_matched_on_land_crop_and_season():
    with pytest.raises(G2PRegistryException) as error:
        sow({**INDEPENDENT, "area_sown": 2}, {("g2p_intake_form_cultivations", "actual_crop_area"): [(1.5,)]})
    assert ("Area sown (2.0 hectares) cannot exceed Actual Crop Area in Cultivation (1.5 hectares) "
            "for Land ID 'Plot 1' and Crop 'CROP_TEFF'") in error.value.message
    session = sow({**INDEPENDENT, "area_sown": 1}, {("g2p_intake_form_cultivations", "actual_crop_area"): [(1.5,)]})
    sql, params = session.queries[0]
    assert "commodity = ANY(:crops)" in sql and "season = ANY(:seasons)" in sql and "TRIM(land_id) = :land_id" in sql
    assert {"CROP_TEFF", "crop_teff"} <= set(params["crops"]) and params["land_id"] == "Plot 1"


def test_a_row_without_a_crop_or_land_is_not_compared():
    session = sow({**INDEPENDENT, "commodity": "", "area_sown": 9}, {("g2p_intake_form_cultivations", "actual_crop_area"): [(1,)]})
    assert session.queries == []


def test_every_lookup_names_the_rows_land_and_none_falls_back_to_any_row_of_the_record():
    session = sow({**INDEPENDENT, **CLUSTERED, "cluster_status": ["CLUSTERED", "INDEPENDENT"],
                   "area_sown": 1, "cluster_area_sown": 1}, {})
    harvested = harvest({**INDEPENDENT, **CLUSTERED, "cluster_status": ["CLUSTERED", "INDEPENDENT"],
                         "area_harvested": 1, "cluster_area_harvested": 1}, {})
    for sql, _ in session.queries + harvested.queries:
        assert ":land_id" in sql or ":cluster_land_id" in sql, sql


def test_a_clustered_sowing_is_checked_against_its_cultivation_cluster_then_its_planning_cluster():
    with pytest.raises(G2PRegistryException) as error:
        sow({**CLUSTERED, "cluster_area_sown": 12},
            {("g2p_register_cultivation_clusters", "cluster_area_hectare"): [(10.0,)],
             ("g2p_intake_form_clusters", "cluster_plan"): [(20.0,)]})
    assert ("Area sown, cluster (12.0 hectares) cannot exceed Total cultivated area in Cultivation cluster "
            "(10.0 hectares) for Farmer production cluster 'Gara Cluster' and Land ID (cluster) 'C-1'") in error.value.message
    with pytest.raises(G2PRegistryException) as error:
        sow({**CLUSTERED, "cluster_area_sown": 12}, {("g2p_intake_form_clusters", "cluster_plan"): [(8.0,)]})
    assert "cannot exceed Planned area in Planning cluster (8.0 hectares)" in error.value.message
    session = sow({**CLUSTERED, "cluster_area_sown": 5}, {("g2p_intake_form_clusters", "cluster_plan"): [(8.0,)]})
    sql, params = session.queries[0]
    assert "TRIM(land_id) = :cluster_land_id AND UPPER(TRIM(cluster_name)) = :cluster_name" in sql
    assert params["cluster_name"] == "GARA CLUSTER" and params["cluster_land_id"] == "C-1"
    sow({**CLUSTERED, "cluster_area_sown": 99}, {})  # no matching cluster: nothing to check


def test_a_row_with_both_ticked_is_checked_on_both_sides():
    rows = {("g2p_intake_form_cultivations", "actual_crop_area"): [(5.0,)],
            ("g2p_intake_form_cultivation_clusters", "cluster_area_hectare"): [(1.0,)]}
    with pytest.raises(G2PRegistryException) as error:
        sow({**INDEPENDENT, **CLUSTERED, "cluster_status": ["CLUSTERED", "INDEPENDENT"],
             "area_sown": 2, "cluster_area_sown": 3}, rows)
    assert "Area sown, cluster (3.0 hectares)" in error.value.message  # the Independent side passed


def test_harvest_is_matched_on_land_crop_and_season_then_on_the_cluster_and_fpc():
    with pytest.raises(G2PRegistryException) as error:
        harvest({**INDEPENDENT, "area_harvested": 2}, {("g2p_register_sowings", "area_sown"): [(1.0,)]})
    assert ("Area harvested (2.0 hectares) cannot exceed Area Sown in Sowing (1.0 hectares) "
            "for Land ID 'Plot 1' and Crop 'CROP_TEFF'") in error.value.message
    with pytest.raises(G2PRegistryException) as error:
        harvest({**CLUSTERED, "cluster_area_harvested": 4}, {("g2p_intake_form_sowings", "cluster_area_sown"): [(3.0,)]})
    assert ("Area harvested, cluster (4.0 hectares) cannot exceed Area Sown (cluster) in Sowing (3.0 hectares) "
            "for Farmer production cluster 'Gara Cluster' and Land ID (cluster) 'C-1'") in error.value.message
    session = harvest({**CLUSTERED, "cluster_area_harvested": 1}, {("g2p_intake_form_sowings", "cluster_area_sown"): [(3.0,)]})
    assert "TRIM(cluster_land_id) = :cluster_land_id AND UPPER(TRIM(cluster_name)) = :cluster_name" in session.queries[0][0]
