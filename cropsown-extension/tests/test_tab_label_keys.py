"""Register tab labels are lowercase translation keys with display text.

The platform validator rejects any other tab_label when a tab is rebuilt from the
metadata cache, which made the change request search fail with SYS-ERR-001.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "src" / "openg2p_registry_cropsown_extension" / "meta_data"
DOMAIN = ROOT.parent / "translation" / "domain.json"
KEY = re.compile(r"^[a-z][a-z0-9_]*$")  # G2PRegisterUITab.validate_tab_label
ROW = re.compile(r"\('([^']+)','[^']+','([^']+)',\d+,'(?:TRUE|FALSE)'\)")


def register_tabs():
    tabs = {}
    for sql in sorted(META.rglob("*.sql")):
        text = sql.read_text(encoding="utf-8")
        for insert in re.findall(r'INSERT INTO "public"\."g2p_register_ui_tabs".*?;', text, re.S):
            tabs.update(ROW.findall(insert))
    return tabs


def test_register_tab_labels_are_translated_keys():
    tabs = register_tabs()
    assert "cropsown_farmer_tab" in tabs
    domain = json.loads(DOMAIN.read_text(encoding="utf-8"))
    for tab_id, label in tabs.items():
        assert KEY.match(label), (tab_id, label)
        assert domain.get(label), label


def test_farmer_tab_key_has_its_display_text():
    overlay = (META / "zz-oan" / "50_tab_label_keys.sql").read_text(encoding="utf-8")
    assert '"cropsown_farmer_tab": "Farmer"' in overlay
