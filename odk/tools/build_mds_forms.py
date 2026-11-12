"""Build the four Crop Sown ODK forms whose season, crop and geography choices come from Master Data.

    python odk/tools/build_mds_forms.py --pack ../openg2p-data/packs/ETH-OAN

The forms are the Planning, Cultivation, Sowing and Harvesting forms published on
ODK Central project 2 (form ids crop_sown_registry_plan, _prep, _sown, _harvest;
the submission header prefix of each id selects the registry intake form, so the ids
never change). Their published workbooks are kept unchanged in odk/source/. This
builder rewrites them:

1. Identity. The first group of every form is "farmer_identity" and holds exactly two
   required questions: Farmer ID (FR- and 12 digits) and Fayda ID (a 16 digit FAN or a
   12 digit FIN, spaces allowed). The registry transform
   (odk_to_crop_intake.j2) reads the fields farmer_id and fayda_id from that group and
   tells a FIN from a FAN by length, so the typed Fayda ID (fayda_id_entered) is copied
   into a hidden calculate named fayda_id with the spaces removed. Crop year and
   production season move to the group production_season_info, which the transform also
   reads. The old fyda_id / fayda_fan_id, is_farmer_registered and farmer_name questions
   are dropped.
2. Master Data lists. ODK Collect cannot read Master Data while a form is filled in, so
   the form carries each list at build time, exactly as Master Data serves it: the choice
   name is the value code (what the registry stores) and the label its display.
     - production season and season       -> CROP_SEASON          (inline choices)
     - agro ecological zone               -> AGRO_ECOLOGICAL_ZONE (inline choices)
     - the land, seed, fertilizer, water, machinery, land preparation, growth stage,
       severity, pest and weed questions  -> their Master Data lists (inline choices,
                                             see INLINE_LISTS), so ODK offers exactly the
                                             options and codes of the web intake form
     - crop_name.csv                      -> CROP_COMMODITY, with its CROP_CATEGORY
     - seed_variety.csv                   -> SEED_VARIETY (the one "Variety" question)
     - region/zone/woreda/kebele.csv      -> the geography, named by P-code, each row
                                             carrying its parent's P-code
   Every list is read from --pack. The forms carry one variety question, "Variety",
   on SEED_VARIETY; the source workbooks' separate "Crop Variety" question (a list
   the pack does not carry) is dropped. The geography is read from --geography
   (levels.json and values.json in the pack's format; default: the pack's), which must be
   the geography of the environment the form is published to. Each place is labelled
   as Master Data names it (level_value_mnemonic, e.g. "Agarfa (ET041104)" where two
   places share a name).
3. Questions. "Plot not registered" (a tick box) becomes the Yes/No question "Is plot
   registered?" (is_plot_registered), as on the web form; "Security Level" is labelled
   "Severity level"; Disease Type reads CROP_DISEASE, as on the web form;
   Pest name is typed text and Method of control (pest) reads PEST_CONTROL_ACTION; dates use the
   Ethiopian calendar (the stored value stays Gregorian); the cluster Land ID questions
   carry no rule tying them to the planning or cultivation Land ID, as on the web form.
4. Land and crop locations, as on the web form (match_web_form). Planning drops the
   Address group (the farmer's address comes from the Farmer Registry) and asks "Land
   location" after Kebele and "Crop location" after Expected Yield, as GPS points.
   Cultivation asks "Is planning record created?" first in the row; No adds the
   Planning row's land questions (Is plot registered?, Plot Category, Ownership Type,
   Soil Fertility, Region to Kebele, Land location); every row asks "Crop location"
   after Actual Crop Area. Sowing's Type of Infestation offers Pest, Weed and Disease, as
   Master Data does: Nutrient Deficiency and Climate Shock, and their groups, are dropped.
   Sowing and Harvest ask the Land ID inside each Cluster status group, after "Is planning
   record created?"; No asks the land (Independent) or the cluster location (Clustered).
5. Everything else is left as published (see NOT_MASTER_DATA for why), except the two
   yes/no lists, which are not Master Data lists either.

The form version is the build date (--version, default VERSION below).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "odk/source"
FORMS = REPO / "odk/forms"
MEDIA = REPO / "odk/media/mds"
VERSION = "2026.11.12.1"
FORM_IDS = ("crop_sown_registry_plan", "crop_sown_registry_prep", "crop_sown_registry_sown", "crop_sown_registry_harvest")
LEVELS = ("region", "zone", "woreda", "kebele")

# XLSForm choice list name -> Master Data attribute
INLINE_LISTS = {
    "crop_season": "CROP_SEASON",
    "agro_ecological_zone": "AGRO_ECOLOGICAL_ZONE",
    "plot_cat": "PLOT_CATEGORY",
    "ownership": "OWNERSHIP_TYPE",
    "soil_fertility": "SOIL_FERTILITY",
    "cropping_sys": "CROPPING_SYSTEM",
    "seed_class": "SEED_TYPE",
    "seed_source": "SEED_SOURCE",
    "fertilizer_type": "FERTILIZER_TYPE",
    "water_source": "WATER_SOURCE",
    "method": "WATER_SOURCE_METHOD",
    "frequency": "WATER_SOURCE_FREQUENCY",
    "cult_method": "MACHINERY",
    "land_prep_method": "LAND_PREP_METHOD",
    "growth_stage": "CROP_GROWTH_STAGE",
    "security_level": "INFESTATION_SEVERITY",
    "pest_type": "PEST",
    "weed_type": "WEED",
    "disease_type": "CROP_DISEASE",
    "pest_control_action": "PEST_CONTROL_ACTION",
}
# Source choice lists replaced by an inline Master Data list
REPLACES = {"production_season": "crop_season", "season": "crop_season", "ecological_zone": "agro_ecological_zone"}
# External CSV (media file name in the form) -> (file written, Master Data attribute)
FILE_LISTS = {"crop_name.csv": "CROP_COMMODITY", "seed_variety.csv": "SEED_VARIETY"}
GEO_FILES = {"region.csv": "region", "zone.csv": "zone", "woreda.csv": "woreda", "kebele1.csv": "kebele"}
# Source questions dropped from the forms: the registry has one variety field (seed_variety)
DROPPED_QUESTIONS = {"crop_variety_id"}
# "Plot not registered" tick box -> the web form's Yes/No question; the transform reads
# is_plot_registered (yes = registered) and stores is_plot_not_registered.
PLOT_QUESTION = {"is_plot_not_registered": {"type": "select_one yes_no", "name": "is_plot_registered",
                                            "label": "Is plot registered?"}}
PLOT_CHOICES = [{"list_name": "yes_no", "name": "yes", "label": "Yes"},
                {"list_name": "yes_no", "name": "no", "label": "No"}]
# Labels as the web form shows them.
LABELS = {"security_level": "Severity level", "cluster_status_ids": "Cluster / non cluster status",
          "cluster_status_id": "Cluster / non cluster status"}
# Questions that read a Master Data list on the web form but not in the published form:
# Method of control (pest) (the shared weed/disease method list). Pest name stays typed
# text, as on the web form (zz-oan/97j_pest_name_text.sql).
QUESTION_TYPES = {"pest_pesticide_method": "select_one pest_control_action"}
# The web form does not check these Land IDs against planning / cultivation; neither does ODK.
NO_RULE = {"cluster_land_info_id"}
# Dates are entered on the Ethiopian calendar, as on the web form; the value stays the
# Gregorian date the registry stores.
DATE_APPEARANCE = "ethiopian"
GREGORIAN_SUFFIX = re.compile(r"\s*\(Gregorian calendar\)\s*$")
# Label of the variety question (the registry labels the field "Variety")
VARIETY_LABEL = "Variety"
YES_NO = {"only_yes", "yes_only", "yes_no"}

# Lists left as published, with the reason they are not Master Data lists. A list that is
# neither here, nor yes/no, nor a Master Data list above makes the build fail.
NOT_MASTER_DATA = {
    "cluster_status": "the transform and the form's own rules compare the answer to 'clustered' and 'independent'",
    "fert_type": "organic or inorganic: the transform reads the name as given",
    "sowing_status": "no Master Data list",
    "infestation_type": "the form's relevance rules compare the answer to pest, weed and disease; Master Data has only these three, so nutrient_deficiency and climate_shock are dropped (DROPPED_CHOICES)",
    "method_control": "no Master Data list",
    "pesticides_type": "no Master Data list",
    "weedicides_type": "no Master Data list",
    "fungicide_type": "no Master Data list",
    "nutrient_type": "no Master Data list",
    "method_of_control": "no Master Data list",
    "m_control": "no Master Data list",
    "shock_type": "Master Data's shock type list is for households",
    "recovery_type": "no Master Data list",
    "crop_maturity": "no Master Data list",
}

IDENTITY_ROWS = [
    {"type": "begin_group", "name": "farmer_identity", "label": "Farmer Identity", "appearance": "field-list"},
    {"type": "text", "name": "farmer_id", "label": "Farmer ID",
     "hint": "FR- followed by 12 digits, for example FR-123456789012", "required": "yes",
     "required_message": "Enter the Farmer ID.",
     "constraint": "regex(., '^FR-[0-9]{12}$')",
     "constraint_message": "The Farmer ID must be FR- followed by 12 digits, for example FR-123456789012."},
    {"type": "text", "name": "fayda_id_entered", "label": "Fayda ID",
     "hint": "The 16 digit FAN or the 12 digit FIN. Spaces are allowed.", "required": "yes",
     "required_message": "Enter the Fayda ID.",
     "constraint": "regex(translate(., ' ', ''), '^([0-9]{12}|[0-9]{16})$')",
     "constraint_message": "The Fayda ID must be a 16 digit FAN or a 12 digit FIN. Spaces are allowed."},
    {"type": "calculate", "name": "fayda_id", "calculation": "translate(${fayda_id_entered}, ' ', '')"},
    {"type": "end_group"},
]
KEEP_FROM_OLD_IDENTITY = ("crop_year", "production_season")

# Planning and Cultivation follow the web form's land and crop locations
# (zz-oan/97c_planning_map_location.sql, 97e_address_section.sql, 97f_cultivation_land_details.sql).
# A GPS point is ODK's map: the transform reads its latitude and longitude.
LAND_GPS = {"type": "geopoint", "name": "planning_gps", "label": "Land location", "appearance": "placement-map",
            "hint": "Capture the location of the land, or pick it on the map."}
CROP_GPS = {"type": "geopoint", "name": "crop_gps", "label": "Crop location", "appearance": "placement-map",
            "hint": "Capture the location of the crop, or pick it on the map."}
# The farmer's address comes from the Farmer Registry, so Planning no longer asks for it.
DROPPED_GROUPS = {"crop_sown_registry_plan": {"address"},
                  # Sowing infestations: Pest, Weed and Disease only, as Master Data's INFESTATION_TYPE
                  "crop_sown_registry_sown": {"nutrient_deficiency", "climate_shock"}}
DROPPED_CHOICES = {"crop_sown_registry_sown": {"infestation_type": {"nutrient_deficiency", "climate_shock"}}}
# Cultivation: "Is planning record created?" first in the row. No asks the land details,
# copied from the Planning form's row; Yes (or no answer) asks only Land ID and land area.
PLANNING_QUESTION = {"type": "select_one yes_no", "name": "is_planning_record_created",
                     "label": "Is planning record created?"}
WHEN_NO = "${is_planning_record_created} = 'no'"
AFTER_LAND_ID = ("land_category", "ownership_type")
AFTER_LAND_AREA = ("soil_fertility", "region_name_id", "zone_name_id", "woreda_name_id", "kebele_id")
# Sowing and Harvest (zz-oan/97g_sowing_harvest_land_rows.sql): each Cluster status group
# starts with "Is planning record created?" and its own Land ID; No asks the land (the
# Planning row's questions) or the cluster location (the Planning cluster's questions).
LAND_ROW_FORMS = ("crop_sown_registry_sown", "crop_sown_registry_harvest")
LAND_RECORDED = {"type": "select_one yes_no", "name": "is_land_recorded", "label": "Is planning record created?"}
CLUSTER_LAND_RECORDED = {"type": "select_one yes_no", "name": "is_cluster_land_recorded",
                         "label": "Is planning record created?"}
CLUSTER_LAND_ID = {"type": "text", "name": "cluster_land_info_id", "label": "Land ID (cluster)", "required": "yes",
                   "required_message": "Enter the Land ID (cluster)."}
LAND_WHEN_NO = "${is_land_recorded} = 'no'"
CLUSTER_WHEN_NO = "${is_cluster_land_recorded} = 'no'"
INDEPENDENT_LAND = ("is_plot_registered", "land_category", "ownership_type", "land_area", "soil_fertility",
                    "region_name_id", "zone_name_id", "woreda_name_id", "kebele_id")
CLUSTER_LOCATION = ("cluster_region_id", "cluster_zone_id", "cluster_woreda_id", "cluster_kebele_id")
CLUSTER_SUB_KEBELE = {"type": "text", "name": "cluster_sub_kebele", "label": "Sub-Kebele"}
# The infestation Land ID must be one of the Sowing rows' Land IDs, either side.
INFESTATION_LAND_RULE = "selected(join(' ', ${land_info_id}), .) or selected(join(' ', ${cluster_land_info_id}), .)"
CLUSTER_GPS = {"type": "geopoint", "name": "cluster_gps", "label": "Cluster location", "appearance": "placement-map",
               "hint": "Capture the location of the cluster land, or pick it on the map."}


def read_lists(*folders: Path) -> dict[str, dict]:
    """Every Master Data list found under the folders, by attribute id."""
    lists = {}
    for folder in folders:
        for path in sorted(folder.rglob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "attribute_id" in data and "values" in data:
                lists[data["attribute_id"]] = data
    return lists


def ordered(values: list[dict]) -> list[dict]:
    return sorted(values, key=lambda v: (v.get("sort_order") or 0, v["value_code"]))


def read_geography(folder: Path) -> dict[str, list[dict]]:
    levels = {level["level_id"]: level["level_mnemonic"] for level in json.loads((folder / "levels.json").read_text(encoding="utf-8"))}
    units: dict[str, list[dict]] = {level: [] for level in LEVELS}
    for value in json.loads((folder / "values.json").read_text(encoding="utf-8")):
        level = levels[value["level_id"]]
        if level in units:
            units[level].append(value)
    return units


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def write_media(lists: dict[str, dict], units: dict[str, list[dict]], media: Path) -> dict[str, int]:
    """The external lists, one CSV each; choice names are Master Data codes."""
    counts = {}
    categories = {v["value_code"]: v["value_display"] for v in lists["CROP_CATEGORY"]["values"]}
    crops = []
    for value in ordered(lists["CROP_COMMODITY"]["values"]):
        category = (value.get("attributes") or {}).get("category", "")
        if category and category not in categories:
            raise SystemExit(f"{value['value_code']}: category {category} is not a CROP_CATEGORY code")
        crops.append([value["value_code"], value["value_display"], category, categories.get(category, "")])
    write_csv(media / "crop_name.csv", ["name", "label", "category", "category_label"], crops)
    counts["crop_name.csv"] = len(crops)
    for file, attribute in (("seed_variety.csv", "SEED_VARIETY"),):
        rows = [[v["value_code"], v["value_display"]] for v in ordered(lists[attribute]["values"])]
        write_csv(media / file, ["name", "label"], rows)
        counts[file] = len(rows)
    for level in LEVELS:
        rows = [[u["level_value_id"], u.get("level_value_mnemonic") or u["display_name"], u["level_value_id"], (u.get("parent_level_value_id") or "") if level != "region" else ""]
                for u in sorted(units[level], key=lambda u: u["level_value_id"])]
        write_csv(media / f"{level}.csv", ["name", "label", "code", "parent"], rows)
        counts[f"{level}.csv"] = len(rows)
    return counts


def sheet_rows(sheet) -> tuple[list[str], list[dict]]:
    header = [c.value for c in sheet[1]]
    columns = [h for h in header if h]
    rows = []
    for values in sheet.iter_rows(min_row=2, values_only=True):
        row = {h: v for h, v in zip(header, values) if h and v not in (None, "")}
        if row:
            rows.append(row)
    return columns, rows


def put_rows(book, title: str, columns: list[str], rows: list[dict]) -> None:
    old = book[title]
    index = book.index(old)
    book.remove(old)
    sheet = book.create_sheet(title, index)
    sheet.append(columns)
    for row in rows:
        sheet.append([row.get(c) for c in columns])


def with_columns(columns: list[str], *extra: str) -> list[str]:
    return columns + [e for e in extra if e not in columns]


def rebuild_identity(survey: list[dict], form_id: str) -> list[dict]:
    """Replace the first group with the two identity questions; keep crop year and season."""
    if survey[0].get("type") != "begin_group":
        raise SystemExit(f"{form_id}: the first row is not the identity group")
    end = next(i for i, row in enumerate(survey) if row.get("type") == "end_group")
    old = survey[1:end]
    kept = [row for row in old if row.get("name") in KEEP_FROM_OLD_IDENTITY]
    if {row["name"] for row in kept} != set(KEEP_FROM_OLD_IDENTITY):
        raise SystemExit(f"{form_id}: the old identity group has no crop year and production season")
    season_group = [{"type": "begin_group", "name": "production_season_info", "label": "Production Season", "appearance": "field-list"},
                    *kept, {"type": "end_group"}]
    return [dict(r) for r in IDENTITY_ROWS] + season_group + survey[end + 1:]


def use_master_data(survey: list[dict], form_id: str) -> set[str]:
    """Point the questions at the Master Data lists. Returns the external files used."""
    files_used = set()
    survey[:] = [row for row in survey if row.get("name") not in DROPPED_QUESTIONS]
    for row in survey:
        kind = row.get("type") or ""
        parts = kind.split()
        if len(parts) == 2 and parts[0] in ("select_one", "select_multiple") and parts[1] in REPLACES:
            parts[1] = REPLACES[parts[1]]
            row["type"] = " ".join(parts)
        if len(parts) == 2 and parts[0] == "select_one_from_file":
            if parts[1] in GEO_FILES:
                level = GEO_FILES[parts[1]]
                parts[1] = f"{level}.csv"
                row["type"] = " ".join(parts)
                if row.get("choice_filter"):
                    row["choice_filter"] = re.sub(r"^\s*(region|zone|woreda)\s*=", "parent=", row["choice_filter"])
            files_used.add(parts[1])
        if row.get("name") == "crop_category_id":
            row["calculation"] = "instance('crop_name')/root/item[name=${crop_name_id}]/category"
    for row in survey:
        if row.get("name") == "seed_variety":
            row["label"] = VARIETY_LABEL
        if row.get("name") in LABELS:
            row["label"] = LABELS[row["name"]]
        if row.get("name") in PLOT_QUESTION:
            row.update(PLOT_QUESTION[row["name"]])
        if row.get("name") in QUESTION_TYPES:
            row["type"] = QUESTION_TYPES[row["name"]]
        if row.get("name") in NO_RULE:
            row.pop("constraint", None)
            row.pop("constraint_message", None)
        if (row.get("type") or "").split(" ")[0] == "date":
            row["appearance"] = DATE_APPEARANCE
            if row.get("label"):
                row["label"] = GREGORIAN_SUFFIX.sub("", row["label"])
    out = []
    for row in survey:
        out.append(row)
        if row.get("name") == "crop_category_id":
            out.append({"type": "calculate", "name": "crop_category_name",
                        "calculation": "instance('crop_name')/root/item[name=${crop_name_id}]/category_label"})
    for row in out:
        if row.get("name") == "note_crop_category":
            row["label"] = "Crop Category: ${crop_category_name}"
    survey[:] = out
    return files_used


def without_groups(survey: list[dict], names: set[str]) -> list[dict]:
    """Drop the named top-level groups, from their begin_group to their end_group."""
    out, depth = [], 0
    for row in survey:
        kind = row.get("type")
        if depth:
            depth += {"begin_group": 1, "begin_repeat": 1, "end_group": -1, "end_repeat": -1}.get(kind, 0)
            continue
        if kind == "begin_group" and row.get("name") in names:
            depth = 1
            continue
        out.append(row)
    return out


def planning_rows(source: Path) -> dict[str, dict]:
    """The Planning form's questions by name, as this builder writes them."""
    _, survey = sheet_rows(openpyxl.load_workbook(source / "crop_sown_registry_plan.xlsx")["survey"])
    survey = rebuild_identity(survey, "crop_sown_registry_plan")
    use_master_data(survey, "crop_sown_registry_plan")
    return {row["name"]: row for row in survey if row.get("name")}


