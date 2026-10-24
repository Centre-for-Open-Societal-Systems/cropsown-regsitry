"""Domain payload adapters; Farmer trust is resolved by the finalize service."""
import logging
from typing import Dict
from sqlalchemy.orm import Session
from openg2p_registry_core.interfaces import G2PPayloadEnricherInterface
_logger = logging.getLogger("g2p-payload-enricher-service")

class G2PDciCropSownCreateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        return data

class G2PDciCropSownUpdateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciCropSownUpdateEnricherService")
        return data

class G2PDciCropSownDeleteEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciCropSownDeleteEnricherService")
        return data


class G2PPassThroughEnricherService(G2PPayloadEnricherInterface):
    """Identity enricher: returns the raw payload unchanged.

    Used by connectors (e.g. ODK) whose payload already arrives in the
    template's expected ``expanded`` shape, so no per-field enrichment is
    needed before the Jinja transform runs. Farmer identity enrichment for
    those flows is done later, at finalize, by the register domain service /
    two-CR hooks — not here."""

    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PPassThroughEnricherService (identity pass-through)")
        return data


# SPDCI Payload Enrichers
class G2PSpdciCropSownCreateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PSpdciCropSownCreateEnricherService")
        return data

class G2PSpdciCropSownUpdateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PSpdciCropSownUpdateEnricherService")
        return data

class G2PSpdciCropSownDeleteEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PSpdciCropSownDeleteEnricherService")
        return data

# UNDP Payload Enrichers
class G2PUndpCropSownCreateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PUndpCropSownCreateEnricherService")
        return data

class G2PUndpCropSownUpdateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PUndpCropSownUpdateEnricherService")
        return data

class G2PUndpCropSownDeleteEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PUndpCropSownDeleteEnricherService")
        return data
