"""Cultivation rows ask "Is planning record created?"; No shows the land details, Yes is checked."""
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException

from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_cultivation import (
    G2PRegisterDomainServiceCultivation,
)

ZZ_OAN = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension/meta_data/zz-oan"
OVERLAY = ZZ_OAN / "97f_cultivation_land_details.sql"
MASTER = "openg2p_registry_cropsown_extension.register_domain.services.cropsown_intake_validation_service.get_master_records_for_submission"


class Session:
    """Answers the two Planning lookups: rows of this intake, rows of the farmer's records."""

    def __init__(self, intake=False, registered=False):
        self.intake, self.registered, self.calls = intake, registered, []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append(sql)
        hit = self.intake if "g2p_intake_form_plannings" in sql else self.registered
        return SimpleNamespace(first=lambda: (1,) if hit else None)


def check(record, session, master_ids=("rec-1",)):
    service = G2PRegisterDomainServiceCultivation()
    with patch(MASTER, new=AsyncMock(return_value=(list(master_ids), "fan", "2026", "SEASON_MEHER"))):
        asyncio.run(service._validate_planning_record_exists(record, session))


def test_yes_with_the_land_in_this_intakes_planning_passes():
    check({"is_planning_record_created": True, "land_id": "121", "submission_id": "sub-1"}, Session(intake=True))


def test_yes_with_the_land_in_the_farmers_planning_of_the_season_passes():
    check({"is_planning_record_created": True, "land_id": "121", "submission_id": "sub-1"}, Session(registered=True))


def test_yes_without_a_matching_planning_row_is_refused():
    with pytest.raises(G2PRegistryException) as error:
        check({"is_planning_record_created": True, "land_id": "12", "submission_id": "sub-1"}, Session())
    assert "No planning record found for Land ID '12'" in error.value.message


def test_no_or_no_answer_is_never_checked():
    for answer in (False, None):
        session = Session()
        check({"is_planning_record_created": answer, "land_id": "12", "submission_id": "sub-1"}, session)
        assert session.calls == []


def test_an_edited_record_is_checked_against_its_own_planning():
    with pytest.raises(G2PRegistryException):
        check({"is_planning_record_created": True, "land_id": "12", "link_internal_record_id": "rec-9"}, Session(),
              master_ids=())


def test_the_overlay_shows_the_land_details_only_for_no():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "WHERE \"section_id\" = 'cropsown_cultivation_details_section_01'" in sql
    assert "'widget-label', 'Is planning record created?'" in sql
    assert '{"field": "is_planning_record_created", "operator": "equals", "value": false}' in sql
    assert "WHERE s.\"section_id\" = 'cropsown_planning_details_section_01'" in sql  # copied from Planning
    for key in ("'plot_category'", "'ownership_type'", "'soil_fertility_type'", "'region'", "'kebele'",
                "'map_location'", "'latitude'", "'longitude'"):
        assert key in sql
    assert "widget-required" not in sql  # ODK and file import do not send the answer yet
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names.index(OVERLAY.name) > names.index("97c_planning_map_location.sql")
    assert names[-1] == "98_ethiopian_dates.sql"
    assert len({n.split("_")[0] for n in names}) == len(names)


def test_the_crop_location_is_on_every_row_after_the_actual_crop_area():
    sql = OVERLAY.read_text(encoding="utf-8")
    block = sql.split("ELSIF col->>'column-key' = 'actual_crop_area' THEN", 1)[1].split("END IF;\n        END LOOP;", 1)[0]
    assert "ARRAY['crop_map_location', 'crop_latitude', 'crop_longitude']" in block
    assert "when_no" not in block  # shown whatever the answer
    from openg2p_registry_cropsown_extension.register_domain.models.cultivation import G2PRegisterCultivation
    from openg2p_registry_cropsown_extension.register_domain.schemas.cultivation import G2PRegisterSchemaCultivation
    for key in ("crop_latitude", "crop_longitude"):
        assert key in G2PRegisterCultivation.__table__.columns
        assert key in G2PRegisterSchemaCultivation.model_fields
