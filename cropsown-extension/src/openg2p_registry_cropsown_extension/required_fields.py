"""Required fields of the Crop Sown intake forms, read from the section metadata.

`widget-required` in a section's UI schema is the one place the rule lives: the
staff UI marks the field, and the save and submit checks (required_intake.py)
read the same flag, on every channel (web, ODK, partner). Making a field
optional is a metadata change, not a code change.

The rules follow the staff UI (ui-widgets `evaluateWidgetConditions`):

- rules run in order and the last show/hide wins; a field hidden by a rule is
  not required;
- a `require` rule makes a field required while its condition matches;
- a list (table) section needs at least one row only when the table widget
  itself is `widget-required`; each row must carry its required columns.

A condition is {"field", "operator", "value"} (equals, notEquals, in, notIn,
empty, notEmpty, contains, notContains, greaterThan, lessThan) or a group
{"and": [...]}, {"or": [...]}, {"not": {...}}. A condition this module does not
know does not match, so the field keeps its metadata default.

This module has no database or framework imports, so it can be tested alone.
"""

# Widgets whose value is not a field of the section's record: a table is its own
# list of rows, display and group widgets hold no input.
SKIPPED = {"table", "dialog-table", "register-lookup", "parent-lookup", "display", "header-section"}
TABLES = ("table", "dialog-table")

# A widget whose typed value is stored in other columns: the Farmer lookup
# section takes one Fayda ID and the field rules store it as the FIN or the FAN.
# The stored row has no such column, so it counts as filled when one of the
# columns it is stored in is.
STORED_AS = {"fayda_id": ("fayda_fin", "fayda_fan_id")}

MESSAGES = {
    "required_fill_in": "{section}: fill in {fields}",
    "required_fill_in_row": "{section}, row {row}: fill in {fields}",
    "required_add_file": "{section}: add {fields}",
    "required_add_row": "{section}: add at least one row",
}


def is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or (
        isinstance(value, (list, tuple, dict, set)) and not value)


def humanize(key) -> str:
    """A readable name for a key nobody translated: no underscores or hyphens."""
    text = " ".join(str(key or "").replace("_", " ").replace("-", " ").split())
    return text[:1].upper() + text[1:]


# --------------------------------------------------------------- conditions --
def value_at(values: dict, path):
    """`path` is "<register id>.<field>" or a bare column key; `values` maps
    register ids to records, or is a record itself."""
    if not isinstance(path, str):
        return None
    if path in values:
        return values.get(path)
    current = values
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _boolean_like(value) -> bool:
    if value is True or value == 1:
        return True
    if value is False or value == 0:
        return False
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return bool(value)


def _same(field, expected) -> bool:
    if isinstance(expected, bool):
        return isinstance(field, bool) and field == expected
    if isinstance(field, bool):
        return field == _boolean_like(expected)
    return field == expected or (field is not None and expected is not None and str(field) == str(expected))


def condition_matches(condition, values: dict) -> bool:
    if not isinstance(condition, dict):
        return False
    for key in ("and", "or"):
        if isinstance(condition.get(key), list):
            results = [condition_matches(item, values) for item in condition[key]]
            return all(results) if key == "and" else any(results)
    if "not" in condition:
        return not condition_matches(condition["not"], values)
    field = value_at(values, condition.get("field"))
    operator, expected = condition.get("operator"), condition.get("value")
    if operator == "equals":
        return _same(field, expected)
    if operator == "notEquals":
        return not _same(field, expected)
    if operator in ("in", "notIn"):
        options = expected if isinstance(expected, (list, tuple, set)) else [expected]
        found = any(_same(field, option) for option in options)
        return found if operator == "in" else not found
    if operator == "notEmpty":
        return not is_blank(field)
    if operator in ("empty", "isEmpty"):
        return is_blank(field)
    if operator in ("greaterThan", "lessThan"):
        try:
            left, right = float(field), float(expected)
        except (TypeError, ValueError):
            return False
        return left > right if operator == "greaterThan" else left < right
    if operator in ("contains", "notContains"):
        if isinstance(field, str) and isinstance(expected, str) or isinstance(field, (list, tuple, set)):
            found = expected in field
        else:
            found = False
        return found if operator == "contains" else not found
    return False


def _rules(options) -> list:
    if not isinstance(options, dict):
        return []
    actions = options.get("actions")
    if isinstance(actions, list) and actions:
        return [a for a in actions if isinstance(a, dict) and a.get("action")]
    if options.get("action") and options.get("condition"):
        return [{"action": options["action"], "condition": options["condition"]}]
    return []


