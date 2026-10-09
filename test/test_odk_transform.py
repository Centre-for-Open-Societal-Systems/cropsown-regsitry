"""csr_odk_transform.j2 on ODK submissions shaped like the connector sends them.

Each payload is what reaches the registry inside {"header", "message":
{"payload": ...}}: one stage form's groups, with repeats already expanded by
the connector (resolve_nav_links) and photos inline when the pipeline embeds
attachments.
"""

import base64
import copy
import json
import pathlib

import pytest

jinja2 = pytest.importorskip("jinja2")

REPO = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = (
    REPO / "cropsown-extension/src/openg2p_registry_cropsown_extension/templates/csr_odk_transform.j2"
)

PHOTO = {
    "__type": "File",
    "name": "1791460254539.jpg",
    "type": "image/jpeg",
    "data": base64.b64encode(b"\xff\xd8\xff\xe0 not really a jpeg").decode(),
}

PLANNING = {
    "farmer_identity": {
        "farmer_id": "FR-0000000001",
        "fayda_fan_id": "1234567890123456",
        "crop_year": 2026,
        "production_season": "belg",
    },
    "address": {"region_display_id": "REGION_ET07", "zone_display_id": "ET0714", "woreda_display_id": "ET071401", "kebele_display_id": "07140101001"},
    "planning": [{"land_info_id": "LND-1", "season_id": "belg", "crop_name_id": "teff", "crop_planned_area": 1, "cluster_information": []}],
    "__system": {"submissionDate": "2026-10-08T06:00:00.000Z"},
}

SOWING = {
    "farmer_plot": {"fyda_id": "1234 5678 9012 3456", "crop_year": 2026, "production_season": "belg"},
    "sowing_details": [
        {
            "land_info_id": "LND-1",
            "cluster_status_ids": "independent",
            "clustered_details": {},
            "independant_details": {"season_id": "belg", "area_sown": 1, "crop_name_id": "teff", "sowing_date_gc": "2026-09-01"},
        }
    ],
    "infestation_incidents": [
        {"infestation_land_info_id": "LND-1", "cluster_status_id": "independent", "infestation_type_ids": "pest", "observation_date": "2026-09-20"}
    ],
    "__system": {"submissionDate": "2026-10-08T06:00:00.000Z"},
}


def render(submission):
    return json.loads(jinja2.Template(TEMPLATE.read_text(encoding="utf-8")).render(expanded=submission))


@pytest.mark.parametrize(
    "typed, sent",
    [
        ("1234567890123456", "1234 5678 9012 3456"),  # as agents type it
        ("1234-5678-9012-3456", "1234 5678 9012 3456"),
        (" 1234 5678  9012 3456 ", "1234 5678 9012 3456"),
        ("1234 5678 9012 3456", "1234 5678 9012 3456"),
        ("12345", "12345"),  # not 16 digits: left for the validator to reject
    ],
)
def test_fayda_id_is_sent_in_the_registers_format(typed, sent):
    submission = copy.deepcopy(PLANNING)
    submission["farmer_identity"]["fayda_fan_id"] = typed
    assert render(submission)["cs_intake_record"][0]["fayda_fan_id"] == sent


def test_no_photos_means_no_document_fields():
    plan, sow = render(PLANNING), render(SOWING)
    assert "record_image_document_id" not in plan["cs_intake_record"][0]
    assert "geo_tagged_photo_document_id" not in sow["cs_sowing_details"][0]
    assert "geo_tagged_photo_document_id" not in sow["cs_infestation_details"][0]


def test_an_inline_record_photo_reaches_the_crop_sown_record():
    submission = copy.deepcopy(PLANNING)
    submission["farmer_identity"]["record_photo"] = PHOTO
    assert render(submission)["cs_intake_record"][0]["record_image_document_id"] == PHOTO


def test_inline_sowing_and_infestation_photos_reach_their_rows():
    submission = copy.deepcopy(SOWING)
    submission["sowing_details"][0]["geo_tagged_photo"] = PHOTO
    submission["infestation_incidents"][0]["infestation_photo"] = PHOTO
    out = render(submission)
    assert out["cs_sowing_details"][0]["geo_tagged_photo_document_id"] == PHOTO
    assert out["cs_infestation_details"][0]["geo_tagged_photo_document_id"] == PHOTO
    assert out["cs_common_intake_record"][0]["fayda_fan_id"] == "1234 5678 9012 3456"


def test_a_photo_that_arrived_as_a_file_name_only_is_left_out():
    submission = copy.deepcopy(SOWING)
    submission["sowing_details"][0]["geo_tagged_photo"] = "1791460254539.jpg"
    assert "geo_tagged_photo_document_id" not in render(submission)["cs_sowing_details"][0]
