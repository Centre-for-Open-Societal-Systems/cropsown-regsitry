"""ODK Ingestion Hooks for OpenG2P Crop Sown Registry.

This is a standalone, independent extension module. It intercepts validation
and ensures database engine initialization and submodule aliasing during
ingestion without requiring any changes to base platform files.
"""

import importlib
import logging
import os
import sys
from contextvars import ContextVar

_logger = logging.getLogger("openg2p.odk_ingest_hooks")
_active_session: ContextVar = ContextVar("odk_active_session", default=None)

# Every service's settings prefix, most specific shared one first. Each pod sets
# only its own prefix (the staff API sets REGISTRY_STAFF_PORTAL_API_*, the beat
# producer REGISTRY_CELERY_BEAT_*, ...), so every setting must be looked up
# under all of them — a lookup that skips a prefix silently falls through.
_SETTING_PREFIXES = (
    "COMMON_",
    "REGISTRY_CORE_",
    "REGISTRY_PARTNER_API_",
    "REGISTRY_CELERY_WORKERS_",
    "REGISTRY_CELERY_BEAT_",
    "REGISTRY_STAFF_PORTAL_API_",
)


def _setting(name, default=None):
    """First non-empty <prefix><name> across the service prefixes, else default."""
    for prefix in _SETTING_PREFIXES:
        value = os.environ.get(prefix + name)
        if value:
            return value
    return default


def _db_dsn(kind, db_prefix):
    """Build a DSN from <prefix><db_prefix>_* settings, or None when any credential is missing.

    There are deliberately no credential defaults: a guessed user or password
    (the old "cropsown_user"/"master_data_pass") only turns a missing setting into
    a login failure far from its cause, so the platform's own engine is kept instead.
    """
    hostname = _setting(f"{db_prefix}_HOSTNAME")
    dbname = _setting(f"{db_prefix}_DBNAME")
    username = _setting(f"{db_prefix}_USERNAME")
    password = _setting(f"{db_prefix}_PASSWORD")
    port = _setting(f"{db_prefix}_PORT", "5432")
    missing = [n for n, v in (("HOSTNAME", hostname), ("DBNAME", dbname),
                              ("USERNAME", username), ("PASSWORD", password)) if not v]
    if missing:
        _logger.warning("ODK Hook: %s DB settings missing (%s_%s); keeping the platform engine",
                        kind, db_prefix, "/".join(missing))
        return None
    return f"postgresql+asyncpg://{username}:{password}@{hostname}:{port}/{dbname}"


def _get_registry_engine():
    """Construct an AsyncEngine connected to the primary registry database."""
    from sqlalchemy.ext.asyncio import create_async_engine
    dsn = _db_dsn("registry", "DB")
    return create_async_engine(dsn) if dsn else None


def _ensure_dbengine_initialized():
    """Ensure dbengine GlobalVar is set to a valid AsyncEngine pointing to the registry DB."""
    try:
        from openg2p_fastapi_common.context import dbengine
        eng = dbengine.get()
        needs_fix = eng is None or (hasattr(eng, "url") and eng.url.host in ("localhost", "127.0.0.1", None))
        if needs_fix:
            try:
                from openg2p_registry_celery_worker.engine import Engine
                eng = Engine.get_async_engine()
            except Exception:
                eng = None
            if eng is None:
                eng = _get_registry_engine()
            if eng is not None:
                dbengine.set(eng)
                _logger.info("ODK Hook: dbengine initialized to %s", eng.url)
    except Exception as e:
        _logger.debug("ODK Hook: Error in _ensure_dbengine_initialized: %s", e)


def _patch_base_initializer():
    """Patch BaseInitializer.init_db to avoid binding to localhost."""
    try:
        from openg2p_fastapi_common.app import Initializer as BaseInitializer
        if not hasattr(BaseInitializer, "_orig_init_db"):
            orig_init_db = BaseInitializer.init_db
            BaseInitializer._orig_init_db = orig_init_db

            def patched_init_db(self):
                orig_init_db(self)
                _ensure_dbengine_initialized()

            BaseInitializer.init_db = patched_init_db
            _logger.info("ODK Hook: Patched BaseInitializer.init_db")
    except Exception as e:
        _logger.debug("ODK Hook: Error patching BaseInitializer.init_db: %s", e)


