"""A farmer identified by a FIN (12 digits, no FAN) gets the same parent reuse and
record lookups as a FAN farmer."""
import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_cropsown_extension.register_domain.services import cropsown_intake_validation_service as checks
from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_crop_sown import (
    G2PRegisterDomainServiceCropSown,
)


class Session:
    """Answers the header read and the crop-record search; records the SQL."""

    def __init__(self, header=None, parents=()):
        self.header, self.parents, self.calls = header, list(parents), []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params or {}))
        if "FROM g2p_intake_form_crop_sowns" in sql:
            return SimpleNamespace(fetchone=lambda: self.header)
        if "FROM g2p_register_crop_sowns" in sql:
            return SimpleNamespace(fetchall=lambda: self.parents)
        return SimpleNamespace(fetchall=lambda: [], fetchone=lambda: None)


def reuse(row, session):
    service = G2PRegisterDomainServiceCropSown()
    reuse_parent = getattr(service, "_oan_reuse_existing_parent", None) or service._coss_reuse_existing_parent
    return asyncio.run(reuse_parent(row, session))


def new_root(**fayda):
    return SimpleNamespace(internal_record_id="new-1", farmer_id="FR-983278153587", crop_year="2026",
                           production_season="SEASON_IRRIGATION", record_status="ACTIVE",
                           **{"fayda_fan_id": None, "fayda_fin": None, **fayda})


def test_a_fin_farmers_new_intake_attaches_to_the_existing_record():
    session = Session(parents=[("parent-1", "SEASON_IRRIGATION")])
    row = new_root(fayda_fin="654752159325")
    assert reuse(row, session) is True
    assert row.record_status == "INACTIVE"  # the duplicate root is retired
    sql, params = next(c for c in session.calls if "FROM g2p_register_crop_sowns" in c[0])
    assert "fayda_fin" in sql and params["fayda_ns"] == "654752159325"
    assert any("UPDATE" in c[0] and c[1].get("p") == "parent-1" for c in session.calls)


def test_a_fan_farmer_still_attaches_and_no_fayda_does_nothing():
    assert reuse(new_root(fayda_fan_id="1234 5678 9012 3456"), Session(parents=[("p", "SEASON_IRRIGATION")])) is True
    session = Session(parents=[("p", "SEASON_IRRIGATION")])
    assert reuse(new_root(), session) is False and session.calls == []


def test_another_season_is_not_the_same_parent():
    assert reuse(new_root(fayda_fin="654752159325"), Session(parents=[("p", "SEASON_MEHER")])) is False


def test_the_farmers_records_are_found_by_fin():
    session = Session(header=("654752159325", "2026", "SEASON_IRRIGATION", "FR-983278153587"),
                      parents=[("rec-1", "2026", "SEASON_IRRIGATION", "FR-983278153587"),
                               ("rec-2", "2026", "SEASON_MEHER", "FR-983278153587")])
    ids, fayda, year, season = asyncio.run(checks.get_master_records_for_submission(session, "sub-1"))
    assert ids == ["rec-1"] and fayda == "654752159325"
    header_sql = session.calls[0][0]
    assert "fayda_fin" in header_sql
    search_sql = session.calls[1][0]
    assert "fayda_fin" in search_sql and "fayda_fan_id" in search_sql
