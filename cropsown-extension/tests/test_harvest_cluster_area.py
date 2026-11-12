"""Area harvested is compared only with the same farmer's land, and a Clustered-only row
(which also carries land_id, equal to its Land ID (cluster)) is not compared with an
Independent Area sown."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException

from openg2p_registry_cropsown_extension.register_domain.services import cropsown_intake_validation_service as checks
from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_harvest import (
    G2PRegisterDomainServiceHarvest,
)


class Session:
    """Answers a register query only for the farmer's own records (ids = rec-1)."""

    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    async def execute(self, statement, params=None):
        sql, params = str(statement), params or {}
        self.queries.append((sql, params))
        table = next((t for t in self.rows if t in sql), None)
        hit = self.rows.get(table, [])
        if table and table.startswith("g2p_register_") and "rec-1" not in (params.get("ids") or [params.get("link_id")]):
            hit = []  # another farmer's land
        return SimpleNamespace(fetchall=lambda: hit, fetchone=lambda: hit[0] if hit else None)


def run(record, rows, master=(["rec-1"], "fan", "2026", "SEASON_MEHER")):
    session = Session(rows)
    with patch.object(checks, "get_master_records_for_submission", new=AsyncMock(return_value=master)):
        asyncio.run(G2PRegisterDomainServiceHarvest()._validate_harvest_area_after_sowing(
            {"submission_id": "sub-1", **record}, session))
    return session


def test_a_clustered_only_row_is_not_compared_with_an_independent_area_sown():
    record = {"cluster_status": ["CLUSTERED"], "land_id": "Plot 1", "cluster_land_id": "Plot 1",
              "cluster_area_harvested": 0.7}
    session = run(record, {"g2p_register_sowings": [(0.5,)]})
    assert session.queries == []  # nothing looked up, nothing refused


def test_an_independent_row_is_still_compared_with_its_own_sowing():
    record = {"cluster_status": ["CLUSTERED", "INDEPENDENT"], "land_id": "Plot 1", "area_harvested": 0.7}
    with pytest.raises(G2PRegistryException) as error:
        run(record, {"g2p_register_sowings": [(0.5,)]})
    assert "Area harvested (0.7 hectares) cannot exceed Area Sown in Sowing (0.5 hectares)" in error.value.message


def test_another_farmers_land_with_the_same_land_id_is_never_used():
    record = {"cluster_status": ["INDEPENDENT"], "land_id": "Plot 1", "area_harvested": 0.7}
    # the farmer has no crop records: no register row is read by Land ID alone
    session = run(record, {"g2p_register_sowings": [(0.5,)], "g2p_register_cultivations": [(0.4,)]},
                  master=([], "", "", ""))
    for sql, _ in session.queries:
        if "g2p_register_" in sql:
            assert "link_internal_record_id" in sql, sql