def _patch_document_handler():
    """Ensure DocumentHandler uses the correct MinIO endpoint inside docker."""
    try:
        from openg2p_registry_core.helpers.document import document_factory
        from openg2p_registry_core.helpers.document.minio_client import MinioClient
        from openg2p_registry_core.helpers.document.document_handlers import DocumentHandler
        from openg2p_fastapi_common.component import component_registry

        endpoint = _setting("MINIO_ENDPOINT")
        access_key = _setting("MINIO_ACCESS_KEY")
        secret_key = _setting("MINIO_SECRET_KEY")
        secure = _setting("MINIO_SECURE", "false").lower() == "true"
        if not (endpoint and access_key and secret_key):
            # No "minioadmin" guess: wrong keys surface later as S3 AccessDenied.
            _logger.warning("ODK Hook: MinIO endpoint/keys not set; keeping the platform DocumentHandler")
            return

        def make_minio_client():
            return MinioClient(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
            )

        document_factory._create_document_handler = make_minio_client

        # Replace any existing DocumentHandler in component_registry if it pointed to localhost
        cr = component_registry.get()
        if cr:
            for i, c in enumerate(cr):
                if isinstance(c, DocumentHandler):
                    cr[i] = make_minio_client()
                    _logger.info("ODK Hook: Replaced DocumentHandler with docker minio client")
                    break
    except Exception as e:
        _logger.debug("ODK Hook: Error in _patch_document_handler: %s", e)


def _ensure_core_services():
    """Ensure Core services like G2PDocumentService are initialized."""
    try:
        from openg2p_registry_core.services import G2PDocumentService
        if G2PDocumentService.get_component() is None:
            from openg2p_registry_core.app import Initializer as CoreInitializer
            CoreInitializer().initialize()
            _logger.info("ODK Hook: CoreInitializer initialized core services")
    except Exception as e:
        _logger.debug("ODK Hook: Error initializing core services: %s", e)


def _ensure_master_data_engine():
    """Ensure db_engine_master_data connects to postgres rather than defaulting to localhost."""
    try:
        from openg2p_registry_core import engine
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import NullPool

        dsn = _db_dsn("master data", "MASTER_DATA_DB")
        if dsn is None:
            return
        eng = create_async_engine(dsn, poolclass=NullPool)
        if engine._engines is None:
            engine._engines = {}
        engine._engines["db_engine_master_data"] = eng
        # eng.url masks the password; the raw dsn must never be logged.
        _logger.info("ODK Hook: Initialized db_engine_master_data to %s", eng.url)
    except Exception as e:
        _logger.debug("ODK Hook: Error initializing master data engine: %s", e)


def _alias_extension_modules():
    """Ensure openg2p_registry_extensions and all its subpackages alias to cropsown extension."""
    ext = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_cropsown_extension")
    if "openg2p_registry_extensions" not in sys.modules:
        try:
            sys.modules["openg2p_registry_extensions"] = sys.modules.get(ext) or importlib.import_module(ext)
            for sub in (
                "config",
                "ingestion_pipeline",
                "ingestion_pipeline.enricher_services",
                "register_domain",
                "register_domain.models",
                "register_domain.schemas",
                "register_domain.services",
                "register_domain.controllers",
                "register_domain.factory",
            ):
                try:
                    sys.modules[f"openg2p_registry_extensions.{sub}"] = importlib.import_module(f"{ext}.{sub}")
                except Exception:
                    pass
            _logger.info("ODK Hook: Aliased openg2p_registry_extensions -> %s", ext)
        except Exception as e:
            _logger.debug("ODK Hook: Error aliasing extension modules: %s", e)


def _patch_request_response_helper():
    """Patch RequestResponseHelper._construct_data_model_response for Pydantic v2 JSON serialization."""
    try:
        from openg2p_registry_partner_api.ingestion.helpers.request_response_helper import RequestResponseHelper
        from fastapi.responses import JSONResponse
        from openg2p_registry_core.helpers import TemplateHelper

        if not hasattr(RequestResponseHelper, "_orig_construct_data_model_response"):
            RequestResponseHelper._orig_construct_data_model_response = RequestResponseHelper._construct_data_model_response

            def patched_construct_data_model_response(self, response_template_store_id, response):
                if not response_template_store_id:
                    return JSONResponse(content=response.model_dump(mode="json"))

                template_helper = TemplateHelper.get_component()
                response_data = response.model_dump(mode="json")
                response_data = template_helper.render_with_template(
                    document_store_id=response_template_store_id,
                    data=response_data,
                    expand_data=False,
                )
                return JSONResponse(content=response_data)

            RequestResponseHelper._construct_data_model_response = patched_construct_data_model_response
            _logger.info("ODK Hook: Patched RequestResponseHelper._construct_data_model_response")
    except Exception as e:
        _logger.debug("Could not patch RequestResponseHelper: %s", e)


