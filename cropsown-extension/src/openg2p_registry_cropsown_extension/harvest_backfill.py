"""Fill in the Harvest performance figures on existing crop records, once.

    python -m openg2p_registry_cropsown_extension.harvest_backfill --backfill

Run it in the staff-portal-api container after deploying the harvest_metrics
change. It recalculates the five figures (register_domain/services/
harvest_metrics.py) on every crop record that has an active harvest row, and is
safe to run again: an unchanged figure is not rewritten.

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

    harvest_metrics = importlib.import_module(module + ".register_domain.services.harvest_metrics")

    async def run():
        engine = dbengine.get()
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                result = await harvest_metrics.backfill(session)
                await session.commit()
                return result
        finally:
            await engine.dispose()

    records, changed = asyncio.run(run())
    print(f"Harvest figures recalculated on {records} crop record(s); {changed} value(s) changed.")


if __name__ == "__main__":
    main()
