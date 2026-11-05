"""The form dropdowns save ETH-OAN pack codes, so the schemas and the DCI mapping must accept and send those codes."""
from pathlib import Path
import ast

PACKAGE = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension"


def members(name):
    tree = ast.parse((PACKAGE / "register_domain/models/enums.py").read_text(encoding="utf-8"))
    found = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
    return {item.value.value for item in found.body if isinstance(item, ast.Assign)}


def test_growth_stage_accepts_the_pack_codes():
    assert {"GS_EMERGENCE", "GS_VEGETATIVE", "GS_FLOWERING", "GS_GRAIN_FILLING", "GS_MATURITY"} <= members("GrowthStageEnum")


def test_severity_accepts_the_pack_codes():
    assert {"SEV_LOW", "SEV_MEDIUM", "SEV_HIGH"} <= members("SeverityLevelEnum")


def test_dci_mapping_falls_back_to_pack_codes():
    template = (PACKAGE / "templates/dci_to_openg2p_cropsown.json.j2").read_text(encoding="utf-8")
    assert '{% set zone = "AEZ_WEYNA_DEGA" %}' in template
    assert '{% set severity = "SEV_LOW" %}' in template
