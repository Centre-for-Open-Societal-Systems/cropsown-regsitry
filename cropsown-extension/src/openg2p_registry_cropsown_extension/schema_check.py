"""Read-only deployment check of mapped domain columns using native SQLAlchemy."""
import asyncio
import importlib
import sys

from sqlalchemy import inspect


async def missing_columns(engine, models):
    tables = {model.__table__.key:model.__table__ for model in models}
    schema_map = engine.sync_engine.get_execution_options().get('schema_translate_map') or {}
    missing = []
    async with engine.connect() as connection:
        for table in sorted(tables.values(),key=lambda item:item.key):
            schema = schema_map.get(table.schema,table.schema)

            def columns(sync):
                inspector = inspect(sync)
                if not inspector.has_table(table.name,schema=schema):
                    return set()
                return {column['name'] for column in inspector.get_columns(table.name,schema=schema)}

            present = await connection.run_sync(columns)
            missing.extend(f'{table.key}.{column.name}' for column in table.columns if column.name not in present)
    return missing


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',required=True)
    parser.parse_args()
    module = __package__
    sys.modules.setdefault('openg2p_registry_extensions',importlib.import_module(module))
    importlib.import_module('openg2p_registry_staff_api.config').Settings.get_config()
    app = importlib.import_module(module+'.app')
    app.Initializer()
    from openg2p_fastapi_common.context import dbengine

    async def check():
        engine = dbengine.get()
        try:
            return await missing_columns(engine,[getattr(app.models,name) for name in app.MODEL_NAMES]+list(app.REFERENCE_MODELS))
        finally:
            await engine.dispose()

    missing = asyncio.run(check())
    if missing:
        sys.exit('Missing mapped domain columns: '+', '.join(missing))
    print('PASS: all mapped domain columns are present; database unchanged')


if __name__ == '__main__':
    main()
