"""Everything staff read in the Crop Sown registry is plain English.

After the metadata replay (register metadata, the language rows, the overlays and
the translation defaults) no visible label, hint, option, section title, tab
name, search or filter label, translation entry or validation message may contain
an underscore, be an upper-case code, use an unexplained abbreviation, or be in
Title Case. The code side holds the same line: every Farmer lookup refusal has a
sentence, and no validation message names a stored field.
"""

import ast
import importlib
import os
import re
import unittest
from pathlib import Path

import pytest

pytest.importorskip("openg2p_registry_core")

PACKAGE = "openg2p_registry_cropsown_extension"
CROP = "6b06a95a-9a6c-5a33-a33d-c1625716c59c"
META = Path(importlib.import_module(PACKAGE).__file__).parent / "meta_data"
SRC = Path(importlib.import_module(PACKAGE).__file__).parent

TEXT_KEYS = {
    "widget-label", "label", "widget-data-placeholder", "widget-data-add-label", "widget-data-dialog-title-add",
    "widget-data-dialog-title-edit", "patternMessage", "minDateMessage", "message", "section-title", "column-group",
    "placeholder", "hint", "help", "tooltip",
}
# Words that stay as they are: acronyms staff know, product and place names, local words.
KEEP = {
    "ID", "FAN", "FIN", "GPS", "Fayda", "Kebele", "Woreda", "Zone", "Region", "Ethiopian", "Ethiopic", "Gregorian",
    "Amharic", "Farmer", "Registry", "Crop", "Sown", "Maresha", "Debo", "Jigi", "Shilshalo", "Meher", "Belg", "Bega",
    "Kolla", "Dega", "Wurch", "Bereha", "Woina", "Timad", "Land", "Fayda", "Ethiopia",
}
ALLOWED_CODES = {"GPS", "FAN", "FIN", "ID", "NGO", "DAP", "NPS", "NPSB", "MCPA", "TFM", "BH-660"}
ABBREVIATION = re.compile(r"\b(GC|EC|DA|FPC|ha|Quintial|pct|qty)\b|\(ha\)")
PROPER = {
    "Adi Daero", "Laelay Koraro", "North Western", "South Eastern", "Tahtay Koraro", "Seyemti Adyabo", "Tahtay Adiyabo",
    "Shire Endaslasie town", "South West Ethiopia", "Kuncho Teff", "Crop Sown Registry", "Crop Sown Registry intake form",
}
GEOGRAPHY = re.compile(r"^(ZONE|WOREDA|REGION|KEBELE)_")


def walk(node, found=None):
    found = [] if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            if key in TEXT_KEYS and isinstance(value, str):
                found.append((key, value))
            walk(value, found)
    elif isinstance(node, list):
        for value in node:
            walk(value, found)
    return found


def problems(text, *, message=False):
    found = []
    if "_" in text:
        found.append("underscore")
    if text not in ALLOWED_CODES and re.fullmatch(r"[A-Z0-9][A-Z0-9 /\-]+", text):
        found.append("upper-case code")
    if ABBREVIATION.search(text):
        found.append("unexplained abbreviation")
    if not message:
        words = [re.sub(r"[^A-Za-z]", "", word) for word in text.split(" ")[1:]]
        if any(len(w) > 1 and w[0].isupper() and w[1:].islower() and w not in KEEP for w in words) and text not in PROPER:
            found.append("title case")
    return found


