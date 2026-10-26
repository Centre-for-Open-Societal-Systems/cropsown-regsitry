"""Crop-Sown -> Farmer register cross-reference (single approval).

A single Crop-Sown intake is about a farmer who is the system-of-record of the
Farmer Registry, not of this registry. The approver sees ONE approval item, the
Crop-Sown intake itself. Its approval materialises both entries: the Crop-Sown
record (native register ingest) and the farmer as a first-class row in this
registry's Farmer register (``g2p_register_farmers``), enriched from the Farmer
Registry, not typed.

This module is the clean, env-driven replacement for the old in-container
live-hook: it carries NO secrets and opens NO hand-built database connections.
Farmer identity comes from :mod:`farmer_registry_enrichment` (the DCI partner
API + Consent Manager, both-ID required), and every database access runs in the
caller's own session (finalize or register ingest) — exactly as the core
services do — so it works unchanged in the staff-api and in the celery worker.

Behaviour:
  * finalize stages the reference — the enriched identity is snapshotted into a
    hidden shell row (``record_status='INACTIVE'``, never listed) so approval
    needs no second lookup. No Farmer change-request is raised.
  * intake approval activates it — the Crop-Sown ``post_ingest`` hook flips the
    staged shell ACTIVE in the same transaction that writes the Crop-Sown
    record, stamped with the intake approver.
  * existing-farmer skip — if the Farmer ID already has an ACTIVE row in this
    registry's Farmer register, nothing is staged or changed (no dup).
  * approval of a Farmer-register section CR stays create-or-update, so Farmer
    CRs raised before this change, and Farmer reference UPDATE CRs, still apply.

Fails open: when disabled or anything goes wrong, this logs and returns without
blocking the finalize/ingest it is attached to.

Config (env; the farmer identity settings live in farmer_registry_enrichment):
  CROPSOWN_TWO_CR_ENABLED        enable flag (default false; name kept for
                                 deployed configuration)
  CROPSOWN_FARMER_REGISTER_ID    target Farmer register id
  CROPSOWN_FARMER_TAB_ID         Farmer tab id      (default cropsown_farmer_tab)
  CROPSOWN_FARMER_SECTION_ID     Farmer section id  (default cropsown_farmer_identity_section_01)
  CROPSOWN_TWO_CR_INTAKE_TABLE   intake table to read farmer ids from
                                 (default g2p_intake_form_crop_sowns)
  CROPSOWN_TWO_CR_CREATED_BY     created_by/change_request_source actor
                                 (default cropsown-two-cr)
"""

import logging
import os
import re
import uuid
from datetime import datetime, timezone

from openg2p_fastapi_common.config import Settings as CommonSettings
from sqlalchemy import func, inspect, select, text

from .farmer_registry_enrichment import (
    compose_farmer_name,
    fetch_farmer_record,
    to_farmer_fields,
)

_logger = logging.getLogger(CommonSettings.get_config(strict=False).logging_default_logger_name)

_DEFAULT_REGISTER_ID = "fa120001-0000-4000-8000-000000000001"
_DEFAULT_TAB_ID = "cropsown_farmer_tab"
_DEFAULT_SECTION_ID = "cropsown_farmer_identity_section_01"
_DEFAULT_INTAKE_TABLE = "g2p_intake_form_crop_sowns"


