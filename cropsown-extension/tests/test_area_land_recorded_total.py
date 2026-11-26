"""Yes to "Is planning record created?": the row has no Total land area of its own, so Area sown
and Area harvested are checked against the land's total area in the earlier row of the same
Land ID: Cultivation first, else Planning (Clustered: Cultivation cluster, else Planning cluster).
The land is matched by Land ID only, never by crop."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException  # noqa: E402

from openg2p_registry_cropsown_extension.register_domain.services import (  # noqa: E402
    cropsown_intake_validation_service as checks,
)

MASTER = (["rec-1"], "fan", "2026", "SEASON_MEHER")


class Session:
    """Each table named holds the land with that total area (None = the land without a total)."""

    def __init__(self, totals):
        self.totals, self.queries = totals, []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.queries.append((sql, dict(params or {})))
        table = next((t for t in self.totals if f" {t} " in sql), None)
        return SimpleNamespace(first=lambda: (self.totals[table],) if table else None)


def check(totals, **row):
    session = Session(totals)
    with patch.object(checks, "get_master_records_for_submission", new=AsyncMock(return_value=MASTER)):
        asyncio.run(checks.validate_land_recorded({"submission_id": "sub-1", **row}, session))
    return session


YES = {"is_land_recorded": True, "land_id": "L1"}
CLUSTER_YES = {"is_cluster_land_recorded": True, "cluster_land_id": "C1"}


def refused(totals, **row):
    with pytest.raises(G2PRegistryException) as error:
        check(totals, **row)
    return error.value.message


def test_cultivation_comes_first():
    totals = {"g2p_intake_form_cultivations": 2.0, "g2p_intake_form_plannings": 5.0}
    check(totals, **YES, area_sown=2.0)
    assert refused(totals, **YES, area_sown=2.5) == \
        "Area sown (2.5 hectares) cannot be more than Total land area (2 hectares) in Cultivation for Land ID 'L1'."


def test_planning_when_there_is_no_cultivation_or_it_has_no_total():
    assert "Total land area (2 hectares) in Planning" in refused({"g2p_intake_form_plannings": 2.0}, **YES, area_sown=3)
    totals = {"g2p_intake_form_cultivations": None, "g2p_intake_form_plannings": 2.0}
    assert "Total land area (2 hectares) in Planning" in refused(totals, **YES, area_sown=3)


def test_the_farmers_crop_records_when_this_intake_has_no_total():
    assert "in Cultivation" in refused({"g2p_register_cultivations": 1.5}, **YES, area_harvested=2)
    totals = {"g2p_intake_form_plannings": None, "g2p_register_plannings": 1.5}
    assert "Area harvested (2 hectares) cannot be more than Total land area (1.5 hectares) in Planning" in \
        refused(totals, **YES, area_harvested=2)
    check({"g2p_register_cultivations": 1.5}, **YES, area_harvested=1.5)


def test_a_land_without_any_total_is_not_area_checked():
    check({"g2p_intake_form_cultivations": None}, **YES, area_sown=99)


def test_the_land_is_matched_by_land_id_only_never_by_crop():
    session = check({"g2p_intake_form_cultivations": 2.0}, **YES, commodity="CROP_TEFF", area_sown=1)
    for sql, params in session.queries:
        assert "TRIM(land_id) = :land" in sql and "commodity" not in sql and "crops" not in params, sql


def test_clustered_harvest_is_checked_against_the_cultivation_cluster_then_the_planning_cluster():
    totals = {"g2p_intake_form_cultivation_clusters": 3.0, "g2p_intake_form_clusters": 9.0}
    check(totals, **CLUSTER_YES, cluster_area_harvested=3)
    assert refused(totals, **CLUSTER_YES, cluster_area_harvested=3.5) == (
        "Area harvested, cluster (3.5 hectares) cannot be more than Total cultivated area (3 hectares) "
        "in Cultivation cluster for Land ID (cluster) 'C1'.")
    assert "in Planning cluster" in refused({"g2p_register_clusters": 3.0}, **CLUSTER_YES, cluster_area_sown=4)


def test_a_clustered_sowing_with_its_own_total_cultivated_area_uses_that_one():
    # The row's own Total cultivated area is checked on the row (same-row check), not here.
    check({"g2p_intake_form_cultivation_clusters": 1.0}, **CLUSTER_YES, cluster_area_hectare=5, cluster_area_sown=4)


def test_no_still_checks_nothing_here():
    session = check({"g2p_intake_form_cultivations": 1.0}, is_land_recorded=False, land_id="L1", area_sown=9)
    assert session.queries == []


def test_a_land_not_found_is_still_refused():
    assert "No planning or cultivation record found for Land ID 'L1'" in refused({}, **YES, area_sown=1)
