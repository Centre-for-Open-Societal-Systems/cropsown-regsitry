"""The Crop sown record's first tab is named "Farmer details" (label key cropsown_record_tab)."""
from pathlib import Path

ZZ_OAN = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension/meta_data/zz-oan"
OVERLAY = ZZ_OAN / "97d_record_tab_farmer_details.sql"


def test_the_record_tab_is_named_farmer_details_in_every_language():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "jsonb_build_object('cropsown_record_tab', 'Farmer details')" in sql
    assert "\"language_code\" IN ('en', 'am', 'om', 'ti')" in sql


def test_the_overlay_runs_after_the_label_casing_and_before_the_dates():
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names.index(OVERLAY.name) > names.index("30_label_casing.sql")
    assert names[-1] == "98_ethiopian_dates.sql"
    assert len({n.split("_")[0] for n in names}) == len(names)
