"""Tests for the required fields at save and submit (required_intake.py).

They need the registry platform for its validation error, so they run inside the
staff API image and are skipped elsewhere. The platform's intake service is
replaced by a small stand-in that holds what a submission stores, so the mixin
is exercised end to end: a section save, then a finalize, the way the web UI,
the ODK worker and a partner push call it.
"""

import asyncio
import importlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException  # noqa: E402

PACKAGE = Path(__file__).parents[1] / "src/openg2p_registry_cropsown_extension"
_package = types.ModuleType("crop_required_pure")
_package.__path__ = [str(PACKAGE)]
sys.modules.setdefault("crop_required_pure", _package)
ri = importlib.import_module("crop_required_pure.required_intake")

ROOT = "6b06a95a-9a6c-5a33-a33d-c1625716c59c"
LAND = "0c0343ca-bac1-5c41-ae5d-72476fa21033"


def _widget(widget_id, required=False, kind="text", options=None, label=None):
    found = {"widget": kind, "widget-id": widget_id, "widget-label": label or widget_id, "widget-required": required,
             "widget-data-path": f"{ROOT}.{widget_id}"}
    if options:
        found["widget-data-options"] = options
    return found


def _section(section_id, register, is_list, ui, description=""):
    return types.SimpleNamespace(section_id=section_id, section_register_id=register, is_list=is_list,
                                 section_ui_schema=ui, section_mnemonic=section_id, section_description=description)


LOOKUP = _section("crop_farmer_lookup", ROOT, False, {
    "section-title": "Farmer lookup",
    "panels": [{"widgets": [_widget("farmer_id", True, label="Farmer ID"),
                            _widget("fayda_id", True, label="Fayda ID (FAN or FIN)")]}]})
SEASON = _section("season", ROOT, False, {
    "section-title": "Production Season",
    "panels": [{"widgets": [_widget("crop_year", True, "number", label="Crop Year"),
                            _widget("production_season", True, "select", label="Production Season")]}]})
PEST = _section("pest", ROOT, False, {
    "section-title": "Pests",
    "panels": [{"widgets": [
        _widget("infested", kind="boolean"),
        _widget("pest_name", options={"actions": [
            {"action": "show", "condition": {"field": f"{ROOT}.infested", "operator": "equals", "value": True}},
            {"action": "require", "condition": {"field": f"{ROOT}.infested", "operator": "equals", "value": True}}]}),
        _widget("shade", options={"actions": [
            {"action": "require", "condition": {"field": f"{ROOT}.infested", "operator": "equals", "value": True}}]}),
    ]}]})
PLANNING = _section("planning", LAND, True, {
    "section-title": "Crop Planning Details",
    "panels": [{"widgets": [{"widget": "table", "widget-id": "planning_table", "widget-required": True,
                            "widget-data-columns": [{"widget": "text", "column-key": "land_id", "widget-label": "Land ID",
                                                     "widget-required": True, "widget-data-path": "land_id"}]}]}]})
OPTIONAL_TABLE = _section("optional_table", LAND, True, {
    "section-title": "Sowing Details",
    "panels": [{"widgets": [{"widget": "table", "widget-id": "sowing_table", "widget-required": False,
                            "widget-data-columns": [{"widget": "text", "column-key": "land_id", "widget-label": "Land ID",
                                                     "widget-required": True, "widget-data-path": "land_id"}]}]}]})
DOCUMENTS = _section("documents", ROOT, False, {
    "section-title": "Documents",
    "panels": [{"widgets": [_widget("permit", True, "file", label="permit")]}]})


class Platform:
    """What the real intake service does after the checks: it saved."""

    async def save_intake_form_submission_with_session(self, submission_id, section_id, section_payload,
                                                       section_register_id, form_id, register_id, created_by,
                                                       session, documents=None):
        self.stored.setdefault(section_register_id, {})
        for record in section_payload:
            self.stored[section_register_id].setdefault(record["internal_record_id"], {}).update(
                {k: v for k, v in record.items() if k not in ("edit_action", "oan_documents")})
        return "saved"

    async def finalize_submission_with_session(self, submission_id, session, *args, **kwargs):
        self.platform_finalized = True
        return "finalized"


