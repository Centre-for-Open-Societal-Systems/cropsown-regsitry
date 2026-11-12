"""Stable-reference Crop identity mirrors through native approval/ingest hooks."""
from ...farmer_reference.projection import refresh_domain_on_ingest


def _models():
    from openg2p_registry_extensions.register_domain.models import G2PRegisterCropSown, G2PRegisterFarmer
    return G2PRegisterFarmer, G2PRegisterCropSown


async def refresh_crop_name_on_ingest(session, crop):
    farmer_model, _ = _models()
    return await refresh_domain_on_ingest(session, farmer_model, crop)


async def backfill_crop_addresses(session) -> tuple[int, int]:
    """Once, for records written before the Address came from the Farmer: copy each
    active crop record's address from its approved Farmer (see address_backfill.py).
    A Farmer without an address leaves its records as they are."""
    from sqlalchemy import select

    from ...farmer_reference.projection import _mirror_address

    farmer_model, crop_model = _models()
    crops = (await session.execute(select(crop_model).where(
        crop_model.record_status == "ACTIVE", crop_model.farmer_uuid.is_not(None)))).scalars().all()
    changed = 0
    for crop in crops:
        farmer = await session.get(farmer_model, crop.farmer_uuid)
        if farmer is not None and farmer.record_status == "ACTIVE" and _mirror_address(crop, farmer):
            crop.search_text = crop.get_search_text_fields()
            crop.record_name = crop.get_record_name_fields()
            changed += 1
    return len(crops), changed
