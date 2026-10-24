"""Stable-reference Crop identity mirrors through native approval/ingest hooks."""
from ...farmer_reference.projection import refresh_domain_on_ingest, refresh_linked_domains


def _models():
    from openg2p_registry_extensions.register_domain.models import G2PRegisterCropSown, G2PRegisterFarmer
    return G2PRegisterFarmer, G2PRegisterCropSown


async def refresh_crop_names_from_farmer(session, farmer_internal_id):
    farmer_model, crop_model = _models()
    return await refresh_linked_domains(session, farmer_model, crop_model, farmer_internal_id)


async def refresh_crop_name_on_ingest(session, crop):
    farmer_model, _ = _models()
    return await refresh_domain_on_ingest(session, farmer_model, crop)
