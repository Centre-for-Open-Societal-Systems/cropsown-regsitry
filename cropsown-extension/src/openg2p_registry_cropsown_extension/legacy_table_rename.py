"""Rename the Farmer-reference tables to their g2p_ names before the new code serves.

The statement lives in legacy_table_rename.sql (also copied to ci/migrations for a
manual run on a restored copy). It is idempotent, so it runs on every migration.
"""

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

SQL_PATH = Path(__file__).with_name("legacy_table_rename.sql")


async def rename_legacy_tables(engine: AsyncEngine) -> None:
    statement = SQL_PATH.read_text(encoding="utf-8")
    schema_map = (
        engine.sync_engine.get_execution_options().get("schema_translate_map") or {}
    )
    schema = schema_map.get(None)
    async with engine.begin() as connection:
        if schema:
            await connection.execute(
                text("SELECT set_config('search_path', :schema, true)"),
                {"schema": schema},
            )
        await connection.execute(text(statement))
