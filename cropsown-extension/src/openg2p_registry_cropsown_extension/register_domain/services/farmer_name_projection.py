"""Keep the current Crop Sown name aligned with its approved Farmer reference."""
import logging
import re

from sqlalchemy import func, select, text

_logger = logging.getLogger("g2p-register-domain-service")


def _models():
    # Reuse the platform's initialized model namespace; do not load tables twice.
    from openg2p_registry_extensions.register_domain.models import G2PRegisterCropSown, G2PRegisterFarmer
    return G2PRegisterFarmer, G2PRegisterCropSown


def _identity(farmer_id, fan):
    farmer_id = str(farmer_id or "").strip()
    fan = "".join(str(fan or "").split())
    if re.fullmatch(r"FR-[0-9]{12}", farmer_id) and re.fullmatch(r"[0-9]{16}", fan):
        return farmer_id, fan
    return None


async def _lock(session, pair):
    # Both orders converge: reference approval before or after Crop ingestion.
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                              {"key": "crop-farmer-name:" + ":".join(pair)})


async def _reference(session, farmer_model, pair):
    rows = (await session.execute(select(farmer_model).where(
        func.trim(farmer_model.functional_record_id) == pair[0],
        farmer_model.record_status == "ACTIVE").execution_options(populate_existing=True))).scalars().all()
    matches = [r for r in rows if _identity(r.functional_record_id, r.fayda_fan_id) == pair
               and r.last_approved_at and r.last_approved_by
               and (not r.farmer_id or str(r.farmer_id).strip() == pair[0])]
    return matches[0] if len(matches) == 1 else None


def _apply(crop, farmer):
    name = " ".join(str(p).strip() for p in (farmer.first_name, farmer.middle_name, farmer.last_name) if p and str(p).strip())
    if not name or crop.farmer_name == name:
        return 0
    crop.farmer_name = name
    crop.search_text = crop.get_search_text_fields()
    return 1


async def refresh_crop_names_from_farmer(session, farmer_internal_id):
    """Project an approved reference into matching ACTIVE Crop Sown records."""
    farmer_model, crop_model = _models()
    farmer = await session.get(farmer_model, farmer_internal_id)
    pair = _identity(farmer.functional_record_id, farmer.fayda_fan_id) if farmer else None
    if not pair:
        return 0
    await session.flush()
    await _lock(session, pair)
    farmer = await _reference(session, farmer_model, pair)
    if farmer is None or farmer.internal_record_id != farmer_internal_id:
        return 0
    crops = (await session.execute(select(crop_model).where(
        func.trim(crop_model.farmer_id) == pair[0], crop_model.record_status == "ACTIVE")
        .order_by(crop_model.internal_record_id).with_for_update())).scalars().all()
    changed = sum(_apply(crop, farmer) for crop in crops if _identity(crop.farmer_id, crop.fayda_fan_id) == pair)
    await session.flush()
    _logger.info("Approved Farmer name projected into %d matching Crop Sown records", changed)
    return changed


async def refresh_crop_name_on_ingest(session, crop):
    """Use the latest approved reference when an older intake is ingested."""
    pair = _identity(crop.farmer_id, crop.fayda_fan_id)
    if not pair or crop.record_status != "ACTIVE":
        return 0
    farmer_model, _ = _models()
    await _lock(session, pair)
    farmer = await _reference(session, farmer_model, pair)
    changed = _apply(crop, farmer) if farmer else 0
    await session.flush()
    return changed
