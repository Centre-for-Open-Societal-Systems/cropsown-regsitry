"""Table row limits, checked on the server on Next and submit (and for ODK, file import and
change requests) by comparing two fields of the same row: area limits, End date on or after
Start date, and Planned / Cultivation / Establishing date between Start date and End date."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def helpers():
    pytest.importorskip("openg2p_registry_core")
    from openg2p_registry_cropsown_extension.register_domain.services import domain_validation_utils
    from openg2p_registry_core.errors import G2PRegistryException
    return domain_validation_utils, G2PRegistryException


@pytest.mark.parametrize("start,end", [("2026-06-01", "2026-06-01"), ("2026-06-01", "2026-10-30"),
                                       ("2026-06-01", None), (None, "2026-06-01"), ("", "")])
def test_an_end_date_on_or_after_the_start_or_a_blank_date_passes(start, end):
    utils, _ = helpers()
    utils.validate_season_window({"start_gc": start, "end_gc": end})


def test_an_end_date_before_the_start_is_refused():
    utils, error_class = helpers()
    with pytest.raises(error_class) as error:
        utils.validate_season_window({"start_gc": "2026-06-01", "end_gc": "2026-05-31"})
    assert error.value.message == "End date cannot be earlier than Start date."


@pytest.mark.parametrize("day", ["2026-06-01", "2026-08-15", "2026-10-30", None, ""])
def test_an_establishing_date_inside_the_window_or_blank_passes(day):
    utils, _ = helpers()
    utils.validate_date_in_window({"start_gc": "2026-06-01", "end_gc": "2026-10-30", "establishing_date": day},
                                  "establishing_date", "Establishing date")
    utils.validate_date_in_window({"establishing_date": "2026-01-01"}, "establishing_date", "Establishing date")


@pytest.mark.parametrize("day", ["2026-05-31", "2026-10-31"])
def test_an_establishing_date_outside_the_window_is_refused(day):
    utils, error_class = helpers()
    with pytest.raises(error_class) as error:
        utils.validate_date_in_window({"start_gc": "2026-06-01", "end_gc": "2026-10-30", "establishing_date": day},
                                      "establishing_date", "Establishing date")
    assert error.value.message == "Establishing date must be between Start date and End date."


def test_not_more_than_compares_only_given_values():
    utils, error_class = helpers()
    message = "Area sown ({value} hectares) cannot be more than Total land area ({limit} hectares)."
    for record in ({"area_sown": 2, "land_area": 2}, {"area_sown": 9, "land_area": None}, {"area_sown": None, "land_area": 1},
                   {"area_sown": 9, "land_area": 0}):
        utils.validate_not_more_than(record, "area_sown", "land_area", message)
    with pytest.raises(error_class) as error:
        utils.validate_not_more_than({"area_sown": "2.5", "land_area": "2"}, "area_sown", "land_area", message)
    assert error.value.message == "Area sown (2.5 hectares) cannot be more than Total land area (2 hectares)."


@pytest.mark.parametrize("module,method", [
    ("g2p_register_domain_service_planning", "self._validate_season_window(record)"),
    ("g2p_register_domain_service_cultivation", "validate_season_window(record)"),
    ("g2p_register_domain_service_cluster", "validate_season_window(record)"),
    ("g2p_register_domain_service_cultivation_cluster", "validate_season_window(record)"),
    ("g2p_register_domain_service_cluster", 'validate_date_in_window(record, "establishing_date", "Establishing date")'),
    ("g2p_register_domain_service_cultivation_cluster", 'validate_date_in_window(record, "establishing_date", "Establishing date")'),
    ("g2p_register_domain_service_sowing", 'validate_not_more_than(record, "area_sown", "land_area",'),
    ("g2p_register_domain_service_sowing", 'validate_not_more_than(record, "cluster_area_sown", "cluster_area_hectare",'),
    ("g2p_register_domain_service_harvest", 'validate_not_more_than(record, "area_harvested", "land_area",'),
    ("g2p_register_domain_service_harvest", "self._validate_cluster_disposal_quantities(record)"),
])
def test_each_service_runs_its_rule_on_save_and_submit(module, method):
    source = (ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services"
              / f"{module}.py").read_text(encoding="utf-8")
    body = source.split("async def validate_domain_attributes")[1].split("\n    def ")[0].split("\n    async def ")[0]
    assert method in body


def test_land_area_rules_skip_a_yes_row():
    for module in ("g2p_register_domain_service_sowing", "g2p_register_domain_service_harvest"):
        source = (ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services"
                  / f"{module}.py").read_text(encoding="utf-8")
        assert 'if as_bool(record.get("is_land_recorded")) is not True:' in source


def test_clustered_harvest_quantities():
    pytest.importorskip("openg2p_registry_core")
    from openg2p_registry_core.errors import G2PRegistryException
    from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_harvest import (
        G2PRegisterDomainServiceHarvest,
    )
    service = G2PRegisterDomainServiceHarvest()
    service._validate_cluster_disposal_quantities({"cluster_qty_harvested": 10, "cluster_qty_stored": 6, "cluster_qty_sold": 4})
    service._validate_cluster_disposal_quantities({"cluster_qty_harvested": None, "cluster_qty_stored": 6})
    with pytest.raises(G2PRegistryException, match=r"\(cluster\) must not be more than the quantity harvested \(cluster\)"):
        service._validate_cluster_disposal_quantities({"cluster_qty_harvested": 10, "cluster_qty_stored": 7, "cluster_qty_sold": 4})


# --- an area needs the total area of its row ------------------------------------------------

@pytest.mark.parametrize("module,cls,method,area_field,message", [
    ("g2p_register_domain_service_planning", "G2PRegisterDomainServicePlanning", "_validate_planned_area",
     "planned_area", "Enter Total land area first: Planned crop area needs Total land area."),
    ("g2p_register_domain_service_cultivation", "G2PRegisterDomainServiceCultivation", "_validate_actual_crop_area",
     "actual_crop_area", "Enter Total land area first: Actual crop area needs Total land area."),
])
def test_an_area_needs_total_land_area(module, cls, method, area_field, message):
    pytest.importorskip("openg2p_registry_core")
    import importlib
    from openg2p_registry_core.errors import G2PRegistryException
    service = getattr(importlib.import_module(
        f"openg2p_registry_cropsown_extension.register_domain.services.{module}"), cls)()
    check = getattr(service, method)
    check({area_field: 2, "land_area": 3})
    check({area_field: None, "land_area": None})  # no area: nothing needed
    for blank in (None, "", "  "):
        with pytest.raises(G2PRegistryException) as error:
            check({area_field: 2, "land_area": blank})
        assert error.value.message == message


def test_area_sown_cluster_needs_total_cultivated_area_on_a_clustered_row():
    source = (ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services"
              / "g2p_register_domain_service_sowing.py").read_text(encoding="utf-8")
    body = source.split("async def validate_domain_attributes")[1].split("\n    def ")[0].split("\n    async def ")[0]
    assert ('if clustered and not is_blank(record.get("cluster_area_sown")) and is_blank(record.get("cluster_area_hectare")):'
            in body)
    assert 'validation_error("Enter Total cultivated area first: Area sown, cluster needs Total cultivated area.")' in body