def land_rows(survey: list[dict], form_id: str, source: Path) -> None:
    """Sowing / Harvest: the Land ID of each Cluster status, inside its group."""
    planning = planning_rows(source)
    old = next((row for row in survey if row.get("name") == "land_info_id"), None)
    if old is None:
        raise SystemExit(f"{form_id}: questions not found: land_info_id")
    independent = [dict(LAND_RECORDED), dict(old),
                   *({**planning[n], "relevant": LAND_WHEN_NO} for n in INDEPENDENT_LAND),
                   {**LAND_GPS, "relevant": LAND_WHEN_NO}]
    cluster = [dict(CLUSTER_LAND_RECORDED), dict(CLUSTER_LAND_ID),
               *({**planning[n], "relevant": CLUSTER_WHEN_NO} for n in CLUSTER_LOCATION),
               {**CLUSTER_SUB_KEBELE, "relevant": CLUSTER_WHEN_NO}, {**CLUSTER_GPS, "relevant": CLUSTER_WHEN_NO}]
    out, found = [], set()
    for row in survey:
        if row is old:
            continue  # moved into the Independent group
        if row.get("name") == "cluster_status_ids":
            row["required"] = "yes"  # the Land IDs depend on it
        out.append(row)
        if row.get("type") == "begin_group" and row.get("name") == "independant_details":
            out.extend(independent)
            found.add("independant_details")
        elif row.get("type") == "begin_group" and row.get("name") == "clustered_details":
            out.extend(cluster)
            found.add("clustered_details")
    if found != {"independant_details", "clustered_details"}:
        raise SystemExit(f"{form_id}: Cluster status groups not found")
    for row in out:
        if row.get("name") == "infestation_land_info_id" and row.get("constraint"):
            row["constraint"] = INFESTATION_LAND_RULE
    survey[:] = out


