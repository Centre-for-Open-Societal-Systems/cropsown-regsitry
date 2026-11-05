"""The Farmer-reference tables move from their old names to g2p_ names, twice-safe."""

import importlib
import os
import re
import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PACKAGE = os.environ.get(
    "REGISTRY_EXTENSION_MODULE", "openg2p_registry_cropsown_extension"
)
rename = importlib.import_module(PACKAGE + ".legacy_table_rename")
ROOT = Path(rename.__file__).parent
REPO = ROOT.parents[2].parent

PAIRS = {
    "coss_farmer_references": "g2p_farmer_references",
    "coss_farmer_reference_requests": "g2p_farmer_reference_requests",
    "coss_farmer_submission_dependencies": "g2p_farmer_submission_dependencies",
    "coss_farmer_workflow_outbox": "g2p_farmer_reference_awe_outbox",
    "coss_farmer_pending_lookups": "g2p_farmer_pending_lookups",
    "coss_approval_binding_archive": "g2p_approval_binding_archive",
}


class RenameStatementTests(unittest.TestCase):
    def test_every_orm_table_is_in_the_rename_list(self):
        models = (ROOT / "farmer_reference" / "models.py").read_text(encoding="utf-8")
        tables = set(re.findall(r'__tablename__ = "([a-z0-9_]+)"', models))
        self.assertEqual(tables, set(PAIRS.values()))
        sql = rename.SQL_PATH.read_text(encoding="utf-8")
        for old, new in PAIRS.items():
            self.assertIn(f"'{old}', '{new}'", sql)

    def test_the_manual_migration_is_the_packaged_statement(self):
        manual = REPO / "ci/migrations/20261106_rename_legacy_tables_to_g2p.sql"
        if not manual.is_file():
            self.skipTest("repository checkout not mounted")
        self.assertEqual(
            manual.read_text(encoding="utf-8"),
            rename.SQL_PATH.read_text(encoding="utf-8"),
        )

    def test_nothing_is_dropped_or_deleted(self):
        sql = rename.SQL_PATH.read_text(encoding="utf-8").upper()
        for word in ("DROP ", "DELETE ", "TRUNCATE", "CREATE TABLE"):
            self.assertNotIn(word, sql)


@unittest.skipUnless(
    os.environ.get("FARMER_TEST_DATABASE_URL"), "Requires owned disposable PostgreSQL"
)
class RenameOnPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.url = os.environ["FARMER_TEST_DATABASE_URL"]
        self.assertTrue(self.url.startswith("postgresql+asyncpg://"))
        self.schema = "oan_rename_test_" + uuid4().hex
        admin = create_async_engine(self.url)
        async with admin.begin() as conn:
            await conn.execute(text('CREATE SCHEMA "' + self.schema + '"'))
        await admin.dispose()
        self.engine = create_async_engine(
            self.url, execution_options={"schema_translate_map": {None: self.schema}}
        )

    async def asyncTearDown(self):
        await self.engine.dispose()
        assert re.fullmatch("oan_rename_test_[0-9a-f]{32}", self.schema)
        admin = create_async_engine(self.url)
        async with admin.begin() as conn:
            await conn.execute(text('DROP SCHEMA "' + self.schema + '" CASCADE'))
        await admin.dispose()

    async def run_sql(self, statements):
        async with self.engine.connect() as conn:
            await conn.execute(text(f'SET search_path TO "{self.schema}"'))
            for statement in statements:
                await conn.execute(text(statement))
            await conn.commit()

    async def create_old_tables(self):
        await self.run_sql(
            [
                "CREATE TABLE coss_farmer_references (reference_id varchar PRIMARY KEY, "
                "farmer_id varchar NOT NULL, UNIQUE (farmer_id))",
                "CREATE TABLE coss_farmer_reference_requests (request_id varchar PRIMARY KEY, "
                "reference_id varchar NOT NULL REFERENCES coss_farmer_references (reference_id))",
                "CREATE INDEX ix_coss_farmer_reference_requests_reference_id "
                "ON coss_farmer_reference_requests (reference_id)",
                "CREATE TABLE coss_farmer_submission_dependencies (submission_id varchar PRIMARY KEY, "
                "reference_id varchar NOT NULL REFERENCES coss_farmer_references (reference_id))",
                "CREATE TABLE coss_farmer_workflow_outbox (native_cr_id varchar PRIMARY KEY, "
                "request_id varchar NOT NULL UNIQUE REFERENCES coss_farmer_reference_requests (request_id))",
                "CREATE TABLE coss_farmer_pending_lookups (submission_id varchar PRIMARY KEY, "
                "state varchar NOT NULL)",
                "CREATE INDEX ix_coss_farmer_pending_lookups_state ON coss_farmer_pending_lookups (state)",
                "CREATE TABLE coss_approval_binding_archive (binding_id varchar, content_hash varchar, "
                "PRIMARY KEY (binding_id, content_hash))",
                "INSERT INTO coss_farmer_references VALUES ('r1', 'FR-000000000001')",
                "INSERT INTO coss_farmer_reference_requests VALUES ('q1', 'r1')",
                "INSERT INTO coss_farmer_workflow_outbox VALUES ('cr1', 'q1')",
            ]
        )

    async def names(self, sql):
        async with self.engine.connect() as conn:
            result = await conn.execute(text(sql), {"s": self.schema})
            return {row[0] for row in result}

    async def tables(self):
        return await self.names("SELECT tablename FROM pg_tables WHERE schemaname = :s")

    async def relations(self):
        return await self.names(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = :s AND c.relkind IN ('i', 'S')"
        )

    async def constraints(self):
        return await self.names(
            "SELECT conname FROM pg_constraint k JOIN pg_namespace n ON n.oid = k.connamespace "
            "WHERE n.nspname = :s"
        )

    async def test_rename_moves_tables_indexes_and_constraints_and_runs_twice(self):
        await self.create_old_tables()
        for _ in range(2):
            await rename.rename_legacy_tables(self.engine)
            self.assertEqual(await self.tables(), set(PAIRS.values()))
            relations = await self.relations()
            self.assertIn("ix_g2p_farmer_pending_lookups_state", relations)
            self.assertIn("ix_g2p_farmer_reference_requests_reference_id", relations)
            self.assertIn("g2p_farmer_references_pkey", relations)
            for name in relations | await self.constraints():
                self.assertNotIn("coss", name)
        async with self.engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(f'SELECT reference_id, farmer_id FROM "{self.schema}".g2p_farmer_references')
                )
            ).all()
        self.assertEqual([tuple(row) for row in rows], [("r1", "FR-000000000001")])

    async def test_a_fresh_database_is_left_alone(self):
        await rename.rename_legacy_tables(self.engine)
        self.assertEqual(await self.tables(), set())

    async def test_when_the_new_table_exists_the_old_one_is_not_touched(self):
        await self.create_old_tables()
        await self.run_sql(["CREATE TABLE g2p_farmer_references (reference_id varchar)"])
        await rename.rename_legacy_tables(self.engine)
        tables = await self.tables()
        self.assertIn("coss_farmer_references", tables)
        self.assertIn("g2p_farmer_references", tables)
        self.assertIn("g2p_farmer_reference_requests", tables)


if __name__ == "__main__":
    unittest.main()
