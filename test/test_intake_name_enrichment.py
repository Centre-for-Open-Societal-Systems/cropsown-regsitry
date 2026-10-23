"""Real ORM transaction checks for the submitted intake's displayed name."""
import ast
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services/farmer_register_crossref.py'
class Base(DeclarativeBase):pass
class Row(Base):
    __tablename__='g2p_intake_form_crop_sowns'
    internal_record_id:Mapped[str]=mapped_column(String,primary_key=True)
    submission_id:Mapped[str]=mapped_column(String)
    farmer_id:Mapped[str]=mapped_column(String,nullable=True)
    fayda_fan_id:Mapped[str]=mapped_column(String,nullable=True)
    farmer_name:Mapped[str]=mapped_column(String,nullable=True)

@pytest.mark.parametrize('mode',['matched','unresolved','disabled','lookup-exception'])
def test_verified_name_is_saved_in_native_transaction_and_failures_are_isolated(mode):
    fn=next(n for n in ast.parse(SOURCE.read_text(encoding="utf-8")).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='enrich_intake_names')
    fn.body=[n for n in fn.body if not isinstance(n,ast.ImportFrom)]
    fetch=AsyncMock(side_effect=(RuntimeError('offline') if mode=='lookup-exception' else lambda fid,fan:{'name':'Source Farmer'} if fid=='FR-123456789012' and fan=='9988102320260001' and mode=='matched' else None))
    scope={'select':select,'G2PIntakeFormCropSown':Row,'_enabled':lambda:mode!='disabled','_config':lambda:{'intake_table':Row.__tablename__},'fetch_farmer_record':fetch,'to_farmer_fields':lambda _:dict(first_name='Source',middle_name=None,last_name='Farmer'),'compose_farmer_name':lambda *p:' '.join(v for v in p if v)}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(SOURCE),'exec'),scope)
    async def main():
        engine=create_async_engine('sqlite+aiosqlite://')
        async with engine.begin() as conn:await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine,expire_on_commit=False)() as s:
            s.add_all([Row(internal_record_id='a',submission_id='target',farmer_id=' FR-123456789012 ',fayda_fan_id='9988 1023 2026 0001',farmer_name=None),Row(internal_record_id='b',submission_id='target',farmer_id='FR-123456789012',fayda_fan_id='9988102320260001',farmer_name='Typed'),Row(internal_record_id='c',submission_id='target',farmer_id='FR-999999999999',fayda_fan_id='9988102320260001',farmer_name='Other'),Row(internal_record_id='d',submission_id='another',farmer_id='FR-123456789012',fayda_fan_id='9988102320260001',farmer_name='Separate submission')]);await s.commit()
            if mode=='lookup-exception':
                with pytest.raises(RuntimeError):await scope['enrich_intake_names']('target',s)
            else:assert await scope['enrich_intake_names']('target',s)==(2 if mode=='matched' else 0)
            assert s.is_active
            rows=(await s.execute(select(Row).order_by(Row.internal_record_id))).scalars().all()
            assert [r.farmer_name for r in rows]==(['Source Farmer','Source Farmer','Other','Separate submission'] if mode=='matched' else [None,'Typed','Other','Separate submission'])
            if mode=='matched':assert fetch.await_count==2
            if mode=='disabled':fetch.assert_not_awaited()
        await engine.dispose()
    asyncio.run(main())
