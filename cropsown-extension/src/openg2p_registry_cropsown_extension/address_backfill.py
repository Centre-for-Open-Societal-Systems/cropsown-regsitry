"""Fill the Address of existing crop records from their approved Farmer, once.

    python -m openg2p_registry_cropsown_extension.address_backfill --backfill

Run it in the staff-portal-api container after deploying the Address change
(farmer_reference/projection.py, zz-oan/97e_address_section.sql). New records
get the address when they are written; this covers the ones written before. It
is safe to run again: an unchanged address is not rewritten, and a Farmer
without an address leaves its records as they are.

It sits at the package top level, like schema_check.py, so the staff API settings
are loaded before the register domain services are imported.
"""
import asyncio
import importlib
import sys


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backfill", action="store_true", required=True)
    parser.parse_args()
    module = __package__
    sys.modules.setdefault("openg2p_registry_extensions", importlib.import_module(module))
    importlib.import_module("openg2p_registry_staff_api.config").Settings.get_config()
    app = importlib.import_module(module + ".app")
    app.Initializer()
    from openg2p_fastapi_common.context import dbengine
    from sqlalchemy.ext.asyncio import async_sessionmaker

    projection = importlib.import_module(module + ".register_domain.services.farmer_name_projection")

    async def run():
        engine = dbengine.get()
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                result = await projection.backfill_crop_addresses(session)
                await session.commit()
                return result
        finally:
            await engine.dispose()

    records, changed = asyncio.run(run())
    print(f"Address checked on {records} crop record(s); {changed} updated from their Farmer.")


if __name__ == "__main__":
    main()
