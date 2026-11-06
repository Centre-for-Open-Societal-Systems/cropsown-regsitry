"""The ODK forms offer the Master Data lists themselves (choice name = value code), so the
transform passes those codes on unchanged: what an officer picks in ODK is what the web
intake form stores. "Is plot registered?" is the web form's question, asked the same way."""
import importlib
import json
import os
from pathlib import Path

import pytest
from jinja2 import Environment

PACKAGE = os.environ.get('REGISTRY_EXTENSION_MODULE', 'openg2p_registry_cropsown_extension')
ROOT = Path(importlib.import_module(PACKAGE).__file__).parent

pytestmark = pytest.mark.skipif('cropsown' not in PACKAGE, reason='crop transform')


def render(**sections):
    template = (ROOT / 'templates' / 'odk_to_crop_intake.j2').read_text(encoding='utf-8')
    data = {
        'farmer_identity': {'farmer_id': 'FR-000000000001', 'fayda_id': '001234567890'},
        'production_season_info': {'crop_year': '2026', 'production_season': 'SEASON_MEHER'},
        **sections,
    }
    return json.loads(Environment().from_string(template).render(expanded=data))


PLAN = {
    'land_info_id': 'L1', 'land_category': 'ANNUAL_CROP', 'ownership_type': 'OWNER',
    'soil_fertility': 'SF_HIGH', 'water_resource_id': 'WS_RIVER', 'method_id': 'DRIP',
    'frequency': 'DAILY',
    'crop_details': {'cropping_system': 'CSYS_PURE'},
    'seed_planned_inputs': {'seed_planned': 'SEED_IMPROVED', 'seed_source': 'SEEDSRC_MARKET',
                            'seed_planned_fertilizer_type': 'FERT_DAP'},
}


def test_planning_passes_the_master_data_codes_through():
    row = render(planning=[PLAN])['cs_planning_details'][0]
    assert (row['plot_category'], row['ownership_type'], row['soil_fertility_type']) == ('ANNUAL_CROP', 'OWNER', 'SF_HIGH')
    assert (row['cropping_system'], row['seed_class'], row['seed_source']) == ('CSYS_PURE', 'SEED_IMPROVED', 'SEEDSRC_MARKET')
    assert row['planned_fertilizer_type'] == 'FERT_DAP'
    assert (row['water_source'], row['water_source_method'], row['water_source_frequency']) == ('WS_RIVER', 'DRIP', 'DAILY')


def test_cultivation_passes_machinery_seed_and_fertilizer_codes_through():
    row = render(cult_land_prep=[{
        'land_info_id': 'L1', 'cultivated_by': 'OXEN_TILLAGE',
        'crop_actual_inputs': {'land_prep_method_ids': 'MANUAL_DIGGING SOIL_WATER_CONSERVATION_STRUCTURES'},
        'seed_actual_inputs': {'actual_seed_class': 'SEED_LOCAL', 'actual_seed_source': 'SEEDSRC_OWN_SAVED',
                               'actual_fertilizer_type': 'FERT_UREA'},
    }])['cs_cultivation_details'][0]
    assert row['cultivation_type'] == 'OXEN_TILLAGE'
    assert (row['actual_seed_class'], row['actual_seed_source'], row['actual_fertilizer_type']) == ('SEED_LOCAL', 'SEEDSRC_OWN_SAVED', 'FERT_UREA')
    assert row['land_prep_method'] == 'MANUAL_DIGGING,SOIL_WATER_CONSERVATION_STRUCTURES'


@pytest.mark.parametrize('answer, not_registered', [('yes', False), ('no', True)])
def test_is_plot_registered_is_stored_as_is_plot_not_registered(answer, not_registered):
    for section, key in (('planning', 'cs_planning_details'), ('cult_land_prep', 'cs_cultivation_details')):
        row = render(**{section: [{'land_info_id': 'L1', 'is_plot_registered': answer}]})[key][0]
        assert row['is_plot_not_registered'] is not_registered


def test_infestation_sends_severity_growth_stage_pest_weed_and_cluster_codes_and_no_disease():
    inc = render(sowing_details=[{'land_info_id': 'L1'}], infestation_incidents=[{
        'infestation_land_info_id': 'L1', 'cluster_status_id': 'clustered',
        'growth_stage': 'GS_FLOWERING', 'security_level': 'SEV_HIGH',
        # group names as the published Sowing form spells them
        'pest_occurance': {'pest_type': 'APHIDS', 'pest_name': 'ARMYWORM', 'pest_pesticide_method': 'CTRL_CHEMICAL'},
        'weed_occurrence': {'weed_type': 'ANNUAL'},
    }])['cs_infestation_details'][0]
    assert inc['cluster_status'] == 'CLUSTERED'
    assert (inc['growth_stage'], inc['severity_level']) == ('GS_FLOWERING', 'SEV_HIGH')
    assert (inc['pest_type'], inc['weed_type']) == ('APHIDS', 'ANNUAL')
    assert (inc['pest_name'], inc['pesticide_method']) == ('ARMYWORM', 'CTRL_CHEMICAL')
    assert inc['disease_type'] == ''
