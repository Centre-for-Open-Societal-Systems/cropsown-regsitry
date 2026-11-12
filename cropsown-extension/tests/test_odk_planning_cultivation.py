"""ODK Planning and Cultivation submissions carry the land and crop locations and the
"Is planning record created?" answer, as the web form stores them."""
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
            'production_season_info': {'crop_year': '2026', 'production_season': 'SEASON_MEHER'}}
LAND = ('plot_category', 'ownership_type', 'soil_fertility_type', 'region', 'zone', 'woreda', 'kebele',
        'latitude', 'longitude')


def render(**data):
    template = (ROOT / 'templates' / 'odk_to_crop_intake.j2').read_text(encoding='utf-8')
    return json.loads(Environment().from_string(template).render(expanded={**IDENTITY, **data}))


def test_planning_rows_carry_the_land_and_crop_points():
    row = render(planning=[{'land_info_id': 'L1', 'crop_name_id': 'CROP_TEFF',
                            'planning_gps': {'type': 'Point', 'coordinates': [40.21, 7.27, 1800]},
                            'crop_gps': '7.3 40.3 1800 5'}])['cs_planning_details'][0]
    assert (row['latitude'], row['longitude']) == ('7.27', '40.21')  # GeoJSON is longitude first
    assert (row['crop_latitude'], row['crop_longitude']) == ('7.3', '40.3')  # text is latitude first


def test_planning_without_points_leaves_them_empty():
    row = render(planning=[{'land_info_id': 'L1', 'crop_name_id': 'CROP_TEFF'}])['cs_planning_details'][0]
    assert [row[k] for k in ('latitude', 'longitude', 'crop_latitude', 'crop_longitude')] == ['', '', '', '']


def test_cultivation_yes_keeps_only_the_land_id_and_area():
    row = render(cult_land_prep=[{'is_planning_record_created': 'yes', 'land_info_id': 'L1', 'land_area': 2,
                                  'crop_name_id': 'CROP_TEFF',
                                  'crop_gps': {'type': 'Point', 'coordinates': [40.5, 7.5]}}])['cs_cultivation_details'][0]
    assert row['is_planning_record_created'] is True and row['is_plot_not_registered'] is None
    assert (row['land_id'], row['land_area']) == ('L1', 2.0)
    assert all(row[k] == '' for k in LAND)
    assert (row['crop_latitude'], row['crop_longitude']) == ('7.5', '40.5')


def test_cultivation_no_carries_the_land_details():
    row = render(cult_land_prep=[{
        'is_planning_record_created': 'no', 'is_plot_registered': 'yes', 'land_info_id': 'L2',
        'land_category': 'ANNUAL_CROP', 'ownership_type': 'OWNER', 'soil_fertility': 'SF_HIGH',
        'region_name_id': 'ET04', 'zone_name_id': 'ET0411', 'woreda_name_id': 'ET041106',
        'kebele_id': 'ET04110601', 'planning_gps': '7.27 40.21 0 3', 'crop_name_id': 'CROP_TEFF'}])['cs_cultivation_details'][0]
    assert row['is_planning_record_created'] is False and row['is_plot_not_registered'] is False
    assert [row[k] for k in LAND] == ['ANNUAL_CROP', 'OWNER', 'SF_HIGH', 'ET04', 'ET0411', 'ET041106',
                                      'ET04110601', '7.27', '40.21']


def test_cultivation_from_an_older_form_is_read_as_before():
    row = render(cult_land_prep=[{'land_info_id': 'L3', 'crop_name_id': 'CROP_TEFF'}])['cs_cultivation_details'][0]
    assert row['is_planning_record_created'] is None and row['is_plot_not_registered'] is False
    assert all(row[k] == '' for k in LAND)