def _patch_celery_worker():
    """Patch ingest_data_worker to bind dbengine and active session."""
    try:
        import openg2p_registry_celery_worker.tasks.ingest_data_worker as worker_mod
        if worker_mod and not hasattr(worker_mod, "_orig_save_sections_async"):
            orig_save_sections_async = worker_mod._save_sections_async
            worker_mod._orig_save_sections_async = orig_save_sections_async

            async def patched_save_sections_async(
                submission_id: str,
                incoming_classified_data,
                ordered_sections: list,
                transformed_data: dict,
                session,
            ) -> None:
                try:
                    from openg2p_fastapi_common.context import dbengine
                    if hasattr(session, "bind") and session.bind:
                        dbengine.set(session.bind)
                    else:
                        _ensure_dbengine_initialized()
                    _ensure_core_services()
                except Exception:
                    pass

                t_session = _active_session.set(session)
                try:
                    # Auto-enrich intake records with farmer name, location, and status
                    try:
                        from sqlalchemy import text
                        for sec_key in ("cs_common_intake_record", "cs_intake_record"):
                            rows = transformed_data.get(sec_key) or []
                            for row in rows:
                                fayda = row.get("fayda_fan_id")
                                f_name = row.get("farmer_name")
                                if not row.get("status"):
                                    row["status"] = "DRAFT"
                                if fayda and (not f_name or not str(f_name).strip() or not row.get("region")):
                                    res = await session.execute(
                                        text("""
                                            SELECT farmer_name, farmer_id, region, zone, woreda, kebele,
                                                   address_line_1, address_line_2, latitude, longitude, gps_coordinate
                                            FROM g2p_intake_form_crop_sowns
                                            WHERE fayda_fan_id = :fayda AND farmer_name IS NOT NULL AND farmer_name != ''
                                            ORDER BY created_at DESC LIMIT 1
                                        """),
                                        {"fayda": str(fayda).strip()}
                                    )
                                    r = res.fetchone()
                                    if not r:
                                        res_reg = await session.execute(
                                            text("""
                                                SELECT farmer_name, farmer_id, region, zone, woreda, kebele,
                                                       address_line_1, address_line_2, latitude, longitude,
                                                       latitude || ', ' || longitude as gps_coordinate
                                                FROM g2p_register_crop_sowns
                                                WHERE fayda_fan_id = :fayda AND farmer_name IS NOT NULL AND farmer_name != ''
                                                ORDER BY created_at DESC LIMIT 1
                                            """),
                                            {"fayda": str(fayda).strip()}
                                        )
                                        r = res_reg.fetchone()
                                    if r:
                                        if not row.get("farmer_name") and r[0]:
                                            row["farmer_name"] = r[0]
                                        if not row.get("farmer_id") and r[1]:
                                            row["farmer_id"] = r[1]
                                        if not row.get("region") and r[2]:
                                            row["region"] = r[2]
                                        if not row.get("zone") and r[3]:
                                            row["zone"] = r[3]
                                        if not row.get("woreda") and r[4]:
                                            row["woreda"] = r[4]
                                        if not row.get("kebele") and r[5]:
                                            row["kebele"] = r[5]
                                        if not row.get("latitude") and r[8]:
                                            row["latitude"] = r[8]
                                        if not row.get("longitude") and r[9]:
                                            row["longitude"] = r[9]
                                        if not row.get("gps_coordinate") and r[10]:
                                            row["gps_coordinate"] = r[10]

                                f_id = row.get("farmer_id")
                                if f_id:
                                    row["record_name"] = str(f_id)
                                else:
                                    row["record_name"] = None
                                for attr_id, code_key, name_key in (
                                    ("REGION", "region", "region_name"),
                                    ("ZONE", "zone", "zone_name"),
                                    ("WOREDA", "woreda", "woreda_name"),
                                    ("KEBELE", "kebele", "kebele_name"),
                                ):
                                    val = row.get(code_key)
                                    if val:
                                        val_str = str(val).strip()
                                        try:
                                            q = text("""
                                                SELECT value_id, value_display FROM g2p_attribute_values 
                                                WHERE attribute_id = :attr_id 
                                                  AND (value_id = :val OR value_code = :val 
                                                       OR value_display ILIKE :val
                                                       OR value_id = (:attr_id || '_' || :val)
                                                       OR value_id = (:attr_id || '_ET' || :val)
                                                       OR value_code LIKE ('%' || :val)
                                                       OR value_id LIKE ('%' || :val))
                                                ORDER BY 
                                                  CASE WHEN value_id = :val THEN 1
                                                       WHEN value_code = :val THEN 2
                                                       WHEN value_id = (:attr_id || '_' || :val) THEN 3
                                                       ELSE 4 END
                                                LIMIT 1
                                            """)
                                            res = (await session.execute(q, {"attr_id": attr_id, "val": val_str})).first()
                                            if res:
                                                row[code_key] = res[0]
                                                row[name_key] = res[1]
                                            else:
                                                row[name_key] = val_str
                                        except Exception as err:
                                            _logger.debug("Error looking up display name for %s: %s", val_str, err)
                                            row[name_key] = val_str

                        # Ensure cs_cropsown_location has gps_coordinate
                        loc_rows = transformed_data.get("cs_cropsown_location") or []
                        for lr in loc_rows:
                            lat = lr.get("latitude")
                            lon = lr.get("longitude")
                            if lat and lon and not lr.get("gps_coordinate"):
                                lr["gps_coordinate"] = f"{lat}, {lon}"
                    except Exception as e:
                        _logger.debug("Error in auto-enriching intake submission: %s", e)

                    return await orig_save_sections_async(
                        submission_id,
                        incoming_classified_data,
                        ordered_sections,
                        transformed_data,
                        session,
                    )
                finally:
                    _active_session.reset(t_session)

            worker_mod._save_sections_async = patched_save_sections_async
            _logger.info("ODK Hook: Patched ingest_data_worker._save_sections_async")
    except Exception as e:
        _logger.debug("Could not patch ingest_data_worker: %s", e)


