"""Plain messages for a code that is not on its list, and Validate that says what Submit says."""
import asyncio
import importlib
import json
import os
import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("openg2p_registry_core")

PACKAGE = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_cropsown_extension")
messages = importlib.import_module(PACKAGE + ".register_domain.services.attribute_messages")
rules = importlib.import_module(PACKAGE + ".register_domain.services.field_rules")
required_intake = importlib.import_module(PACKAGE + ".required_intake")
native = importlib.import_module(PACKAGE + ".farmer_reference.native")
profile = importlib.import_module(PACKAGE + ".farmer_reference.profile")
from openg2p_registry_core.errors import G2PRegistryException

META = Path(importlib.import_module(PACKAGE).__file__).parent / "meta_data"


def run(coro):
    return asyncio.run(coro)


# A. unknown codes -----------------------------------------------------------------
CROP = "record 0: commodity='CROP_NOT_REAL' is not a value of CROP_COMMODITY (permitted: CROP_MAIZE, CROP_TEFF)"
SEASON = "record 0: production_season='NOT_A_SEASON' is not a value of CROP_SEASON (permitted: SEASON_BELG, SEASON_MEHER)"


def test_an_unknown_crop_says_choose_a_crop_without_codes():
    assert messages.reword(CROP) == "Crop: choose a crop from the list."


def test_an_unknown_season_says_choose_a_season_without_codes():
    assert messages.reword(SEASON) == "Production season: choose a season from the list."
    assert messages.reword(SEASON.replace("production_season", "season")) == "Season: choose a season from the list."


def _master_data_fields():
    found = set()
    text = (META / "register-metadata" / "g2p_register_sections.sql").read_text(encoding="utf-8")
    for blob in re.findall(r"'(\{.*?\})'(?=,|\))", text, re.S):
        try:
            schema = json.loads(blob.replace("''", "'"))
        except ValueError:
            continue
        stack = [schema]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                source = node.get("widget-data-source")
                params = source.get("params") if isinstance(source, dict) else None
                if isinstance(params, dict) and params.get("attribute_id"):
                    found.add(node.get("column-key") or (node.get("widget-data-path") or "").rsplit(".", 1)[-1])
                stack.extend(node.values())
    return found


def test_every_master_data_field_on_the_forms_has_a_label_and_a_noun():
    found = _master_data_fields()
    assert len(found) >= 20
    assert sorted(found - set(messages.FIELDS)) == []
    for field in found:
        label, noun = messages.FIELDS[field]
        assert "_" not in label and label[0].isupper() and noun
        raw = f"record 0: {field}='x' is not a value of LIST (permitted: A, B)"
        assert messages.reword(raw) == f"{label}: choose {noun} from the list."


def test_several_rows_with_the_same_mistake_say_it_once_and_other_text_is_kept():
    raw = CROP + "; " + CROP.replace("record 0", "record 3") + "; Something else"
    assert messages.reword(raw) == "Crop: choose a crop from the list. Something else"


def test_the_wording_comes_from_the_registry_translation_when_it_has_one():
    assert messages.reword(CROP, {"coss_code_choice": "{label}: pick {noun}."}) == "Crop: pick a crop."
    assert messages.reword(CROP, {"coss_code_choice": "{broken}"}) == "Crop: choose a crop from the list."


def test_a_message_that_is_not_about_a_list_is_unchanged():
    assert messages.reword("Planned area must be greater than zero.") == "Planned area must be greater than zero."


def test_the_translation_is_seeded_without_replacing_other_keys():
    sql = (META / "zz-oan" / "87_code_choice_message.sql").read_text(encoding="utf-8")
    assert '"coss_code_choice": "{label}: choose {noun} from the list."' in sql
    assert sql.index("coss_code_choice") < sql.index('COALESCE("domain_translation"') and "\r" not in sql


