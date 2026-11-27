"""Guard: every consent scope id the repository names is one the partner API can release.

At the pinned platform the partner API clamps a DCI search response to the consent's effective data scopes by
matching them against the TOP-LEVEL keys of the rendered search response (openg2p_registry_partner_api,
G2PDciService._clamp_record_fields): any other scope name matches nothing and releases nothing, without an error.
So a valid scope id is a top-level key of templates/openg2p_cropsown_to_dci.json.j2, the CropSown register's
outgoing DCI template (meta_data/registry-outbound-messages-templates/outgoing_templates.sql).

The scope ids named here are the sanity DCI e2e's consented and denied scopes, helm values
registry.sanity.dataScopes / deniedScopes, which the platform chart passes to the sanity image as
SANITY_DATA_SCOPES / SANITY_DENIED_SCOPES. Crop ships no data-scopes catalogue of its own.
"""

import json
from pathlib import Path

import yaml
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension"
VALUES = ROOT / "helm/openg2p-cropsown-registry/values.yaml"
TEMPLATE = "openg2p_cropsown_to_dci.json.j2"


def releasable_scopes():
    template = (EXT / "templates" / TEMPLATE).read_text(encoding="utf-8")
    return set(json.loads(Environment().from_string(template).render()))


def named_scopes():
    """(where, scope id) for every consent scope id the repository names."""
    sanity = yaml.safe_load(VALUES.read_text(encoding="utf-8"))["registry"]["sanity"]
    for key in ("dataScopes", "deniedScopes"):
        for scope in str(sanity.get(key) or "").split(","):
            if scope.strip():
                yield f"values.yaml registry.sanity.{key}", scope.strip()


def test_consent_scope_ids_are_releasable():
    assert TEMPLATE in (EXT / "meta_data/registry-outbound-messages-templates/outgoing_templates.sql").read_text()
    releasable = releasable_scopes()
    assert {"crop_sown_details", "farm_details"} <= releasable, releasable
    named = set(named_scopes())
    assert ("values.yaml registry.sanity.dataScopes", "crop_sown_details") in named
    invalid = sorted((where, scope) for where, scope in named if scope not in releasable)
    assert not invalid, invalid
