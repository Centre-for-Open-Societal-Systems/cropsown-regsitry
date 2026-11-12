"""Date of observation (Infestation): today or an earlier date, and no longer compared
with the Sowing date."""
from datetime import date, timedelta
from pathlib import Path

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_cropsown_extension.register_domain.services import field_rules

SRC = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension"
ZZ_OAN = SRC / "meta_data/zz-oan"
OVERLAY = ZZ_OAN / "97i_dates_not_future.sql"


def issues(value):
    return [p.key for p in field_rules.clean_records([{"observation_date": value}]) if p.field == "observation_date"]


def test_a_future_observation_date_is_refused():
    assert issues((date.today() + timedelta(days=1)).isoformat()) == ["validation_rule_date_future"]


def test_today_and_past_observation_dates_are_accepted():
    assert issues(date.today().isoformat()) == []
    assert issues("2020-01-01") == []


def test_the_sowing_date_comparison_and_sowing_requirement_are_off():
    code = (SRC / "register_domain/services/g2p_register_domain_service_infestation.py").read_text(encoding="utf-8")
    live = [line for line in code.splitlines() if not line.strip().startswith("#")]
    assert not any("must be after" in line and "Sowing date" in line for line in live)
    assert not any("No sowing record found" in line for line in live)  # no saved Sowing is required either
    assert not any("run_record_cross_validation(self._validate_infestation_after_sowing" in line for line in live)


def test_the_web_date_picker_stops_at_today():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "('cropsown_infestation_details_section_01', 'observation_date')" in sql
    assert "'validation_observation_date_future', 'Date of observation: the date is in the future." in sql
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql" and len({n.split("_")[0] for n in names}) == len(names)
