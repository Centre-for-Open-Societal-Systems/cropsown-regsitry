from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_registry_core.models import G2PRegister, G2PRegisterHistory
from openg2p_fastapi_common.models import BaseORMModel
import uuid


# All Register classes should have the prefix G2PRegister
class G2PRegisterFamily(G2PRegister):
    __tablename__ = "g2p_register_families"

    family_name: Mapped[str] = mapped_column(String, nullable=True)

    type_of_housing: Mapped[str] = mapped_column(String, nullable=True)
    house_condition: Mapped[str] = mapped_column(String, nullable=True)
    sanitation_condition: Mapped[str] = mapped_column(String, nullable=True)
    water_access: Mapped[str] = mapped_column(String, nullable=True)
    electricity_access: Mapped[str] = mapped_column(String, nullable=True)

    ethnic_group: Mapped[str] = mapped_column(String, nullable=True)
    belong_to_protected_groups: Mapped[bool] = mapped_column(Boolean, nullable=True)
    under_other_vulnerable_status: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # Addl fields
    no_of_children: Mapped[int] = mapped_column(Integer, nullable=True)     # family members under the age of 15

    def get_search_text_fields(self) -> list[str]:
        """
        Return family-specific fields for search text aggregation.
        G2PRegister fields are automatically included via event listeners.
        """
        return [
            self.family_name or "",
            self.type_of_housing or "",
            self.house_condition or "",
            self.sanitation_condition or "",
            self.water_access or "",
            self.electricity_access or "",
            self.ethnic_group or "",
            str(self.belong_to_protected_groups) if self.belong_to_protected_groups is not None else "",
            str(self.under_other_vulnerable_status) if self.under_other_vulnerable_status is not None else "",
        ]

    def get_record_name_fields(self) -> list[str]:
        """Return family fields used to build record_name."""
        return [
            self.family_name or "",
        ]

# All Register History classes should have the prefix G2PRegisterHistory
class G2PRegisterHistoryFamily(G2PRegisterHistory):
    __tablename__ = "g2p_register_history_families"

    # Override all columns from G2PRegisterFamilyBase to make them nullable for history
    family_name: Mapped[str] = mapped_column(String, nullable=True)
    type_of_housing: Mapped[str] = mapped_column(String, nullable=True)
    house_condition: Mapped[str] = mapped_column(String, nullable=True)
    sanitation_condition: Mapped[str] = mapped_column(String, nullable=True)
    water_access: Mapped[str] = mapped_column(String, nullable=True)
    electricity_access: Mapped[str] = mapped_column(String, nullable=True)
    ethnic_group: Mapped[str] = mapped_column(String, nullable=True)
    belong_to_protected_groups: Mapped[bool] = mapped_column(Boolean, nullable=True)
    under_other_vulnerable_status: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # Addl fields
    no_of_children: Mapped[int] = mapped_column(Integer, nullable=True)     # family members under the age of 15