def match_web_form(survey: list[dict], form_id: str, source: Path) -> None:
    """Land and crop locations of Planning and Cultivation, as on the web form."""
    survey[:] = without_groups(survey, DROPPED_GROUPS.get(form_id, set()))
    if form_id in LAND_ROW_FORMS:
        land_rows(survey, form_id, source)
        return
    if form_id == "crop_sown_registry_plan":
        after = {"kebele_id": [LAND_GPS], "crop_expected": [CROP_GPS]}
    elif form_id == "crop_sown_registry_prep":
        planning = planning_rows(source)
        when_no = lambda names: [{**planning[n], "relevant": WHEN_NO} for n in names]
        after = {"land_info_id": when_no(AFTER_LAND_ID),
                 "land_area": when_no(AFTER_LAND_AREA) + [{**LAND_GPS, "relevant": WHEN_NO}],
                 "actual_crop_area": [CROP_GPS]}
        for row in survey:
            if row.get("name") == "is_plot_registered":
                row["relevant"] = WHEN_NO
    else:
        return
    out = []
    for row in survey:
        if form_id == "crop_sown_registry_prep" and row.get("name") == "is_plot_registered":
            out.append(dict(PLANNING_QUESTION))
        out.append(row)
        out.extend(dict(extra) for extra in after.get(row.get("name"), []))
    missing = [name for name in after if not any(row.get("name") == name for row in survey)]
    if missing:
        raise SystemExit(f"{form_id}: questions not found: {', '.join(missing)}")
    survey[:] = out


