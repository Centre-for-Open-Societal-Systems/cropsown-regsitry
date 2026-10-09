#!/usr/bin/env python3
"""Build the crop sown forms' location lists from the registry's own hierarchy.

The planning and cultivation forms pick region > zone > woreda > kebele from
media/region.csv, zone.csv, woreda.csv and kebele1.csv. The crop sown registry
holds the same places as attribute values (REGION_ET07, ZONE_ET0714,
WOREDA_ET071401, KEBELE_ET071401101001; meta_data/lookup-data/
g2p_attribute_values.sql), which is the shared Ethiopia location hierarchy every
registry's Master Data uses. Generating the CSVs from it keeps the two in step:
every place the registry knows is offered, with the registry's name, and every
pick becomes an id the registry resolves. csr_odk_transform.j2 maps the picks:

    region   name region_et07          -> REGION_ET07   (region_map)
    zone     name ET0714               -> ZONE_ET0714
    woreda   name ET071401             -> WOREDA_ET071401
    kebele   name ET071401101001       -> KEBELE_ET071401101001

Run after the hierarchy changes, then publish the new CSVs on ODK Central
(README.md, "Publishing"):

    python docs/odk/build_location_media.py          # rewrite media/*.csv
    python docs/odk/build_location_media.py --check  # exit 1 if they are stale

test/test_odk_location_media.py runs the check.
"""

from __future__ import annotations

import csv
import io
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
SOURCE = (
    REPO
    / "cropsown-extension/src/openg2p_registry_cropsown_extension/meta_data/lookup-data/g2p_attribute_values.sql"
)
MEDIA = HERE / "media"

# A name is a plain '...' string, or E'...' when it holds a backslash.
_ROW = re.compile(
    r"\('(REGION|ZONE|WOREDA|KEBELE)_(ET\d+)','\1','ET\d+',(E?)'((?:[^'\\]|''|\\.)*)',"
    r"(?:NULL|'(?:REGION|ZONE|WOREDA)_(ET\d+)'),"
)


def load_hierarchy(source: pathlib.Path = SOURCE) -> dict[str, list[tuple[str, str, str | None]]]:
    """{level: [(code, name, parent code)]} from the attribute value seed."""
    levels: dict[str, list[tuple[str, str, str | None]]] = {"region": [], "zone": [], "woreda": [], "kebele": []}
    seen = set()
    for match in _ROW.finditer(source.read_text(encoding="utf-8")):
        level, code, escaped, name, parent = (
            match.group(1).lower(), match.group(2), match.group(3), match.group(4), match.group(5)
        )
        if escaped:
            name = re.sub(r"\\(.)", r"\1", name)
        if (level, code) in seen:
            continue
        seen.add((level, code))
        levels[level].append((code, name.replace("''", "'").strip(), parent))
    return levels


def _region_key(code: str) -> str:
    return f"region_{code.lower()}"


def build(levels) -> dict[str, str]:
    """The four CSVs as text, in the column layout the forms read."""

    def table(header, rows):
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
        return buffer.getvalue()

    by_name = lambda row: (row[1].lower(), row[0])  # noqa: E731
    regions = sorted(levels["region"], key=by_name)
    zones = sorted((z for z in levels["zone"] if z[2]), key=lambda z: (z[2], z[1].lower(), z[0]))
    woredas = sorted((w for w in levels["woreda"] if w[2]), key=lambda w: (w[2], w[1].lower(), w[0]))
    kebeles = sorted((k for k in levels["kebele"] if k[2]), key=lambda k: (k[2], k[1].lower(), k[0]))
    return {
        "region.csv": table(["label", "name"], [(name, _region_key(code)) for code, name, _ in regions]),
        "zone.csv": table(["region", "name", "label"], [(_region_key(p), code, name) for code, name, p in zones]),
        "woreda.csv": table(["zone", "name", "label"], [(p, code, name) for code, name, p in woredas]),
        "kebele1.csv": table(["name", "label", "woreda"], [(code, name, p) for code, name, p in kebeles]),
    }


def main(argv: list[str]) -> int:
    files = build(load_hierarchy())
    stale = [name for name, text in files.items() if (MEDIA / name).read_bytes().decode("utf-8") != text]
    if "--check" in argv:
        if stale:
            print(f"stale, rerun docs/odk/build_location_media.py: {stale}", file=sys.stderr)
            return 1
        print("location media match the registry hierarchy")
        return 0
    for name, text in files.items():
        (MEDIA / name).write_bytes(text.encode("utf-8"))
    print(f"wrote {', '.join(files)}" + (f" (changed: {stale})" if stale else " (no changes)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
