"""Text shown for an approved intake while its Farmer ADD is not yet approved."""
import importlib
import importlib.util
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

PACKAGE = "openg2p_registry_cropsown_extension"
messages = importlib.import_module(PACKAGE + ".farmer_reference.messages")


class TextTests(unittest.TestCase):
    def test_waiting_text_is_the_agreed_sentence(self):
        self.assertEqual(messages.WAITING_FOR_FARMER_APPROVAL, "Approved, waiting for Farmer approval")

    def test_texts_are_readable(self):
        for text in (messages.WAITING_FOR_FARMER_APPROVAL, messages.FARMER_APPROVAL_REJECTED,
                     messages.FARMER_REFERENCE_MISSING, messages.FARMER_LOOKUP_PENDING):
            self.assertNotIn("_", text)
            self.assertNotIn("FARMER_REFERENCE", text)

    def test_held_text_by_reference_state(self):
        pending = SimpleNamespace(state="PENDING")
        self.assertEqual(messages.held_text(SimpleNamespace(state="PENDING"), None),
                         messages.WAITING_FOR_FARMER_APPROVAL)
        self.assertEqual(messages.held_text(None, pending), messages.WAITING_FOR_FARMER_APPROVAL)
        self.assertEqual(messages.held_text(SimpleNamespace(state="REJECTED"), None),
                         messages.FARMER_APPROVAL_REJECTED)
        self.assertEqual(messages.held_text(None, None), messages.FARMER_REFERENCE_MISSING)

    def test_waiting_recognition_includes_rows_held_before_the_text_change(self):
        self.assertTrue(messages.is_waiting_text(messages.WAITING_FOR_FARMER_APPROVAL))
        self.assertTrue(messages.is_waiting_text("FARMER_REFERENCE_DEPENDENCY_PENDING"))
        self.assertFalse(messages.is_waiting_text(messages.FARMER_APPROVAL_REJECTED))
        self.assertFalse(messages.is_waiting_text(None))


@unittest.skipUnless(importlib.util.find_spec("openg2p_registry_core"), "Requires the registry platform")
class FlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.native = importlib.import_module(PACKAGE + ".farmer_reference.native")
        self.models = importlib.import_module(PACKAGE + ".farmer_reference.models")

    def submission(self, **fields):
        values = dict(submission_id="s1", register_id="r1", approval_status="APPROVED", draft_status="FINAL",
                      register_ingest_process_status="PENDING", register_ingest_process_last_error_code=None)
        values.update(fields)
        return SimpleNamespace(**values)

    async def approve(self, reference, pending_lookup=None):
        native = self.native
        submission = self.submission()
        session = MagicMock()
        session.flush = AsyncMock()
        records = {
            (self.models.FarmerSubmissionDependency, "s1"): SimpleNamespace(reference_id="ref") if reference else None,
            (self.models.FarmerReference, "ref"): reference,
            (self.models.FarmerPendingLookup, "s1"): pending_lookup,
        }
        session.get = AsyncMock(side_effect=lambda model, key, **kw: records.get((model, key)))
        service = object.__new__(native.ReferenceIntakeService)
        service._get_register_definition = AsyncMock(return_value=SimpleNamespace(register_mnemonic="CropSown"))
        intake_status = AsyncMock()
        with patch.object(native.G2PIntakeFormDataService, "approve_submission_with_session",
                          AsyncMock(return_value=submission)), \
                patch.object(native, "set_intake_farmer_status", intake_status):
            await service.approve_submission_with_session("s1", session, "reviewer")
        return submission, intake_status

    async def test_approved_while_farmer_add_is_pending_shows_waiting_text(self):
        submission, intake_status = await self.approve(SimpleNamespace(state="PENDING"))
        self.assertEqual(submission.register_ingest_process_status, "NOT_APPLICABLE")
        self.assertEqual(submission.register_ingest_process_last_error_code, "Approved, waiting for Farmer approval")
        intake_status.assert_awaited_once()
        self.assertEqual(intake_status.await_args.args[2], "Approved, waiting for Farmer approval")

    async def test_approved_after_farmer_rejection_shows_rejection_text(self):
        submission, _ = await self.approve(SimpleNamespace(state="REJECTED"))
        self.assertEqual(submission.register_ingest_process_last_error_code, messages.FARMER_APPROVAL_REJECTED)

    async def test_approved_with_approved_farmer_is_untouched(self):
        submission, intake_status = await self.approve(SimpleNamespace(state="APPROVED"))
        self.assertEqual(submission.register_ingest_process_status, "PENDING")
        self.assertIsNone(submission.register_ingest_process_last_error_code)
        intake_status.assert_not_awaited()

    async def decide(self, approved, submission):
        native = self.native
        request = SimpleNamespace(reference_id="ref", action="ADD")
        first, second = MagicMock(), MagicMock()
        first.scalar_one.return_value = request
        second.scalars.return_value.all.return_value = [submission]
        session = MagicMock()
        session.execute = AsyncMock(side_effect=[first, second])
        session.flush = AsyncMock()
        intake_status = AsyncMock()
        onboarding = MagicMock(record_decision=AsyncMock())
        with patch.object(native, "onboarding_service", return_value=onboarding), \
                patch.object(native, "set_intake_farmer_status", intake_status):
            await native.record_native_decision(session, "cr1", approved)
        return intake_status

    async def test_farmer_approval_clears_the_waiting_text_and_releases_ingest(self):
        submission = self.submission(register_ingest_process_status="NOT_APPLICABLE",
                                     register_ingest_process_last_error_code=messages.WAITING_FOR_FARMER_APPROVAL)
        intake_status = await self.decide(True, submission)
        self.assertEqual(submission.register_ingest_process_status, "PENDING")
        self.assertIsNone(submission.register_ingest_process_last_error_code)
        self.assertEqual(intake_status.await_args.args[2], messages.FARMER_REFERENCE_LINKED)

    async def test_farmer_rejection_replaces_the_waiting_text(self):
        submission = self.submission(register_ingest_process_status="NOT_APPLICABLE",
                                     register_ingest_process_last_error_code=messages.WAITING_FOR_FARMER_APPROVAL)
        intake_status = await self.decide(False, submission)
        self.assertEqual(submission.register_ingest_process_last_error_code, messages.FARMER_APPROVAL_REJECTED)
        self.assertEqual(intake_status.await_args.args[2], messages.FARMER_APPROVAL_REJECTED)
