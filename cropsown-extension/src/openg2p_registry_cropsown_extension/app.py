# ruff: noqa: E402
import asyncio
import logging

from .config import Settings

_config = Settings.get_config()

from openg2p_fastapi_common.app import Initializer as BaseInitializer
from openg2p_registry_core.app import Initializer as CoreInitializer

from .register_domain.models import (
    G2PRegisterCropSown, G2PRegisterHistoryCropSown,
    G2PRegisterPlanning, G2PRegisterHistoryPlanning,
    G2PRegisterCultivation, G2PRegisterHistoryCultivation,
    G2PRegisterSowing, G2PRegisterHistorySowing,
    G2PRegisterProduction, G2PRegisterHistoryProduction,
    G2PRegisterHarvest, G2PRegisterHistoryHarvest,
    G2PRegisterInfestation, G2PRegisterHistoryInfestation,
    G2PRegisterCluster, G2PRegisterHistoryCluster,
    G2PRegisterCultivationCluster, G2PRegisterHistoryCultivationCluster,
    G2PIntakeFormCropSown,
    G2PIntakeFormPlanning, G2PIntakeFormCultivation, G2PIntakeFormSowing,
    G2PIntakeFormProduction, G2PIntakeFormHarvest, G2PIntakeFormInfestation,
    G2PIntakeFormCluster, G2PIntakeFormCultivationCluster,
)
from .register_domain.factory import G2PRegisterDomainFactory
from .register_domain.services import (
    G2PRegisterDomainServiceCropSown,
    G2PRegisterDomainServiceSowing,
)

_logger = logging.getLogger(_config.logging_default_logger_name)


class Initializer(BaseInitializer):
    def initialize(self, **kwargs):
        super().initialize()
        CoreInitializer().initialize()

        G2PRegisterDomainFactory()
        G2PRegisterDomainServiceCropSown()
        G2PRegisterDomainServiceSowing()

    def migrate_database(self, args):

        async def migrate():
            _logger.info("Migrating extensions database")

            # The crop sown record is the root: it carries the land attributes
            # flat (land is not a register of its own) and every crop line hangs
            # off it.
            await G2PRegisterCropSown.create_migrate()
            await G2PRegisterHistoryCropSown.create_migrate()
            await G2PIntakeFormCropSown.create_migrate()

            # The seven crop lines, all children of the crop sown record.
            await G2PRegisterPlanning.create_migrate()
            await G2PRegisterHistoryPlanning.create_migrate()
            await G2PIntakeFormPlanning.create_migrate()

            await G2PRegisterCultivation.create_migrate()
            await G2PRegisterHistoryCultivation.create_migrate()
            await G2PIntakeFormCultivation.create_migrate()

            await G2PRegisterSowing.create_migrate()
            await G2PRegisterHistorySowing.create_migrate()
            await G2PIntakeFormSowing.create_migrate()

            await G2PRegisterProduction.create_migrate()
            await G2PRegisterHistoryProduction.create_migrate()
            await G2PIntakeFormProduction.create_migrate()

            await G2PRegisterHarvest.create_migrate()
            await G2PRegisterHistoryHarvest.create_migrate()
            await G2PIntakeFormHarvest.create_migrate()

            await G2PRegisterInfestation.create_migrate()
            await G2PRegisterHistoryInfestation.create_migrate()
            await G2PIntakeFormInfestation.create_migrate()

            await G2PRegisterCluster.create_migrate()
            await G2PRegisterHistoryCluster.create_migrate()
            await G2PIntakeFormCluster.create_migrate()

            await G2PRegisterCultivationCluster.create_migrate()
            await G2PRegisterHistoryCultivationCluster.create_migrate()
            await G2PIntakeFormCultivationCluster.create_migrate()

        asyncio.run(migrate())