def _setting(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _enabled() -> bool:
    return _setting("CROPSOWN_TWO_CR_ENABLED", "false").lower() in {"true", "1", "yes"}


def _config() -> dict:
    return {
        "register_id": _setting("CROPSOWN_FARMER_REGISTER_ID", _DEFAULT_REGISTER_ID),
        "tab_id": _setting("CROPSOWN_FARMER_TAB_ID", _DEFAULT_TAB_ID),
        "section_id": _setting("CROPSOWN_FARMER_SECTION_ID", _DEFAULT_SECTION_ID),
        "intake_table": _setting("CROPSOWN_TWO_CR_INTAKE_TABLE", _DEFAULT_INTAKE_TABLE),
        "created_by": _setting("CROPSOWN_TWO_CR_CREATED_BY", "cropsown-two-cr"),
    }


def _identity(farmer_id, fan) -> tuple[str, str] | None:
    """(Farmer ID, FAN) when both are well formed; FAN display spaces removed."""
    farmer_id = str(farmer_id or "").strip()
    fan = "".join(str(fan or "").split())
    if re.fullmatch(r"FR-[0-9]{12}", farmer_id) and re.fullmatch(r"[0-9]{16}", fan):
        return farmer_id, fan
    return None


def _models():
    # Reuse the platform's initialized model namespace; do not load tables twice.
    from openg2p_registry_extensions.register_domain.models import (
        G2PRegisterFarmer,
        G2PRegisterHistoryFarmer,
    )
    return G2PRegisterFarmer, G2PRegisterHistoryFarmer


async def _intake_farmer_ids(session, submission_id: str, cfg: dict) -> list[dict]:
    """Distinct (farmer_id, fayda_fan_id) carried by this submission's intake rows.

    Read in the finalize session, so intakes saved and finalized in one
    transaction (the ingestion worker) are visible without an early commit."""
    table = cfg["intake_table"]
    if not table.replace("_", "").isalnum():  # defensive: table name is config, keep it an identifier
        _logger.warning("Farmer reference: refusing non-identifier intake table %r", table)
        return []
    result = await session.execute(
        text(
            f"SELECT DISTINCT farmer_id, fayda_fan_id FROM {table} "
            "WHERE submission_id = :sid AND farmer_id IS NOT NULL AND farmer_id <> ''"
        ),
        {"sid": submission_id},
    )
    return [dict(row._mapping) for row in result]


async def _lock_farmer(session, farmer_id: str) -> None:
    """Serialise staging and activation per Farmer ID until the transaction ends."""
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:fid))"), {"fid": farmer_id})


async def _farmer_exists_active(session, farmer_id: str) -> bool:
    """True when this Farmer ID already has an ACTIVE row in the Farmer register."""
    found = await session.execute(
        text(
            "SELECT 1 FROM g2p_register_farmers "
            "WHERE functional_record_id = :fid AND record_status = 'ACTIVE' LIMIT 1"
        ),
        {"fid": farmer_id},
    )
    return found.first() is not None


def _reference_fields(farmer_id: str, fields: dict) -> dict:
    """Editable Farmer identity fields; status and display names are server-derived."""
    return {
        "farmer_id": farmer_id,
        "fayda_fan_id": fields.get("fayda_fan_id"),
        "first_name": fields.get("first_name"),
        "middle_name": fields.get("middle_name"),
        "last_name": fields.get("last_name"),
        "gender": fields.get("gender"),
        "date_of_birth": fields.get("date_of_birth"),
        "mobile_number": fields.get("mobile_number"),
    }


async def _stage_reference(session, farmer_id: str, fields: dict, farmer_name: str, created_by: str) -> str:
    """Snapshot the enriched identity into this farmer's hidden (INACTIVE) shell
    and return its internal_record_id.

    Reuses a non-ACTIVE shell left by an earlier submission, or by a Farmer CR
    raised before single approval, instead of inserting a second one (which would
    orphan the first and, under a unique functional_record_id, fail outright)."""
    values = _reference_fields(farmer_id, fields)
    values["farmer_name"] = farmer_name or None
    values["record_name"] = " ".join(x for x in (farmer_name, farmer_id) if x)
    values["search_text"] = " ".join(x for x in (farmer_id, farmer_name, values["fayda_fan_id"]) if x)
    existing = await session.execute(
        text(
            "SELECT internal_record_id FROM g2p_register_farmers "
            "WHERE functional_record_id = :fid AND record_status <> 'ACTIVE' "
            "ORDER BY created_at LIMIT 1"
        ),
        {"fid": farmer_id},
    )
    row = existing.first()
    if row:
        assignments = ", ".join(f"{key} = :{key}" for key in values)
        await session.execute(
            text(f"UPDATE g2p_register_farmers SET {assignments} WHERE internal_record_id = :irid"),
            {**values, "irid": row[0]},
        )
        return row[0]
    internal_record_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    columns = ", ".join(values)
    params = ", ".join(f":{key}" for key in values)
    await session.execute(
        text(
            f"INSERT INTO g2p_register_farmers (internal_record_id, functional_record_id, {columns}, "
            " record_status, status, created_by, created_at, last_approved_at, last_approved_by) "
            f"VALUES (:irid, :fid, {params}, 'INACTIVE', 'APPROVAL_STATUS_DRAFT', "
            "        :created_by, :now, :now, 'system')"
        ),
        {**values, "irid": internal_record_id, "fid": farmer_id, "created_by": created_by, "now": now},
    )
    return internal_record_id


async def enrich_intake_names(submission_id: str, session) -> int:
    """Fill the displayed intake name before native finalize takes its snapshot."""
    if not _enabled():
        return 0
    from openg2p_registry_extensions.register_domain.models import G2PIntakeFormCropSown
    if _config()["intake_table"] != G2PIntakeFormCropSown.__tablename__:
        return 0
    count = 0
    # Isolate optional enrichment failures from the native intake transaction.
    async with session.begin_nested():
        rows = (await session.execute(select(G2PIntakeFormCropSown).where(
            G2PIntakeFormCropSown.submission_id == submission_id))).scalars().all()
        matches = {}
        for row in rows:
            pair = (str(row.farmer_id or "").strip(), "".join(str(row.fayda_fan_id or "").split()))
            if pair not in matches:
                matches[pair] = await fetch_farmer_record(*pair)
            personal = matches[pair]
            if not personal:
                continue
            fields = to_farmer_fields(personal)
            name = compose_farmer_name(fields.get("first_name"), fields.get("middle_name"), fields.get("last_name"))
            if name:
                row.farmer_name = name
                count += 1
        await session.flush()
    return count


async def stage_farmer_reference(submission_id: str, session) -> None:
    """For each farmer in the submission, stage the enriched Farmer reference that
    approving the intake activates (unless the farmer is already ACTIVE). No
    Farmer change-request is raised: the intake is the only approval item.

    Writes in the finalize transaction, so the staged row commits (or rolls
    back) with the finalized intake."""
    if not _enabled():
        return
    cfg = _config()
    try:
        rows = await _intake_farmer_ids(session, submission_id, cfg)
    except Exception as exc:
        _logger.warning("Farmer reference: could not read intake farmer ids for %s: %r", submission_id, exc)
        return
    if not rows:
        _logger.info("Farmer reference: submission %s carries no farmer_id; nothing to stage", submission_id)
        return

    for row in rows:
        farmer_id = (row.get("farmer_id") or "").strip()
        fayda = (row.get("fayda_fan_id") or "").strip()
        if not farmer_id:
            continue
        try:
            personal = await fetch_farmer_record(farmer_id, fayda or None)
            if not personal:
                _logger.warning("Farmer reference: submission %s has no matching Farmer identity; verify both source identifiers", submission_id)
                continue
            fields = to_farmer_fields(personal)
            farmer_name = compose_farmer_name(fields.get("first_name"), fields.get("middle_name"), fields.get("last_name"))

            # The per-Farmer-ID lock lasts until the finalize transaction ends, so
            # concurrent submissions and an activation running in the ingest
            # worker cannot interleave. The savepoint keeps a failed write from
            # touching the intake.
            async with session.begin_nested():
                await _lock_farmer(session, farmer_id)
                if await _farmer_exists_active(session, farmer_id):
                    _logger.info("Farmer reference: farmer of submission %s is already ACTIVE; nothing staged", submission_id)
                    continue
                await _stage_reference(session, farmer_id, fields, farmer_name, cfg["created_by"])
            _logger.info("Farmer reference staged for submission %s; approving the intake activates it", submission_id)
        except Exception as exc:
            _logger.warning("Farmer reference: staging failed for submission %s: %s", submission_id, type(exc).__name__)


