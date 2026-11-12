"""Approved identity mirrors through native domain hooks, in their transaction.

The complete profile stays in the local Farmer reference. Only existing domain
identity/display columns and the farmer's address (the record's Address section)
are mirrored; plot/holding geography (the stage rows' own location) and business
fields are owned by the domain. This service never discovers or creates a relationship
from a mutable UID, a matching name, or a sibling submission.
"""
from sqlalchemy import select
from .profile import FarmerReferenceError, reference_identity, model_identity, normalize_farmer_id


async def _approved_farmer(session, farmer_model, reference_id):
    if not isinstance(reference_id, str) or not reference_id.strip():
        raise FarmerReferenceError("FARMER_REFERENCE_APPROVED_DEPENDENCY_REQUIRED")
    # Flush pending native approval fields before re-reading. The caller owns
    # commit/rollback; no nested independent commit may expose partial projection.
    await session.flush()
    farmer = (await session.execute(
        select(farmer_model).where(farmer_model.internal_record_id == reference_id)
        .with_for_update().execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if (farmer is None or farmer.record_status != "ACTIVE" or
            not farmer.last_approved_at or not farmer.last_approved_by):
        raise FarmerReferenceError("FARMER_REFERENCE_APPROVED_DEPENDENCY_REQUIRED")
    reference_identity(model_identity(farmer))
    return farmer


def _mirror(domain_row, farmer):
    if domain_row.farmer_uuid != farmer.internal_record_id:
        raise FarmerReferenceError("FARMER_REFERENCE_LINK_MISMATCH")
    farmer_id, uid = reference_identity(model_identity(farmer))
    if domain_row.farmer_id not in (None, ""):
        # A UID rotation on the same stable reference is allowed. A different
        # Farmer ID is an identity correction and cannot be silently relinked.
        existing_id = normalize_farmer_id(domain_row.farmer_id)
        if existing_id != farmer_id:
            raise FarmerReferenceError("FARMER_REFERENCE_LINK_IDENTITY_MISMATCH")
    parts = (farmer.first_name, farmer.middle_name, farmer.last_name)
    if any(value is not None and not isinstance(value, str) for value in parts):
        raise FarmerReferenceError("FARMER_REFERENCE_INVALID_PROFILE_VALUE")
    name = " ".join(value.strip() for value in parts if value and value.strip()) or None
    proposed = {"farmer_id": farmer_id, "fayda_fan_id": farmer.fayda_fan_id,
                "link_foundational_id": uid, "farmer_name": name}
    if hasattr(domain_row, "farmer_reference_status"):
        proposed["farmer_reference_status"] = "Farmer reference linked"
    fin = getattr(farmer, "fayda_fin", None)
    if fin and getattr(domain_row, "last_authentication_status", None) != "SUCCESS":
        proposed["fayda_fin"] = fin
    changed = any(getattr(domain_row, key) != value for key, value in proposed.items())
    for key, value in proposed.items():
        setattr(domain_row, key, value)
    changed = _mirror_address(domain_row, farmer) or changed
    if changed:
        domain_row.search_text = domain_row.get_search_text_fields()
        domain_row.record_name = domain_row.get_record_name_fields()
    return int(changed)


# The farmer's address, from the approved Farmer, shown in the record's Address
# section (zz-oan/97e_address_section.sql). Farmer column -> record column.
ADDRESS_FIELDS = {
    "region_id": "region", "zone_id": "zone", "woreda_id": "woreda", "kebele_id": "kebele",
    "region_name": "region_name", "zone_name": "zone_name",
    "woreda_name": "woreda_name", "kebele_name": "kebele_name",
    "latitude": "latitude", "longitude": "longitude",
}


def _mirror_address(domain_row, farmer) -> bool:
    """Copy the approved Farmer's address onto a record that has the same columns.

    Only when the Farmer has an address (a location in the hierarchy or a woreda),
    so a Farmer without one never clears the address a record already holds.
    """
    if not hasattr(domain_row, "woreda") or not hasattr(domain_row, "geo_lowest_level_value_id"):
        return False
    if not (getattr(farmer, "geo_lowest_level_value_id", None) or getattr(farmer, "woreda_id", None)):
        return False
    changed = False
    for source, target in ADDRESS_FIELDS.items():
        value = getattr(farmer, source, None)
        if target in ("latitude", "longitude") and value is not None:
            value = str(value)  # the Farmer keeps numbers, the record text
        if getattr(domain_row, target, None) != value:
            setattr(domain_row, target, value)
            changed = True
    lowest = getattr(farmer, "geo_lowest_level_value_id", None)
    if getattr(domain_row, "geo_lowest_level_value_id", None) != lowest:
        # Setting it makes the platform look the chain up; the Farmer's own chain
        # is written over it just below.
        domain_row.geo_lowest_level_value_id = lowest
        changed = True
    hierarchy = getattr(farmer, "geo_code_hierarchy_json", None)
    if hierarchy is not None and getattr(domain_row, "geo_code_hierarchy_json", None) != hierarchy:
        domain_row.geo_code_hierarchy_json = hierarchy
        changed = True
    return changed


async def refresh_domain_on_ingest(session, farmer_model, domain_row):
    """Block activation without the already approved stable local dependency.

    The native ingester invokes post_ingest before committing. A failure rolls
    back its new live row. Onboarding must supply farmer_uuid; a reviewed link
    migration must handle old records rather than this hook choosing an owner.
    """
    farmer = await _approved_farmer(session, farmer_model, domain_row.farmer_uuid)
    changed = _mirror(domain_row, farmer)
    await session.flush()
    return changed
