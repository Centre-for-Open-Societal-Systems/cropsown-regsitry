"""The five read-only performance figures on a Harvest row.

    Yield (kg per hectare)  = quantity harvested (kg) / area harvested (ha)
    Yield performance (%)   = quantity harvested / expected yield (Planning) x 100
    Land utilization rate   = actual crop area (Cultivation) / planned crop area (Planning)
    Seed productivity       = quantity harvested (kg) / actual seed quantity (Cultivation, kg)
    Fertilizer efficiency   = quantity harvested (kg) / actual fertilizer quantity (Cultivation, kg)

Quantities harvested and expected yield are entered in quintal (1 quintal = 100 kg);
areas in hectare; seed and fertilizer in kg. A cluster harvest row uses its cluster
quantity and area. A harvest row takes its Planning and Cultivation values from the
row on the same crop record with the same Land ID and crop (a crop record has one
production season, so the season matches too). A figure whose inputs are missing,
or that would divide by zero, is left blank.

The figures are recalculated for the whole crop record whenever its Harvest,
Planning or Cultivation rows are ingested or a change to them is approved, so a
later correction to Planning or Cultivation shows up on the harvest. Existing
records can be filled in once with (see harvest_backfill.py):

    python -m openg2p_registry_cropsown_extension.harvest_backfill --backfill
"""

import logging

from .domain_validation_utils import as_float

_logger = logging.getLogger("g2p-register-domain-service")

QUINTAL_TO_KG = 100.0
FIELDS = (
    "yield_kg_ha",
    "yield_performance_pct",
    "land_utilization_rate",
    "seed_productivity",
    "fertilizer_efficiency",
)


def _get(row, field):
    return row.get(field) if isinstance(row, dict) else getattr(row, field, None)


def _divide(numerator, denominator):
    """None when an input is missing or the denominator is zero (shown blank)."""
    n, d = as_float(numerator), as_float(denominator)
    if n is None or not d:
        return None
    return n / d


def _round(value, places=2):
    return None if value is None else round(value, places)


def harvested_quantity_and_area(harvest) -> tuple:
    """Independent rows use qty/area_harvested; cluster rows their cluster_* twins."""
    qty = as_float(_get(harvest, "qty_harvested"))
    area = as_float(_get(harvest, "area_harvested"))
    if qty is None and area is None:
        qty = as_float(_get(harvest, "cluster_qty_harvested"))
        area = as_float(_get(harvest, "cluster_area_harvested"))
    return qty, area


def yield_kg_ha(harvest):
    qty, area = harvested_quantity_and_area(harvest)
    return _round(_divide(None if qty is None else qty * QUINTAL_TO_KG, area))


def harvest_metrics(harvest, planning=None, cultivation=None) -> dict:
    qty, area = harvested_quantity_and_area(harvest)
    total_kg = None if qty is None else qty * QUINTAL_TO_KG
    planning = planning or {}
    cultivation = cultivation or {}
    # Both in quintal, so no conversion before the ratio.
    performance = _divide(qty, _get(planning, "expected_yield"))
    return {
        "yield_kg_ha": _round(_divide(total_kg, area)),
        "yield_performance_pct": _round(None if performance is None else performance * 100),
        "land_utilization_rate": _round(
            _divide(_get(cultivation, "actual_crop_area"), _get(planning, "planned_area"))
        ),
        "seed_productivity": _round(_divide(total_kg, _get(cultivation, "actual_seed_qty"))),
        "fertilizer_efficiency": _round(_divide(total_kg, _get(cultivation, "actual_fertilizer_qty"))),
    }


def _same(a, b) -> bool:
    return str(a or "").strip().upper() == str(b or "").strip().upper()


def matching_row(rows, harvest):
    """The row with the harvest's Land ID and crop; Land ID alone when the harvest
    names no crop (a cluster row). None when nothing matches."""
    land_id = str(_get(harvest, "land_id") or "").strip()
    if not land_id:
        return None
    same_land = [r for r in rows if str(_get(r, "land_id") or "").strip() == land_id]
    commodity = _get(harvest, "commodity")
    if commodity:
        return next((r for r in same_land if _same(_get(r, "commodity"), commodity)), None)
    return same_land[0] if same_land else None


async def refresh_harvest_metrics(session, crop_record_id) -> int:
    """Recalculate the figures on every active harvest row of one crop record."""
    if not crop_record_id:
        return 0
    from sqlalchemy import select

    from ..models import G2PRegisterCultivation, G2PRegisterHarvest, G2PRegisterPlanning

    async def active(model):
        result = await session.execute(
            select(model)
            .where(
                model.link_internal_record_id == str(crop_record_id),
                model.record_status == "ACTIVE",
            )
            .order_by(model.created_at.desc())
        )
        return result.scalars().all()

    harvests = await active(G2PRegisterHarvest)
    if not harvests:
        return 0
    plannings = await active(G2PRegisterPlanning)
    cultivations = await active(G2PRegisterCultivation)
    changed = 0
    for harvest in harvests:
        values = harvest_metrics(harvest, matching_row(plannings, harvest), matching_row(cultivations, harvest))
        for field, value in values.items():
            current = as_float(getattr(harvest, field, None))
            if current != value:
                setattr(harvest, field, value)
                changed += 1
    return changed


async def crop_record_id_of(session, record_id):
    """The crop record a change request or row belongs to: the id itself when it is
    a crop record, else the parent of the Harvest / Planning / Cultivation row."""
    if not record_id:
        return None
    from sqlalchemy import text

    found = await session.execute(
        text("SELECT 1 FROM g2p_register_crop_sowns WHERE internal_record_id = :rid"),
        {"rid": str(record_id)},
    )
    if found.fetchone():
        return str(record_id)
    for table in ("g2p_register_harvests", "g2p_register_plannings", "g2p_register_cultivations"):
        parent = await session.execute(
            text(f"SELECT link_internal_record_id FROM {table} WHERE internal_record_id = :rid"),
            {"rid": str(record_id)},
        )
        row = parent.fetchone()
        if row and row[0]:
            return str(row[0])
    return None


async def refresh_after_change(session, record_id) -> None:
    """Hook body for post_ingest / post_approve. Never blocks the save it follows:
    it runs in a savepoint, so a failure rolls back only the recalculation."""
    try:
        async with session.begin_nested():
            crop_record_id = await crop_record_id_of(session, record_id)
            await refresh_harvest_metrics(session, crop_record_id)
    except Exception:
        _logger.exception("Harvest figures not recalculated for record %s", record_id)


async def backfill(session) -> tuple[int, int]:
    """Recalculate every crop record that has an active harvest row."""
    from sqlalchemy import text

    result = await session.execute(
        text(
            "SELECT DISTINCT link_internal_record_id FROM g2p_register_harvests "
            "WHERE record_status = 'ACTIVE' AND link_internal_record_id IS NOT NULL"
        )
    )
    records = [row[0] for row in result.fetchall()]
    changed = 0
    for crop_record_id in records:
        changed += await refresh_harvest_metrics(session, crop_record_id)
    return len(records), changed


