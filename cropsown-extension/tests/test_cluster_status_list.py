"""Sowing and Harvest Cluster status reads the CLUSTER_STATUS list (CLUSTERED, INDEPENDENT),
as Infestation does: the form, ODK and file import all store CLUSTERED."""
import importlib
import json
import os
from pathlib import Path

import pytest
from jinja2 import Environment

PACKAGE = os.environ.get('REGISTRY_EXTENSION_MODULE', 'openg2p_registry_cropsown_extension')
ROOT = Path(importlib.import_module(PACKAGE).__file__).parent
ZZ_OAN = ROOT / 'meta_data' / 'zz-oan'
OVERLAY = ZZ_OAN / '97k_cluster_status_list.sql'

pytestmark = pytest.mark.skipif('cropsown' not in PACKAGE, reason='crop overlay')

BASE = {'farmer_id': 'FR-000000000001', 'fayda_id': '0000 1234 5678 9012', 'crop_year': '2026',
        'production_season': 'SEASON_MEHER'}
ODK_IDENTITY = {'farmer_identity': {'farmer_id': 'FR-000000000001', 'fayda_id': '001234567890'},
                'production_season_info': {'crop_year': '2026', 'production_season': 'SEASON_MEHER'},
                '__system': {'submissionDate': '2026-11-11T08:00:00Z'}}
DETAILS = {'sowing': 'cs_sowing_details', 'harvesting': 'cs_harvest_details'}


def file_import(form, row):
    template = (ROOT / 'templates' / f'crop_file_import_{form}_intake.j2').read_text(encoding='utf-8')
    return json.loads(Environment().from_string(template).render(expanded={**BASE, **row}))[DETAILS[form]][0]


def odk(**data):
    template = (ROOT / 'templates' / 'odk_to_crop_intake.j2').read_text(encoding='utf-8')
    return json.loads(Environment().from_string(template).render(expanded={**ODK_IDENTITY, **data}))


def test_the_overlay_moves_sowing_and_harvest_to_the_list_and_its_codes():
    sql = OVERLAY.read_text(encoding='utf-8')
    assert "'cropsown_sowing_details_section_01', 'cropsown_harvest_details_section_01'" in sql
    assert '"attribute_id": "CLUSTER_STATUS"' in sql and '"valueKey": "value_code"' in sql
    assert '{"value": "CLUSTERED"}' in sql  # the CLUSTER rules, on every column of the table
    for table in ('g2p_intake_form_sowings', 'g2p_register_sowings', 'g2p_register_history_sowings',
                  'g2p_intake_form_harvests', 'g2p_register_harvests', 'g2p_register_history_harvests'):
        assert f"'{table}'" in sql  # stored CLUSTER rows rewritten
    assert 'RAISE EXCEPTION' in sql


def test_the_overlay_runs_after_the_land_rows_and_before_the_dates():
    names = sorted(p.name for p in ZZ_OAN.glob('*.sql'))
    assert names.index('97g_sowing_harvest_land_rows.sql') < names.index(OVERLAY.name) < names.index('98_ethiopian_dates.sql')
    assert names[-1] == '98_ethiopian_dates.sql'
    assert len({n.split('_')[0] for n in names}) == len(names)


@pytest.mark.parametrize('form', ('sowing', 'harvesting'))
@pytest.mark.parametrize('given,stored', [
    ('CLUSTERED', ['CLUSTERED']),
    ('clustered;independent', ['CLUSTERED', 'INDEPENDENT']),
    ('CLUSTER', ['CLUSTERED']),  # a file made before the list
    ('Cluster; Independent', ['CLUSTERED', 'INDEPENDENT']),
    ('INDEPENDENT', ['INDEPENDENT']),
])
def test_file_import_stores_the_list_codes(form, given, stored):
    record = file_import(form, {'land_id': 'L1', 'cluster_status': given})
    assert record['cluster_status'] == stored
    if 'CLUSTERED' in stored:
        assert record['cluster_land_id'] == 'L1'  # a Clustered row without cluster_land_id takes its land_id


@pytest.mark.parametrize('answer,stored', [
    ('clustered', ['CLUSTERED']),
    ('clustered independent', ['CLUSTERED', 'INDEPENDENT']),
    ('independent', ['INDEPENDENT']),
])
def test_odk_stores_the_list_codes(answer, stored):
    sowing = odk(sowing_details=[{'cluster_status_ids': answer}])['cs_sowing_details'][0]
    harvest = odk(harvesting=[{'cluster_status_ids': answer}])['cs_harvest_details'][0]
    assert sowing['cluster_status'] == stored
    assert harvest['cluster_status'] == stored
