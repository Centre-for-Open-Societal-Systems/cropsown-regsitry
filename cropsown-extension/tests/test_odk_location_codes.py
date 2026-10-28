"""ODK submissions carry Master Data geo unit ids (P-codes), never the retired
REGION/ZONE/WOREDA/KEBELE code-list values, and the record gets the hierarchy
document the staff portal's geo-hierarchy widget reads."""
import importlib
import json
import os
from pathlib import Path

import pytest
from jinja2 import Environment

PACKAGE = os.environ.get('REGISTRY_EXTENSION_MODULE', 'openg2p_registry_cropsown_extension')
ROOT = Path(importlib.import_module(PACKAGE).__file__).parent

pytestmark = pytest.mark.skipif('cropsown' not in PACKAGE, reason='crop transform')


def render(data):
    template = (ROOT / 'templates' / 'csr_odk_transform.j2').read_text(encoding='utf-8')
    return json.loads(Environment().from_string(template).render(expanded=data))


def submission(address, planning):
    return {
        'farmer_identity': {'farmer_id': 'FR-000000000001', 'fayda_id': '001234567890'},
        'production_season_info': {'crop_year': '2026', 'production_season': 'meher'},
        'address': address,
        'planning': planning,
    }


@pytest.mark.parametrize('address', [
    # the current form: region slug, bare zone / woreda codes, 12-digit CSA kebele code
    {'region_display_id': 'amhara', 'zone_display_id': 'ET0303', 'woreda_display_id': 'ET030303',
     'kebele_id': '030303001001'},
    # an older form still sending the code-list values
    {'region_display_id': 'REGION_ET03', 'zone_display_id': 'ZONE_ET0303',
     'woreda_display_id': 'WOREDA_ET030303', 'kebele_id': 'KEBELE_ET030303001001'},
    # Master Data ids as they are
    {'region_display_id': 'ET03', 'zone_display_id': 'ET0303', 'woreda_display_id': 'ET030303',
     'kebele_id': 'ET030303001001'},
])
def test_record_address_is_master_data_pcodes(address):
    result = render(submission(address, [{}]))
    for section in ('cs_intake_record', 'cs_cropsown_location'):
        row = result[section][0]
        assert (row['region'], row['zone'], row['woreda'], row['kebele']) == (
            'ET03', 'ET0303', 'ET030303', 'ET030303001001')
        assert row['geo_lowest_level_value_id'] == 'ET030303001001'
        hierarchy = row['geo_code_hierarchy_json']
        assert hierarchy['lowest_level_value_id'] == 'ET030303001001'
        assert [(h['level_id'], h['level_mnemonic'], h['level_value_id']) for h in hierarchy['hierarchy']] == [
            ('l1', 'region', 'ET03'), ('l2', 'zone', 'ET0303'),
            ('l3', 'woreda', 'ET030303'), ('l4', 'kebele', 'ET030303001001')]
    plot = result['cs_planning_details'][0]
    assert not any(str(plot[k]).startswith(('REGION_', 'ZONE_', 'WOREDA_', 'KEBELE_'))
                   for k in ('region', 'zone', 'woreda', 'kebele'))


def test_record_without_address_has_no_hierarchy():
    row = render(submission({}, [{}]))['cs_intake_record'][0]
    assert row['region'] == '' and row['kebele'] == ''
    assert row['geo_lowest_level_value_id'] is None
    assert row['geo_code_hierarchy_json'] is None


def test_plot_and_cluster_rows_carry_pcodes():
    planning = [{
        'region_name_id': 'REGION_ET04', 'zone_name_id': 'ZONE_ET0404',
        'woreda_name_id': 'ET040404', 'kebele_id': 'KEBELE_ET040404888003',
        'cluster_information': [{
            'cluster_region_id': 'oromia', 'cluster_zone_id': 'ET0404',
            'cluster_woreda_id': 'WOREDA_ET040404', 'cluster_kebele_id': '40404888003',
        }],
    }]
    result = render(submission({}, planning))
    for section in ('cs_planning_details', 'cs_cluster_details'):
        row = result[section][0]
        assert (row['region'], row['zone'], row['woreda'], row['kebele']) == (
            'ET04', 'ET0404', 'ET040404', 'ET040404888003'), section