def used_lists(survey: list[dict]) -> set[str]:
    """Names of the inline choice lists the questions use."""
    used = set()
    for row in survey:
        parts = (row.get("type") or "").split()
        if len(parts) == 2 and parts[0] in ("select_one", "select_multiple"):
            used.add(parts[1])
    return used


def build_choices(rows: list[dict], lists: dict[str, dict], form_id: str, survey: list[dict]) -> list[dict]:
    """Drop the replaced lists, add the Master Data ones, and refuse any other list we cannot account for."""
    used = used_lists(survey)
    unknown = sorted(n for n in used if n not in INLINE_LISTS and n not in YES_NO and n not in NOT_MASTER_DATA)
    if unknown:
        raise SystemExit(f"{form_id}: choice lists neither Master Data nor accounted for: {', '.join(unknown)}")
    kept = [r for r in rows if r.get("list_name") in used and r.get("list_name") not in INLINE_LISTS]
    if "yes_no" in used and not any(r.get("list_name") == "yes_no" for r in kept):
        kept += [dict(r) for r in PLOT_CHOICES]
    for name, attribute in INLINE_LISTS.items():
        if name in used:
            for value in ordered(lists[attribute]["values"]):
                kept.append({"list_name": name, "name": value["value_code"], "label": value["value_display"]})
    return kept


