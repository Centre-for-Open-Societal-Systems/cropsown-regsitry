"""An approved Crop record keeps its Crop sown ID, crop year and production season.

They are checked on save (core validates a change request without a session, so the
check opens its own), and again when the change request is approved. The Crop record
section shows them as not editable.
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException
from openg2p_registry_cropsown_extension.register_domain.services import (
    g2p_register_domain_service_crop_sown as module,
)
from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_crop_sown import (
    G2PRegisterDomainServiceCropSown,
)

RECORD_ID = "1aa7c675-91d6-40be-86ba-41d7b9172049"
PREFIX = "6b06a95a-9a6c-5a33-a33d-c1625716c59c."
OVERLAY = (Path(module.__file__).resolve().parents[2] / "meta_data" / "zz-oan" / "93_crop_record_header_readonly.sql")


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeSession:
    """Answers the established record lookup; child sections hold no rows."""

    def __init__(self, established):
        self.established = established

    async def execute(self, statement, params=None):
        if "FROM g2p_register_crop_sowns" in str(statement):
            return Rows([self.established] if self.established else [])
        return Rows([])


ESTABLISHED = (RECORD_ID, "2026", "SEASON_BELG", "REG/S2/2026/98176")


def save(record, established=ESTABLISHED):
    service = G2PRegisterDomainServiceCropSown()
    asyncio.run(service._validate_immutability_of_season_and_year(record, FakeSession(established)))


def same(**changes):
    return {"internal_record_id": RECORD_ID, PREFIX + "functional_record_id": "REG/S2/2026/98176",
            PREFIX + "crop_year": "2026", PREFIX + "production_season": "SEASON_BELG", **changes}


def test_saving_the_same_values_is_allowed():
    save(same())


@pytest.mark.parametrize("field, value, message", [
    ("functional_record_id", "REG/S2/2026/98177", "Crop sown ID cannot be changed"),
    ("production_season", "SEASON_MEHER", "Production season cannot be changed"),
    ("crop_year", "2025", "Crop year cannot be changed"),
])
def test_changing_an_established_value_fails_on_save(field, value, message):
    with pytest.raises(G2PRegistryException) as error:
        save(same(**{PREFIX + field: value}))
    assert message in error.value.message


def test_a_record_that_is_not_in_the_register_yet_is_not_checked():
    save(same(**{PREFIX + "production_season": "SEASON_MEHER"}), established=None)


def test_a_record_without_a_crop_sown_id_yet_can_get_one():
    save(same(**{PREFIX + "functional_record_id": "REG/S2/2026/98176"}),
         established=(RECORD_ID, "2026", "SEASON_BELG", None))


def test_without_a_session_the_check_opens_its_own():
    service = G2PRegisterDomainServiceCropSown()
    session = FakeSession(ESTABLISHED)

    class Maker:
        def __call__(self):
            return self

        async def __aenter__(self):
            return session

        async def __aexit__(self, *exc):
            return False

    with patch("openg2p_fastapi_common.context.get_async_session_maker", return_value=Maker()):
        with pytest.raises(G2PRegistryException):
            asyncio.run(service._validate_immutability_on_own_session(
                same(**{PREFIX + "functional_record_id": "REG/S2/2026/98177"})))


def test_without_ids_or_a_database_the_save_check_is_skipped():
    service = G2PRegisterDomainServiceCropSown()
    with patch("openg2p_fastapi_common.context.get_async_session_maker", side_effect=AssertionError("not opened")):
        asyncio.run(service._validate_immutability_on_own_session({"crop_year": "2026"}))
    with patch("openg2p_fastapi_common.context.get_async_session_maker", side_effect=RuntimeError("no engine")):
        asyncio.run(service._validate_immutability_on_own_session(same()))


@pytest.mark.parametrize("item, fails", [
    ({"internal_record_id": RECORD_ID, "functional_record_id": "REG/S2/2026/98176",
      "crop_year": "2026", "production_season": "SEASON_BELG"}, False),
    ({"internal_record_id": RECORD_ID, "functional_record_id": "REG/S2/2026/98177"}, True),
    ({"internal_record_id": RECORD_ID, "production_season": "SEASON_MEHER"}, True),
])
def test_approval_rejects_a_changed_crop_sown_id_year_or_season(item, fails):
    service = G2PRegisterDomainServiceCropSown()
    record = SimpleNamespace(internal_record_id=RECORD_ID, functional_record_id="REG/S2/2026/98176",
                             crop_year="2026", production_season="SEASON_BELG")
    session = SimpleNamespace(get=AsyncMock(return_value=record))
    change_request = SimpleNamespace(internal_record_id=RECORD_ID, change_request_id="cr-1",
                                     section_id="cropsown_cropsown_record_section_01")
    cr_service = SimpleNamespace(_get_change_request_payload=AsyncMock(
        return_value=SimpleNamespace(change_payload=[item])))
    with patch("openg2p_registry_core.services.g2p_register_change_request_service."
               "G2PRegisterChangeRequestService.get_component", return_value=cr_service):
        run = lambda: asyncio.run(service._check_immutable_header_season_and_year(change_request, session))
        if fails:
            with pytest.raises(G2PRegistryException):
                run()
        else:
            run()


def test_the_crop_record_section_shows_the_three_fields_as_not_editable():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "'cropsown_cropsown_record_section_01'" in sql
    assert "IN ('functional_record_id', 'crop_year')" in sql and '"widget": "display"' in sql
    assert "= 'production_season'" in sql and '{"widget-readonly": true}' in sql
    later = sorted(p.name for p in OVERLAY.parent.glob("*.sql"))
    assert later.index(OVERLAY.name) > later.index("41_crop_record_tab_layout.sql")
    assert later[-1] == "98_ethiopian_dates.sql"
