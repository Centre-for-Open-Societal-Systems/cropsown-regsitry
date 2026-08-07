import logging
from datetime import date, datetime

from openg2p_registry_core.services import G2PRegisterDomainService
from openg2p_registry_core.schemas import ChangeRequestRequestPayload
from openg2p_registry_core.models import G2PRegisterChangeRequest, G2PRegisterChangeRequestPayload
from ..models import G2PRegisterFamily, G2PRegisterFamilyMember
from sqlalchemy.ext.asyncio import AsyncSession

_logger = logging.getLogger('g2p-register-family-member-service')

class G2PRegisterDomainServiceFamilyMember(G2PRegisterDomainService):

    async def validate_domain_attributes(self, change_request_request_payload: ChangeRequestRequestPayload):
        _logger.info("Validating family member domain attributes")
        return

    async def post_approve(self, change_request: G2PRegisterChangeRequest, session: AsyncSession):

        payload_obj = await session.get(G2PRegisterChangeRequestPayload, change_request.change_request_id)

        if not payload_obj or not payload_obj.change_payload:
            return

        for record in payload_obj.change_payload:

            edit_action = record.get("edit_action")
            link_internal_record_id = record.get("link_internal_record_id")

            if not link_internal_record_id:
                continue

            g2p_register_family = await session.get(G2PRegisterFamily, link_internal_record_id)

            # --- Birth date & age ---
            birth_date_str = record.get("birth_date")
            birth_date = self._parse_birth_date(birth_date_str)
            age = self._calculate_age(birth_date)

            # ---------------- ADD ----------------
            if edit_action == "ADD":
                if age is not None and age < 15:
                    g2p_register_family.no_of_children = (
                        (g2p_register_family.no_of_children or 0) + 1
                    )

            # ---------------- UPDATE ----------------
            elif edit_action == "UPDATE":

                member_internal_id = record.get("internal_record_id")
                if not member_internal_id:
                    continue

                # Fetch existing member (old data)
                family_member = await session.get(
                    G2PRegisterFamilyMember,
                    member_internal_id
                )

                if not family_member:
                    continue

                # ---- PREV AGE ----
                old_birth_date = family_member.birth_date
                old_age = self._calculate_age(old_birth_date) if old_birth_date else None

                # ---- THRESHOLD CROSSING (child → adult at 15) ----
                if (
                    old_age is not None
                    and age is not None
                    and old_age < 15
                    and age >= 15
                ):
                    g2p_register_family.no_of_children = max(
                        0,
                        (g2p_register_family.no_of_children or 0) - 1
                    )


            # ---------------- DELETE ----------------
            elif edit_action == "DELETE":
                if age is not None and age < 15:
                    g2p_register_family.no_of_children = max(
                        0,
                        (g2p_register_family.no_of_children or 0) - 1
                    )

            # ---------------- NO CHANGE ----------------
            elif edit_action == "NO_CHANGE":
                continue
        return

    def _parse_birth_date(self, value: str | None) -> date | None:
        """Try multiple formats, return date or None."""
        if not value:
            return None

        value = value.strip()

        formats = [
            "%Y-%m-%d",        # 2025-12-30
            "%d-%m-%Y",        # 30-12-2025
            "%d/%m/%Y",        # 30/12/2025
            "%Y/%m/%d",        # 2025/12/30
            "%d %b %Y",        # 30 Dec 2025
            "%d %B %Y",        # 30 December 2025
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except Exception:
                continue

        return None


    def _calculate_age(self, birth_date: date | None) -> int | None:
        if not birth_date:
            return None

        today = date.today()
        return (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )