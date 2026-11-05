"""The ingest worker resolves the post-ingest hook through the domain factory.

A missing or failing factory only logs a warning in the worker and skips the
hook, leaving the Farmer identity unmirrored. The factory must therefore always
return the Crop Sown service, and fail loudly when it cannot.
"""
import importlib
import importlib.util
import unittest
from unittest.mock import AsyncMock, patch

PACKAGE = "openg2p_registry_cropsown_extension"


@unittest.skipUnless(importlib.util.find_spec("openg2p_registry_core"), "Requires the registry platform")
class DomainFactoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.factory_module = importlib.import_module(PACKAGE + ".register_domain.factory")
        self.factory = self.factory_module.G2PRegisterDomainFactory()
        self.service_module = importlib.import_module(
            PACKAGE + ".register_domain.services.g2p_register_domain_service_crop_sown"
        )

    def test_worker_import_path_exports_the_factory(self):
        module = importlib.import_module(PACKAGE + ".register_domain.factory")
        self.assertTrue(hasattr(module, "G2PRegisterDomainFactory"))

    def test_crop_sown_service_is_resolved(self):
        service = self.factory.get_domain_service("CropSown")
        self.assertIsNotNone(service)
        self.assertIsInstance(service, self.service_module.G2PRegisterDomainServiceCropSown)

    def test_unresolvable_crop_sown_service_raises(self):
        implementation = importlib.import_module(PACKAGE + ".register_domain.factory.g2p_register_domain_factory")
        with patch.object(implementation, "SERVICES_MODULE", PACKAGE + ".register_domain.no_such_services"):
            with self.assertRaises(implementation.DomainServiceUnavailable):
                self.factory.get_domain_service("CropSown")

    def test_register_without_a_service_has_no_hook(self):
        self.assertIsNone(self.factory.get_domain_service("NoSuchRegister"))

    async def test_post_ingest_mirrors_only_the_crop_sown_register(self):
        service = self.service_module.G2PRegisterDomainServiceCropSown()
        projection = importlib.import_module(PACKAGE + ".register_domain.services.farmer_name_projection")
        row, session = object(), object()
        with patch.object(projection, "refresh_crop_name_on_ingest", AsyncMock()) as mirror:
            await service.post_ingest("c9ee1d48-93b5-52d5-a8fc-280266a39c10", row, session)
            mirror.assert_not_awaited()
            await service.post_ingest(self.service_module.CROP_SOWN_REGISTER_ID, row, session)
            mirror.assert_awaited_once_with(session, row)
