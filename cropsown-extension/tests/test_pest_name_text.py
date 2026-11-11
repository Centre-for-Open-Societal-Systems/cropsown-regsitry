"""Pest name is typed text on the web form and ODK; an infestation on a cluster land finds its Sowing."""
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

SRC = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension"
ZZ_OAN = SRC / "meta_data/zz-oan"
OVERLAY = ZZ_OAN / "97j_pest_name_text.sql"


def test_the_web_form_asks_pest_name_as_text_without_a_list():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "WHERE \"section_id\" = 'cropsown_infestation_details_section_01'" in sql
    assert "(node - 'widget-data-source') || '{\"widget\": \"text\"}'::jsonb" in sql
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql" and len({n.split("_")[0] for n in names}) == len(names)


def test_a_text_pest_name_is_not_checked_against_master_data():
    pytest.importorskip("openg2p_registry_core")
    from openg2p_registry_core.services.g2p_attribute_value_validator import G2PAttributeValueValidator
    text = {"widget": "text", "column-key": "pest_name", "widget-data-path": "pest_name"}
    listed = {"widget": "select", "column-key": "pest_type",
              "widget-data-source": {"type": "api", "params": {"attribute_id": "PEST"}}}
    assert G2PAttributeValueValidator.field_map_from_ui_schema([text, listed]) == {"pest_type": "PEST"}


class Session:
    def __init__(self):
        self.sql = []

    async def execute(self, statement, params=None):
        self.sql.append(str(statement))
        hit = [("CROP_TEFF", "2026-07-01", "FPC")] if "g2p_intake_form_sowings" in str(statement) else []
        return SimpleNamespace(fetchall=lambda: hit, fetchone=lambda: None, all=lambda: [])


def test_an_infestation_finds_its_sowing_by_either_land_id():
    pytest.importorskip("openg2p_registry_core")
    from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_infestation import (
        G2PRegisterDomainServiceInfestation,
    )
    session = Session()
    record = {"land_id": "C1", "submission_id": "sub-1", "cluster_status": "CLUSTER", "cluster_name": "FPC",
              "observation_date": "2026-06-01"}
    asyncio.run(G2PRegisterDomainServiceInfestation()._validate_infestation_after_sowing(record, session))
    assert "(land_id = :land_id OR cluster_land_id = :land_id)" in session.sql[0]
