"""The multi-select list says how many items are chosen, not "SelectedCount".

The widget (@openg2p/registry-widgets) reads common.selectedCount with the
number as {count}, and common.selectAll / deselectAll / clearAll for its
buttons. The English seed held the raw keys. The overlay merges readable text
inside "common" for English only, after the seed and the casing overlays.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "cropsown-extension/src/openg2p_registry_cropsown_extension/meta_data"
OVERLAY = META / "zz-oan/97r_multi_select_labels.sql"
METADATA = ROOT / "reference/new-dev/metadata.json"
KEYS = {"selectedCount", "selectAll", "deselectAll", "clearAll"}


def merged():
    text = OVERLAY.read_text(encoding="utf-8")
    return json.loads(re.search(r"\|\|\s*'(\{.*?\})'::jsonb", text, re.S).group(1))


def test_every_raw_key_gets_readable_text():
    values = merged()
    assert set(values) == KEYS
    assert values["selectedCount"] == "{count} selected"
    for value in values.values():
        assert not re.fullmatch(r"[A-Z][a-z]+(?:[A-Z][a-z]*)+", value), value


def test_merged_inside_common_for_english_only():
    text = OVERLAY.read_text(encoding="utf-8")
    assert "jsonb_set(" in text and "'{common}'" in text
    assert "-> 'common'" in text, "the other common keys must be kept"
    assert re.search(r"WHERE \"language_code\" = 'en';\s*$", text)


def test_new_dev_english_held_the_raw_keys_the_overlay_replaces():
    languages = json.loads(METADATA.read_text(encoding="utf-8"))["languages"]
    english = next(lang for lang in languages if lang["language_code"] == "en")
    common = english["core_translation"]["common"]
    assert {key for key in KEYS if re.fullmatch(r"[A-Z]\w+", common.get(key) or "")} == KEYS


def test_runs_after_the_seed_and_the_casing_overlays():
    names = sorted(p.name for p in (META / "zz-oan").glob("*.sql"))
    assert names.index("30_label_casing.sql") < names.index("85_readable_text.sql") < names.index(OVERLAY.name)
