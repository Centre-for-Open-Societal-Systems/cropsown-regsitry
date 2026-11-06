"""Deployment configuration; private material is read only from mounted files."""
from dataclasses import fields
import json
import os
from pathlib import Path

import logging

from .lookup import FarmerLookup, LookupConfig, RecordContract
from .profile import FarmerReferenceError, SOURCE_TO_LOCAL_FIELDS


_logger = logging.getLogger("oan-farmer-reference-configuration")
SETTING_PREFIX = "REGISTRY_FARMER_REFERENCE_"
# Read for one release so a running deployment keeps working until its values
# switch to the new names; the fallback is removed afterwards.
LEGACY_SETTING_PREFIX = "COSS_FARMER_"
_legacy_warned = False


def setting(name, default=None):
    """The one place the Farmer-reference settings are read from the environment.

    REGISTRY_FARMER_REFERENCE_<name> wins; COSS_FARMER_<name> is the fallback and
    logs a single warning per process when it is the only one set.
    """
    global _legacy_warned
    value = os.environ.get(SETTING_PREFIX + name)
    if value is not None:
        return value
    value = os.environ.get(LEGACY_SETTING_PREFIX + name)
    if value is not None:
        if not _legacy_warned:
            _legacy_warned = True
            _logger.warning("Farmer-reference settings are read from %s* names (first seen: %s); "
                            "rename them to %s* before the fallback is removed",
                            LEGACY_SETTING_PREFIX, LEGACY_SETTING_PREFIX + name, SETTING_PREFIX)
        return value
    return default


def configured_lookup():
    def required(name):
        value = (setting(name) or "").strip()
        if not value:
            raise FarmerReferenceError("FARMER_REFERENCE_LOOKUP_CONFIGURATION_REQUIRED")
        return value
    try:
        contract_data = json.loads(Path(required("RECORD_CONTRACT_FILE")).read_text(encoding="utf-8"))
        if (not isinstance(contract_data, dict) or set(contract_data) - {field.name for field in fields(RecordContract)} or
                set(contract_data.get("profile_paths", {})) - set(SOURCE_TO_LOCAL_FIELDS)):
            raise ValueError
        contract = RecordContract(**contract_data)
        paths = [contract.source_id, contract.farmer_id, contract.uid, contract.fin, contract.uid_query_field, contract.fin_query_field, contract.approved_at, contract.status, contract.source_query_field,
                 *contract.profile_paths.values(), *([contract.photo] if contract.photo is not None else [])]
        if not all(isinstance(path, str) and path and all(path.split(".")) for path in paths):
            raise ValueError
        config = LookupConfig(url=required("DCI_URL"), sender_id=required("SENDER_ID"),
            source_id=required("SOURCE_ID"), signing_key=Path(required("SIGNING_KEY_FILE")).read_text(),
            signing_kid=required("SIGNING_KID"), source_public_key=Path(required("SOURCE_PUBLIC_KEY_FILE")).read_text(),
            source_kid=required("SOURCE_KID"), consent_audience=required("CONSENT_AUDIENCE"),
            consent_controller=required("CONSENT_CONTROLLER"), consent_purpose=required("CONSENT_PURPOSE"),
            consent_scopes=tuple(value.strip() for value in required("CONSENT_SCOPES").split(",") if value.strip()),
            algorithm=setting("SIGNING_ALGORITHM", "RS256"),
            source_algorithm=setting("SOURCE_ALGORITHM", "RS256"))
        return FarmerLookup(config, contract)
    except (OSError, ValueError, TypeError, AttributeError):
        raise FarmerReferenceError("FARMER_REFERENCE_LOOKUP_CONFIGURATION_REQUIRED") from None