class Service(ri.RequiredFieldsMixin, Platform):
    """The mixin over a stand-in that stores records in a dict."""

    def __init__(self, sections):
        self.sections = {s.section_id: s for s in sections}
        self.stored = {}
        self.files = {}
        self.platform_finalized = False

    async def _required_messages(self, session):
        return {}

    async def _get_section_or_error(self, section_id, session):
        return self.sections[section_id]

    async def _stored_records(self, submission_id, section_register_id, session):
        return dict(self.stored.get(section_register_id, {})) if submission_id else {}

    async def _stored_file_labels(self, submission_id, section_id, session):
        return set(self.files.get(section_id, ()))

    async def _get_submission_or_error(self, submission_id, session):
        return types.SimpleNamespace(submission_id=submission_id, form_id="form", register_id=ROOT)

    async def _get_form_sections(self, form_id, session):
        return list(self.sections.values())

    async def _section_records(self, submission_id, section, session):
        rows = list(self.stored.get(section.section_register_id, {}).values())
        return rows if section.is_list else rows[:1]

    @staticmethod
    def _records_for_validation(records):
        return [r for r in records or [] if (r or {}).get("edit_action") != "DELETE"]

    def save(self, section, payload, submission_id="sub-1", documents=None):
        return asyncio.run(self.save_intake_form_submission_with_session(
            submission_id, section.section_id, payload, section.section_register_id, "form", ROOT, "user", None,
            documents=documents))

    def finalize(self):
        asyncio.run(self.ensure_form_complete("sub-1", None))
        return asyncio.run(self.finalize_submission_with_session("sub-1", None))


def _refused(call, *args, **kwargs) -> str:
    with pytest.raises(G2PRegistryException) as error:
        call(*args, **kwargs)
    return error.value.message


# ------------------------------------------------------------------- save --
def test_saving_an_empty_required_section_is_refused():
    service = Service([SEASON])
    assert _refused(service.save, SEASON, [{"internal_record_id": "r1"}]) == (
        "Production Season: fill in Crop Year, Production Season")
    assert service.stored == {}


def test_saving_a_complete_section_passes():
    service = Service([SEASON])
    record = {"internal_record_id": "r1", "crop_year": 2026, "production_season": "SEASON_MEHER"}
    assert service.save(SEASON, [record]) == "saved"


def test_a_field_saved_earlier_counts_when_the_ui_leaves_it_out():
    service = Service([SEASON])
    service.stored[ROOT] = {"r1": {"internal_record_id": "r1", "crop_year": 2026, "production_season": "SEASON_MEHER"}}
    assert service.save(SEASON, [{"internal_record_id": "r1", "crop_year": 2027}]) == "saved"


def test_clearing_a_required_field_is_refused():
    service = Service([SEASON])
    service.stored[ROOT] = {"r1": {"internal_record_id": "r1", "crop_year": 2026, "production_season": "SEASON_MEHER"}}
    assert _refused(service.save, SEASON, [{"internal_record_id": "r1", "production_season": None}]) == (
        "Production Season: fill in Production Season")


def test_the_farmer_lookup_takes_the_typed_fayda_id_or_the_stored_one():
    service = Service([LOOKUP])
    assert _refused(service.save, LOOKUP, [{"internal_record_id": "r1", "farmer_id": "FR-000000000001"}]) == (
        "Farmer lookup: fill in Fayda ID (FAN or FIN)")
    assert service.save(LOOKUP, [{"internal_record_id": "r1", "farmer_id": "FR-000000000001",
                                  "fayda_id": "001234567890"}]) == "saved"
    stored = Service([LOOKUP])
    stored.stored[ROOT] = {"r1": {"internal_record_id": "r1", "farmer_id": "FR-000000000001",
                                  "fayda_fin": "001234567890"}}
    assert stored.save(LOOKUP, [{"internal_record_id": "r1", "farmer_id": "FR-000000000002"}]) == "saved"


def test_a_hidden_field_is_not_required():
    service = Service([PEST])
    assert service.save(PEST, [{"internal_record_id": "r1", "infested": False}]) == "saved"


def test_a_require_rule_makes_a_field_required_on_save():
    service = Service([PEST])
    assert _refused(service.save, PEST, [{"internal_record_id": "r1", "infested": True}]) == (
        "Pests: fill in Pest name, Shade")
    done = {"internal_record_id": "r1", "infested": True, "pest_name": "Armyworm", "shade": "Full"}
    assert service.save(PEST, [done]) == "saved"


def test_saving_a_required_table_with_no_rows_is_refused():
    service = Service([PLANNING])
    assert _refused(service.save, PLANNING, []) == "Crop Planning Details: add at least one row"
    assert _refused(service.save, PLANNING, [{"internal_record_id": "l1", "edit_action": "DELETE"}]) == (
        "Crop Planning Details: add at least one row")


