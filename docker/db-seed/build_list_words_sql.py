#!/usr/bin/env python3
"""Render the commodity and season words of the ETH-OAN pack as db-seed SQL.

    build_list_words_sql.py <openg2p-data directory>     # SQL on stdout
    build_list_words_sql.py <openg2p-data directory> <plain_text.py>
        # check only: fails when a planning record name word differs from the pack

The register lists show the codes stored in the records (CROP_MAIZE,
SEASON_MEHER). The staff portal looks every list value up in the English domain
translations, so this merges the pack's labels for CROP_COMMODITY and
CROP_SEASON into them. The pack is the source: nothing here is typed by hand, and
the image build runs this against the openg2p-data commit it pins.

The merge puts these defaults first and the language row's own values last, so a
translation edited locally wins, and a second run changes nothing. Standard
library only: it runs inside the registry db-seed image.
"""
import importlib.util
import json
import sys
from pathlib import Path

DOMAIN = Path("packs/ETH-OAN/domains/agriculture")
LISTS = ("crop_commodity.json", "crop_season.json")


def words(data_dir: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for name in LISTS:
        pack = json.loads((data_dir / DOMAIN / name).read_text(encoding="utf-8"))
        for value in pack["values"]:
            code, label = value["value_code"], value["value_display"]
            if not code or not label:
                raise SystemExit(f"{name}: a value has no code or no label")
            found[code] = label
    return found


def render(found: dict[str, str]) -> str:
    body = ",\n".join(f" {json.dumps(code)}: {json.dumps(label, ensure_ascii=False)}" for code, label in sorted(found.items()))
    body = body.replace("'", "''")
    return (
        "-- Generated from the ETH-OAN pack by docker/db-seed/build_list_words_sql.py; do not edit.\n"
        'UPDATE "public"."registry_languages"\n'
        "SET \"domain_translation\" = ('{\n" + body + "\n}'::jsonb || COALESCE(\"domain_translation\"::jsonb, '{}'::jsonb))::json\n"
        "WHERE \"language_code\" = 'en';\n"
    )


def mismatched_names(found: dict[str, str], plain_text: Path) -> list[str]:
    """Commodity codes whose record-name word (plain_text.py) is not the pack label."""
    spec = importlib.util.spec_from_file_location("plain_text", plain_text)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return sorted(code for code, label in found.items()
                  if code.startswith("CROP_") and module.commodity_label(code) != label)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        wrong = mismatched_names(words(Path(sys.argv[1])), Path(sys.argv[2]))
        if wrong:
            raise SystemExit("Record-name words differ from the pack labels: " + ", ".join(wrong))
    elif len(sys.argv) == 2:
        sys.stdout.write(render(words(Path(sys.argv[1]))))
    else:
        raise SystemExit(__doc__)
