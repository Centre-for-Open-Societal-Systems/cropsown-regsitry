"""Every Crop Sown intake form starts with Farmer lookup: Farmer ID and one Fayda ID.

The metadata replays (register metadata, then the overlays that run after it) must
leave exactly two widgets on the first section of each of the four intake forms,
retire the old Farmer Identity bindings, and stay identical on a second replay.
Saving the section through the native intake service stores the typed Fayda ID in
the FAN or FIN field by its length.
"""

import importlib
import os
import unittest
from pathlib import Path
from uuid import uuid4

import pytest

pytest.importorskip("openg2p_registry_core")

PACKAGE = "openg2p_registry_cropsown_extension"
REGISTER = "6b06a95a-9a6c-5a33-a33d-c1625716c59c"
LOOKUP = "crop_farmer_lookup"
OLD = {"cropsown_intake_record_section_01", "cropsown_common_intake_record_section_01"}
TABS = {
    "8bd9fe3b-bb8c-4d5d-9f57-f7b5542050b8": "cropsown_intake_season_section_01",
    "29ec34f5-24f7-4007-b8f0-32acc1bc1952": "cropsown_common_intake_season_section_01",
    "56ce9d3d-eb8d-44b5-b175-ff9189ac1c3a": "cropsown_common_intake_season_section_01",
    "01d306ec-d50e-4d73-9bc4-7199b6654eb4": "cropsown_common_intake_season_section_01",
}
META = Path(importlib.import_module(PACKAGE).__file__).parent / "meta_data"


def widgets(node):
    if isinstance(node, dict):
        if "widget" in node:
            yield node
        for value in node.values():
            yield from widgets(value)
    elif isinstance(node, list):
        for value in node:
            yield from widgets(value)


def test_overlay_runs_after_every_register_metadata_file():
    # The seed applies every file under meta_data in sorted path order.
    files = sorted(str(path.relative_to(META)).replace("\\", "/") for path in META.rglob("*.sql"))
    lookup = files.index("zz-oan/10_farmer_lookup.sql")
    assert all(index < lookup for index, name in enumerate(files) if name.startswith("register-metadata/"))


@unittest.skipUnless(os.environ.get("FARMER_TEST_DATABASE_URL"), "Requires disposable PostgreSQL")
class FarmerLookupSectionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = importlib.import_module("test_farmer_reference_native").NativeReferenceTests()
        await self.fixture.asyncSetUp()

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def replay(self):
        paths = sorted((META / "register-metadata").glob("*.sql")) + sorted((META / "zz-oan").glob("*.sql"))
        async with self.fixture.engine.begin() as connection:
            raw = await connection.get_raw_connection()
            for path in paths:
                sql = (path.read_text(encoding="utf-8")
                       .replace('"public".', '"' + self.fixture.schema + '".')
                       .replace("public.", '"' + self.fixture.schema + '".'))
                await raw.driver_connection.execute(sql)

    async def bindings(self):
        from openg2p_registry_core.models import G2PIntakeFormUITabSection
        from sqlalchemy import select
        async with self.fixture.sessions() as session:
            return sorted((await session.execute(select(
                G2PIntakeFormUITabSection.tab_id, G2PIntakeFormUITabSection.section_id,
                G2PIntakeFormUITabSection.section_order))).all())

    async def test_every_intake_starts_with_two_fields_and_saves_fan_or_fin(self):
        from openg2p_registry_core.models import G2PIntakeFormUITab, G2PRegisterSection
        from sqlalchemy import select

        await self.replay()
        first = await self.bindings()
        await self.replay()
        self.assertEqual(await self.bindings(), first)

        for tab_id, season in TABS.items():
            ordered = [section for tab, section, _ in sorted(first, key=lambda row: row[2]) if tab == tab_id]
            self.assertEqual(ordered[:2], [LOOKUP, season], tab_id)
            self.assertEqual(sorted(order for tab, _, order in first if tab == tab_id),
                             list(range(1, len(ordered) + 1)))
        self.assertFalse(OLD & {section for _, section, _ in first})

        native = importlib.import_module("openg2p_registry_extensions.farmer_reference.native")
        service = native.G2PIntakeFormDataService.get_component()
        root = native.domain_models().G2PIntakeFormCropSown
        async with self.fixture.sessions.begin() as session:
            section = await session.get(G2PRegisterSection, LOOKUP)
            self.assertEqual(section.section_mnemonic, LOOKUP)
            fields = [w for w in widgets(section.section_ui_schema)]
            self.assertEqual([w["widget-id"] for w in fields], ["farmer_id", "fayda_id"])
            self.assertTrue(all(w["widget-required"] is True and w["widget"] == "text" for w in fields))
            self.assertEqual([w["widget-label"] for w in fields], ["Farmer ID", "Fayda ID (FAN or FIN)"])
            self.assertNotIn("identity_verification", str(section.section_ui_schema))

            tab = await session.get(G2PIntakeFormUITab, "8bd9fe3b-bb8c-4d5d-9f57-f7b5542050b8")
            for typed, fan, fin in (("001234567890", None, "001234567890"),
                                    ("0012 3456 7890 1234", "0012345678901234", None)):
                submission = await service.save_intake_form_submission_with_session(
                    None, LOOKUP, [{"farmer_id": "FR-000000000001", "fayda_id": typed}],
                    section.section_register_id, tab.form_id, REGISTER, "synthetic-lookup-test", session)
                submission.application_reference = "lookup-" + uuid4().hex
                await session.flush()
                row = (await session.execute(select(root).where(
                    root.submission_id == submission.submission_id))).scalar_one()
                self.assertEqual(row.farmer_id, "FR-000000000001")
                self.assertEqual(row.fayda_fan_id, fan)
                self.assertEqual(row.fayda_fin, fin)
