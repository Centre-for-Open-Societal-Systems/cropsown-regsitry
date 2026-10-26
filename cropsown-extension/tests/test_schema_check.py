"""Deployment inspection reports missing columns and never repairs schema."""
import asyncio
from types import SimpleNamespace

import pytest
sa = pytest.importorskip('sqlalchemy')
pytest.importorskip('aiosqlite')
from sqlalchemy.ext.asyncio import create_async_engine
from openg2p_registry_cropsown_extension.schema_check import missing_columns


def test_schema_inspection_is_read_only_and_reports_each_missing_mapped_column():
    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        metadata = sa.MetaData()
        table = sa.Table('owned_domain',metadata,sa.Column('id',sa.Integer),sa.Column('domain_answer',sa.String))
        model = SimpleNamespace(__table__=table)
        assert await missing_columns(engine,[model]) == ['owned_domain.id','owned_domain.domain_answer']
        async with engine.begin() as connection:
            await connection.execute(sa.text('CREATE TABLE owned_domain (id INTEGER)'))
            await connection.execute(sa.text('INSERT INTO owned_domain VALUES (7)'))
        assert await missing_columns(engine,[model]) == ['owned_domain.domain_answer']
        async with engine.connect() as connection:
            assert (await connection.execute(sa.text('SELECT * FROM owned_domain'))).all() == [(7,)]
        async with engine.begin() as connection:
            await connection.execute(sa.text('ALTER TABLE owned_domain ADD COLUMN domain_answer VARCHAR'))
        assert await missing_columns(engine,[model]) == []
        await engine.dispose()
    asyncio.run(run())