@unittest.skipUnless(os.environ.get("FARMER_TEST_DATABASE_URL"), "Requires disposable PostgreSQL")
class ReadableTextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = importlib.import_module("test_farmer_reference_native").NativeReferenceTests()
        await self.fixture.asyncSetUp()

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def replay(self):
        files = sorted(
            [p for p in (META / "register-metadata").glob("*.sql")]
            + [p for p in (META / "registry-configurations").glob("registry_languages*.sql")]
            + [p for p in (META / "zz-oan").glob("*.sql")]
            + [META / "zzzzzz_field_translations.sql"])
        async with self.fixture.engine.begin() as connection:
            raw = await connection.get_raw_connection()
            for path in files:
                sql = (path.read_text(encoding="utf-8")
                       .replace('"public".', '"' + self.fixture.schema + '".')
                       .replace("public.", '"' + self.fixture.schema + '".'))
                await raw.driver_connection.execute(sql)

    async def test_no_visible_text_is_a_code_or_jargon(self):
        from openg2p_registry_core.models import (
            G2PRegisterDefinition, G2PRegisterSchema, G2PRegisterSection, G2PRegisterUITab, G2PRegistryLanguage)
        from sqlalchemy import select

        await self.replay()
        await self.replay()
        async with self.fixture.sessions() as session:
            english = (await session.execute(select(G2PRegistryLanguage).where(
                G2PRegistryLanguage.language_code == "en"))).scalar_one()
            translations = dict(english.domain_translation or {})
            sections = (await session.execute(select(G2PRegisterSection))).scalars().all()
            schemas = (await session.execute(select(G2PRegisterSchema))).scalars().all()
            definitions = (await session.execute(select(G2PRegisterDefinition))).scalars().all()
            tabs = (await session.execute(select(G2PRegisterUITab))).scalars().all()
            core = dict(english.core_translation or {})

        failures = []
        for section in sections:
            crop = section.register_id == CROP
            for key, raw_text in walk(section.section_ui_schema):
                shown = translations.get(raw_text, raw_text)
                if not shown:
                    continue
                for problem in problems(shown, message=key in {"patternMessage", "minDateMessage", "message"} or not crop):
                    failures.append(f"{section.section_id} {key} {raw_text!r} -> {shown!r}: {problem}")
        for key, value in translations.items():
            if GEOGRAPHY.match(key) or value in PROPER or key.startswith(("coss_", "common.")):
                continue
            for problem in problems(str(value)):
                failures.append(f"translation {key!r} -> {value!r}: {problem}")
        for key, value in translations.items():
            if key.startswith("coss_"):
                for problem in problems(str(value), message=True):
                    failures.append(f"message {key!r} -> {value!r}: {problem}")
                assert "1900-01-01" not in value and "Remove digits" not in value, key
        for schema in schemas:
            for column in ("search_result_schema", "filter_schema"):
                for entry in getattr(schema, column) or []:
                    for text in [entry.get("display_label")] + [o.get("label") for o in entry.get("options_source") or []]:
                        if text:
                            for problem in problems(translations.get(text, text)):
                                failures.append(f"{schema.register_id} {column} {text!r}: {problem}")
        for definition in definitions:
            for text in (definition.register_subject, definition.register_description):
                shown = translations.get(text, text)
                if text and shown not in PROPER:
                    for problem in problems(shown):
                        failures.append(f"{definition.register_id} {text!r}: {problem}")
        for tab in [t for t in tabs if t.register_id == CROP]:
            shown = translations.get(tab.tab_label)
            assert shown and "_" not in shown, tab.tab_label
        for key in ("ACTIVE", "INACTIVE", "ARCHIVED"):
            assert core[key] == key.capitalize()
        for key in ("cropsown_planning_intake_tab", "cropsown_cultivation_intake_tab",
                    "cropsown_sowing_intake_tab", "cropsown_harvesting_intake_tab", "CultivationCluster"):
            assert translations[key] and "_" not in translations[key], key
        self.assertEqual(failures, [])


def test_every_farmer_lookup_refusal_has_a_sentence():
    messages = importlib.import_module(PACKAGE + ".farmer_reference.messages")
    raised = set()
    for path in SRC.rglob("*.py"):
        raised.update(re.findall(r'FarmerReferenceError\("(FARMER_REFERENCE_[A-Z_]+)"\)', path.read_text(encoding="utf-8")))
    raised.update({"FARMER_REFERENCE_DEPENDENCY_PENDING", "FARMER_REFERENCE_DEPENDENCY_REJECTED"})
    missing = sorted(code for code in raised if code not in messages.MESSAGES and code not in messages.UNAVAILABLE)
    assert missing == []
    for code, sentence in messages.MESSAGES.items():
        assert "_" not in sentence and "{" not in sentence.replace("{ids}", ""), code
        assert sentence[0].isupper() and sentence == sentence.strip(), code


def test_validation_messages_name_fields_in_plain_words():
    """No message in the domain services shows a stored column name or a unit symbol."""
    root = SRC / "register_domain"
    calls = {"validation_error", "ValueError"}
    offenders = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
            if name not in calls:
                continue
            for part in ast.walk(node):
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    text = part.value
                    if re.search(r"\b[a-z]+_[a-z_]+\b", text) or ABBREVIATION.search(text) or "FARMER_REFERENCE_" in text:
                        if not text.startswith("FARMER_REFERENCE_LIFECYCLE"):
                            offenders.append(f"{path.name}:{part.lineno}: {text}")
    assert offenders == []
