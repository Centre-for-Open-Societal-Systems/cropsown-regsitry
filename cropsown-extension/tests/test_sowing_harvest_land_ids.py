"""Sowing and Harvest rows: Land ID for Independent, Land ID (cluster) for Clustered."""
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException

from openg2p_registry_cropsown_extension.register_domain.services import cropsown_intake_validation_service as checks

ZZ_OAN = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension/meta_data/zz-oan"
OVERLAY = ZZ_OAN / "97g_sowing_harvest_land_rows.sql"
SERVICES = Path(checks.__file__).parent


def test_each_status_takes_its_own_land_id():
    row = {"land_id": "IND-1", "cluster_land_id": "CL-1"}
    assert checks.row_lands({**row, "cluster_status": ["INDEPENDENT"]}) == ("", "IND-1")
    assert checks.row_lands({**row, "cluster_status": ["CLUSTER"]}) == ("CL-1", "")
    assert checks.row_lands({**row, "cluster_status": ["CLUSTER", "INDEPENDENT"]}) == ("CL-1", "IND-1")
    # no status (ODK, file import, older rows): the one Land ID, as before
    assert checks.row_lands({"land_id": "IND-1"}) == ("", "IND-1")
    assert checks.row_lands({"land_id": "OLD", "cluster_name": "FPC", "cluster_status": None}) == ("OLD", "")


class Session:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, statement, params=None):
        sql = str(statement)
        hit = [r for table, r in self.rows if table in sql]
        return SimpleNamespace(fetchall=lambda: hit)


def run(fn, rows, payload):
    with patch.object(checks, "get_master_records_for_submission",
                      new=AsyncMock(return_value=(["rec-1"], "fan", "2026", "MEHER"))):
        asyncio.run(fn(Session(rows), payload, "sub-1"))


def test_a_clustered_sowing_is_dated_against_the_cultivation_cluster_of_its_cluster_land():
    rows = [("g2p_intake_form_cultivation_clusters", ("CL-1", "FPC", "2026-07-01", None)),
            ("g2p_intake_form_cultivations", ("CL-1", "MAIZE", "MEHER", "2026-01-01", None))]
    row = {"cluster_status": ["CLUSTER"], "cluster_land_id": "CL-1", "cluster_name": "FPC", "sowing_date": "2026-06-01"}
    with pytest.raises(G2PRegistryException) as error:
        run(checks.validate_sowing_against_cultivation, rows, [row])
    assert "Land ID (cluster) 'CL-1'" in error.value.message
    # the same land as an Independent Land ID is not a cluster land
    run(checks.validate_sowing_against_cultivation, rows,
        [{"cluster_status": ["CLUSTER"], "cluster_land_id": "OTHER", "cluster_name": "FPC", "sowing_date": "2026-06-01"}])


def test_a_row_with_both_ticked_is_checked_on_the_independent_side_too():
    rows = [("g2p_intake_form_cultivations", ("IND-1", "MAIZE", "MEHER", "2026-07-01", None))]
    row = {"cluster_status": ["CLUSTER", "INDEPENDENT"], "land_id": "IND-1", "cluster_land_id": "CL-1",
           "cluster_name": "FPC", "commodity": "MAIZE", "season": "MEHER", "sowing_date": "2026-06-01"}
    with pytest.raises(G2PRegistryException) as error:
        run(checks.validate_sowing_against_cultivation, rows, [row])
    assert "Land ID 'IND-1'" in error.value.message


def test_a_clustered_harvest_is_dated_against_the_sowing_of_its_cluster_land():
    rows = [("g2p_intake_form_sowings", ("IND-9", None, "FPC", None, "MEHER", "2026-08-01", ["CLUSTER"], "CL-1"))]
    row = {"cluster_status": ["CLUSTER"], "cluster_land_id": "CL-1", "cluster_name": "FPC",
           "cluster_harvest_date": "2026-07-01"}
    with pytest.raises(G2PRegistryException) as error:
        run(checks.validate_harvest_against_sowing, rows, [row])
    assert "Land ID (cluster) 'CL-1'" in error.value.message


def test_the_save_asks_for_the_land_id_of_each_side_ticked():
    for name, section in (("sowing", "Sowing"), ("harvest", "Harvest")):
        code = (SERVICES / f"g2p_register_domain_service_{name}.py").read_text(encoding="utf-8")
        assert f'"Land ID (cluster) is required in {section} details."' in code
        assert "if (independent or not clustered) and not str(record.get(\"land_id\")" in code


def test_the_overlay_shows_each_land_id_for_its_status():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "'cropsown_sowing_details_section_01', 'cropsown_harvest_details_section_01'" in sql
    assert "'widget-label', 'Land ID (cluster)'" in sql
    assert "ARRAY['INDEPENDENT', 'CLUSTER']" in sql
    assert "land - 'widget-required'" in sql  # a hidden required column would block the table check
    assert "ARRAY['cluster_status', 'cluster_land_id']" in sql  # Land ID (cluster) opens the cluster fields
    assert "NOT IN ('season', 'commodity')" in sql  # Land ID opens the Independent fields
    assert "'action', 'require'" in sql  # required while shown, on both channels
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql"
    assert len({n.split("_")[0] for n in names}) == len(names)
