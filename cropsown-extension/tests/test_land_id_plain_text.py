"""Land ID and Land ID (cluster) are plain text, typed as on the land certificate (UPID or
Adjudication ID): no format is enforced. Only a value of spaces alone is refused, on every
channel (web, ODK, file import, change requests); an empty value is left to the required rules."""
from pathlib import Path

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_cropsown_extension.register_domain.services import field_rules  # noqa: E402

META = Path(field_rules.__file__).resolve().parents[2] / "meta_data"


def issues(field, value):
    return [p.key for p in field_rules.clean_records([{field: value}]) if p.field == field]


@pytest.mark.parametrize("field", ["land_id", "cluster_land_id"])
@pytest.mark.parametrize("value", [
    "RN/10/06/026/09231", "rn/10/06/026/09231", "UPID 12345", "ADJ-0098", "Plot 13", "12", "OLD",
    "ደህ/10/06/026/09231", "  ADJ-0098 "])
def test_any_text_is_accepted(field, value):
    assert issues(field, value) == []


@pytest.mark.parametrize("field", ["land_id", "cluster_land_id"])
@pytest.mark.parametrize("value", [" ", "    ", "\t", " \n "])
def test_only_spaces_is_refused(field, value):
    assert issues(field, value) == ["validation_rule_land_id_blank"]


@pytest.mark.parametrize("value", ["", None])
def test_an_empty_land_id_is_left_to_the_required_rules(value):
    assert issues("land_id", value) == []


def test_a_prefixed_key_is_checked_too():
    problems = field_rules.clean_records([{"0c0343ca.land_id": "   "}])
    assert [(p.field, p.key) for p in problems] == [("land_id", "validation_rule_land_id_blank")]


def test_the_message():
    message = field_rules.explain(field_rules.Issue("cluster_land_id", "validation_rule_land_id_blank"))
    assert message == "Land ID (cluster): enter the ID from the land certificate."


def test_no_format_is_left_anywhere():
    assert not hasattr(field_rules, "LAND_ID_FORMAT") and not hasattr(field_rules, "LAND_ID_PREFIXES")
    sql = (META / "register-metadata/update_060_field_rules.sql").read_text(encoding="utf-8")
    assert "WHEN field IN ('land_id','cluster_land_id') THEN pattern:='\\S'; message_key:='validation_land_id';" in sql
    translations = (META / "translations_fields.sql").read_text(encoding="utf-8")
    assert '"validation_rule_land_id_blank": "{label}: enter the ID from the land certificate."' in translations
    assert '"validation_land_id": "Enter the ID from the land certificate."' in translations
    assert "RN or RC" not in sql + translations and "validation_rule_land_id_format" not in translations