def widget_state(widget: dict, values: dict) -> tuple[bool, bool]:
    """(visible, required), as the staff UI evaluates the widget."""
    base = widget.get("widget-required") is True
    visible, required = True, base
    for rule in _rules(widget.get("widget-data-options")):
        match = condition_matches(rule.get("condition"), values)
        if rule["action"] == "show":
            visible = match
        elif rule["action"] == "hide":
            visible = not match
        elif rule["action"] == "require":
            required = base or match
    return visible, required


# ------------------------------------------------------------------ widgets --
def widgets_of(node):
    if isinstance(node, dict):
        if "widget" in node and "widget-id" in node:
            yield node
        for value in node.values():
            yield from widgets_of(value)
    elif isinstance(node, list):
        for item in node:
            yield from widgets_of(item)


def value_path(widget: dict):
    path = widget.get("widget-data-path")
    if isinstance(path, dict):
        path = path.get("value")
    return path if isinstance(path, str) else None


def field_of(widget: dict):
    """The record field a widget writes: the last part of its data path, or the
    column key of a table column."""
    if widget.get("column-key"):
        return str(widget["column-key"])
    path = value_path(widget)
    return path.split(".")[-1] if path else None


def table_of(schema: dict):
    """The table widget of a list section."""
    stack = [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get("widget") in TABLES and "widget-data-columns" in node:
                return node
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return None


def with_stored_as(record: dict) -> dict:
    """The record with the typed fields filled from the columns they are stored in."""
    found = dict(record)
    for field, columns in STORED_AS.items():
        if field not in found:
            found[field] = next((record[c] for c in columns if not is_blank(record.get(c))), None)
    return found


class _Words:
    """Section titles and field labels as the form shows them."""

    def __init__(self, messages):
        self.messages = messages or {}

    def _known(self, key):
        found = self.messages.get(key) if key else None
        return found if isinstance(found, str) and found else None

    def title(self, schema: dict, fallback: str = "") -> str:
        key = (schema or {}).get("section-title") or fallback
        return self._known(key) or humanize(key)

    def label(self, widget: dict, field: str) -> str:
        for candidate in (widget.get("widget-label"), field):
            if self._known(candidate):
                return self._known(candidate)
        return humanize(widget.get("widget-label") or field)

    def text(self, key: str, **params) -> str:
        template = self._known(key) or MESSAGES[key]
        try:
            return template.format(**params)
        except (KeyError, IndexError, ValueError):
            return MESSAGES[key].format(**params)


def _file_labels(widget: dict, field: str) -> set:
    return {widget.get("widget-label"), field, widget.get("widget-id")}


def missing_in_record(widgets, record: dict, values: dict, words: _Words, saved_files=None):
    """(fields to fill in, files to add) for one record.

    `values` is what conditions are evaluated against: register id -> record
    for a single-record section, the row itself for a table row.
    """
    fill: list = []
    files: list = []
    for widget in widgets:
        if widget.get("widget") in SKIPPED or widget.get("widget-readonly"):
            continue
        field = field_of(widget)
        if not field:
            continue
        visible, required = widget_state(widget, values)
        if not (visible and required):
            continue
        label = words.label(widget, field)
        if widget.get("widget") == "file":
            title = (widget.get("widget-data-options") or {}).get("title")
            if title:
                label = words.label({"widget-label": title}, field)
            if not (_file_labels(widget, field) & (saved_files or set())) and label not in files:
                files.append(label)
        elif is_blank(record.get(field)) and label not in fill:
            fill.append(label)
    return fill, files


def section_problems(schema, is_list, records, values, messages=None, saved_files=None, fallback_title=""):
    """One sentence per thing a section still needs, in the section's words.

    `records` are the section's records as they will be stored (the surviving
    rows); `values` maps register ids to records, for conditions that look at
    another section of the same form.
    """
    words = _Words(messages)
    title = words.title(schema, fallback_title)
    problems: list = []
    if is_list:
        table = table_of(schema)
        if table is None:
            return problems
        if table.get("widget-required") is True and not records:
            return [words.text("required_add_row", section=title)]
        columns = [c for c in table.get("widget-data-columns") or [] if isinstance(c, dict)]
        for number, row in enumerate(records, start=1):
            fill, _ = missing_in_record(columns, row, {**values, **row}, words)
            if fill:
                problems.append(words.text("required_fill_in_row", section=title, row=number, fields=", ".join(fill)))
        return problems
    record = with_stored_as(records[0]) if records else {}
    fill, files = missing_in_record(list(widgets_of(schema)), record, values, words, saved_files)
    if fill:
        problems.append(words.text("required_fill_in", section=title, fields=", ".join(fill)))
    if files:
        problems.append(words.text("required_add_file", section=title, fields=", ".join(files)))
    return problems