def test_the_installed_validator_rewords_what_core_refuses(monkeypatch):
    core = importlib.import_module("openg2p_registry_core.services.g2p_attribute_value_validator")
    monkeypatch.setattr(core.G2PAttributeValueValidator, "enabled", property(lambda self: True))
    monkeypatch.setattr(core.G2PAttributeValueValidator, "_load", AsyncMock(
        return_value={"CROP_COMMODITY": {"CROP_MAIZE", "CROP_TEFF"}, "CROP_SEASON": {"SEASON_MEHER"}}))
    monkeypatch.setattr(rules, "_translations", AsyncMock(return_value={}))
    validator = messages.install_attribute_messages()
    field_map = {"commodity": "CROP_COMMODITY", "production_season": "CROP_SEASON"}
    with pytest.raises(G2PRegistryException) as caught:
        run(validator.validate_records([{"commodity": "CROP_NOT_REAL", "production_season": "X"}], field_map=field_map))
    assert caught.value.message == "Crop: choose a crop from the list. Production season: choose a season from the list."
    run(validator.validate_records([{"commodity": "CROP_MAIZE", "production_season": "SEASON_MEHER"}], field_map=field_map))
    assert messages.install_attribute_messages() is validator


# B. Validate says what Submit says ---------------------------------------------------
class _Base:
    async def validate_submission_for_approval_with_session(self, submission_id, session):
        return SimpleNamespace(issues=[], is_valid=True)


class _Service(required_intake.RequiredFieldsMixin, _Base):
    def __init__(self, problems):
        self.problems = problems

    async def _required_on_finalize(self, submission_id, session):
        return self.problems


def test_validate_reports_what_submit_would_refuse_as_sentences():
    service = _Service(["Crop planning details, row 1: fill in Season, Crop", "Land: add at least one row"])
    result = run(service.validate_submission_for_approval_with_session("s", None))
    assert not result.is_valid
    assert [i.message for i in result.issues] == [
        "Crop planning details, row 1: fill in Season, Crop.", "Land: add at least one row."]


def test_validate_is_valid_for_a_complete_form():
    result = run(_Service([]).validate_submission_for_approval_with_session("s", None))
    assert result.is_valid and result.issues == []


def _reference_service(problem):
    service = object.__new__(native.ReferenceIntakeService)
    async def fake(submission_id, session, season=True, farmer=True):
        return problem if farmer else None

    service._submission_problem = AsyncMock(side_effect=fake)
    return service


def _validate(service, base, session=None):
    with patch.object(required_intake.RequiredFieldsMixin, "validate_submission_for_approval_with_session",
                      AsyncMock(return_value=base)):
        return run(service.validate_submission_for_approval_with_session("s", session))


def test_validate_reports_a_farmer_who_cannot_be_linked():
    service = _reference_service(("FARMER_NOT_FOUND", "No farmer with Farmer ID FR-000000000001 is in the Farmer Registry"))
    result = _validate(service, SimpleNamespace(issues=[], is_valid=True))
    assert not result.is_valid
    assert result.issues[0].message == "No farmer with Farmer ID FR-000000000001 is in the Farmer Registry."


def test_validate_is_valid_when_the_farmer_checks_out():
    result = _validate(_reference_service(None), SimpleNamespace(issues=[], is_valid=True))
    assert result.is_valid and result.issues == []


def test_the_farmer_is_not_looked_up_while_the_form_is_still_incomplete():
    service = _reference_service(("X", "anything"))
    result = _validate(service, SimpleNamespace(issues=["missing"], is_valid=False))
    assert [c.kwargs.get("season", True) for c in service._submission_problem.await_args_list] == [False]
    assert result.issues[0] == "missing"


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class _Query:
    def where(self, *args):
        return self


class _Dependency:
    pass


class _Live:
    pass


def _session(row, dependency=None, live=None):
    async def get(model, key):
        if model is _Dependency:
            return dependency
        return live if model is _Live else None

    return SimpleNamespace(get=get, execute=AsyncMock(return_value=_Rows([row])))


