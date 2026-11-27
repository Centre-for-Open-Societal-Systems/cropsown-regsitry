"""The Actual cultivation date, and the Cultivation cluster date, may be earlier than the Planned
date in Planning: no check compares them any more (web, ODK, file import, change requests). The
dates stay checked against the row's own Start and End date."""
from pathlib import Path

SERVICES = (Path(__file__).resolve().parents[1]
            / "src/openg2p_registry_cropsown_extension/register_domain/services")


def active_lines(name: str) -> str:
    """The file's code without its comments."""
    return "\n".join(line for line in (SERVICES / name).read_text(encoding="utf-8").splitlines()
                     if not line.strip().startswith("#"))


def test_cultivation_no_longer_compares_with_the_planned_date():
    code = active_lines("g2p_register_domain_service_cultivation.py")
    for retired in ("_validate_date_after_planning", "_resolve_planning_date", "validate_cultivation_against_planning"):
        assert retired not in code, retired
    # the row's own dates still are
    assert 'await self._validate_date_in_season_enhanced(record, "actual_cultivation_date", session)' in code
    assert "validate_season_window(record)" in code


def test_cultivation_cluster_no_longer_compares_with_the_planning_date():
    code = active_lines("g2p_register_domain_service_cultivation_cluster.py")
    assert "validate_cultivation_cluster_against_planning" not in code
    assert "validate_season_window(record)" in code


def test_the_retired_checks_are_not_defined_any_more():
    code = active_lines("cropsown_intake_validation_service.py")
    for retired in ("async def validate_cultivation_against_planning",
                    "async def validate_cultivation_cluster_against_planning"):
        assert retired not in code
    # Sowing is still checked against Cultivation and Planning
    assert "async def validate_sowing_against_cultivation" in code
