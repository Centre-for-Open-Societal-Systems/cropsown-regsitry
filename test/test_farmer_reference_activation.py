"""Single approval: the approved Crop intake activates its staged Farmer reference."""
import ast
import asyncio
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import Boolean, DateTime, String, event, func, inspect, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services/farmer_register_crossref.py"
FID = "FR-123456789012"
FAN = "9999102220260001"
APPROVED_AT = datetime(2026, 10, 26, 12, 0, 0)


class Base(DeclarativeBase):
    pass


class Identity:
    internal_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    functional_record_id: Mapped[str] = mapped_column(String, nullable=True)
    farmer_id: Mapped[str] = mapped_column(String, nullable=True)
    fayda_fan_id: Mapped[str] = mapped_column(String, nullable=True)
    farmer_name: Mapped[str] = mapped_column(String, nullable=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    middle_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    gender: Mapped[str] = mapped_column(String, nullable=True)
    record_name: Mapped[str] = mapped_column(String, nullable=True)
    record_status: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Farmer(Identity, Base):
    __tablename__ = "g2p_register_farmers"
    search_text: Mapped[str] = mapped_column(String, nullable=True)
    last_approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_approved_by: Mapped[str] = mapped_column(String, nullable=True)

    def get_record_name_fields(self):
        return " ".join(v for v in (self.farmer_name, self.farmer_id) if v)

    def get_search_text_fields(self):
        return " ".join(v for v in (self.functional_record_id, self.fayda_fan_id, self.farmer_name, self.gender) if v)


class History(Identity, Base):
    __tablename__ = "g2p_register_history_farmers"
    internal_record_id: Mapped[str] = mapped_column(String)
    history_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    tab_id: Mapped[str] = mapped_column(String)
    section_id: Mapped[str] = mapped_column(String)
    change_request_id: Mapped[str] = mapped_column(String, nullable=True)
    submission_id: Mapped[str] = mapped_column(String, nullable=True)
    change_request_source: Mapped[str] = mapped_column(String)
    is_primary_section: Mapped[bool] = mapped_column(Boolean)
    approved_by: Mapped[str] = mapped_column(String)
    approved_at: Mapped[datetime] = mapped_column(DateTime)


class Marker(Base):
    """Stands in for the Crop Sown record written in the same ingest transaction."""
    __tablename__ = "crop_marker"
    id: Mapped[str] = mapped_column(String, primary_key=True)


def load(history_model=History):
    names = {"_setting", "_enabled", "_config", "_identity", "_lock_farmer", "activate_farmer_reference", "_activate"}
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    assert {n.name for n in nodes} == names
    scope = {
        "os": os, "re": re, "uuid": uuid, "datetime": datetime, "select": select, "func": func,
        "inspect": inspect, "text": text, "_logger": logging.getLogger("test-activation"),
        "_DEFAULT_REGISTER_ID": "fa120001-0000-4000-8000-000000000001", "_DEFAULT_TAB_ID": "cropsown_farmer_tab",
        "_DEFAULT_SECTION_ID": "cropsown_farmer_identity_section_01", "_DEFAULT_INTAKE_TABLE": "g2p_intake_form_crop_sowns",
        "_models": lambda: (Farmer, history_model),
        "compose_farmer_name": lambda *parts: " ".join(p for p in parts if p).strip(),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), scope)
    return scope["activate_farmer_reference"]


def shell(**overrides):
    values = dict(internal_record_id="shell", functional_record_id=FID, farmer_id=FID, fayda_fan_id=FAN,
                  farmer_name="Abebe Kebede", first_name="Abebe", last_name="Kebede", gender="MALE",
                  record_name=f"Abebe Kebede {FID}", record_status="INACTIVE", status="APPROVAL_STATUS_DRAFT",
                  created_by="cropsown-two-cr", created_at=datetime(2026, 10, 26, 9, 0, 0),
                  last_approved_at=datetime(2026, 10, 26, 9, 0, 0), last_approved_by="system")
    values.update(overrides)
    return Farmer(**values)


def crop(**overrides):
    values = dict(farmer_id=FID, fayda_fan_id="9999 1022 2026 0001", record_status="ACTIVE",
                  last_approved_at=APPROVED_AT, last_approved_by="nina.patel")
    values.update(overrides)
    return SimpleNamespace(**values)


