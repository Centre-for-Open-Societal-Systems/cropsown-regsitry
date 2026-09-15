import logging
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from openg2p_registry_core.interfaces import G2PPayloadEnricherInterface
from openg2p_registry_core.models import MaritalStatusEnum, GenderEnum
from openg2p_registry_extensions.register_domain.models import G2PRegisterFamilyMember


_logger = logging.getLogger('g2p-payload-enricher-service')

# DCI Payload Enrichers
class G2PDciFamilyMemberCreateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciFamilyMemberCreateEnricherService")

        parent_link_internal_record_id = None

        # Try to find a parent family member using parent1_identifier
        parent1_identifier_data = data.get('parent1_identifier')
        if isinstance(parent1_identifier_data, dict):
            identifier_value = parent1_identifier_data.get('identifier_value')
            if identifier_value:
                _logger.debug(f"Checking for parent family member with parent1_identifier: {identifier_value}")
                parent_family_member = session.execute(
                    select(G2PRegisterFamilyMember).filter_by(foundational_id=identifier_value)
                ).scalar_one_or_none()

                if parent_family_member:
                    parent_link_internal_record_id = parent_family_member.link_internal_record_id
                    _logger.info(f"Found parent family member via parent1_identifier. Link record ID: {parent_link_internal_record_id}")

        # If parent1_identifier didn't yield a result, try parent2_identifier
        if parent_link_internal_record_id is None:
            parent2_identifier_data = data.get('parent2_identifier')
            if isinstance(parent2_identifier_data, dict):
                identifier_value = parent2_identifier_data.get('identifier_value')
                if identifier_value:
                    _logger.debug(f"Checking for parent family member with parent2_identifier: {identifier_value}")
                    parent_family_member = session.execute(
                        select(G2PRegisterFamilyMember).filter_by(foundational_id=identifier_value)
                    ).scalar_one_or_none()

                    if parent_family_member:
                        parent_link_internal_record_id = parent_family_member.link_internal_record_id
                        _logger.info(f"Found parent family member via parent2_identifier. Link record ID: {parent_link_internal_record_id}")

        if parent_link_internal_record_id:
            data['link_internal_record_id'] = parent_link_internal_record_id
        else:
            _logger.warning("Could not find a parent family member using either parent1_identifier or parent2_identifier.")
            data["link_internal_record_id"] = None
        
        # Normalize and map marital_status values to G2P standard values.
        marital_status_mapping = {
            "s": MaritalStatusEnum.SINGLE.value,
            "u": MaritalStatusEnum.SINGLE.value,
            "m": MaritalStatusEnum.MARRIED.value,
            "w": MaritalStatusEnum.WIDOWED.value,
            "d": MaritalStatusEnum.DIVORCED.value,
            "a": MaritalStatusEnum.SEPARATED.value,
            "l": MaritalStatusEnum.SEPARATED.value,
            "widow": MaritalStatusEnum.WIDOWED.value,
            "married": MaritalStatusEnum.MARRIED.value,
            "unmarried": MaritalStatusEnum.SINGLE.value,
            "divorced": MaritalStatusEnum.DIVORCED.value,
            "annulled": MaritalStatusEnum.SEPARATED.value,
            "never married": MaritalStatusEnum.SINGLE.value,
            "legally separated": MaritalStatusEnum.SEPARATED.value,
        }

        marital_status = data.get("marital_status")
        if isinstance(marital_status, str):
            marital_status_normalized = marital_status.strip().lower()
            g2p_value = marital_status_mapping.get(marital_status_normalized)
            # Also support single-letter codes mapped from uppercase (e.g. "S", "W", etc.)
            if g2p_value:
                data["marital_status"] = g2p_value
            else:
                # If mapping fails, set as "UNKNOWN"
                data["marital_status"] = MaritalStatusEnum.UNKNOWN.value
                
        # Transform birth_date and death_date to only Date (YYYY-MM-DD), removing time component if present.
        for date_field in ["birth_date", "death_date"]:
            value = data.get(date_field)
            if isinstance(value, str) and value.strip():
                # Handle cases like "YYYY-MM-DDTHH:MM:SS" or "YYYY-MM-DD"
                try:
                    if "T" in value:
                        date_str = value.split("T")[0]
                    else:
                        date_str = value

                    parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                    # Set as "YYYY-MM-DD"
                    data[date_field] = parsed_date.strftime("%Y-%m-%d")
                except Exception as e:
                    # If parsing fails, leave the original value or set to None
                    _logger.warning(f"Could not parse {date_field}: {value} ({str(e)})")

        return data

class G2PDciFamilyMemberUpdateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciFamilyMemberUpdateEnricherService")
        return data

class G2PDciFamilyMemberDeleteEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciFamilyMemberDeleteEnricherService")
        return data

class G2PDciVcFamilyMemberCreateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciVcFamilyMemberCreateEnricherService")

        parent_link_internal_record_id = None

        jwt_payload = data.get('jwt', {}).get('payload', {})

        # parents data: jwt.payload.parent
        parents_data = jwt_payload.get('parents')
            
        if isinstance(parents_data, dict):
            parents_data = [parents_data]
        elif not isinstance(parents_data, list):
            parents_data = []

        for parent in parents_data:
            if isinstance(parent, dict):
                identifier_value = parent.get('identifier')
                if identifier_value:
                    _logger.debug(f"Checking for parent family member with identifier: {identifier_value}")
                    parent_family_member = session.execute(
                        select(G2PRegisterFamilyMember).filter_by(foundational_id=identifier_value)
                    ).scalar_one_or_none()

                    if parent_family_member:
                        parent_link_internal_record_id = parent_family_member.link_internal_record_id
                        _logger.info(f"Found parent family member via identifier. Link record ID: {parent_link_internal_record_id}")
                        break
        
        if parent_link_internal_record_id:
            data['link_internal_record_id'] = parent_link_internal_record_id

        return data

class G2PDciVcFamilyMemberUpdateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciVcFamilyMemberUpdateEnricherService")
        return data

class G2PDciVcFamilyMemberDeleteEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciVcFamilyMemberDeleteEnricherService")
        return data

# SPDCI Payload Enrichers
class G2PSpdciFamilyMemberCreateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PSpdciFamilyMemberCreateEnricherService")
        return data

class G2PSpdciFamilyMemberUpdateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PSpdciFamilyMemberUpdateEnricherService")
        return data

class G2PSpdciFamilyMemberDeleteEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PSpdciFamilyMemberDeleteEnricherService")
        return data

# UNDP Payload Enrichers
class G2PUndpFamilyMemberCreateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PUndpFamilyMemberCreateEnricherService")
        return data

class G2PUndpFamilyMemberUpdateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PUndpFamilyMemberUpdateEnricherService")
        return data

class G2PUndpFamilyMemberDeleteEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PUndpFamilyMemberDeleteEnricherService")
        return data
