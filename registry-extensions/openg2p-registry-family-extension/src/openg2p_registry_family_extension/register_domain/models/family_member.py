from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_registry_core.models import (
    G2PRegister, G2PRegisterHistory, G2PPerson, G2PGeo,
    G2PPersonHistory, G2PGeoHistory
)


# All Register classes should have the prefix G2PRegister
class G2PRegisterFamilyMember(G2PRegister, G2PPerson, G2PGeo):
    __tablename__ = "g2p_register_family_members"

    # Additional marital info
    marriage_date: Mapped[str] = mapped_column(String, nullable=True)
    divorce_date: Mapped[str] = mapped_column(String, nullable=True)

    # Social Registry Commons
    employment_status: Mapped[str] = mapped_column(String, nullable=True)
    role_in_household: Mapped[str] = mapped_column(String, nullable=True)
    relationship_with_household_head: Mapped[str] = mapped_column(String, nullable=True)

    sources_of_income: Mapped[str] = mapped_column(String, nullable=True)
    annual_income: Mapped[str] = mapped_column(String, nullable=True)
    owns_a_two_wheeler: Mapped[bool] = mapped_column(Boolean, nullable=True)
    owns_a_three_wheeler: Mapped[bool] = mapped_column(Boolean, nullable=True)
    owns_a_four_wheeler: Mapped[bool] = mapped_column(Boolean, nullable=True)
    owns_a_cart: Mapped[bool] = mapped_column(Boolean, nullable=True)
    land_ownership: Mapped[bool] = mapped_column(Boolean, nullable=True)
    type_of_land_owned: Mapped[str] = mapped_column(String, nullable=True)
    land_size: Mapped[str] = mapped_column(String, nullable=True)
    owns_house: Mapped[bool] = mapped_column(Boolean, nullable=True)
    owns_livestock: Mapped[bool] = mapped_column(Boolean, nullable=True)

    is_head: Mapped[bool] = mapped_column(Boolean, nullable=True)
    is_disabled: Mapped[bool] = mapped_column(Boolean, nullable=True)
    is_pregnant_and_lactating: Mapped[bool] = mapped_column(Boolean, nullable=True)
    is_malnourished_child: Mapped[bool] = mapped_column(Boolean, nullable=True)

    def get_search_text_fields(self) -> list[str]:
        """
        Return family member-specific fields for search text aggregation.
        G2PRegister, G2PPerson, and G2PGeo fields are automatically included via event listeners.
        """
        return [
            # Marital
            self.marriage_date or "",
            self.divorce_date or "",
            # Social Registry Commons
            self.employment_status or "",
            self.role_in_household or "",
            self.relationship_with_household_head or "",
            self.sources_of_income or "",
            self.annual_income or "",
            str(self.owns_a_two_wheeler) if self.owns_a_two_wheeler is not None else "",
            str(self.owns_a_three_wheeler) if self.owns_a_three_wheeler is not None else "",
            str(self.owns_a_four_wheeler) if self.owns_a_four_wheeler is not None else "",
            str(self.owns_a_cart) if self.owns_a_cart is not None else "",
            str(self.land_ownership) if self.land_ownership is not None else "",
            self.type_of_land_owned or "",
            self.land_size or "",
            str(self.owns_house) if self.owns_house is not None else "",
            str(self.owns_livestock) if self.owns_livestock is not None else "",
            str(self.is_head) if self.is_head is not None else "",
            str(self.is_disabled) if self.is_disabled is not None else "",
            str(self.is_pregnant_and_lactating) if self.is_pregnant_and_lactating is not None else "",
            str(self.is_malnourished_child) if self.is_malnourished_child is not None else "",
        ]

    def get_record_name_fields(self) -> list[str]:
        """Return family member fields used to build record_name."""
        return [
            self.first_name or "",
            self.last_name or "",
        ]


# All Register History classes should have the prefix G2PRegisterHistory
class G2PRegisterHistoryFamilyMember(G2PRegisterHistory, G2PPersonHistory, G2PGeoHistory):
    __tablename__ = "g2p_register_history_family_members"

    # FamilyMember-specific fields for history
    marriage_date: Mapped[str] = mapped_column(String, nullable=True)
    divorce_date: Mapped[str] = mapped_column(String, nullable=True)

    # Social Registry Commons
    employment_status: Mapped[str] = mapped_column(String, nullable=True)
    role_in_household: Mapped[str] = mapped_column(String, nullable=True)
    relationship_with_household_head: Mapped[str] = mapped_column(String, nullable=True)
    sources_of_income: Mapped[str] = mapped_column(String, nullable=True)
    annual_income: Mapped[str] = mapped_column(String, nullable=True)
    owns_a_two_wheeler: Mapped[bool] = mapped_column(Boolean, nullable=True)
    owns_a_three_wheeler: Mapped[bool] = mapped_column(Boolean, nullable=True)
    owns_a_four_wheeler: Mapped[bool] = mapped_column(Boolean, nullable=True)
    owns_a_cart: Mapped[bool] = mapped_column(Boolean, nullable=True)
    land_ownership: Mapped[bool] = mapped_column(Boolean, nullable=True)
    type_of_land_owned: Mapped[str] = mapped_column(String, nullable=True)
    land_size: Mapped[str] = mapped_column(String, nullable=True)
    owns_house: Mapped[bool] = mapped_column(Boolean, nullable=True)
    owns_livestock: Mapped[bool] = mapped_column(Boolean, nullable=True)
    is_head: Mapped[bool] = mapped_column(Boolean, nullable=True)
    is_disabled: Mapped[bool] = mapped_column(Boolean, nullable=True)
    is_pregnant_and_lactating: Mapped[bool] = mapped_column(Boolean, nullable=True)
    is_malnourished_child: Mapped[bool] = mapped_column(Boolean, nullable=True)
