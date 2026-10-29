"""Estimated Crop Damage is stored as the number its Numeric(5, 2) column holds."""

import importlib

import pytest

pytest.importorskip("openg2p_registry_core")
module = importlib.import_module(
    "openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_infestation"
)
service = object.__new__(module.G2PRegisterDomainServiceInfestation)


@pytest.mark.parametrize(
    ("value", "stored"),
    [("12%", 12.0), (" 50 % ", 50.0), ("10.5", 10.5), (7, 7.0), ("0%", 0.0), ("", None), ("  ", None), (None, None)],
)
def test_damage_is_stored_as_a_number(value, stored):
    row = {"estimated_damage_pct": value}
    service._validate_estimated_damage(row)
    assert row["estimated_damage_pct"] == stored


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("101%", "between 0% and 100%"),
        ("-1", "must not be negative"),
        ("1000", "999.99 or less"),
        ("12 percent", "cannot contain letters"),
        ("1.2.3", "must be a number"),
    ],
)
def test_bad_damage_names_the_field(value, message):
    with pytest.raises(Exception) as failure:
        service._validate_estimated_damage({"estimated_damage_pct": value})
    assert message in str(failure.value)