def _connect_celery_signals():
    """Register Celery signals to ensure dbengine is set for all background tasks."""
    try:
        from celery.signals import task_prerun

        @task_prerun.connect
        def on_celery_task_prerun(*args, **kwargs):
            _ensure_dbengine_initialized()
            _ensure_core_services()
    except Exception:
        pass


def _patch_intake_form_data_service():
    """Patch G2PIntakeFormDataService to handle land_id validation and Decimal serialization."""
    try:
        from openg2p_registry_core.services.intake_form_data_service import G2PIntakeFormDataService
        from sqlalchemy import select, text
        from decimal import Decimal

        if not hasattr(G2PIntakeFormDataService, "_odk_patched_serialize_model"):
            G2PIntakeFormDataService._odk_patched_serialize_model = True
            orig_serialize = G2PIntakeFormDataService._serialize_model

            def patched_serialize_model(self, row, exclude=None):
                data = orig_serialize(self, row, exclude)
                for k, v in data.items():
                    if isinstance(v, Decimal):
                        data[k] = str(v)
                return data

            G2PIntakeFormDataService._serialize_model = patched_serialize_model
            _logger.info("ODK Hook: Patched G2PIntakeFormDataService._serialize_model for Decimal handling")

        if not hasattr(G2PIntakeFormDataService, "_odk_patched_insert_live_register_row"):
            G2PIntakeFormDataService._odk_patched_insert_live_register_row = True
            orig_insert = G2PIntakeFormDataService._insert_live_register_row

            async def patched_insert_live_register_row(
                self,
                submission,
                section,
                register_definition,
                schema_class,
                register_class,
                intake_row,
                session,
                root_record_id_mapping=None,
            ):
                res = await orig_insert(
                    self,
                    submission,
                    section,
                    register_definition,
                    schema_class,
                    register_class,
                    intake_row,
                    session,
                    root_record_id_mapping,
                )
                try:
                    if hasattr(register_class, "zone_name") and hasattr(intake_row, "internal_record_id"):
                        for attr_id, code_key, name_key in (
                            ("REGION", "region", "region_name"),
                            ("ZONE", "zone", "zone_name"),
                            ("WOREDA", "woreda", "woreda_name"),
                            ("KEBELE", "kebele", "kebele_name"),
                        ):
                            cur_name = getattr(intake_row, name_key, None)
                            cur_code = getattr(intake_row, code_key, None)
                            val = cur_name or cur_code
                            if val:
                                q = text("""
                                    SELECT value_display FROM g2p_attribute_values 
                                    WHERE attribute_id = :attr_id 
                                      AND (value_id = :val OR value_code = :val 
                                           OR value_display ILIKE :val
                                           OR value_id = (:attr_id || '_' || :val)
                                           OR value_id = (:attr_id || '_ET' || :val)
                                           OR value_code LIKE ('%' || :val)
                                           OR value_id LIKE ('%' || :val))
                                    ORDER BY 
                                      CASE WHEN value_id = :val THEN 1
                                           WHEN value_code = :val THEN 2
                                           WHEN value_id = (:attr_id || '_' || :val) THEN 3
                                           ELSE 4 END
                                    LIMIT 1
                                """)
                                disp = (await session.execute(q, {"attr_id": attr_id, "val": str(val).strip()})).scalar_one_or_none()
                                if disp:
                                    update_q = text(f"""
                                        UPDATE g2p_register_crop_sowns 
                                        SET {name_key} = :disp 
                                        WHERE internal_record_id = :rec_id
                                    """)
                                    await session.execute(update_q, {"disp": disp, "rec_id": intake_row.internal_record_id})
                except Exception as e:
                    _logger.debug("Error updating admin display names in register: %s", e)
                return res

            G2PIntakeFormDataService._insert_live_register_row = patched_insert_live_register_row
            _logger.info("ODK Hook: Patched G2PIntakeFormDataService._insert_live_register_row for admin unit display names")

        if hasattr(G2PIntakeFormDataService, "_odk_patched_validate_land_ids"):
            return
        G2PIntakeFormDataService._odk_patched_validate_land_ids = True
        orig_fn = G2PIntakeFormDataService._validate_land_ids_against_fayda_records

        async def patched_validate_land_ids(self, submission, session):
            try:
                return await orig_fn(self, submission, session)
            except Exception as exc:
                # If validation failed because land_id was not yet in active registers,
                # check if it exists in pending intake forms
                fayda_fan_id = None
                sections = await self._get_form_sections(submission.form_id, session)
                sowing_land_ids = set()
                infestation_land_ids = set()
                harvest_land_ids = set()

                for section in sections:
                    _reg_def, intake_cls, _reg_cls, _schema_cls, _hist_cls = (
                        await self._resolve_submission_models(section.section_register_id, session)
                    )
                    rows = (
                        await session.execute(
                            select(intake_cls).where(
                                *self._submission_section_filters(
                                    intake_cls,
                                    submission.submission_id,
                                    section.section_id,
                                )
                            )
                        )
                    ).scalars().all()

                    for row in rows:
                        if not fayda_fan_id and hasattr(row, "fayda_fan_id") and getattr(row, "fayda_fan_id"):
                            fayda_fan_id = getattr(row, "fayda_fan_id")
                        land_id = getattr(row, "land_id", None)
                        if land_id and str(land_id).strip():
                            clean_land = str(land_id).strip()
                            reg_mnemonic = _reg_def.register_mnemonic
                            if reg_mnemonic == "Sowing":
                                sowing_land_ids.add(clean_land)
                            elif reg_mnemonic == "Infestation":
                                infestation_land_ids.add(clean_land)
                            elif reg_mnemonic == "Harvest":
                                harvest_land_ids.add(clean_land)

                all_check_lands = sowing_land_ids | infestation_land_ids | harvest_land_ids
                if not all_check_lands:
                    raise exc

                intake_lands = set()
                if fayda_fan_id:
                    res_fayda = (
                        await session.execute(
                            text("""
                                SELECT DISTINCT p.land_id 
                                FROM g2p_intake_form_plannings p
                                JOIN g2p_intake_form_crop_sowns cs ON p.submission_id = cs.submission_id
                                WHERE cs.fayda_fan_id = :fayda AND p.land_id IS NOT NULL
                                UNION
                                SELECT DISTINCT c.land_id 
                                FROM g2p_intake_form_cultivations c
                                JOIN g2p_intake_form_crop_sowns cs ON c.submission_id = cs.submission_id
                                WHERE cs.fayda_fan_id = :fayda AND c.land_id IS NOT NULL
                                UNION
                                SELECT DISTINCT s.land_id 
                                FROM g2p_intake_form_sowings s
                                JOIN g2p_intake_form_crop_sowns cs ON s.submission_id = cs.submission_id
                                WHERE cs.fayda_fan_id = :fayda AND s.land_id IS NOT NULL
                            """),
                            {"fayda": fayda_fan_id}
                        )
                    ).scalars().all()
                    intake_lands.update([str(l).strip() for l in res_fayda if l and str(l).strip()])

                res_any = (
                    await session.execute(
                        text("""
                            SELECT DISTINCT land_id FROM g2p_intake_form_plannings WHERE land_id IS NOT NULL
                            UNION
                            SELECT DISTINCT land_id FROM g2p_intake_form_cultivations WHERE land_id IS NOT NULL
                            UNION
                            SELECT DISTINCT land_id FROM g2p_intake_form_sowings WHERE land_id IS NOT NULL
                        """)
                    )
                ).scalars().all()
                intake_lands.update([str(l).strip() for l in res_any if l and str(l).strip()])

                if all_check_lands.issubset(intake_lands):
                    return
                raise exc

        G2PIntakeFormDataService._validate_land_ids_against_fayda_records = patched_validate_land_ids
        _logger.info("ODK Hook: Patched G2PIntakeFormDataService._validate_land_ids_against_fayda_records")
    except Exception as e:
        _logger.debug("Could not patch G2PIntakeFormDataService: %s", e)


