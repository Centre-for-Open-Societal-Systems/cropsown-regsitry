"""Print one field of ci/deploy/connector-image.newdev.json, the connector images New Dev runs.

    python3 ci/deploy/connector_image.py tag                       the develop build tag
    python3 ci/deploy/connector_image.py registry-connector-api    the pinned digest of that image
    python3 ci/deploy/connector_image.py registry-connector-ui

Standard library only. Exit codes: 0 printed, 1 unknown field or malformed pin.
"""
import json
import re
import sys
from pathlib import Path

PIN = Path(__file__).resolve().parent / "connector-image.newdev.json"


def field(name, path=PIN):
    pin = json.loads(Path(path).read_text(encoding="utf-8"))
    if name == "tag":
        value = pin["tag"]
        if not re.fullmatch(r"\d+\.\d+\.\d+-develop\.[1-9]\d*", value):
            raise ValueError("tag must be a develop build tag: %r" % value)
        return value
    value = pin["digests"][name]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ValueError("%s: not a sha256 digest" % name)
    return value


if __name__ == "__main__":
    try:
        print(field(sys.argv[1]))
    except (IndexError, KeyError, ValueError, OSError) as error:
        sys.exit("FAIL: %s" % error)
