"""ODK areas are stored as entered: a blank Planned crop area, Actual crop area, Area sown or
Area harvested stays blank (no 1.0 placeholder) and 0 stays 0. A future Sowing date is kept."""
import importlib
import json
import os
from pathlib import Path

import pytest
from jinja2 import Environment

PACKAGE = os.environ.get('REGISTRY_EXTENSION_MODULE', 'openg2p_registry_cropsown_extension')
ROOT = Path(importlib.import_module(PACKAGE).__file__).parent

pytestmark = pytest.mark.skipif('cropsown' not in PACKAGE, reason='crop transform')

IDENTITY = {'farmer_identity': {'farmer_id': 'FR-000000000001', 'fayda_id': '001234567890'},
            'production_season_info': {'crop_year': '2026', 'production_season': 'SEASON_MEHER'},
            '__system': {'submissionDate': '2026-11-11T08:00:00Z'}}
INDEPENDENT = {'is_land_recorded': 'no', 'land_info_id': 'L1', 'land_area': 3}


def render(**data):
    template = (ROOT / 'templates' / 'odk_to_crop_intake.j2').read_text(encoding='utf-8')
    return json.loads(Environment().from_string(template).render(expanded={**IDENTITY, **data}))


def planned(value):
    inputs = {} if value is None else {'crop_planned_area': value}
    row = {'land_info_id': 'L1', 'crop_name_id': 'CROP_TEFF', 'crop_planned_inputs': inputs}
    return render(planning=[row])['cs_planning_details'][0]['planned_area']


def actual(value):
    inputs = {} if value is None else {'actual_crop_area': value}
    row = {'land_info_id': 'L1', 'crop_name_id': 'CROP_TEFF', 'crop_actual_inputs': inputs}
    return render(cult_land_prep=[row])['cs_cultivation_details'][0]['actual_crop_area']


def sowing(**details):
    row = {'cluster_status_ids': 'independent',
           'independant_details': {**INDEPENDENT, 'crop_name_id': 'CROP_TEFF', **details}}
    return render(sowing_details=[row])['cs_sowing_details'][0]


def harvested(**details):
    row = {'cluster_status_ids': 'independent', 'independant_details': {**INDEPENDENT, **details}}
    return render(harvesting=[row])['cs_harvest_details'][0]['area_harvested']


@pytest.mark.parametrize('read', [planned, actual])
def test_planning_and_cultivation_areas_are_stored_as_entered(read):
    assert read(None) is None
    assert read('') is None
    assert read(0) == 0.0
    assert read('2.5') == 2.5


def test_area_sown_is_stored_as_entered():
    assert sowing()['area_sown'] is None
    assert sowing(independent_area_sown='')['area_sown'] is None
    assert sowing(independent_area_sown=0)['area_sown'] == 0.0
    assert sowing(independent_area_sown='1.5')['area_sown'] == 1.5


def test_area_harvested_is_stored_as_entered():
    assert harvested() is None
    assert harvested(independent_area_harvested='') is None
    assert harvested(independent_area_harvested=0) == 0.0
    assert harvested(independent_area_harvested='2') == 2.0


def test_a_future_sowing_date_is_kept():
    assert sowing(sowing_date_gc='2027-03-01')['sowing_date'] == '2027-03-01'
    assert sowing(sowing_date_gc='2026-07-01')['sowing_date'] == '2026-07-01'


def test_a_blank_sowing_date_still_falls_back_to_the_submission_date():
    assert sowing()['sowing_date'] == '2026-11-11'


def test_no_placeholder_area_is_left_in_the_mapping():
    template = (ROOT / 'templates' / 'odk_to_crop_intake.j2').read_text(encoding='utf-8')
    assert 'or 1.0' not in template and 'else 1.0' not in template and '= 1.0 %}' not in template