async def run(rows, crop_row, enabled="true", history_model=History):
    engine = create_async_engine("sqlite+aiosqlite://")

    # pysqlite/aiosqlite need explicit BEGIN for SAVEPOINT to behave like PostgreSQL.
    @event.listens_for(engine.sync_engine, "connect")
    def _connect(dbapi_connection, _record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine.sync_engine, "begin")
    def _begin(connection):
        connection.exec_driver_sql("BEGIN")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            session.add_all(rows)
    activate = load(history_model)
    with patch.dict(os.environ, {"CROPSOWN_TWO_CR_ENABLED": enabled}):
        async with maker() as session:
            async with session.begin():
                session.add(Marker(id="crop-record"))
                result = await activate(session, crop_row)
    async with maker() as session:
        farmers = (await session.execute(select(Farmer).order_by(Farmer.internal_record_id))).scalars().all()
        history = (await session.execute(select(History))).scalars().all()
        markers = (await session.execute(select(Marker))).scalars().all()
    await engine.dispose()
    assert [m.id for m in markers] == ["crop-record"]  # the Crop record always commits
    return result, farmers, history


def test_staged_reference_becomes_active_with_the_intake_approver():
    result, farmers, history = asyncio.run(run([shell()], crop()))
    assert result == 1
    [farmer] = farmers
    assert (farmer.record_status, farmer.status) == ("ACTIVE", "APPROVAL_STATUS_APPROVED")
    assert (farmer.last_approved_at, farmer.last_approved_by) == (APPROVED_AT, "nina.patel")
    assert farmer.record_name == f"Abebe Kebede {FID}"
    assert farmer.search_text == f"{FID} {FAN} Abebe Kebede MALE"
    [entry] = history
    assert entry.internal_record_id == "shell" and entry.record_status == "ACTIVE"
    assert (entry.tab_id, entry.section_id) == ("cropsown_farmer_tab", "cropsown_farmer_identity_section_01")
    assert (entry.change_request_id, entry.change_request_source, entry.is_primary_section) == (None, "cropsown-two-cr", False)
    assert (entry.approved_by, entry.approved_at, entry.gender) == ("nina.patel", APPROVED_AT, "MALE")


@pytest.mark.parametrize("case", ["already-active", "nothing-staged", "other-fan", "legacy-empty-shell",
                                  "disabled", "crop-inactive", "crop-bad-fan", "other-farmer"])
def test_nothing_changes_unless_a_matching_reference_was_staged(case):
    rows = [shell()]
    crop_row = crop()
    enabled = "true"
    if case == "already-active":
        rows.append(shell(internal_record_id="active", record_status="ACTIVE", status="APPROVAL_STATUS_APPROVED",
                          created_at=datetime(2026, 10, 1)))
    if case == "nothing-staged":
        rows = []
    if case == "other-fan":
        rows = [shell(fayda_fan_id="1111222233334444")]
    if case == "legacy-empty-shell":
        rows = [shell(first_name=None, last_name=None, farmer_name=None, fayda_fan_id=None)]
    if case == "disabled":
        enabled = "false"
    if case == "crop-inactive":
        crop_row = crop(record_status="INACTIVE")
    if case == "crop-bad-fan":
        crop_row = crop(fayda_fan_id="12345")
    if case == "other-farmer":
        crop_row = crop(farmer_id="FR-999999999999")
    before = {(r.internal_record_id, r.record_status) for r in rows}
    result, farmers, history = asyncio.run(run(rows, crop_row, enabled))
    assert result == 0
    assert {(f.internal_record_id, f.record_status) for f in farmers} == before
    assert history == []


def test_activation_failure_keeps_the_crop_record_and_the_shell_hidden():
    class BrokenHistory:
        """Not a mapped model: writing the history row fails after the flip."""

    result, farmers, history = asyncio.run(run([shell()], crop(), history_model=BrokenHistory))
    assert result == 0
    [farmer] = farmers
    assert (farmer.record_status, farmer.status) == ("INACTIVE", "APPROVAL_STATUS_DRAFT")
    assert history == []
