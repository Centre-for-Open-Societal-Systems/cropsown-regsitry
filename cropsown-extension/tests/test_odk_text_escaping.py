"""ODK text answers are escaped and trimmed: a new line, a double quote or a backslash typed on
the phone cannot break the mapped JSON, and spaces or new lines at the start and end are dropped."""
import importlib
import json
import os
import re
from pathlib import Path

import pytest
from jinja2 import Environment

PACKAGE = os.environ.get('REGISTRY_EXTENSION_MODULE', 'openg2p_registry_cropsown_extension')
ROOT = Path(importlib.import_module(PACKAGE).__file__).parent
TEMPLATE = ROOT / 'templates' / 'odk_to_crop_intake.j2'

pytestmark = pytest.mark.skipif('cropsown' not in PACKAGE, reason='crop transform')

IDENTITY = {'farmer_identity': {'farmer_id': 'FR-000000000001', 'fayda_id': '001234567890'},
            'production_season_info': {'crop_year': '2026', 'production_season': 'SEASON_MEHER'},
            '__system': {'submissionDate': '2026-11-11T08:00:00Z'}}


def render(**data):
    return json.loads(Environment().from_string(TEMPLATE.read_text(encoding='utf-8'))
                      .render(expanded={**IDENTITY, **data}))


def cultivation(**row):
    base = {'is_planning_record_created': 'yes', 'land_info_id': 'RN/11/20/112/00001', 'land_area': 2,
            'season_id': 'SEASON_MEHER', 'crop_name_id': 'CROP_TEFF'}
    return render(cult_land_prep=[{**base, **row}])['cs_cultivation_details'][0]


def test_a_new_line_alone_is_stored_as_empty():
    # The submission that failed on dev: Local Name was only a new line.
    assert cultivation(local_name='\n')['local_name'] == ''


@pytest.mark.parametrize('typed, stored', [
    ('Red "local" teff', 'Red "local" teff'),
    ('A\\B', 'A\\B'),
    ('line one\nline two', 'line one\nline two'),
    ('  Teff  ', 'Teff'),
    ("Farmer's teff", "Farmer's teff"),
    ('<b>&</b>', '<b>&</b>'),
])
def test_text_is_escaped_and_trimmed(typed, stored):
    row = cultivation(local_name=typed, scientific_name=typed)
    assert row['local_name'] == stored and row['scientific_name'] == stored


def test_ordinary_values_are_unchanged():
    row = cultivation(local_name='Teff', scientific_name='Eragrostis tef')
    assert (row['land_id'], row['season'], row['local_name'], row['scientific_name']) == (
        'RN/11/20/112/00001', 'SEASON_MEHER', 'Teff', 'Eragrostis tef')


def test_no_text_value_is_written_between_quotes():
    text = TEMPLATE.read_text(encoding='utf-8')
    assert not re.search(r'"[A-Za-z0-9_]+":\s*"\{\{', text)
