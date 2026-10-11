import logging

from openg2p_registry_core.models import G2PRegisterChangeRequest
from openg2p_registry_core.models.enum import ChangeActionEnum
from openg2p_registry_core.services import G2PRegisterDomainService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified


from .domain_validation_utils import as_bool, fallback_record_name, is_blank, validate_enum_values, validation_error

_logger = logging.getLogger("g2p-register-domain-service")

_MEMBERSHIP_NAME_FIELDS = {
    "is_primary_cooperative_member": "primary_cooperative_name",
    "is_cooperative_union_member": "cooperative_union_name",
}



def _enum_fields() -> dict:
    # Imported lazily: ..models imports these services at module level, so a
    # top-level import here would be circular whenever services load first.
    from ..models.enums import FarmerClusterRoleEnum

    return {"farmer_cluster_role": FarmerClusterRoleEnum}


class G2PRegisterDomainServiceMembershipDetails(G2PRegisterDomainService):
    async def validate_domain_attributes(self, records: list[dict]):
        for record in records:
            validate_enum_values(record, _enum_fields())
            self._clear_membership_names_without_membership(record)
            self._validate_cluster_membership(record)

    @staticmethod
    def _clear_membership_names_without_membership(record: dict) -> bool:
        cleared = False
        for flag_field, name_field in _MEMBERSHIP_NAME_FIELDS.items():
            if flag_field not in record:
                continue
            if as_bool(record.get(flag_field)) is not True:
                record[name_field] = None
                cleared = True
        return cleared

    def _validate_cluster_membership(self, record: dict) -> None:
        is_member = as_bool(record.get("is_farmer_cluster_member"))
        if is_member is False and not is_blank(record.get("farmer_cluster_role")):
            validation_error(
                "farmer_cluster_role must be empty when is_farmer_cluster_member is false"
            )

    def construct_search_text(self, payload: dict, extra: list[str] = None) -> str:
        _logger.info("Constructing search text for membership details")

        keys = [
            "primary_cooperative_name",
            "cooperative_union_name",
            "farmer_cluster_role",
        ]
        search_text = []
        if extra:
            search_text.extend(
                str(value).strip() for value in extra if str(value).strip()
            )
        search_text.extend(
            str(payload.get(key) or "").strip()
            for key in keys
            if str(payload.get(key) or "").strip()
        )

        return " ".join(search_text).strip()

    def construct_record_name(self, payload: dict, extra: list[str] = None) -> str:
        _logger.info("Constructing record name for membership details")

        keys = ["primary_cooperative_name", "cooperative_union_name"]
        record_name = []
        if extra:
            record_name.extend(str(item).strip() for item in extra if str(item).strip())
        record_name.extend(
            str(payload.get(key) or "").strip()
            for key in keys
            if str(payload.get(key) or "").strip()
        )

        return " ".join(record_name).strip() or fallback_record_name(payload, "Membership")

    async def pre_approve(self, change_request: G2PRegisterChangeRequest, session: AsyncSession):
        from openg2p_registry_core.models import G2PRegisterChangeRequestPayload

        payload_obj = await session.get(
            G2PRegisterChangeRequestPayload, change_request.change_request_id
        )
        if not payload_obj or not payload_obj.change_payload:
            return

        cleared = False
        for record in payload_obj.change_payload:
            if record.get("edit_action") in {
                ChangeActionEnum.DELETE.value,
                ChangeActionEnum.NO_CHANGE.value,
            }:
                continue
            if self._clear_membership_names_without_membership(record):
                cleared = True
        if cleared:
            flag_modified(payload_obj, "change_payload")
