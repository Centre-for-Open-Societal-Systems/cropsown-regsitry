"""Resolve approved source notifications through the existing consented lookup."""
import asyncio
from openg2p_registry_core.interfaces import G2PPayloadEnricherInterface
from ...register_domain.services.farmer_registry_enrichment import fetch_farmer_record,to_farmer_fields


class G2PFarmerReferenceNotificationEnricher(G2PPayloadEnricherInterface):
    def enrich(self, data, session):
        farmer_id = str(data.get("farmer_id") or "").strip()
        fan = "".join(str(data.get("fayda_fan_id") or "").split())
        personal = asyncio.run(fetch_farmer_record(farmer_id, fan))
        if not personal:
            # Unlike interactive Submit, the ingestion pipeline must retry.
            raise ValueError("FARMER_REFERENCE_LOOKUP_NOT_RESOLVED")
        fields = to_farmer_fields(personal)
        if not fields.get("first_name"):
            raise ValueError("FARMER_REFERENCE_NAME_MISSING")
        if fields.get("date_of_birth"):
            fields["date_of_birth"] = fields["date_of_birth"].isoformat()
        return {"farmer_id":farmer_id, **fields}
