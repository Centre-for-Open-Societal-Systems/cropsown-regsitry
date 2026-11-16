"""The Crop Sown id carries the season segment for the Master Data season codes, and is
never issued without it."""
from datetime import date

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_cropsown_extension.register_domain.id_generator.g2p_id_generator_service import (  # noqa: E402
    G2PIdGeneratorService,
)

YEAR = date.today().year


@pytest.mark.parametrize("season, segment", [
    ("SEASON_MEHER", "S1/"),
    ("SEASON_BELG", "S2/"),
    ("SEASON_IRRIGATION", "S3/"),
    ("CROP_SEASON_MEHER", "S1/"),
    ("MEHER", "S1/"),
    ("season_belg", "S2/"),
])
def test_season_segment(season, segment):
    assert G2PIdGeneratorService.season_segment(season) == segment


@pytest.mark.parametrize("season", ["SEASON_MEHAR", "SEASON_UNKNOWN", "", None])
def test_an_unknown_or_missing_season_gets_no_seasonless_id(season):
    # The seasonless form (REG/2026/...) is gone: no number, no id.
    assert G2PIdGeneratorService.season_number(season) is None
    with pytest.raises(ValueError, match="is not a known season"):
        G2PIdGeneratorService.season_segment(season)
    with pytest.raises(ValueError, match="is not a known season"):
        G2PIdGeneratorService().generate_prefix_suffix({"production_season": season}, "cropsown")


def test_a_crop_sown_id_carries_its_season_and_year():
    affix = G2PIdGeneratorService().generate_prefix_suffix({"production_season": "SEASON_BELG"}, "CropSown")
    assert (affix.prefix, affix.suffix) == (f"REG/S2/{YEAR}/", "")


def test_other_prefixes_keep_their_optional_season_segment():
    # Only Crop Sown records are issued ids; the other prefixes are unchanged.
    service = G2PIdGeneratorService()
    assert service.generate_prefix_suffix({"season": None}, "cluster").prefix == f"CLTR/{YEAR}/"
    assert service.generate_prefix_suffix({"season": "SEASON_MEHER"}, "cluster").prefix == f"CLTR/S1/{YEAR}/"
