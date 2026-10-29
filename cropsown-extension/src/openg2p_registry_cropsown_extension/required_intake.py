"""A Crop Sown intake cannot be saved or submitted with a required field empty.

The platform validates only the fields a section save carries (the staff UI
omits the ones nobody touched) and checks nothing at submit. This mixin makes
`widget-required` in the section metadata (required_fields.py) binding on the
server, for every channel: web, ODK and partner ingestion all save sections and
finalize through this service.

- save: the section being saved, merged with what the submission already
  stores for it, must have every required field. "Next" on an empty required
  section is refused, naming the fields;
- finalize: every section of the form must be complete, including sections
  never opened, so an incomplete submission never starts an approval or a
  Farmer lookup. The service's finalize calls ensure_form_complete first,
  because it does its Farmer lookup before it reaches the platform.

An incomplete ingestion is refused with the same readable sentence. The
ingestion worker records the service error on the ingestion row, so nothing
crashes and nobody has to read a log.

Put it first in the intake service's bases, before DirectApprovalClosed.
It defines neither approve_submission nor approve_change_request.
"""

import logging

from .required_fields import section_problems

_logger = logging.getLogger("oan-required-fields")

_STORED_ONLY = {"submission_id", "section_id"}
_NOT_A_FIELD = ("edit_action", "oan_documents")


def refuse(problems):
    from openg2p_registry_core.errors import G2PRegistryErrorCodes, G2PRegistryException

    raise G2PRegistryException(
        code=G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[1],
        message="; ".join(dict.fromkeys(problems)),
    )


class RequiredFieldsMixin:
    async def _required_messages(self, session) -> dict:
        """The default language's translations; the sentences read fine without."""
        import json

        from sqlalchemy import text

        try:
            found = (await session.execute(text(
                "SELECT domain_translation FROM registry_languages WHERE is_default"))).scalar()
        except Exception as error:  # noqa: BLE001 - a missing translation never blocks the check
            _logger.warning("required fields: translations not read (%s)", error)
            return {}
        found = json.loads(found) if isinstance(found, str) else found
        return found if isinstance(found, dict) else {}

    async def save_intake_form_submission_with_session(
        self, submission_id, section_id, section_payload, section_register_id,
        form_id, register_id, created_by, session, documents=None,
    ):
        problems = await self._required_on_save(
            submission_id, section_id, section_payload, section_register_id, documents, session)
        if problems:
            refuse(problems)
        return await super().save_intake_form_submission_with_session(
            submission_id, section_id, section_payload, section_register_id,
            form_id, register_id, created_by, session, documents=documents)

    async def ensure_form_complete(self, submission_id, session):
        """Refuse a submission whose form still has a required field empty.

        A service whose finalize does work of its own before calling the
        platform (the Farmer lookup) calls this first, so an incomplete form
        never reaches a lookup or an approval.
        """
        problems = await self._required_on_finalize(submission_id, session)
        if problems:
            refuse(problems)

    async def _required_on_save(
        self, submission_id, section_id, section_payload, section_register_id, documents, session
    ) -> list:
        section = await self._get_section_or_error(section_id, session)
        stored = await self._stored_records(submission_id, section_register_id, session)
        surviving = [r for r in self._records_for_validation(section_payload) if isinstance(r, dict)]
        records = []
        for record in surviving:
            known = stored.get(str(record.get("internal_record_id") or ""))
            if known is None and not section.is_list and len(stored) == 1:
                known = next(iter(stored.values()))
            changes = {k: v for k, v in record.items() if k not in _NOT_A_FIELD}
            records.append({**(known or {}), **changes})
        saved_files = {getattr(d, "label", None) for d in documents or []}
        for record in surviving:
            saved_files |= set((record.get("oan_documents") or {}).get(section.section_mnemonic) or {})
        saved_files |= await self._stored_file_labels(submission_id, section_id, session)
        values = {section_register_id: records[0] if records else {}}
        return section_problems(
            section.section_ui_schema or {}, bool(section.is_list), records, values,
            await self._required_messages(session), saved_files, section.section_description or "")

    async def _required_on_finalize(self, submission_id, session) -> list:
        submission = await self._get_submission_or_error(submission_id, session)
        sections = await self._get_form_sections(submission.form_id, session)
        gathered = []
        values: dict = {}
        for section in sections:
            records = await self._section_records(submission.submission_id, section, session)
            gathered.append((section, records))
            if not section.is_list and records and not values.get(section.section_register_id):
                values[section.section_register_id] = records[0]
        messages = await self._required_messages(session)
        problems: list = []
        for section, records in gathered:
            files = await self._stored_file_labels(submission.submission_id, section.section_id, session)
            problems += section_problems(
                section.section_ui_schema or {}, bool(section.is_list), records, values, messages, files,
                section.section_description or "")
        return problems

    async def _stored_records(self, submission_id, section_register_id, session) -> dict:
        """The rows the submission already stores for a register, by record id."""
        if not submission_id:
            return {}
        try:
            submission = await self._get_submission_or_error(submission_id, session)
            intake_class = await self._resolve_intake_form_class(section_register_id, session)
            rows = await self._get_intake_rows(intake_class, submission.submission_id, session)
        except Exception as error:  # noqa: BLE001 - an unknown submission is the platform's to report
            _logger.warning("required fields: no stored rows for submission %s (%s)", submission_id, error)
            return {}
        return {str(k): self._serialize_model(v, _STORED_ONLY) for k, v in rows.items()}

    async def _section_records(self, submission_id, section, session) -> list:
        from sqlalchemy import select

        intake_class = await self._resolve_intake_form_class(section.section_register_id, session)
        rows = (await session.execute(select(intake_class).where(
            *self._submission_section_filters(intake_class, submission_id, section.section_id)))).scalars().all()
        return [self._serialize_model(row, _STORED_ONLY) for row in rows]

    async def _stored_file_labels(self, submission_id, section_id, session) -> set:
        if not submission_id:
            return set()
        from openg2p_registry_core.models import G2PIntakeFormSectionDocuments
        from sqlalchemy import select

        rows = await session.execute(select(G2PIntakeFormSectionDocuments.label).where(
            G2PIntakeFormSectionDocuments.submission_id == str(submission_id),
            G2PIntakeFormSectionDocuments.section_id == section_id))
        return set(rows.scalars().all())
