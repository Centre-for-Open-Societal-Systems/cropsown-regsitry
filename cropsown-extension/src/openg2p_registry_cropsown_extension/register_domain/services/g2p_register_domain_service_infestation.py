import logging
from datetime import date

from openg2p_registry_core.services import G2PRegisterDomainService

from .embedded_files import persist_embedded_files

from .domain_compute_utils import compute_ec_date
from .domain_validation_utils import as_float, parse_date, validation_error

_logger = logging.getLogger("g2p-register-domain-service")


class G2PRegisterDomainServiceInfestation(G2PRegisterDomainService):
    async def validate_domain_attributes(self, records: list[dict], session=None, **kwargs):
        for record in records:
            # A photo sent inline (ODK, or the intake 'file' widget) is uploaded
            # and replaced by its document_id before anything is saved.
            await persist_embedded_files(record, ("geo_tagged_photo_document_id",), purpose="infestation")
            inf_type = record.get("infestation_type")
            if isinstance(inf_type, list):
                record["infestation_type"] = inf_type[0] if inf_type else None
            elif isinstance(inf_type, str) and (inf_type.startswith("[") or inf_type.startswith('["')):
                import json
                try:
                    parsed = json.loads(inf_type)
                    if isinstance(parsed, list):
                        record["infestation_type"] = parsed[0] if parsed else None
                except Exception:
                    record["infestation_type"] = inf_type.replace("[", "").replace("]", "").replace('"', "").replace("'", "").strip()

            from .domain_validation_utils import validate_alphabetical_name, validate_mobile_number
            validate_alphabetical_name(record.get("farmer_name"), "Farmer Name")
            # validate_alphabetical_name(record.get("da_name"), "DA Name")
            # validate_alphabetical_name(record.get("supervisor_name"), "Supervisor Name")
            # validate_mobile_number(record.get("da_mobile_number"), "DA Mobile Number")
            # validate_mobile_number(record.get("supervisor_mobile_number"), "Supervisor Mobile Number")
            self._validate_observation_date(record)
            self._validate_estimated_damage(record)
            compute_ec_date(record, "observation_date", "observation_date_ec")
            if session:
                await self._validate_infestation_after_sowing(record, session=session)

    async def _validate_infestation_after_sowing(self, record: dict, session) -> None:
        land_id = str(record.get("land_id") or "").strip()
        if not land_id:
            return

        submission_id = record.get("submission_id")
        link_internal_record_id = record.get("link_internal_record_id")
        fayda_fan_id = record.get("fayda_fan_id")
        internal_record_id = record.get("internal_record_id")

        raw_cs = record.get("cluster_status")
        if isinstance(raw_cs, (list, tuple, set)):
            cluster_status = " ".join(str(item) for item in raw_cs if item).upper()
        else:
            cluster_status = str(raw_cs or "").upper()
        is_clustered = "CLUSTER" in cluster_status

        commodity = record.get("commodity")
        from .domain_validation_utils import get_attribute_variants
        commodity_vars = get_attribute_variants(commodity, "CROP_COMMODITY") if commodity else []

        from sqlalchemy import text

        sowing_found = False

        # 1. Check in Intake Form (current form submission)
        if submission_id:
            if is_clustered:
                query = "SELECT id FROM g2p_intake_form_sowings WHERE submission_id = :sub_id AND land_id = :land_id"
                params = {"sub_id": submission_id, "land_id": land_id}
                res = await session.execute(text(query), params)
                if res.fetchone():
                    sowing_found = True
            else:
                if commodity_vars:
                    query = "SELECT commodity FROM g2p_intake_form_sowings WHERE submission_id = :sub_id AND land_id = :land_id"
                    params = {"sub_id": submission_id, "land_id": land_id}
                    res = await session.execute(text(query), params)
                    for r in res.fetchall():
                        s_comm = r[0]
                        if s_comm and any(v.upper() == str(s_comm).strip().upper() for v in commodity_vars):
                            sowing_found = True
                            break

        # 2. Build master_ids for Register check if not found in intake
        if not sowing_found:
            master_ids = set()
            if submission_id:
                if not fayda_fan_id:
                    res_f = await session.execute(
                        text("SELECT fayda_fan_id FROM g2p_intake_form_crop_sowns WHERE submission_id = :sub_id AND fayda_fan_id IS NOT NULL"),
                        {"sub_id": submission_id}
                    )
                    f_row = res_f.fetchone()
                    if f_row and f_row[0]:
                        fayda_fan_id = f_row[0]

                res_root = await session.execute(
                    text("SELECT internal_record_id::text FROM g2p_intake_form_crop_sowns WHERE submission_id = :sub_id AND internal_record_id IS NOT NULL"),
                    {"sub_id": submission_id}
                )
                row_root = res_root.fetchone()
                if row_root and row_root[0]:
                    master_ids.add(str(row_root[0]))

            if link_internal_record_id:
                master_ids.add(str(link_internal_record_id))
            elif internal_record_id:
                res_root = await session.execute(
                    text("SELECT internal_record_id::text FROM g2p_register_crop_sowns WHERE internal_record_id = :rec_id AND record_status = 'ACTIVE'"),
                    {"rec_id": str(internal_record_id)}
                )
                if res_root.fetchone():
                    master_ids.add(str(internal_record_id))
                else:
                    res_child = await session.execute(
                        text("SELECT link_internal_record_id::text FROM g2p_register_infestations WHERE internal_record_id = :rec_id"),
                        {"rec_id": str(internal_record_id)}
                    )
                    row_c = res_child.fetchone()
                    if row_c and row_c[0]:
                        master_ids.add(str(row_c[0]))

            if fayda_fan_id:
                res_m = await session.execute(
                    text("SELECT internal_record_id::text FROM g2p_register_crop_sowns WHERE fayda_fan_id = :fayda AND record_status = 'ACTIVE'"),
                    {"fayda": fayda_fan_id}
                )
                for r in res_m.fetchall():
                    if r[0]:
                        master_ids.add(str(r[0]))

            if master_ids:
                if is_clustered:
                    query = "SELECT id FROM g2p_register_sowings WHERE link_internal_record_id = ANY(:m_ids) AND record_status = 'ACTIVE' AND land_id = :land_id"
                    params = {"m_ids": list(master_ids), "land_id": land_id}
                    res = await session.execute(text(query), params)
                    if res.fetchone():
                        sowing_found = True
                else:
                    if commodity_vars:
                        query = "SELECT commodity FROM g2p_register_sowings WHERE link_internal_record_id = ANY(:m_ids) AND record_status = 'ACTIVE' AND land_id = :land_id AND commodity = ANY(:commodity_vars)"
                        params = {"m_ids": list(master_ids), "land_id": land_id, "commodity_vars": commodity_vars}
                        res = await session.execute(text(query), params)
                        if res.fetchone():
                            sowing_found = True

        if not sowing_found:
            crop_str = f" for Crop '{commodity}'" if commodity else ""
            validation_error(
                f"No Sowing record found{crop_str} on Land ID '{land_id}'. "
                f"Pest/Disease Infestation incident can only be created for a crop that has a Sowing record."
            )

    def _validate_observation_date(self, record: dict) -> None:
        # Future observation dates are allowed; no restriction here.
        return

    def _validate_estimated_damage(self, record: dict) -> None:
        raw_val = record.get("estimated_damage_pct")
        if raw_val is None or str(raw_val).strip() == "":
            return

        val_str = str(raw_val).strip()

        # Reject any alphabetic characters
        if any(c.isalpha() for c in val_str):
            validation_error("Estimated Crop Damage cannot contain letters. Enter percentage with '%' (e.g. 50%) or pure number for hectares (e.g. 10.5)")

        if "%" in val_str:
            num_part = val_str.replace("%", "").strip()
            try:
                num = float(num_part)
                if not (0 <= num <= 100):
                    validation_error("Percentage damage must be between 0% and 100%")
            except ValueError:
                validation_error("Invalid percentage format for Estimated Crop Damage (e.g., 50%)")
        else:
            try:
                num = float(val_str)
                if num < 0:
                    validation_error("Estimated Crop Damage must be non-negative")
            except ValueError:
                validation_error("Estimated Crop Damage must be numeric (e.g. 10.5 for ha or 50% for percentage)")

    def construct_search_text(self, payload: dict, extra: list[str] = None) -> str:
        _logger.info("Constructing search text for infestation")

        keys = [
            "functional_record_id",
            "land_id",
            "commodity",
            "growth_stage",
            "infestation_type",
            "pest_name",
            "weed_name",
            "disease_name",
            "chemical_used",
            "severity_level",
            "observation_date",
        ]
        search_text = []
        if extra:
            search_text.extend(str(item).strip() for item in extra if str(item).strip())
        search_text.extend(
            str(payload.get(key) or "").strip()
            for key in keys
            if str(payload.get(key) or "").strip()
        )

        return " ".join(search_text).strip()

    def construct_record_name(self, payload: dict, extra: list[str] = None) -> str:
        _logger.info("Constructing record name for infestation")

        keys = ["infestation_type", "severity_level", "observation_date"]
        record_name = []
        if extra:
            record_name.extend(str(item).strip() for item in extra if str(item).strip())
        record_name.extend(
            str(payload.get(key) or "").strip()
            for key in keys
            if str(payload.get(key) or "").strip()
        )

        return " ".join(record_name).strip()
