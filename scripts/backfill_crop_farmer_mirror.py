"""Re-mirror one Crop Sown record's Farmer identity from its Farmer reference.

The post-ingest hook did not run for records ingested while the domain factory
module was missing, so those records have an empty farmer_name and
link_foundational_id, and no farmer name in search_text. This script runs the
same mirror the hook runs (farmer_reference.projection) for a single record:
farmer_name, link_foundational_id, farmer_id, fayda_fan_id, search_text and
record_name. It is idempotent: a record that is already mirrored is left alone.

Default is a dry run that reports what would change. Pass --apply to write.

Run inside the celery or staff-api image of this registry, where the platform
and this extension are installed:

    DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME \
        python scripts/backfill_crop_farmer_mirror.py --record-prefix dafd4851
    ... --apply

DATABASE_URL is read from the environment only.
"""
import argparse
import asyncio
import importlib
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

PACKAGE = "openg2p_registry_cropsown_extension"
MIRRORED = ("farmer_id", "fayda_fan_id", "link_foundational_id", "farmer_name", "search_text", "record_name")


def load_models():
    # The platform publishes the selected extension under this alias; the
    # extension's own import finder keeps one copy of the mapped classes.
    package = importlib.import_module(PACKAGE)
    sys.modules.setdefault("openg2p_registry_extensions", package)
    return importlib.import_module("openg2p_registry_extensions.register_domain.models")


class DryRun(Exception):
    """Raised inside the transaction to roll it back."""


async def mirror(session, models, prefix):
    projection = importlib.import_module(PACKAGE + ".farmer_reference.projection")
    rows = (await session.execute(select(models.G2PRegisterCropSown).where(
        models.G2PRegisterCropSown.internal_record_id.like(prefix + "%")).with_for_update())).scalars().all()
    if len(rows) != 1:
        raise SystemExit(f"expected exactly one Crop Sown record starting {prefix}, found {len(rows)}")
    crop = rows[0]
    before = {field: getattr(crop, field, None) for field in MIRRORED}
    changed = await projection.refresh_domain_on_ingest(session, models.G2PRegisterFarmer, crop)
    print(f"record {crop.internal_record_id} ({crop.functional_record_id})")
    for field in MIRRORED:
        marker = "->" if before[field] != getattr(crop, field, None) else "=="
        print(f"  {field}: {before[field]!r} {marker} {getattr(crop, field, None)!r}")
    if not changed:
        print("already mirrored; nothing to do")
    return changed


async def run(prefix, apply):
    models = load_models()
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            try:
                async with session.begin():
                    await mirror(session, models, prefix)
                    if not apply:
                        raise DryRun
                print("applied")
            except DryRun:
                print("dry run: nothing written (pass --apply to write)")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--record-prefix", default="dafd4851", help="start of the record's internal_record_id")
    parser.add_argument("--apply", action="store_true", help="write the change (default is a dry run)")
    arguments = parser.parse_args()
    asyncio.run(run(arguments.record_prefix, arguments.apply))