async def activate_farmer_reference(session, crop_row) -> int:
    """Activate the Farmer reference staged for an approved Crop-Sown record.

    Runs from the Crop-Sown ``post_ingest`` hook, inside the transaction that
    writes the approved Crop-Sown record, so both entries land together. A
    savepoint keeps any failure here from rolling back the Crop-Sown record.
    Returns 1 when a reference was activated."""
    if not _enabled():
        return 0
    pair = _identity(getattr(crop_row, "farmer_id", None), getattr(crop_row, "fayda_fan_id", None))
    if not pair or getattr(crop_row, "record_status", None) != "ACTIVE":
        return 0
    try:
        async with session.begin_nested():
            return await _activate(session, pair, crop_row, _config())
    except Exception as exc:
        _logger.warning("Farmer reference activation skipped (Crop-Sown record unaffected): %s", type(exc).__name__)
        return 0


async def _activate(session, pair: tuple[str, str], crop_row, cfg: dict) -> int:
    farmer_model, history_model = _models()
    await _lock_farmer(session, pair[0])
    rows = (await session.execute(
        select(farmer_model)
        .where(func.trim(farmer_model.functional_record_id) == pair[0])
        .order_by(farmer_model.created_at)
        .execution_options(populate_existing=True)
    )).scalars().all()
    if any(r.record_status == "ACTIVE" for r in rows):
        return 0
    staged = next((
        r for r in rows
        if _identity(r.farmer_id or r.functional_record_id, r.fayda_fan_id) == pair
        and (r.first_name or r.last_name)
    ), None)
    if staged is None:
        _logger.info("Farmer reference: nothing staged for an approved Crop-Sown record; skipped")
        return 0

    name = compose_farmer_name(staged.first_name, staged.middle_name, staged.last_name)
    if name:
        staged.farmer_name = name
    staged.record_status = "ACTIVE"
    staged.status = "APPROVAL_STATUS_APPROVED"
    staged.last_approved_at = getattr(crop_row, "last_approved_at", None) or datetime.now()
    staged.last_approved_by = getattr(crop_row, "last_approved_by", None) or "system"
    staged.record_name = staged.get_record_name_fields()
    staged.search_text = staged.get_search_text_fields()
    await session.flush()

    history_columns = inspect(history_model).columns
    history = {
        column.name: getattr(staged, column.name)
        for column in inspect(farmer_model).columns
        if column.name in history_columns
    }
    history.update(
        history_record_id=str(uuid.uuid4()),
        tab_id=cfg["tab_id"],
        section_id=cfg["section_id"],
        change_request_id=None,
        submission_id=None,
        change_request_source=cfg["created_by"],
        is_primary_section=False,
        approved_by=staged.last_approved_by,
        approved_at=staged.last_approved_at,
    )
    session.add(history_model(**history))
    await session.flush()
    _logger.info("Farmer reference activated together with its approved Crop-Sown record")
    return 1


def install(intake_service_cls) -> None:
    """Wrap ``finalize_submission_with_session`` to stage the Farmer reference
    after the platform's own finalize, and patch ``approve_register`` to
    create-or-update the Farmer register row. Idempotent and feature-flagged.
    Activation on intake approval lives in the Crop-Sown ``post_ingest`` hook."""
    if not _enabled():
        return
    if getattr(intake_service_cls, "_cropsown_two_cr_installed", False):
        return

    original_finalize = intake_service_cls.finalize_submission_with_session

    async def finalize_with_farmer_reference(self, submission_id, session, finalized_by=None, bearer_token=None, requester_sub=None):
        try:
            await enrich_intake_names(submission_id, session)
        except Exception as exc:
            _logger.warning("Crop intake name enrichment skipped: %s", type(exc).__name__)
        result = await original_finalize(
            self, submission_id, session, finalized_by=finalized_by,
            bearer_token=bearer_token, requester_sub=requester_sub,
        )
        try:
            await stage_farmer_reference(submission_id, session)
        except Exception as exc:  # never break the intake on the cross-reference
            _logger.warning("Farmer reference: finalize hook error (intake unaffected): %s", type(exc).__name__)
        return result

    intake_service_cls.finalize_submission_with_session = finalize_with_farmer_reference
    _install_approve_register(_config()["register_id"])
    intake_service_cls._cropsown_two_cr_installed = True
    _logger.info("CropSown farmer-reference hooks installed (single approval: finalize staging + approve_register create-or-update)")


