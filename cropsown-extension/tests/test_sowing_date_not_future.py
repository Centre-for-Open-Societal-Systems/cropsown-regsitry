"""Sowing date: today or an earlier date, on every channel."""
from datetime import date, timedelta
from pathlib import Path

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_cropsown_extension.register_domain.services import field_rules

ZZ_OAN = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension/meta_data/zz-oan"
OVERLAY = ZZ_OAN / "97i_dates_not_future.sql"


def issues(value):
    return [p.key for p in field_rules.clean_records([{"sowing_date": value}]) if p.field == "sowing_date"]


def test_a_future_sowing_date_is_refused():
    assert issues((date.today() + timedelta(days=1)).isoformat()) == ["validation_rule_date_future"]


def test_today_and_past_sowing_dates_are_accepted():
    assert issues(date.today().isoformat()) == []
    assert issues("2025-06-01") == []


def test_the_web_date_picker_stops_at_today():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "('cropsown_sowing_details_section_01', 'sowing_date')" in sql
    assert "'maxDate', 'today', 'maxDateMessage', 'validation_' || key || '_future'" in sql
    assert "'validation_sowing_date_future', 'Sowing date: the date is in the future." in sql
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names[-1] == "98_ethiopian_dates.sql" and len({n.split("_")[0] for n in names}) == len(names)
