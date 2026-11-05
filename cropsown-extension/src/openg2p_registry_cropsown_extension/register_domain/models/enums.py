"""Enumerations for values the ERD does NOT model as lookup tables.

Everything the "CROP SOWN REGISTRY ERD UPDATED" draws as a catalog or lookup
table (crop, crop variety, season, plot category, ownership type, soil
fertility, fertilizer type, land preparation method, water source, infestation
type, cluster status, approval/workflow status) is an **attribute lookup**
instead — a plain String column resolved against g2p_attributes /
g2p_attribute_values, so the values are data an administrator can extend rather
than code. What remains here are the closed value sets the ERD leaves as plain
columns.
"""

from enum import StrEnum


class LandSizeUnitEnum(StrEnum):
    HECTARE = "HECTARE"
    TIMAD = "TIMAD"
    ACRE = "ACRE"
    SQUARE_METER = "SQUARE_METER"


# Cropping system, seed type, seed source and agro-ecological zone are Master Data
# lists (ETH-OAN pack: CROPPING_SYSTEM, SEED_TYPE, SEED_SOURCE, AGRO_ECOLOGICAL_ZONE).
# The values are the pack's codes, one code per choice.
class CroppingSystemEnum(StrEnum):
    CSYS_PURE = "CSYS_PURE"
    CSYS_MIXED = "CSYS_MIXED"
    CSYS_INTERCROPPED = "CSYS_INTERCROPPED"


class SeedClassEnum(StrEnum):
    SEED_IMPROVED = "SEED_IMPROVED"
    SEED_LOCAL = "SEED_LOCAL"
    SEED_HYBRID = "SEED_HYBRID"


class SeedSourceEnum(StrEnum):
    SEEDSRC_COOPERATIVE = "SEEDSRC_COOPERATIVE"
    SEEDSRC_GOVERNMENT = "SEEDSRC_GOVERNMENT"
    SEEDSRC_MARKET = "SEEDSRC_MARKET"
    SEEDSRC_OWN_SAVED = "SEEDSRC_OWN_SAVED"
    SEEDSRC_NGO = "SEEDSRC_NGO"
    SEEDSRC_NEIGHBOUR = "SEEDSRC_NEIGHBOUR"



class CropMaturityStatusEnum(StrEnum):
    READY_FOR_HARVEST = "READY_FOR_HARVEST"
    NOT_YET_READY_FOR_HARVEST = "NOT_YET_READY_FOR_HARVEST"




class GrowthStageEnum(StrEnum):
    EMERGENCE = "EMERGENCE"
    VEGETATIVE = "VEGETATIVE"
    FLOWERING = "FLOWERING"
    MATURITY = "MATURITY"


class SeverityLevelEnum(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AgroEcologicalZoneEnum(StrEnum):
    AEZ_BEREHA = "AEZ_BEREHA"
    AEZ_KOLLA = "AEZ_KOLLA"
    AEZ_WEYNA_DEGA = "AEZ_WEYNA_DEGA"
    AEZ_DEGA = "AEZ_DEGA"
    AEZ_WURCH = "AEZ_WURCH"
