"""Domain service factory the platform ingest worker imports by module name.

The worker resolves the post-ingest hook through this module. Without it the
worker only logs a warning and skips the hook, so the Farmer identity mirror
never runs for an ingested record. The factory therefore fails loudly for the
Crop Sown register instead of returning no service.
"""
import importlib
import logging
from typing import Optional

from openg2p_fastapi_common.service import BaseService
from openg2p_registry_core.services import G2PRegisterDomainService

_logger = logging.getLogger("g2p-register-domain-factory")

SERVICES_MODULE = "openg2p_registry_cropsown_extension.register_domain.services"
SERVICE_CLASS_PREFIX = "G2PRegisterDomainService"
# Registers whose post-ingest hook must exist; resolution failure raises.
REQUIRED_MNEMONICS = frozenset({"CropSown"})


class DomainServiceUnavailable(RuntimeError):
    """A required domain service could not be resolved."""


class G2PRegisterDomainFactory(BaseService):
    g2p_register_domain_service: G2PRegisterDomainService = None

    def get_domain_service(self, register_mnemonic: str) -> Optional[G2PRegisterDomainService]:
        class_name = f"{SERVICE_CLASS_PREFIX}{register_mnemonic}"
        required = register_mnemonic in REQUIRED_MNEMONICS
        try:
            implementation_class = getattr(importlib.import_module(SERVICES_MODULE), class_name)
        except (AttributeError, ImportError) as error:
            if required:
                raise DomainServiceUnavailable(
                    f"Domain service {class_name} for register '{register_mnemonic}' cannot be "
                    f"resolved: {error}"
                ) from error
            _logger.info("No domain service for register '%s'; its post-ingest hook is skipped", register_mnemonic)
            return None
        service = implementation_class.get_component()
        if not service:
            service = implementation_class()
        return service
