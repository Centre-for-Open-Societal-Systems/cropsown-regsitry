"""Sowing date and Date of observation: any valid date from 1900, including a future date, on
every channel (web, ODK, file import, change requests). Date of observation is not compared
with the Sowing date; the Sowing date keeps its season and earlier-stage checks."""
from datetime import date, timedelta
from pathlib import Path

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_cropsown_extension.register_domain.services import field_rules

SRC = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension"
META = SRC / "meta_data"


def issues(field, value):
    return [p.key for p in field_rules.clean_records([{field: value}]) if p.field == field]


@pytest.mark.parametrize("field", ["sowing_date", "observation_date"])
def test_a_future_date_is_accepted(field):
    assert issues(field, (date.today() + timedelta(days=1)).isoformat()) == []
    assert issues(field, (date.today() + timedelta(days=400)).isoformat()) == []


@pytest.mark.parametrize("field", ["sowing_date", "observation_date"])
def test_today_and_past_dates_are_accepted(field):
    assert issues(field, date.today().isoformat()) == []
    assert issues(field, "2020-01-01") == []


@pytest.mark.parametrize("field", ["sowing_date", "observation_date"])
def test_the_date_is_still_checked_as_a_date(field):
    assert issues(field, "1899-12-31") == ["validation_rule_date_min"]
    assert issues(field, "not a date") == ["validation_rule_date_format"]


def test_only_date_of_birth_and_registration_date_stay_past_only():
    assert field_rules.PAST_ONLY == frozenset({"date_of_birth", "registration_date"})
    assert issues("date_of_birth", (date.today() + timedelta(days=1)).isoformat()) == ["validation_rule_date_future"]


def test_the_sowing_date_comparison_and_sowing_requirement_are_off():
    code = (SRC / "register_domain/services/g2p_register_domain_service_infestation.py").read_text(encoding="utf-8")
    live = [line for line in code.splitlines() if not line.strip().startswith("#")]
    assert not any("must be after" in line and "Sowing date" in line for line in live)
    assert not any("No sowing record found" in line for line in live)  # no saved Sowing is required either
    assert not any("run_record_cross_validation(self._validate_infestation_after_sowing" in line for line in live)


def test_no_web_date_picker_stops_these_dates_at_today():
    site_configuration = META / "site-configuration"
    assert not (site_configuration / "97i_dates_not_future.sql").exists()
    for path in META.rglob("*.sql"):
        text = path.read_text(encoding="utf-8")
        assert "'maxDate', 'today'" not in text, path.name
    names = sorted(p.name for p in site_configuration.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql" and len({n.split("_")[0] for n in names}) == len(names)
