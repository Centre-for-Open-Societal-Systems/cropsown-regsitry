from datetime import date

from openg2p_fastapi_common.service import BaseService
from openg2p_registry_core.interfaces import G2PIdGeneratorInterface, IdAffix
from openg2p_registry_core.models.g2p_register import G2PRegister


class G2PIdGeneratorService(BaseService, G2PIdGeneratorInterface):
    """Functional-id affixes for the crop sown registers.

    A crop sown id carries the season it belongs to:

        REG/S1/2026/00012

    The season segment is S1-S4, one per cropping season, taken from the
    record's own production season. A Crop Sown id is never issued without
    it: a season code missing from SEASON_NUMBERS raises instead of giving the
    seasonless form (REG/2026/00012). Intake save and submit refuse such a code
    first (_validate_production_season reads SEASON_NUMBERS), so it cannot
    reach approval.

    The year is resolved when the id is minted, so a record created in 2027
    carries /2027/. The padding is the id-generator pool's idLength (5), set in
    the Helm values.
    """

    # register mnemonic -> sequence prefix, minus the season and year segments
    PREFIXES = {
        "cropsown": "REG",
        "production": "CROP/PROD",
        "cluster": "CLTR",
        "infestation": "PI",
    }

    # Ethiopian cropping calendar order: the main rains first, then the short
    # rains, then irrigated and perennial cropping. Records hold the Master Data
    # CROP_SEASON codes (SEASON_MEHER, SEASON_BELG, SEASON_IRRIGATION); the other
    # spellings are kept for older submissions.
    SEASON_NUMBERS = {
        "SEASON_MEHER": 1,
        "SEASON_BELG": 2,
        "SEASON_IRRIGATION": 3,
        "CROP_SEASON_MEHER": 1,
        "MEHER": 1,
        "CROP_SEASON_BELG": 2,
        "BELG": 2,
        "CROP_SEASON_BEGA": 3,
        "BEGA": 3,
    }

    @classmethod
    def season_number(cls, season: str | None) -> int | None:
        """`SEASON_MEHER` / `MEHER` -> 1; a code not in SEASON_NUMBERS -> None."""
        return cls.SEASON_NUMBERS.get(str(season or "").strip().upper())

    @classmethod
    def season_segment(cls, season: str | None) -> str:
        """`SEASON_MEHER` / `MEHER` -> `S1/`. An unknown or missing season raises:
        a Crop Sown id always carries its season."""
        number = cls.season_number(season)
        if not number:
            raise ValueError(
                f"Crop Sown ID not issued: production season {season!r} is not a known season "
                f"({', '.join(sorted(k for k in cls.SEASON_NUMBERS if k.startswith('SEASON_')))})"
            )
        return f"S{number}/"

    def generate_prefix_suffix(
        self, g2p_register: G2PRegister, register_mnemonic: str
    ) -> IdAffix:
        mnemonic = (register_mnemonic or "").lower()
        if isinstance(g2p_register, dict):
            season_val = g2p_register.get("production_season") or g2p_register.get("season")
        else:
            season_val = (
                getattr(g2p_register, "production_season", None)
                or getattr(g2p_register, "season", None)
            )
        if mnemonic == "cropsown":
            season = self.season_segment(season_val)
        else:
            # Only Crop Sown records are issued ids; the other prefixes keep the
            # optional segment they always had.
            number = self.season_number(season_val)
            season = f"S{number}/" if number else ""
        year = date.today().year

        prefix = self.PREFIXES.get(mnemonic)
        if prefix:
            return IdAffix(prefix=f"{prefix}/{season}{year}/", suffix="")

        return IdAffix(prefix=f"CROP/{mnemonic.upper() or 'REC'}/{season}{year}/", suffix="")