def _lookup_service(monkeypatch, lookup):
    service = object.__new__(native.ReferenceIntakeService)
    service._get_submission_or_error = AsyncMock(return_value=SimpleNamespace(register_id="r", form_id="f"))
    service._get_register_definition = AsyncMock(return_value=SimpleNamespace(register_mnemonic="CropSown"))
    service._get_form_sections = AsyncMock(return_value=[SimpleNamespace(section_mnemonic="cs_intake_season")])
    models = SimpleNamespace(G2PIntakeFormCropSown=SimpleNamespace(submission_id=1), G2PRegisterCropSown=_Live)
    monkeypatch.setattr(native, "domain_models", lambda: models)
    monkeypatch.setattr(native, "select", lambda *a: _Query())
    monkeypatch.setattr(native, "FarmerSubmissionDependency", _Dependency)
    monkeypatch.setattr(native, "configured_lookup", lambda: SimpleNamespace(lookup=lookup))
    return service


def _row(**changes):
    values = dict(internal_record_id="x", farmer_id="FR-123456789012", fayda_fin=None,
                  fayda_fan_id="1234567890123456", crop_year=str(date.today().year), production_season="SEASON_MEHER")
    values.update(changes)
    return SimpleNamespace(**values)


def test_an_unknown_farmer_is_explained_before_submit(monkeypatch):
    service = _lookup_service(
        monkeypatch, AsyncMock(side_effect=profile.FarmerReferenceError("FARMER_REFERENCE_NOT_FOUND")))
    code, text = run(service._submission_problem("s", _session(_row())))
    assert text.startswith("No farmer with Farmer ID FR-123456789012 and FAN 1234567890123456 is in the Farmer Registry")


def test_a_wrong_pair_is_explained_before_submit(monkeypatch):
    found = SimpleNamespace(profile={"farmer_id": "FR-123456789012", "fayda_fan_id": "9999999999999999"})
    service = _lookup_service(monkeypatch, AsyncMock(return_value=found))
    code, text = run(service._submission_problem("s", _session(_row())))
    assert text.startswith("The Farmer ID and Fayda ID belong to different farmers in the Farmer Registry")


def test_a_matching_pair_has_no_problem(monkeypatch):
    found = SimpleNamespace(profile={"farmer_id": "FR-123456789012", "fayda_fan_id": "1234567890123456"})
    service = _lookup_service(monkeypatch, AsyncMock(return_value=found))
    assert run(service._submission_problem("s", _session(_row()))) is None


def test_a_form_already_linked_to_a_farmer_is_left_to_submit(monkeypatch):
    lookup = AsyncMock()
    service = _lookup_service(monkeypatch, lookup)
    assert run(service._submission_problem("s", _session(_row(), dependency=_Dependency()))) is None
    lookup.assert_not_called()


def test_a_missing_production_season_is_reported_before_any_lookup(monkeypatch):
    lookup = AsyncMock()
    service = _lookup_service(monkeypatch, lookup)
    code, text = run(service._submission_problem("s", _session(_row(production_season=None))))
    assert text and "season" in text.lower()
    lookup.assert_not_called()


def test_an_unreachable_registry_is_not_called_a_wrong_farmer(monkeypatch):
    service = _lookup_service(
        monkeypatch, AsyncMock(side_effect=profile.FarmerReferenceError("FARMER_REFERENCE_LOOKUP_UNAVAILABLE")))
    code, text = run(service._submission_problem("s", _session(_row())))
    assert text.startswith("The Farmer Registry could not be reached")


def _problem(monkeypatch, lookup, **row):
    return run(_lookup_service(monkeypatch, lookup)._submission_problem("s", _session(_row(**row))))


