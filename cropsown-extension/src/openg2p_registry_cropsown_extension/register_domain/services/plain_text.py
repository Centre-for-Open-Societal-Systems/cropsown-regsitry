"""Words for the Master Data codes a crop planning record name is built from.

A record name is stored and shown in lists, headers and tasks, so it reads
"Maize, Meher 2026" and not "CROP_MAIZE SEASON_MEHER". The name is built inside
the ORM event that saves a record, which cannot call Master Data, so the words
come from the code itself: the list prefix goes, underscores become spaces and
the first letter is a capital. Two commodity codes whose Master Data label
carries punctuation are listed below. The same rule is written in SQL in
meta_data/zz-oan/86_readable_lists.sql, which rewrites names stored before the
change; tests/test_readable_lists.py checks both give the same words.
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

CODE = re.compile(r"^[A-Z0-9]+(?:_[A-Z0-9]+)+$")
COMMODITY_PREFIXES = ("CROP_",)
SEASON_PREFIXES = ("CROP_SEASON_", "SEASON_")
COMMODITY_LABELS = {
    "CROP_MARJORAM_OREGANO": "Marjoram / oregano",
    "CROP_LEMON_SCENTED_EUCALYPTUS": "Lemon-scented eucalyptus",
}


def code_words(value, prefixes=()) -> str:
    """The words of a list code, or the text unchanged when it is not a code."""
    text = str(value or "").strip()
    if not CODE.match(text):
        return text
    for prefix in prefixes:
        if text.startswith(prefix) and len(text) > len(prefix):
            text = text[len(prefix):]
            break
    words = text.replace("_", " ").lower()
    return words[:1].upper() + words[1:]


def commodity_label(value) -> str:
    text = str(value or "").strip()
    return COMMODITY_LABELS.get(text) or code_words(text, COMMODITY_PREFIXES)


def season_label(value) -> str:
    return code_words(value, SEASON_PREFIXES)


def year_of(value) -> str:
    """The four-digit year of a date or a YYYY-MM-DD text, or nothing."""
    if isinstance(value, (date, datetime)):
        return str(value.year)
    match = re.match(r"^(\d{4})-\d{2}-\d{2}", str(value or "").strip())
    return match.group(1) if match else ""


def area_text(value) -> str:
    """An area without trailing zeros: 1.50 is 1.5 and 10 stays 10."""
    text = str(value if value is not None else "").strip()
    if not text:
        return ""
    try:
        number = Decimal(text)
    except InvalidOperation:
        return text
    return format(number.normalize(), "f")


def planning_record_name(payload: dict, extra=None) -> str:
    """Crop, then the season with its year, then the planned area in hectares."""
    season = season_label(payload.get("season"))
    year = year_of(payload.get("planned_date"))
    if season and year:
        season = f"{season} {year}"
    area = area_text(payload.get("planned_area"))
    parts = [commodity_label(payload.get("commodity")), season, f"{area} hectares" if area else ""]
    name = ", ".join(part for part in parts if part)
    lead = " ".join(str(item).strip() for item in (extra or []) if str(item).strip())
    return f"{lead} {name}".strip() if lead else name
