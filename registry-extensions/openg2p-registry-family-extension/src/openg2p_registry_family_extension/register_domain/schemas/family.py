from typing import Optional

from openg2p_registry_core.schemas import G2PRegisterBaseSchema, G2PRegisterHistorySchema


class G2PRegisterSchemaFamily(G2PRegisterBaseSchema):
    """
    Schema for Family register.
    Inherits fields from G2PRegisterBaseSchema.
    """
    # Family-specific fields only
    type_of_housing: Optional[str] = None
    house_condition: Optional[str] = None
    sanitation_condition: Optional[str] = None
    water_access: Optional[str] = None
    electricity_access: Optional[str] = None

    ethnic_group: Optional[str] = None
    belong_to_protected_groups: Optional[bool] = None
    under_other_vulnerable_status: Optional[bool] = None

    # Addl fields
    no_of_children: Optional[int] = None


class G2PRegisterHistorySchemaFamily(G2PRegisterHistorySchema):
    """
    Schema for Family history.
    Inherits fields from G2PRegisterHistorySchema.
    """
    # Family-specific fields only
    type_of_housing: Optional[str] = None
    house_condition: Optional[str] = None
    sanitation_condition: Optional[str] = None
    water_access: Optional[str] = None
    electricity_access: Optional[str] = None

    ethnic_group: Optional[str] = None
    belong_to_protected_groups: Optional[bool] = None
    under_other_vulnerable_status: Optional[bool] = None

    # Addl fields
    no_of_children: Optional[int] = None