def test_issue_codes_tell_the_causes_apart(monkeypatch):
    err = profile.FarmerReferenceError
    assert _problem(monkeypatch, AsyncMock(side_effect=err("FARMER_REFERENCE_NOT_FOUND")))[0] == "FARMER_NOT_FOUND"
    assert _problem(monkeypatch, AsyncMock(side_effect=err("FARMER_REFERENCE_LOOKUP_UNAVAILABLE")))[0] == "LOOKUP_UNAVAILABLE"
    assert _problem(monkeypatch, AsyncMock(side_effect=err("FARMER_REFERENCE_LOOKUP_CONFIGURATION_REQUIRED")))[0] == "LOOKUP_UNAVAILABLE"
    assert _problem(monkeypatch, AsyncMock(side_effect=err("FARMER_REFERENCE_RESPONSE_SIGNATURE_INVALID")))[0] == "LOOKUP_UNAVAILABLE"
    found = SimpleNamespace(profile={"farmer_id": "FR-123456789012", "fayda_fan_id": "9999999999999999"})
    assert _problem(monkeypatch, AsyncMock(return_value=found))[0] == "FARMER_IDENTITY_MISMATCH"
    assert _problem(monkeypatch, AsyncMock(), production_season=None)[0] == "SUBMISSION_INCOMPLETE"


def test_a_signing_failure_is_answered_not_raised(monkeypatch):
    code, text = _problem(monkeypatch, AsyncMock(side_effect=ValueError("bad key material")))
    assert code == "LOOKUP_UNAVAILABLE"
    assert text.startswith("The Farmer Registry could not be reached") and "bad key" not in text


def test_a_lookup_that_never_answers_is_cut_off(monkeypatch):
    async def never(*args, **kwargs):
        await asyncio.sleep(60)

    service = _lookup_service(monkeypatch, never)
    monkeypatch.setattr(native, "configured_lookup",
                        lambda: SimpleNamespace(lookup=never, config=SimpleNamespace(timeout_seconds=0.05)))
    code, _ = run(service._submission_problem("s", _session(_row())))
    assert code == "LOOKUP_UNAVAILABLE"


def test_validate_files_the_issue_under_the_code_of_the_problem():
    service = _reference_service(("FARMER_IDENTITY_MISMATCH", "The IDs belong to different farmers"))
    result = _validate(service, SimpleNamespace(issues=[], is_valid=True))
    assert result.issues[0].code == "FARMER_IDENTITY_MISMATCH"


def _incomplete(*messages):
    issues = [SimpleNamespace(code="SUBMISSION_INCOMPLETE", message=m) for m in messages]
    return SimpleNamespace(issues=issues, is_valid=False)


def test_an_incomplete_draft_with_an_unknown_farmer_reports_both():
    service = _reference_service(("FARMER_NOT_FOUND", "No farmer with Farmer ID FR-000000000001 is in the Farmer Registry"))
    result = _validate(service, _incomplete("Season details: fill in Production season.", "Planning: add at least one row."))
    assert not result.is_valid
    assert [i.code for i in result.issues] == ["SUBMISSION_INCOMPLETE", "SUBMISSION_INCOMPLETE", "FARMER_NOT_FOUND"]


def test_an_incomplete_draft_with_a_wrong_pair_reports_the_mismatch_too(monkeypatch):
    found = SimpleNamespace(profile={"farmer_id": "FR-123456789012", "fayda_fan_id": "9999999999999999"})
    service = _lookup_service(monkeypatch, AsyncMock(return_value=found))
    result = _validate(service, _incomplete("Planning: add at least one row."), _session(_row()))
    assert [i.code for i in result.issues] == ["SUBMISSION_INCOMPLETE", "FARMER_IDENTITY_MISMATCH"]


def test_a_complete_draft_with_a_good_farmer_is_still_valid(monkeypatch):
    found = SimpleNamespace(profile={"farmer_id": "FR-123456789012", "fayda_fan_id": "1234567890123456"})
    service = _lookup_service(monkeypatch, AsyncMock(return_value=found))
    result = _validate(service, SimpleNamespace(issues=[], is_valid=True), _session(_row()))
    assert result.is_valid and result.issues == []


def test_a_missing_or_malformed_id_is_not_looked_up(monkeypatch):
    lookup = AsyncMock()
    service = _lookup_service(monkeypatch, lookup)
    assert run(service._submission_problem("s", _session(_row(farmer_id=None)), season=False)) is None
    assert run(service._submission_problem("s", _session(_row(farmer_id="FR-12")), season=False)) is None
    lookup.assert_not_called()
