"""Guard: every field name the metadata, templates and reporting views use is a column of the model.

A field name that does not match a column fails silently: the platform saves nothing for a widget bound to a
missing column, a search or filter on it finds nothing, and a reporting view breaks only when it is refreshed in
a cluster. This test reads the files statically, so it needs no database or platform image and runs on every push
in under a second. It is the base the other guard tests (test_search_text.py) read the model from.

The model's columns are read from source with ast, without importing it:
  * the crop sown extension's mixins (register_domain/models/*.py)
  * the platform base classes the registers inherit from (CORE_COLUMNS below)
"""

import ast
import re
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension"
MODELS = EXT / "register_domain/models"

# The platform base classes' columns (openg2p_registry_core.models, g2p_register.py) at the pinned platform version.
# When scripts/bump-rp-version.sh moves the pin, compare these with the new version's core models and update
# CORE_VERSION. rc.614 and rc.625 have the same core models.
CORE_VERSION = "1.2.2-rc.614"
CORE_COLUMNS = {
    "G2PRegister": {
        "internal_record_id", "functional_record_id", "link_internal_record_id", "link_foundational_id",
        "record_name", "record_image_document_id", "created_by", "created_at", "last_approved_at",
        "last_approved_by", "search_text", "record_status", "record_status_reason"},
    "G2PGeo": {
        "latitude", "longitude", "altitude", "plus_code", "address_line_1", "address_line_2", "postal_code",
        "country_code", "geo_lowest_level_value_id", "geo_code_hierarchy_json"},
}


@cache
def models():
    """{register mnemonic: columns} and {table name: register mnemonic}, read from the model source."""
    mixins, registers, tables = {}, {}, {}
    for path in sorted(MODELS.glob("*.py")):
        for node in ast.parse(path.read_text()).body:
            if not isinstance(node, ast.ClassDef):
                continue
            columns = {s.target.id for s in node.body if isinstance(s, ast.AnnAssign)
                       and isinstance(s.value, ast.Call) and getattr(s.value.func, "id", None) == "mapped_column"}
            bases = [ast.unparse(b) for b in node.bases]
            if not bases:
                mixins[node.name] = columns
            elif node.name.startswith("G2PRegister") and not node.name.startswith("G2PRegisterHistory"):
                mnemonic = node.name.removeprefix("G2PRegister")
                registers[mnemonic] = columns.union(*(CORE_COLUMNS.get(b, mixins.get(b, set())) for b in bases))
                for s in node.body:
                    if isinstance(s, ast.Assign) and getattr(s.targets[0], "id", None) == "__tablename__":
                        tables[s.value.value] = mnemonic
    return registers, tables


def columns(mnemonic):
    return models()[0][mnemonic]


def test_core_columns_follow_the_platform_pin():
    pin = re.search(r"^ARG RP_VERSION=(\S+)$", (ROOT / "docker/staff-api/Dockerfile").read_text(), re.M)
    assert pin and pin.group(1) == CORE_VERSION, "Platform pin moved: re-check CORE_COLUMNS against its core models"


def test_model_source_yields_every_register():
    registers, tables = models()
    definitions = set(re.findall(r"\('[0-9a-f-]+','([A-Za-z]+)'", "".join(
        (EXT / "meta_data/register-metadata" / name).read_text()
        for name in ("g2p_register_definitions.sql", "update_020_farmer_register.sql"))))
    assert set(registers) == definitions == {
        "Farmer", "CropSown", "Planning", "Cultivation", "Sowing", "Production", "Harvest", "Infestation",
        "Cluster", "CultivationCluster"}
    assert {"g2p_register_farmers", "g2p_register_harvests"} <= set(tables)
    assert {"internal_record_id", "fayda_fan_id", "latitude", "search_text"} <= columns("Farmer")
