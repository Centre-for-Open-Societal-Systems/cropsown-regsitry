from datetime import date, datetime

from openg2p_registry_core.errors import G2PRegistryErrorCodes, G2PRegistryException


def validation_error(message: str) -> None:
    raise G2PRegistryException(
        code=G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[1],
        message=message,
    )


def parse_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def as_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_bool(value) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return bool(value)


def is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def validate_alphabetical_name(value, field_name: str) -> None:
    if is_blank(value):
        return
    import re
    if not re.match(r"^[a-zA-Z\s]+$", str(value)):
        validation_error(f"{field_name} must contain only alphabetical characters and spaces")


def validate_mobile_number(value, field_name: str) -> None:
    if is_blank(value):
        return
    import re
    # Ethiopian mobile numbers: +251 or 0 prefix, then 7/9, then 8 digits
    # (e.g. +251911234567 or 0911234567).
    if not re.match(r"^(\+251[79]\d{8}|0[79]\d{8})$", str(value).strip()):
        validation_error(
            f"{field_name} must be a valid Ethiopian mobile number "
            f"(e.g. +251911234567 or 0911234567)"
        )


def validate_land_id(value, field_name: str = "Land ID") -> None:
    if is_blank(value):
        return
    if " " in str(value):
        validation_error(f"{field_name} must not contain spaces or gaps (e.g. '12345')")





def get_attribute_variants(value, prefix: str = "") -> list[str]:
    if not value or not str(value).strip():
        return []
    v_str = str(value).strip()
    clean = v_str
    for p in ("CROP_SEASON_", "CROP_COMMODITY_", "CROP_VARIETY_", "CROP_CATEGORY_"):
        clean = clean.replace(p, "")
    clean = clean.strip().upper()
    variants = {v_str, clean, v_str.upper(), v_str.lower(), clean.capitalize()}
    if prefix:
        variants.add(f"{prefix}_{clean}")
    return [v for v in variants if v]


async def resolve_production_season(record: dict, session) -> str | None:
    prod_season = (
        record.get("production_season")
        or record.get("6b06a95a-9a6c-5a33-a33d-c1625716c59c.production_season")
    )
    if prod_season:
        return prod_season

    submission_id = record.get("submission_id")
    if session and submission_id:
        from sqlalchemy import text
        res_hdr = await session.execute(
            text("SELECT production_season FROM g2p_intake_form_crop_sowns WHERE submission_id = :sub_id"),
            {"sub_id": submission_id}
        )
        row_hdr = res_hdr.fetchone()
        if row_hdr and row_hdr[0]:
            return row_hdr[0]

    internal_id = (
        record.get("link_internal_record_id")
        or record.get("internal_record_id")
        or record.get("record_id")
    )
    if session and internal_id:
        from sqlalchemy import text
        res_reg = await session.execute(
            text("SELECT production_season FROM g2p_register_crop_sowns WHERE internal_record_id = :rec_id"),
            {"rec_id": str(internal_id)}
        )
        row_reg = res_reg.fetchone()
        if row_reg and row_reg[0]:
            return row_reg[0]

    return None