def _patch_cultivation_service():
    """Patch G2PRegisterDomainServiceCultivation to fall back to intake form plannings."""
    try:
        from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_cultivation import (
            G2PRegisterDomainServiceCultivation,
        )
        from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_base import parse_date
        from sqlalchemy import text

        if hasattr(G2PRegisterDomainServiceCultivation, "_odk_patched_cultivation"):
            return
        G2PRegisterDomainServiceCultivation._odk_patched_cultivation = True

        orig_resolve_planning_date = G2PRegisterDomainServiceCultivation._resolve_planning_date
        orig_resolve_season_bounds = G2PRegisterDomainServiceCultivation._resolve_season_bounds

        async def patched_resolve_planning_date(self, record: dict, session):
            res = await orig_resolve_planning_date(self, record, session)
            if res is not None:
                return res
            if not session:
                return None
            land_id = str(record.get("land_id") or "").strip()
            if land_id:
                res_in = await session.execute(
                    text("SELECT planned_date FROM g2p_intake_form_plannings WHERE land_id = :land_id ORDER BY created_at DESC LIMIT 1"),
                    {"land_id": land_id}
                )
                row_in = res_in.fetchone()
                if row_in and row_in[0]:
                    return parse_date(row_in[0])
            return None

        async def patched_resolve_season_bounds(self, record: dict, session):
            s_val, e_val = await orig_resolve_season_bounds(self, record, session)
            if s_val is not None and e_val is not None:
                return s_val, e_val
            if not session:
                return s_val, e_val
            land_id = str(record.get("land_id") or "").strip()
            if land_id:
                res_in = await session.execute(
                    text("SELECT start_gc, end_gc FROM g2p_intake_form_plannings WHERE land_id = :land_id ORDER BY created_at DESC LIMIT 1"),
                    {"land_id": land_id}
                )
                row_in = res_in.fetchone()
                if row_in and (row_in[0] or row_in[1]):
                    s = parse_date(row_in[0]) if row_in[0] else s_val
                    e = parse_date(row_in[1]) if row_in[1] else e_val
                    return s, e
            return s_val, e_val

        G2PRegisterDomainServiceCultivation._resolve_planning_date = patched_resolve_planning_date
        G2PRegisterDomainServiceCultivation._resolve_season_bounds = patched_resolve_season_bounds
        _logger.info("ODK Hook: Patched G2PRegisterDomainServiceCultivation")
    except Exception as e:
        _logger.debug("Could not patch G2PRegisterDomainServiceCultivation: %s", e)


