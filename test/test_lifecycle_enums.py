r"""Guard: the lifecycle constants used by the service must match the model enums.

`domain_lifecycle_utils` declares the stage and state names as plain strings to
avoid a models -> services -> models import cycle. That duplication is only safe
while the two agree, so this test compares them.

Two things the pattern below has to accommodate, both of which the previous one
got wrong:

  * The two sides are declared differently on purpose. `models/enums.py`
    subclasses `StrEnum`; the service copies are plain classes with no base list
    at all. A pattern that required `class Name(...):` matched the model file and
    never the service file, so every comparison failed with "not found".

  * The body must be matched without nesting a quantifier inside a quantifier.
    `(?:\s+.*\n)+?` overlapped `\s` with `.*\n` and backtracked catastrophically
    on the one class it did match, hanging the test instead of failing it. A
    single lazy `[\s\S]*?`, bounded by the next line beginning in column 0, is
    linear.
"""

import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parent.parent / "cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain"

# class <Name>[(bases)]: plus its indented body, ending at the next top-level
# line — another class, a comment or a statement in column 0 — or end of file.
_CLASS_BODY = r"^class %s\b(?:\([^)]*\))?:[ \t]*\n([\s\S]*?)(?=^\S|\Z)"
_MEMBER = re.compile(r'^\s+([A-Z_]+)\s*=\s*"([^"]+)"', re.M)


def _members(path, class_name):
    src = (SRC / path).read_text()
    block = re.search(_CLASS_BODY % class_name, src, re.M)
    assert block, f"{class_name} not found in {path}"
    return dict(_MEMBER.findall(block.group(1)))


def test_lifecycle_constants_match_the_model_enums():
    for cls in ("LifecycleStageEnum", "StageStateEnum", "RejectedAtStageEnum"):
        model = _members("models/enums.py", cls)
        service = _members("services/domain_lifecycle_utils.py", cls)
        # Without this, a pattern that stopped matching members would compare
        # {} == {} and pass while guarding nothing.
        assert model, f"{cls} parsed as empty in models/enums.py"
        assert model == service, (
            f"{cls} has drifted between models/enums.py and "
            f"services/domain_lifecycle_utils.py:\n  model  : {model}\n  service: {service}"
        )
