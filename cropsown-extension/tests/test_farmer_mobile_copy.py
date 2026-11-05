"""A farmer's mobile number copied from the Farmer Registry keeps its country code.

The Farmer Registry publishes the national number without its trunk 0
(912148121). Crop Sown showed that bare number on the Farmer tab; the copy is
now stored as +251912148121.
"""

import importlib

import pytest

p = importlib.import_module("openg2p_registry_cropsown_extension.farmer_reference.profile")


@pytest.mark.parametrize("value, stored", [
    ("912148121", "+251912148121"),
    ("712 148 121", "+251712148121"),
    ("251912148121", "+251912148121"),
    ("+251912148121", "+251912148121"),
    ("0912148121", "0912148121"),
    ("", ""),
    (None, None),
])
def test_copied_mobile_number_keeps_its_country_code(value, stored):
    assert p.local_profile({"mobile_number": value}) == {"mobile_number": stored}


def test_unrecognised_mobile_number_is_left_for_the_rule_to_refuse():
    assert p.local_profile({"mobile_number": "12345"}) == {"mobile_number": "12345"}