def test_an_optional_table_may_be_saved_empty_but_its_rows_need_their_columns():
    service = Service([OPTIONAL_TABLE])
    assert service.save(OPTIONAL_TABLE, []) == "saved"
    assert _refused(service.save, OPTIONAL_TABLE, [{"internal_record_id": "l1"}]) == (
        "Sowing Details, row 1: fill in Land ID")
    assert service.save(OPTIONAL_TABLE, [{"internal_record_id": "l1", "land_id": "L-1"}]) == "saved"


def test_a_document_attached_by_the_worker_counts_as_saved():
    service = Service([DOCUMENTS])
    assert _refused(service.save, DOCUMENTS, [{"internal_record_id": "r1"}]) == "Documents: add Permit"
    attached = [{"internal_record_id": "r1", "oan_documents": {"documents": {"permit": "doc-1"}}}]
    assert service.save(DOCUMENTS, attached) == "saved"


# --------------------------------------------------------------- finalize --
def test_finalizing_an_incomplete_web_submission_is_refused():
    service = Service([LOOKUP, SEASON, PLANNING])
    service.stored[ROOT] = {"r1": {"internal_record_id": "r1", "farmer_id": "FR-000000000001",
                                   "fayda_fin": "001234567890", "crop_year": 2026}}
    assert _refused(service.finalize) == (
        "Production Season: fill in Production Season; Crop Planning Details: add at least one row")
    assert not service.platform_finalized


def test_finalizing_a_complete_submission_passes():
    service = Service([LOOKUP, SEASON, PLANNING])
    service.stored[ROOT] = {"r1": {"internal_record_id": "r1", "farmer_id": "FR-000000000001",
                                   "fayda_fan_id": "1234567890123456", "crop_year": 2026,
                                   "production_season": "SEASON_MEHER"}}
    service.stored[LAND] = {"l1": {"internal_record_id": "l1", "land_id": "L-1"}}
    assert service.finalize() == "finalized"
    assert service.platform_finalized


def test_a_section_never_opened_is_refused_at_submit():
    service = Service([LOOKUP, SEASON])
    service.stored[ROOT] = {"r1": {"internal_record_id": "r1", "farmer_id": "FR-000000000001",
                                   "fayda_fin": "001234567890"}}
    assert _refused(service.finalize) == "Production Season: fill in Crop Year, Production Season"


def test_a_form_with_nothing_saved_names_every_section():
    service = Service([LOOKUP, SEASON])
    assert _refused(service.finalize) == ("Farmer lookup: fill in Farmer ID, Fayda ID (FAN or FIN); "
                                          "Production Season: fill in Crop Year, Production Season")


def test_an_incomplete_odk_intake_is_refused_with_a_readable_reason():
    # The ODK worker saves each section from the submission, then finalizes.
    # An answer missing from the submission stops the save with a sentence the
    # ingestion row records; nothing else is raised.
    service = Service([LOOKUP, SEASON])
    submission = [{"internal_record_id": "r1", "farmer_id": "FR-000000000001", "oan_documents": {}}]
    message = _refused(service.save, LOOKUP, submission, submission_id=None)
    assert message == "Farmer lookup: fill in Fayda ID (FAN or FIN)"
    assert "_" not in message and "REQ-VAL" not in message


def test_an_incomplete_partner_intake_is_refused_at_submit():
    service = Service([LOOKUP, SEASON])
    service.stored[ROOT] = {"r1": {"internal_record_id": "r1", "farmer_id": "FR-000000000001", "fayda_fin": "001234567890"}}
    assert _refused(service.finalize) == "Production Season: fill in Crop Year, Production Season"


# ------------------------------------------------------- the real service --
def test_the_installed_intake_service_checks_before_its_farmer_lookup():
    pytest.importorskip("openg2p_fastapi_common")
    native = importlib.import_module("openg2p_registry_cropsown_extension.farmer_reference.native")
    cls = native.ReferenceIntakeService
    names = [c.__name__ for c in cls.__mro__]
    assert names.index("RequiredFieldsMixin") < names.index("DirectApprovalClosed") < names.index(
        "G2PIntakeFormDataService")
    assert "approve_submission" not in vars(cls) and "approve_change_request" not in vars(cls)
    assert "ensure_form_complete" in dir(cls)

    import ast
    import inspect
    import textwrap

    source = textwrap.dedent(inspect.getsource(cls.finalize_submission_with_session))
    body = ast.parse(source).body[0].body
    first_calls = [ast.unparse(node) for node in body if isinstance(node, ast.Expr)]
    assert "await self.ensure_form_complete(submission_id, session)" in first_calls
    assert "_finalize_with_farmer" not in " ".join(first_calls[:first_calls.index(
        "await self.ensure_form_complete(submission_id, session)")])
