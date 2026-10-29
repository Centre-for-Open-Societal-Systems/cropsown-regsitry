"""The Crop Sown id carries the season segment for the Master Data season codes."""
import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_cropsown_extension.register_domain.id_generator.g2p_id_generator_service import (  # noqa: E402
    G2PIdGeneratorService,
)


@pytest.mark.parametrize("season, segment", [
    ("SEASON_MEHER", "S1/"),
    ("SEASON_BELG", "S2/"),
    ("SEASON_IRRIGATION", "S3/"),
    ("CROP_SEASON_MEHER", "S1/"),
    ("MEHER", "S1/"),
    ("season_belg", "S2/"),
    ("", ""),
    (None, ""),
    ("SEASON_UNKNOWN", ""),
])
def test_season_segment(season, segment):
    assert G2PIdGeneratorService.season_segment(season) == segment
