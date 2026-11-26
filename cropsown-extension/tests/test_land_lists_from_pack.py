"""Ownership type, Land preparation method and Cultivation type read the ETH-OAN pack's
LAND_OWNERSHIP_TYPE, LAND_PREPARATION_METHOD and FARM_MACHINERY lists, on the web form
(zz-oan/96a_land_lists_from_pack.sql) and in the ODK forms (build_mds_forms.py)."""
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ZZ_OAN = REPO / "cropsown-extension/src/openg2p_registry_cropsown_extension/meta_data/zz-oan"
OVERLAY = ZZ_OAN / "96a_land_lists_from_pack.sql"
NEW_LISTS = {"OWNERSHIP_TYPE": "LAND_OWNERSHIP_TYPE", "LAND_PREP_METHOD": "LAND_PREPARATION_METHOD",
             "MACHINERY": "FARM_MACHINERY"}


def test_the_overlay_moves_each_old_list_to_its_new_one_and_guards_the_result():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "WHEN 'OWNERSHIP_TYPE' THEN 'LAND_OWNERSHIP_TYPE'" in sql
    assert "WHEN 'LAND_PREP_METHOD' THEN 'LAND_PREPARATION_METHOD'" in sql
    assert "ELSE 'FARM_MACHINERY' END" in sql  # the third old list, MACHINERY
    assert "IN ('OWNERSHIP_TYPE', 'LAND_PREP_METHOD', 'MACHINERY')" in sql
    assert "RAISE EXCEPTION 'Crop Sown dropdowns still on an old land list" in sql


def test_the_overlay_runs_before_the_land_rows_copy_the_ownership_dropdown():
    names = sorted(p.name for p in ZZ_OAN.glob("*.sql"))
    assert names.index("89_master_data_dropdowns.sql") < names.index(OVERLAY.name)
    for copier in ("97f_cultivation_land_details.sql", "97g_sowing_harvest_land_rows.sql"):
        assert names.index(OVERLAY.name) < names.index(copier), copier
    assert names[-1] == "98_ethiopian_dates.sql"


def _builder():
    spec = importlib.util.spec_from_file_location("build_mds_forms", REPO / "odk/tools/build_mds_forms.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_odk_forms_read_the_new_lists():
    lists = _builder().INLINE_LISTS
    assert (lists["ownership"], lists["land_prep_method"], lists["cult_method"]) == (
        "LAND_OWNERSHIP_TYPE", "LAND_PREPARATION_METHOD", "FARM_MACHINERY")
    manifest = json.loads((REPO / "odk/forms/manifest.json").read_text(encoding="utf-8"))
    used = {name for form in manifest["forms"] for name in form["master_data_lists"].values()}
    assert not used & set(NEW_LISTS), used & set(NEW_LISTS)
    assert set(NEW_LISTS.values()) <= used
