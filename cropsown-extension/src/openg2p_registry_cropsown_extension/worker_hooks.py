"""Install optional Farmer approval hooks after Celery has initialized core."""
import os


def install_farmer_worker_hooks(**kwargs):
    if os.environ.get("CROPSOWN_TWO_CR_ENABLED", "false").strip().lower() not in {"true", "1", "yes"}:
        return
    from openg2p_registry_core.services.intake_form_data_service import G2PIntakeFormDataService
    from .register_domain.services.farmer_register_crossref import install
    install(G2PIntakeFormDataService)


def connect():
    # Staff API images need not contain Celery. Only an actual worker emits
    # this signal, after its services and logging have been initialized.
    try:
        from celery.signals import worker_init
    except ImportError:
        return
    worker_init.connect(install_farmer_worker_hooks, weak=False)