def _patch_sowing_service():
    """Patch G2PRegisterDomainServiceSowing with intake form fallbacks."""
    try:
        from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_sowing import (
            G2PRegisterDomainServiceSowing,
        )
        from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_base import (
            parse_date,
            validation_error,
        )
        from sqlalchemy import text

        if hasattr(G2PRegisterDomainServiceSowing, "_odk_patched_sowing"):
            return
        G2PRegisterDomainServiceSowing._odk_patched_sowing = True

        orig_validate_sowing_area = G2PRegisterDomainServiceSowing._validate_sowing_area_after_cultivation
        orig_validate_sowing_after_cult = G2PRegisterDomainServiceSowing._validate_sowing_after_cultivation
        orig_validate_land_id = G2PRegisterDomainServiceSowing._validate_land_id_matches_planning

        async def patched_validate_sowing_area(self, record: dict, session):
            try:
                await orig_validate_sowing_area(self, record, session)
            except Exception as exc:
                land_id = str(record.get("land_id") or "").strip()
                area_sown = float(record.get("area_sown") or 0)
                if session and land_id:
                    res_ic = await session.execute(
                        text("SELECT actual_crop_area FROM g2p_intake_form_cultivations WHERE TRIM(land_id) = :land_id AND actual_crop_area IS NOT NULL ORDER BY created_at DESC LIMIT 1"),
                        {"land_id": land_id}
                    )
                    row_ic = res_ic.fetchone()
                    if row_ic and row_ic[0] is not None:
                        max_area = float(row_ic[0])
                        if area_sown > max_area:
                            validation_error(
                                f"Area Sown ({area_sown}) cannot exceed Cultivated Area ({max_area}) for Land ID '{land_id}'."
                            )
                        return
                raise exc

        async def patched_validate_sowing_after_cult(self, record: dict, session):
            try:
                await orig_validate_sowing_after_cult(self, record, session)
            except Exception as exc:
                sowing_date = parse_date(record.get("sowing_date"))
                land_id = str(record.get("land_id") or "").strip()
                if session and land_id and sowing_date:
                    prior_date = None
                    prior_stage = None
                    res_ic = await session.execute(
                        text("SELECT actual_cultivation_date FROM g2p_intake_form_cultivations WHERE land_id = :land_id ORDER BY created_at DESC LIMIT 1"),
                        {"land_id": land_id}
                    )
                    row_ic = res_ic.fetchone()
                    if row_ic and row_ic[0]:
                        prior_date = parse_date(row_ic[0])
                        prior_stage = "Cultivation Date"
                    else:
                        res_ip = await session.execute(
                            text("SELECT planned_date FROM g2p_intake_form_plannings WHERE land_id = :land_id ORDER BY created_at DESC LIMIT 1"),
                            {"land_id": land_id}
                        )
                        row_ip = res_ip.fetchone()
                        if row_ip and row_ip[0]:
                            prior_date = parse_date(row_ip[0])
                            prior_stage = "Planned Date"

                    if prior_date:
                        if sowing_date < prior_date:
                            validation_error(
                                f"Sowing Date ({sowing_date.strftime('%Y-%m-%d')}) cannot be earlier than "
                                f"{prior_stage} ({prior_date.strftime('%Y-%m-%d')})."
                            )
                        return
                raise exc

        async def patched_validate_land_id(self, record: dict, session):
            try:
                await orig_validate_land_id(self, record, session)
            except Exception as exc:
                land_id = str(record.get("land_id") or "").strip()
                if session and land_id:
                    for tbl in ("g2p_intake_form_plannings", "g2p_intake_form_cultivations"):
                        res = await session.execute(
                            text(f"SELECT land_id FROM {tbl} WHERE land_id = :land_id LIMIT 1"),
                            {"land_id": land_id}
                        )
                        if res.fetchone():
                            return
                raise exc

        G2PRegisterDomainServiceSowing._validate_sowing_area_after_cultivation = patched_validate_sowing_area
        G2PRegisterDomainServiceSowing._validate_sowing_after_cultivation = patched_validate_sowing_after_cult
        G2PRegisterDomainServiceSowing._validate_land_id_matches_planning = patched_validate_land_id
        _logger.info("ODK Hook: Patched G2PRegisterDomainServiceSowing")
    except Exception as e:
        _logger.debug("Could not patch G2PRegisterDomainServiceSowing: %s", e)


