"""ODK Sowing and Harvest rows carry the Land ID of each Cluster status and
"Is planning record created?" with its land fields, as the web form stores them."""
import asyncio
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
CLUSTER = {'is_cluster_land_recorded': 'no', 'cluster_land_info_id': 'C1', 'cluster_region_id': 'ET04',
           'cluster_zone_id': 'ET0411', 'cluster_woreda_id': 'ET041106', 'cluster_kebele_id': 'ET04110601',
           'cluster_sub_kebele': 'Goro', 'cluster_gps': {'type': 'Point', 'coordinates': [40.2, 7.3]}}
INDEPENDENT = {'is_land_recorded': 'yes', 'land_info_id': 'L1'}


def render(**data):
    template = (ROOT / 'templates' / 'odk_to_crop_intake.j2').read_text(encoding='utf-8')
    return json.loads(Environment().from_string(template).render(expanded={**IDENTITY, **data}))


def sowing(row):
    return render(sowing_details=[row])['cs_sowing_details'][0]


def harvest(row):
    return render(harvesting=[row])['cs_harvest_details'][0]


def test_sowing_with_both_statuses_carries_each_land_id_and_its_answers():
    row = sowing({'cluster_status_ids': 'clustered independent',
                  'clustered_details': {**CLUSTER, 'cluster_name': 'FPC'},
                  'independant_details': {**INDEPENDENT, 'crop_name_id': 'CROP_TEFF', 'sowing_date_gc': '2026-07-01'}})
    assert (row['land_id'], row['cluster_land_id']) == ('L1', 'C1')
    assert row['is_land_recorded'] is True and row['is_cluster_land_recorded'] is False
    assert [row[k] for k in ('cluster_region', 'cluster_zone', 'cluster_woreda', 'cluster_kebele', 'cluster_sub_kebele',
                             'cluster_latitude', 'cluster_longitude')] == [
        'ET04', 'ET0411', 'ET041106', 'ET04110601', 'Goro', '7.3', '40.2']
    assert row['region'] == '' and row['plot_category'] == ''  # Yes: the land is in Planning


def test_harvest_independent_no_carries_the_land_details():
    row = harvest({'cluster_status_ids': 'independent', 'independant_details': {
        'is_land_recorded': 'no', 'land_info_id': 'L2', 'is_plot_registered': 'no', 'land_category': 'ANNUAL_CROP',
        'ownership_type': 'OWNER', 'land_area': 2, 'soil_fertility': 'SF_HIGH', 'region_name_id': 'ET04',
        'zone_name_id': 'ET0411', 'woreda_name_id': 'ET041106', 'kebele_id': 'ET04110601',
        'planning_gps': '7.27 40.21 0 3', 'actual_crop_name': 'CROP_TEFF', 'independent_harvest_date': '2026-11-01'}})
    assert (row['land_id'], row['cluster_land_id']) == ('L2', '')
    assert row['is_land_recorded'] is False and row['is_plot_not_registered'] is True
    assert [row[k] for k in ('plot_category', 'ownership_type', 'land_area', 'soil_fertility_type', 'region', 'zone',
                             'woreda', 'kebele', 'latitude', 'longitude')] == [
        'ANNUAL_CROP', 'OWNER', 2.0, 'SF_HIGH', 'ET04', 'ET0411', 'ET041106', 'ET04110601', '7.27', '40.21']


@pytest.mark.parametrize('status, land, cluster_land', [
    ('clustered', '', 'OLD'), ('independent', 'OLD', ''), ('clustered independent', 'OLD', 'OLD'), ('', 'OLD', '')])
def test_an_older_form_land_id_goes_to_the_side_ticked(status, land, cluster_land):
    for render_row in (sowing, harvest):
        row = render_row({'land_info_id': 'OLD', 'cluster_status_ids': status})
        assert (row['land_id'], row['cluster_land_id']) == (land, cluster_land)
        assert row['is_land_recorded'] is None and row['is_cluster_land_recorded'] is None


def test_the_rows_pass_the_land_id_rules_on_save():
    pytest.importorskip('openg2p_registry_core')
    from openg2p_registry_cropsown_extension.register_domain.services.g2p_register_domain_service_sowing import (
        G2PRegisterDomainServiceSowing,
    )
    row = sowing({'land_info_id': 'OLD', 'cluster_status_ids': 'clustered',
                  'clustered_details': {'cluster_name': 'FPC'}})
    asyncio.run(G2PRegisterDomainServiceSowing().validate_domain_attributes([row], None))
