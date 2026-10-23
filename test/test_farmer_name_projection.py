"""Exercise both approval orders, identity boundaries and transaction rollback."""
import ast
import asyncio
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services"
spec = importlib.util.spec_from_file_location("projection", SERVICES / "farmer_name_projection.py")
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


class Base(DeclarativeBase):
    pass


class Farmer(Base):
    __tablename__ = "farmers"
    internal_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    functional_record_id: Mapped[str] = mapped_column(String)
    farmer_id: Mapped[str] = mapped_column(String, nullable=True)
    fayda_fan_id: Mapped[str] = mapped_column(String, nullable=True)
    record_status: Mapped[str] = mapped_column(String)
    last_approved_at: Mapped[str] = mapped_column(String, nullable=True)
    last_approved_by: Mapped[str] = mapped_column(String, nullable=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    middle_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)


class Crop(Base):
    __tablename__ = "crops"
    internal_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    farmer_id: Mapped[str] = mapped_column(String, nullable=True)
    fayda_fan_id: Mapped[str] = mapped_column(String, nullable=True)
    farmer_name: Mapped[str] = mapped_column(String, nullable=True)
    record_status: Mapped[str] = mapped_column(String)
    search_text: Mapped[str] = mapped_column(String, nullable=True)
    crop_year: Mapped[str] = mapped_column(String, default="2026")

    def get_search_text_fields(self):
        return f"{self.farmer_name} {self.farmer_id} {self.crop_year}"


FID = "FR-123456789012"
FAN = "9988102320260001"


@pytest.mark.parametrize("case", ["approved", "inactive", "unapproved", "missing-fan", "ambiguous", "blank-name", "rollback", "later-ingest"])
def test_current_names_follow_approved_reference_in_either_order_and_only_matching_pair(case, monkeypatch):
    monkeypatch.setattr(projection, "_models", lambda: (Farmer, Crop))

    async def main():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Native sessions may disable autoflush; the hook must preserve dirty approved fields.
        async with async_sessionmaker(engine, expire_on_commit=False, autoflush=False)() as s:
            farmer = Farmer(internal_record_id="f", functional_record_id=FID, farmer_id=FID,
                            fayda_fan_id=FAN if case != "missing-fan" else None,
                            record_status="INACTIVE" if case == "inactive" else "ACTIVE",
                            last_approved_at=None if case == "unapproved" else "2026-10-23",
                            last_approved_by="reviewer", first_name="Old", last_name="Farmer")
            crops = [Crop(internal_record_id="a", farmer_id=FID, fayda_fan_id=FAN, farmer_name="Old Farmer", record_status="ACTIVE"),
                     Crop(internal_record_id="b", farmer_id=" " + FID + " ", fayda_fan_id="9988 1023 2026 0001", farmer_name="Typed", record_status="ACTIVE"),
                     Crop(internal_record_id="wrong-fan", farmer_id=FID, fayda_fan_id="9988102320260002", farmer_name="Other", record_status="ACTIVE"),
                     Crop(internal_record_id="wrong-id", farmer_id="FR-999999999999", fayda_fan_id=FAN, farmer_name="Other", record_status="ACTIVE"),
                     Crop(internal_record_id="inactive", farmer_id=FID, fayda_fan_id=FAN, farmer_name="Inactive", record_status="INACTIVE")]
            s.add_all([farmer, *crops])
            if case == "ambiguous":
                s.add(Farmer(internal_record_id="duplicate", functional_record_id=FID, farmer_id=FID,
                             fayda_fan_id=FAN, record_status="ACTIVE", last_approved_at="2026-10-23",
                             last_approved_by="reviewer", first_name="Different", last_name="Person"))
            await s.commit()
            farmer.first_name = "New" if case != "blank-name" else None
            if case == "blank-name":
                farmer.last_name = None
            expected = 2 if case in ["approved", "rollback", "later-ingest"] else 0
            assert await projection.refresh_crop_names_from_farmer(s, "f") == expected
            assert crops[0].farmer_name == ("New Farmer" if expected else "Old Farmer")
            assert crops[1].farmer_name == ("New Farmer" if expected else "Typed")
            assert [r.farmer_name for r in crops[2:]] == ["Other", "Other", "Inactive"]
            assert all(r.crop_year == "2026" for r in crops)
            if expected:
                assert "New Farmer" in crops[0].search_text
                assert await projection.refresh_crop_names_from_farmer(s, "f") == 0
            if case == "rollback":
                await s.rollback()
                rows = (await s.execute(select(Crop).order_by(Crop.internal_record_id))).scalars().all()
                assert rows[0].farmer_name == "Old Farmer"
                assert (await s.get(Farmer, "f")).first_name == "Old"
            elif case == "later-ingest":
                await s.commit()
                later = Crop(internal_record_id="later", farmer_id=FID, fayda_fan_id=FAN,
                             farmer_name="Old Farmer", record_status="ACTIVE")
                s.add(later)
                assert await projection.refresh_crop_name_on_ingest(s, later) == 1
                assert later.farmer_name == "New Farmer"
            else:
                assert await projection.refresh_crop_name_on_ingest(s, crops[0]) == 0
            await s.commit()
        await engine.dispose()
    asyncio.run(main())


@pytest.mark.parametrize("service,hook,helper", [
    ("farmer", "post_approve", "refresh_crop_names_from_farmer"),
    ("farmer", "post_ingest", "refresh_crop_names_from_farmer"),
    ("crop_sown", "post_ingest", "refresh_crop_name_on_ingest"),
])
def test_native_approval_and_ingestion_hooks(service, hook, helper):
    tree = ast.parse((SERVICES / f"g2p_register_domain_service_{service}.py").read_text(encoding="utf-8"))
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == hook)
    assert any(isinstance(n, ast.Await) and isinstance(n.value, ast.Call)
               and isinstance(n.value.func, ast.Name) and n.value.func.id == helper for n in ast.walk(method))
