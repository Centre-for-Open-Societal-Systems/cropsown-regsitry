"""Planning and cultivation have one variety dropdown, labelled "Variety" (list SEED_VARIETY).

The older "Crop Variety" dropdown (crop_variety, list CROP_VARIETY) meant the same thing. It is gone from the
table columns of both sections in the base seed and in the zz-oan overlay that repairs databases that still
have it; the database columns stay. The overlay's own replay on PostgreSQL is described in the pull request.
"""
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/meta_data"
SECTIONS = {
    "cropsown_planning_details_section_01": "cs_planning_details_table",
    "cropsown_cultivation_details_section_01": "cs_cultivation_details_table",
}
OVERLAY = META / "zz-oan/96_one_variety_list.sql"


def section_schema(section_id):
    text = (META / "register-metadata/g2p_register_sections.sql").read_text(encoding="utf-8")
    start = text.index(f"'{section_id}'")
    begin = text.index("'{", start)
    end = text.index("}','FALSE','FALSE'", begin)
    return json.loads(text[begin + 1:end + 1].replace("''", "'"))


def widgets(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from widgets(value)
    elif isinstance(node, list):
        for value in node:
            yield from widgets(value)


def table_columns(section_id):
    table = next(w for w in widgets(section_schema(section_id)) if w.get("widget-id") == SECTIONS[section_id])
    return table["widget-data-columns"]


@pytest.mark.parametrize("section_id", SECTIONS)
def test_the_base_seed_has_no_crop_variety_column(section_id):
    schema = section_schema(section_id)
    assert "crop_variety" not in json.dumps(schema)
    assert "CROP_VARIETY" not in json.dumps(schema)
    assert "Crop Variety" not in json.dumps(schema)


@pytest.mark.parametrize("section_id", SECTIONS)
def test_the_remaining_variety_dropdown_is_labelled_variety(section_id):
    varieties = [c for c in table_columns(section_id) if c.get("widget-data-path") == "seed_variety"]
    assert len(varieties) == 1
    column = varieties[0]
    assert column["widget-label"] == "Variety" and column["widget"] == "select"
    assert column["widget-data-source"]["params"]["attribute_id"] == "SEED_VARIETY"


def test_no_seed_file_labels_a_variety_widget_other_than_variety():
    seed = (META / "register-metadata/g2p_register_sections.sql").read_text(encoding="utf-8")
    assert '"widget-label": "Seed Variety"' not in seed and '"widget-label": "Crop Variety"' not in seed
    casing = (META / "zz-oan/30_label_casing.sql").read_text(encoding="utf-8")
    assert '"seed_variety": "Variety"' in casing and "Seed variety" not in casing
    assert "crop_variety" not in casing


def test_the_overlay_repairs_both_sections_by_id_and_guards_the_result():
    sql = OVERLAY.read_text(encoding="utf-8")
    assert b"\r" not in OVERLAY.read_bytes()
    for section_id in SECTIONS:
        assert f"'{section_id}'" in sql
    assert "'crop_variety'" in sql and "'seed_variety', 'Variety'" in sql
    update = sql.split('UPDATE "public"."g2p_register_sections"')[1].split(";")[0]
    assert "WHERE \"section_id\" IN" in update  # explicit section ids, no table-wide rewrite
    assert "RAISE EXCEPTION" in sql and "LIKE '%crop_variety%'" in sql.split("DO $$")[1]
    assert '"seed_variety": "Variety"' in sql


def test_the_overlay_sorts_after_the_files_that_label_the_variety():
    names = sorted(p.name for p in (META / "zz-oan").glob("*.sql"))
    assert names.index("96_one_variety_list.sql") > names.index("86_readable_lists.sql")
    assert len({n.split("_")[0] for n in names}) == len(names)


def test_nothing_around_the_forms_asks_for_a_crop_variety():
    package = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension"
    messages = (package / "register_domain/services/attribute_messages.py").read_text(encoding="utf-8")
    assert '"crop_variety"' not in messages and '"seed_variety": ("Variety", "a variety")' in messages
    assert "CROP_VARIETY" not in (package / "register_domain/services/domain_validation_utils.py").read_text(encoding="utf-8")
    for name in ("odk_to_crop_intake.j2", "crop_file_import_planning_intake.j2", "crop_file_import_cultivation_intake.j2"):
        assert "crop_variety" not in (package / "templates" / name).read_text(encoding="utf-8"), name
    dci = (package / "templates/dci_to_openg2p_cropsown.json.j2").read_text(encoding="utf-8")
    inbound = dci.split('"cs_planning_details"')[1].split('"cs_sowing_details"')[0]
    assert "crop_variety" not in inbound
    for form in ("planning", "cultivation"):
        header = (ROOT / f"import-templates/crop_{form}_intake_import_template.csv").read_text(encoding="utf-8").splitlines()[0]
        assert "crop_variety" not in header.split(",") and "seed_variety" in header.split(",")
    assert "CROP_VARIETY" not in (ROOT / "docs/file-import.md").read_text(encoding="utf-8")


def test_the_odk_forms_have_one_variety_question_and_nothing_needs_crop_variety():
    assert not (ROOT / "odk/mds-export/CROP_VARIETY.json").exists()
    assert not (ROOT / "odk/media/mds/crop_variety.csv").exists()
    assert "CROP_VARIETY" not in (ROOT / "odk/tools/build_mds_forms.py").read_text(encoding="utf-8")
    manifest = (ROOT / "odk/forms/manifest.json").read_text(encoding="utf-8")
    assert "crop_variety" not in manifest and "seed_variety.csv" in manifest
    for form in ("plan", "prep", "sown", "harvest"):
        with zipfile.ZipFile(ROOT / f"odk/forms/crop_sown_registry_{form}.xlsx") as workbook:
            text = "".join(workbook.read(n).decode("utf-8") for n in workbook.namelist() if n.startswith("xl/worksheets/"))
        assert "crop_variety" not in text and "Crop Variety" not in text and "Seed Variety" not in text, form
        assert ("seed_variety" in text) == (form in ("plan", "prep")) and ("Variety" in text) == (form in ("plan", "prep")), form



def test_the_retired_crop_variety_translation_keys_are_not_seeded_for_english():
    seed = (META / "registry-configurations/registry_languages.sql").read_text(encoding="utf-8")
    assert '"crop_variety": "Crop Variety"' not in seed and '"Crop Variety": "Crop Variety"' not in seed
    sql = OVERLAY.read_text(encoding="utf-8")
    assert "- 'crop_variety' - 'Crop Variety'" in sql
