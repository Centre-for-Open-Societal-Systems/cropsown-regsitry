"""The Farmer-reference update template is stored under a Crop Sown-specific object name, and the seed points
the existing document row at it (the shared MinIO bucket holds every registry's templates by file name)."""

import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src/openg2p_registry_cropsown_extension"
SQL = (PACKAGE / "meta_data/registry-inbound-message-rules/zz_farmer_reference.sql").read_text(encoding="utf-8")
DOCUMENT = "7b91ad96-e435-59a1-bd4e-434fc1254f0a"
OBJECT = "crop_farmer_reference_update.json.j2"


def test_the_template_file_carries_the_fin():
    template = (PACKAGE / "templates" / OBJECT).read_text(encoding="utf-8")
    assert '"cs_farmer_identity"' in template and "fayda_fin" in template and "fayda_fan_id" in template
    assert not (PACKAGE / "templates/farmer_reference_update.json.j2").exists()


def test_the_document_row_is_seeded_and_repointed_to_that_object():
    insert = re.search(rf"INSERT INTO public\.g2p_registry_documents .*'{DOCUMENT}','([^']+)','templates'", SQL)
    assert insert and insert.group(1) == OBJECT
    update = re.search(rf"UPDATE public\.g2p_registry_documents SET document_store_id='([^']+)'.*"
                       rf"WHERE document_id='{DOCUMENT}'", SQL)
    assert update and update.group(1) == OBJECT