def _install_approve_register(farmer_register_id: str) -> None:
    """Patch G2PRegisterChangeRequestService.approve_register so a Farmer-register
    section CR creates the row from the DRAFT shell when absent, updates otherwise,
    and flips it ACTIVE. Other registers are untouched."""
    from openg2p_registry_core.schemas.change_request import ChangeActionEnum
    from openg2p_registry_core.services.g2p_register_change_request_service import (
        G2PRegisterChangeRequestService,
    )
    from sqlalchemy.orm.attributes import flag_modified

    if getattr(G2PRegisterChangeRequestService, "_cropsown_approve_coru_installed", False):
        return
    original_approve_register = G2PRegisterChangeRequestService.approve_register

    async def approve_register_create_or_update(self, change_request, section, session):
        if getattr(section, "section_register_id", None) != farmer_register_id:
            return await original_approve_register(self, change_request, section, session)

        _reg_def, register_class, schema_class = await self._get_register_class_and_schema(
            section.section_register_id, session)
        payload = await self._get_change_request_payload(change_request.change_request_id, session)
        existing = await self._get_existing_record(register_class, change_request.internal_record_id, session)
        changed = False
        for change_payload in (payload.change_payload or []):
            action = change_payload.get("edit_action", ChangeActionEnum.UPDATE.value)
            if action == ChangeActionEnum.NO_CHANGE.value:
                continue
            change_payload["internal_record_id"] = change_request.internal_record_id
            schema_instance = schema_class(**(change_payload or {}))
            if existing is None:
                record_data = self._build_record_data(schema_instance.dict(), change_payload, register_class)
                record_data["internal_record_id"] = change_request.internal_record_id
                fid = change_payload.get("farmer_id") or record_data.get("farmer_id")
                self._set_data_if_column(record_data, register_class, "functional_record_id", fid)
                self._set_data_if_column(record_data, register_class, "created_by", change_request.created_by)
                self._set_data_if_column(record_data, register_class, "created_at", change_request.created_at)
                if not record_data.get("record_name"):
                    self._set_data_if_column(record_data, register_class, "record_name", change_payload.get("farmer_name"))
                existing = register_class(**record_data)
                session.add(existing)
                _logger.info("two-CR approve: created Farmer row internal_id=%s name=%s",
                             change_request.internal_record_id, change_payload.get("farmer_name"))
            else:
                self._update_existing_record(existing, schema_instance.dict(), change_payload, register_class)
                _logger.info("two-CR approve: updated Farmer row internal_id=%s name=%s",
                             change_request.internal_record_id, change_payload.get("farmer_name"))
            # These derived fields are intentionally absent from the editable
            # section payload. Compute them only when normal approval succeeds.
            farmer_name = compose_farmer_name(
                getattr(existing, "first_name", None),
                getattr(existing, "middle_name", None),
                getattr(existing, "last_name", None),
            )
            if farmer_name:
                self._set_if_column(existing, "farmer_name", farmer_name)
                self._set_if_column(existing, "record_name", farmer_name)
            self._set_if_column(existing, "search_text", existing.get_search_text_fields())
            self._set_if_column(existing, "record_status", "ACTIVE")
            self._set_if_column(existing, "status", "APPROVAL_STATUS_APPROVED")
            self._set_if_column(existing, "last_approved_at", change_request.approved_at)
            self._set_if_column(existing, "last_approved_by", change_request.approved_by or "system")
            changed = True
        if changed:
            await session.flush()
            flag_modified(payload, "change_payload")

    G2PRegisterChangeRequestService.approve_register = approve_register_create_or_update
    G2PRegisterChangeRequestService._cropsown_approve_coru_installed = True
    _logger.info("CropSown two-CR: approve_register create-or-update patch installed")