def _patch_harvest_service():
    """Patch G2PRegisterDomainServiceHarvest with intake form fallbacks and date comparison."""
    try:
        from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_harvest import (
            G2PRegisterDomainServiceHarvest,
        )
        from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_base import (
            parse_date,
            validation_error,
        )
        from sqlalchemy import text

        if hasattr(G2PRegisterDomainServiceHarvest, "_odk_patched_harvest"):
            return
        G2PRegisterDomainServiceHarvest._odk_patched_harvest = True

        orig_validate_harvest_after_sowing = G2PRegisterDomainServiceHarvest._validate_harvest_after_sowing
        orig_validate_harvest_area = G2PRegisterDomainServiceHarvest._validate_harvest_area_after_sowing
        orig_validate_land_id = G2PRegisterDomainServiceHarvest._validate_land_id_matches_sowing

        async def patched_validate_harvest_after_sowing(self, record: dict, session):
            harvest_date = parse_date(record.get("harvest_date"))
            if harvest_date is None:
                return
            try:
                await orig_validate_harvest_after_sowing(self, record, session)
            except Exception as exc:
                land_id = str(record.get("land_id") or "").strip()
                if session and land_id:
                    prior_date = None
                    prior_stage = None
                    # 1. Check active register sowings
                    res_s_reg = await session.execute(
                        text("SELECT sowing_date FROM g2p_register_sowings WHERE land_id = :land_id AND record_status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1"),
                        {"land_id": land_id}
                    )
                    row_s_reg = res_s_reg.fetchone()
                    if row_s_reg and row_s_reg[0]:
                        prior_date = parse_date(row_s_reg[0])
                        prior_stage = "Sowing Date"
                    else:
                        # 2. Check intake form sowings
                        res_s = await session.execute(
                            text("SELECT sowing_date FROM g2p_intake_form_sowings WHERE land_id = :land_id ORDER BY created_at DESC LIMIT 1"),
                            {"land_id": land_id}
                        )
                        row_s = res_s.fetchone()
                        if row_s and row_s[0]:
                            prior_date = parse_date(row_s[0])
                            prior_stage = "Sowing Date"
                        else:
                            # 3. Check intake form cultivations
                            res_c = await session.execute(
                                text("SELECT actual_cultivation_date FROM g2p_intake_form_cultivations WHERE land_id = :land_id ORDER BY created_at DESC LIMIT 1"),
                                {"land_id": land_id}
                            )
                            row_c = res_c.fetchone()
                            if row_c and row_c[0]:
                                prior_date = parse_date(row_c[0])
                                prior_stage = "Cultivation Date"

                    if prior_date:
                        if harvest_date < prior_date:
                            validation_error(
                                f"Harvest Date ({harvest_date.strftime('%Y-%m-%d')}) cannot be earlier than "
                                f"{prior_stage} ({prior_date.strftime('%Y-%m-%d')})."
                            )
                        return
                raise exc

        async def patched_validate_harvest_area(self, record: dict, session):
            try:
                await orig_validate_harvest_area(self, record, session)
            except Exception as exc:
                land_id = str(record.get("land_id") or "").strip()
                area_harvested = float(record.get("area_harvested") or 0)
                if session and land_id:
                    res_s = await session.execute(
                        text("SELECT area_sown FROM g2p_intake_form_sowings WHERE TRIM(land_id) = :land_id AND area_sown IS NOT NULL ORDER BY created_at DESC LIMIT 1"),
                        {"land_id": land_id}
                    )
                    row_s = res_s.fetchone()
                    max_area = None
                    if row_s and row_s[0] is not None:
                        max_area = float(row_s[0])
                    else:
                        res_c = await session.execute(
                            text("SELECT actual_crop_area FROM g2p_intake_form_cultivations WHERE TRIM(land_id) = :land_id AND actual_crop_area IS NOT NULL ORDER BY created_at DESC LIMIT 1"),
                            {"land_id": land_id}
                        )
                        row_c = res_c.fetchone()
                        if row_c and row_c[0] is not None:
                            max_area = float(row_c[0])

                    if max_area is not None:
                        if area_harvested > max_area:
                            validation_error(
                                f"Area Harvested ({area_harvested}) cannot exceed Allowed Area ({max_area}) for Land ID '{land_id}'."
                            )
                        return
                raise exc

        async def patched_validate_land_id(self, record: dict, session):
            try:
                await orig_validate_land_id(self, record, session)
            except Exception as exc:
                land_id = str(record.get("land_id") or "").strip()
                if session and land_id:
                    for tbl in ("g2p_intake_form_sowings", "g2p_intake_form_cultivations", "g2p_intake_form_plannings"):
                        res = await session.execute(
                            text(f"SELECT land_id FROM {tbl} WHERE land_id = :land_id LIMIT 1"),
                            {"land_id": land_id}
                        )
                        if res.fetchone():
                            return
                raise exc

        G2PRegisterDomainServiceHarvest._validate_harvest_after_sowing = patched_validate_harvest_after_sowing
        G2PRegisterDomainServiceHarvest._validate_harvest_area_after_sowing = patched_validate_harvest_area
        G2PRegisterDomainServiceHarvest._validate_land_id_matches_sowing = patched_validate_land_id
        _logger.info("ODK Hook: Patched G2PRegisterDomainServiceHarvest")
    except Exception as e:
        _logger.debug("Could not patch G2PRegisterDomainServiceHarvest: %s", e)


def install_hooks():
    """Run hook initialization."""
    _alias_extension_modules()
    _patch_base_initializer()
    _patch_document_handler()
    _ensure_core_services()
    _ensure_dbengine_initialized()
    _ensure_master_data_engine()
    _connect_celery_signals()
    _patch_request_response_helper()
    _patch_celery_worker()
    _patch_intake_form_data_service()
    _patch_cultivation_service()
    _patch_sowing_service()
    _patch_harvest_service()


install_hooks()
