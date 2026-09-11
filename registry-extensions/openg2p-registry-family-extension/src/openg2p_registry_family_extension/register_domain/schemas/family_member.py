from typing import Optional

from openg2p_registry_core.schemas import (
    G2PRegisterBaseSchema, G2PPersonSchema, G2PGeoSchema,
    G2PRegisterHistorySchema, G2PPersonHistorySchema, G2PGeoHistorySchema
)


class G2PRegisterSchemaFamilyMember(G2PRegisterBaseSchema, G2PPersonSchema, G2PGeoSchema):
    """
    Schema for FamilyMember register.
    Inherits fields from G2PRegisterBaseSchema, G2PPersonSchema, and G2PGeoSchema.
    """
    # Additional marital info
    marriage_date: Optional[str] = None
    divorce_date: Optional[str] = None

    # Social Registry Commons
    employment_status: Optional[str] = None
    role_in_household: Optional[str] = None
    relationship_with_household_head: Optional[str] = None

    sources_of_income: Optional[str] = None
    annual_income: Optional[str] = None
    owns_a_two_wheeler: Optional[bool] = None
    owns_a_three_wheeler: Optional[bool] = None
    owns_a_four_wheeler: Optional[bool] = None
    owns_a_cart: Optional[bool] = None
    land_ownership: Optional[bool] = None
    type_of_land_owned: Optional[str] = None
    land_size: Optional[str] = None
    owns_house: Optional[bool] = None
    owns_livestock: Optional[bool] = None

    is_head: Optional[bool] = None
    is_disabled: Optional[bool] = None
    is_pregnant_and_lactating: Optional[bool] = None
    is_malnourished_child: Optional[bool] = None


class G2PRegisterHistorySchemaFamilyMember(G2PRegisterHistorySchema, G2PPersonHistorySchema, G2PGeoHistorySchema):
    """
    Schema for FamilyMember history.
    Inherits fields from G2PRegisterHistorySchema, G2PPersonHistorySchema, and G2PGeoHistorySchema.
    """
    # Additional marital info
    marriage_date: Optional[str] = None
    divorce_date: Optional[str] = None

    # Social Registry Commons
    employment_status: Optional[str] = None
    role_in_household: Optional[str] = None
    relationship_with_household_head: Optional[str] = None

    sources_of_income: Optional[str] = None
    annual_income: Optional[str] = None
    owns_a_two_wheeler: Optional[bool] = None
    owns_a_three_wheeler: Optional[bool] = None
    owns_a_four_wheeler: Optional[bool] = None
    owns_a_cart: Optional[bool] = None
    land_ownership: Optional[bool] = None
    type_of_land_owned: Optional[str] = None
    land_size: Optional[str] = None
    owns_house: Optional[bool] = None
    owns_livestock: Optional[bool] = None

    is_head: Optional[bool] = None
    is_disabled: Optional[bool] = None
    is_pregnant_and_lactating: Optional[bool] = None
    is_malnourished_child: Optional[bool] = None