def build_form(form_id: str, lists: dict[str, dict], version: str, source: Path, target: Path) -> dict:
    book = openpyxl.load_workbook(source / f"{form_id}.xlsx")
    s_cols, survey = sheet_rows(book["survey"])
    c_cols, choices = sheet_rows(book["choices"])
    t_cols, settings = sheet_rows(book["settings"])
    survey = rebuild_identity(survey, form_id)
    files = use_master_data(survey, form_id)
    match_web_form(survey, form_id, source)
    # the media files of the questions match_web_form added
    files |= {(row.get("type") or "").split()[1] for row in survey
              if (row.get("type") or "").startswith("select_one_from_file ")}
    choices = build_choices(choices, lists, form_id, survey)
    dropped = DROPPED_CHOICES.get(form_id, {})
    choices = [c for c in choices if c.get("name") not in dropped.get(c.get("list_name"), ())]
    settings[0]["version"] = version
    s_cols = with_columns(s_cols, "required_message", "calculation")
    put_rows(book, "survey", s_cols, survey)
    put_rows(book, "choices", with_columns(c_cols, "list_name", "name", "label"), choices)
    put_rows(book, "settings", with_columns(t_cols, "version"), settings)
    target.mkdir(parents=True, exist_ok=True)
    out = target / f"{form_id}.xlsx"
    book.save(out)
    used = used_lists(survey)
    return {"form_id": form_id, "version": version, "workbook": out.name, "media": sorted(files),
            "master_data_lists": {n: INLINE_LISTS[n] for n in sorted(used & set(INLINE_LISTS))},
            "lists_left_as_published": sorted(used & set(NOT_MASTER_DATA))}


def build(pack: Path, geography: Path | None = None, version: str = VERSION, source: Path = SOURCE,
          target: Path = FORMS, media: Path = MEDIA) -> dict:
    lists = read_lists(pack / "codelists", pack / "domains")
    needed = {"CROP_COMMODITY", "CROP_CATEGORY", "SEED_VARIETY", *INLINE_LISTS.values()}
    missing = sorted(needed - set(lists))
    if missing:
        raise SystemExit(f"not found in the pack: {', '.join(missing)}")
    units = read_geography(geography or pack)
    counts = write_media(lists, units, media)
    forms = [build_form(form_id, lists, version, source, target) for form_id in FORM_IDS]
    report = {"version": version, "media_rows": counts, "forms": forms}
    (target / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--pack", required=True, type=Path, help="the country pack (packs/ETH-OAN of openg2p-data)")
    parser.add_argument("--geography", type=Path, default=None,
                        help="levels.json + values.json of the target environment's geography (default: the pack's)")
    parser.add_argument("--version", default=VERSION)
    args = parser.parse_args()
    print(json.dumps(build(args.pack, args.geography, args.version), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
