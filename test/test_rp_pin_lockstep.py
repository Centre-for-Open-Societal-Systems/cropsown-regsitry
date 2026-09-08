"""Guard: the openg2p-registry pin must be identical in every place it appears.

A variant extends ONE registry-platform version, used two ways:
  * the Docker base images — `ARG RP_VERSION=<v>` in every docker/*/Dockerfile
  * the Helm chart — the `openg2p-registry` dependency `version:` in Chart.yaml

If these drift, the sanity image is built FROM one base while the chart deploys
another, and the overlay lands on a harness it does not match (the failure that
bit us repeatedly). `scripts/bump-rp-version.sh` moves them together; this test
fails the build if anything ever splits them again.

Stdlib only, and deliberately no pytest import: `python3 test/test_rp_pin_lockstep.py`
runs the same check on any machine with a bare interpreter. The Jenkins build
agents have a python3 but no working pip, so the pipeline invokes it that way;
.github/workflows/checks.yml still collects it as an ordinary pytest test.
"""

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CHART = REPO / "helm" / "openg2p-cropsown-registry" / "Chart.yaml"


def _docker_pins():
    pins = {}
    for f in sorted((REPO / "docker").glob("*/Dockerfile")):
        m = re.search(r"^ARG RP_VERSION=(\S+)", f.read_text(), re.M)
        if m:
            pins[f.relative_to(REPO).as_posix()] = m.group(1)
    return pins


def _chart_pin():
    m = re.search(
        r"-\s*name:\s*openg2p-registry\b.*?version:\s*(\S+)",
        CHART.read_text(), re.S,
    )
    return m.group(1) if m else None


def test_rp_pin_is_in_lockstep():
    docker = _docker_pins()
    chart = _chart_pin()
    assert docker, "no ARG RP_VERSION found in any docker/*/Dockerfile"
    assert chart, "no openg2p-registry dependency version found in Chart.yaml"

    all_pins = set(docker.values()) | {chart}
    if len(all_pins) != 1:
        lines = [f"  Chart.yaml openg2p-registry dependency: {chart}"]
        lines += [f"  {p}: {v}" for p, v in docker.items()]
        raise AssertionError(
            "openg2p-registry pin has SPLIT — images and chart must be identical:\n"
            + "\n".join(lines)
            + "\n\nFix with: ./scripts/bump-rp-version.sh <version>"
        )


if __name__ == "__main__":
    try:
        test_rp_pin_is_in_lockstep()
    except AssertionError as err:
        print(err, file=sys.stderr)
        sys.exit(1)
    print("openg2p-registry pin is in lockstep")
