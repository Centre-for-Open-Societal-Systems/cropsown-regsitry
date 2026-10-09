"""The committed ODK forms agree with the pipelines and the transform.

odk/crop_sown_registry_*.xlsx are the four stage XLSForms published on ODK
Central, exported from there. If one drifts from the connector pipelines' form
ids, the connector polls a form nobody fills; if one gains a photo question
under a name the transform does not map, that photo never reaches the intake.
"""

import pathlib
import re

import pytest

openpyxl = pytest.importorskip("openpyxl")

REPO = pathlib.Path(__file__).resolve().parent.parent
ODK = REPO / "odk"
PIPELINES = REPO / "openg2p-connector-service/src/openg2p_connector_service/default_pipelines.py"
LOCAL_SEED = REPO / "local/postgres/seed_connector_pipelines.sql"
# Photo questions csr_odk_transform.j2 maps to a document field.
MAPPED_PHOTOS = {"record_photo", "geo_tagged_photo", "infestation_photo"}
MEDIA_TYPES = {"image", "file", "audio", "video", "background-audio"}
FORMS = sorted(ODK.glob("crop_sown_registry_*.xlsx"))


def _sheet(form, name):
    workbook = openpyxl.load_workbook(form, read_only=True)
    rows = list(workbook[name].iter_rows(values_only=True))
    header = [str(cell).strip() if cell else "" for cell in rows[0]]
    return [dict(zip(header, row)) for row in rows[1:] if any(row)]


def test_the_four_forms_are_the_ones_the_pipelines_poll():
    form_ids = {_sheet(form, "settings")[0]["form_id"] for form in FORMS}
    seeded = set(re.findall(r'"form_id": "([\w]+)"', PIPELINES.read_text(encoding="utf-8")))
    local = set(re.findall(r"'(crop_sown_registry_\w+)'", LOCAL_SEED.read_text(encoding="utf-8")))
    assert len(FORMS) == 4
    assert form_ids == seeded == local


@pytest.mark.parametrize("form", FORMS, ids=lambda p: p.stem)
def test_every_media_file_the_form_reads_is_committed(form):
    referenced = set()
    for row in _sheet(form, "survey"):
        text = " ".join(str(row.get(col) or "") for col in ("type", "appearance", "calculation", "choice_filter"))
        referenced.update(re.findall(r"([\w.-]+\.csv)", text))
        referenced.update(f"{name}.csv" for name in re.findall(r"(?:search|pulldata)\(\s*'([\w.-]+)'", text))
    missing = sorted(name for name in referenced if not (ODK / "media" / name).exists())
    assert not missing, f"media the form reads but odk/media lacks: {missing}"


@pytest.mark.parametrize("form", FORMS, ids=lambda p: p.stem)
def test_every_photo_question_is_mapped_by_the_transform(form):
    photos = {
        row["name"] for row in _sheet(form, "survey")
        if row.get("type") and str(row["type"]).split()[0] in MEDIA_TYPES
    }
    unmapped = sorted(photos - MAPPED_PHOTOS)
    assert not unmapped, (
        f"photo questions {unmapped} are not mapped in csr_odk_transform.j2; "
        "they would be dropped on ingest"
    )
