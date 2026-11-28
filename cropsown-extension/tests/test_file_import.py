"""The native "Import from file" menu: each intake form has its own file-import data model whose key paths,
pattern and Jinja template take one flat CSV or Excel row; the ODK connector's model stays as it was."""
import importlib
import json
import os
import re
from pathlib import Path

import pytest
from jinja2 import Environment
from jinja2.exceptions import UndefinedError

PACKAGE = os.environ.get('REGISTRY_EXTENSION_MODULE', 'openg2p_registry_cropsown_extension')
ROOT = Path(importlib.import_module(PACKAGE).__file__).parent
REPO = ROOT.parents[2]
META = ROOT / 'meta_data'

pytestmark = pytest.mark.skipif('cropsown' not in PACKAGE, reason='crop import')

REGISTER = '6b06a95a-9a6c-5a33-a33d-c1625716c59c'
FORMS = {
    'planning': {'config': '9ad583e8-b792-48f2-aeab-749156903a1f', 'form': '5bf0068c-ce19-46f8-874c-7147997f793b',
                 'details': 'cs_planning_details', 'season': 'cs_intake_season',
                 'required': {'land_id', 'commodity'}},
    'cultivation': {'config': 'c0755be4-bcea-4d8e-9bdf-f91f41bf1e42', 'form': '6be15ab9-0f1b-4c38-995f-395d52a1b17a',
                    'details': 'cs_cultivation_details', 'season': 'cs_common_intake_season',
                    'required': {'land_id', 'commodity'}},
    'sowing': {'config': 'be46f3fd-b78d-4308-bf86-91f8d665a9ab', 'form': '4a7c2c98-0ffb-41d8-8fea-f22349823675',
               'details': 'cs_sowing_details', 'season': 'cs_common_intake_season',
               'required': {'land_id', 'area_sown', 'commodity', 'sowing_date'}},
    'harvesting': {'config': '8fb0d6f0-8c6d-42df-99c3-6147390d6413', 'form': '52150a37-153d-496d-9cd9-2a3815d6e13b',
                   'details': 'cs_harvest_details', 'season': 'cs_common_intake_season',
                   'required': {'land_id', 'commodity', 'harvest_date', 'qty_harvested'}},
}
IDENTITY = {'farmer_id', 'fayda_id', 'crop_year', 'production_season'}
GEO = {'region', 'zone', 'woreda', 'kebele', 'latitude', 'longitude'}
# Columns a site-configuration overlay adds to a dialog table on top of the base section file:
# 97c_planning_map_location.sql gives Crop planning rows their own Latitude and Longitude.
SOWING_HARVEST_LAND = {'cluster_land_id', 'is_land_recorded', 'is_plot_not_registered', 'plot_category', 'ownership_type', 'land_area', 'soil_fertility_type', 'region', 'zone', 'woreda', 'kebele', 'latitude', 'longitude', 'is_cluster_land_recorded', 'cluster_region', 'cluster_zone', 'cluster_woreda', 'cluster_kebele', 'cluster_sub_kebele', 'cluster_latitude', 'cluster_longitude'}
OVERLAY_COLUMNS = {'cs_planning_details': {'latitude', 'longitude', 'crop_latitude', 'crop_longitude'},
                   # site-configuration/97f_cultivation_land_details.sql
                   'cs_cultivation_details': {'is_planning_record_created', 'plot_category', 'ownership_type',
                                              'soil_fertility_type', 'region', 'zone', 'woreda', 'kebele',
                                              'latitude', 'longitude', 'crop_latitude', 'crop_longitude'},
                   # site-configuration/97g_sowing_harvest_land_rows.sql
                   'cs_sowing_details': SOWING_HARVEST_LAND, 'cs_harvest_details': SOWING_HARVEST_LAND}
CHILD_SECTIONS = {'cs_cluster_details', 'cs_cultivation_cluster_details', 'cs_infestation_details'}
BASE = {'farmer_id': 'FR-000000000001', 'fayda_id': '0000 1234 5678 9012', 'crop_year': '2026',
        'production_season': 'SEASON_MEHER'}


def sql(folder, name):
    return (META / folder / name).read_text(encoding='utf-8')


def render(form, row):
    template = (ROOT / 'templates' / f'crop_file_import_{form}_intake.j2').read_text(encoding='utf-8')
    return json.loads(Environment().from_string(template).render(expanded=row))


def header(form):
    return (REPO / 'import-templates' / f'crop_{form}_intake_import_template.csv').read_text(encoding='utf-8').strip().split(',')


def section_columns():
    """Section mnemonic -> {column key: column definition} of the dialog tables in the register metadata."""
    text = sql('register-metadata', 'g2p_register_sections.sql')
    found = {}

    def collect(node, out):
        if isinstance(node, dict):
            out.extend(node.get('widget-data-columns', []))
            for value in node.values():
                collect(value, out)
        elif isinstance(node, list):
            for value in node:
                collect(value, out)

    pattern = rf"\('{REGISTER}','\w+','[^']+','\w+','([^']+)','[^']*','\w+',\d+,'\w+',\d+,'(\{{.*?\}})',"
    for mnemonic, ui in re.findall(pattern, text):
        columns = []
        collect(json.loads(ui), columns)
        found[mnemonic] = {c['column-key']: c for c in columns}
    return found


def sample(column):
    """A value the column accepts, by the kind of widget the register shows for it."""
    widget = column['widget']
    source = column.get('widget-data-source', {})
    if widget == 'number':
        return '2.5'
    if widget == 'date':
        return '2026-06-01'
    if source.get('type') == 'static':
        values = [str(o['value']) for o in source['options']]
        if values == ['True', 'False']:
            return 'yes'
        return ';'.join(values) if widget == 'multi-select' else values[0]
    if source.get('type') == 'api':
        return 'CODE_A;CODE_B' if widget == 'multi-select' else 'CODE_A'
    return 'Sample text'


# The child table a file row can also fill, up to CHILD_GROUPS rows, from numbered column groups
# (<prefix><n>_<field>, n = 1 to CHILD_GROUPS).
CHILD = {'planning': ('cs_cluster_details', 'cluster_'), 'cultivation': ('cs_cultivation_cluster_details', 'cluster_'),
         'sowing': ('cs_infestation_details', 'infestation_')}
CHILD_GROUPS = 3
# Child fields no file column fills: read-only (the registry fills them), removed from the form by an overlay
# (site-configuration/90_season_window_from_dates.sql, 91_drop_ec_date_copies.sql), or never shown (the nutrient and
# climate infestation fields, whose infestation types are not in Master Data).
CLUSTER_NOT_IMPORTED = {'cluster_id', 'cluster_area_hectare', 'start_month', 'start_day', 'end_month', 'end_day',
                        'establishing_date_ec'}
CHILD_NOT_IMPORTED = {
    'cs_cluster_details': CLUSTER_NOT_IMPORTED, 'cs_cultivation_cluster_details': CLUSTER_NOT_IMPORTED,
    'cs_infestation_details': {'infestation_id', 'observation_date_ec', 'nutrient_type', 'nutrient_name', 'nutrient_control_method',
                               'nutrient_fertilizer_type', 'nutrient_fertilizer_name', 'nutrient_frequency_of_application',
                               'shock_type', 'shock_event_name', 'climate_control_method', 'recovery_input_type',
                               'recovery_input_name', 'climate_frequency_of_application'}}
CHILD_VALUES = {'land_id': 'C1', 'region': 'ET04', 'zone': 'ET0404', 'woreda': 'ET040404', 'kebele': 'ET040404888003',
                'sub_kebele': 'Goro', 'latitude': '9.1', 'longitude': '38.8', 'cluster_status': 'CLUSTERED',
                'estimated_damage_pct': '20'}


def child_columns(form, group=None):
    """The file's numbered child columns (all groups, or one group)."""
    if form not in CHILD:
        return []
    prefix = CHILD[form][1]
    groups = [group] if group else range(1, CHILD_GROUPS + 1)
    return [name for name in header(form) if any(name.startswith(f'{prefix}{n}_') for n in groups)]


def child_field(form, column):
    """cluster_2_land_id -> land_id; cluster_2_name -> cluster_name; infestation_1_type -> infestation_type."""
    section, prefix = CHILD[form]
    rest = column.split('_', 2)[2]
    return rest if rest in section_columns()[section] else prefix + rest


def full_row(form):
    sections = section_columns()
    details = sections[FORMS[form]['details']]
    children = set(child_columns(form))
    row = dict(BASE)
    for name in header(form):
        if name in IDENTITY:
            continue
        if name in children:
            field = child_field(form, name)
            row[name] = CHILD_VALUES.get(field) or sample(sections[CHILD[form][0]][field])
            continue
        row[name] = {'region': 'ET04', 'zone': 'ET0404', 'woreda': 'ET040404', 'kebele': 'ET040404888003',
                     'latitude': '9.01', 'longitude': '38.74', 'crop_latitude': '9.02', 'crop_longitude': '38.75',
                     'is_planning_record_created': 'no', 'plot_category': 'ANNUAL_CROP', 'ownership_type': 'OWNER',
                     'soil_fertility_type': 'SF_HIGH', 'cluster_status': 'CLUSTER;INDEPENDENT', 'cluster_land_id': 'C1',
                     'is_land_recorded': 'no', 'is_cluster_land_recorded': 'no', 'is_plot_not_registered': 'no',
                     'land_area': '2', 'cluster_region': 'ET04', 'cluster_zone': 'ET0404', 'cluster_woreda': 'ET040404',
                     'cluster_kebele': 'ET040404888003', 'cluster_sub_kebele': 'Goro', 'cluster_latitude': '9.1',
                     'cluster_longitude': '38.8'}.get(name) or sample(details.get(name, {}))
    return row


@pytest.mark.parametrize('form', FORMS)
def test_import_configuration_keeps_its_id_and_points_at_the_form_own_data_model(form):
    text = sql('registry-configurations', 'g2p_registry_import_file_configurations.sql')
    spec = FORMS[form]
    model = f'file_import_to_crop_{form}_intake'
    assert re.search(rf"'{spec['config']}',\s*'{REGISTER}',\s*'{spec['form']}',\s*'{model}',\s*'{model}',\s*'Import {form} intakes",
                     text)
    assert 'data_model_id = EXCLUDED.data_model_id' in text and 'import_file_template_mnemonic = EXCLUDED' in text
    assert 'odk_to_crop_intake' not in re.sub(r'^--.*$', '', text, flags=re.MULTILINE)
    assert f"('{spec['form']}','{REGISTER}'" in sql('register-metadata', 'g2p_intake_form_definitions.sql').replace('\n', '')


def test_every_form_has_a_separate_model_because_a_model_holds_one_template_per_register():
    ids = re.findall(r"^\s*'(file_import_to_crop_\w+_intake)',\s*$",
                     sql('registry-configurations', 'g2p_registry_import_file_configurations.sql'), re.MULTILINE)
    assert sorted(set(ids)) == sorted(f'file_import_to_crop_{form}_intake' for form in FORMS)
    models = sql('data-models', 'data_models.sql')
    for form in FORMS:
        model = f'file_import_to_crop_{form}_intake'
        assert f"('{model}','{model.upper()}','$.headers.sender_id=>^Staff Portal$',NULL,TRUE)" in models
    assert 'ON CONFLICT ("data_model_id") DO UPDATE' in models.split('-- FILE_IMPORT_TO_CROP')[1]


@pytest.mark.parametrize('form', FORMS)
def test_key_paths_match_the_import_envelope_and_pattern_reads_the_flat_body(form):
    model = f'file_import_to_crop_{form}_intake'
    paths = sql('registry-inbound-message-rules', 'incoming_model_key_paths.sql')
    assert (f"('{model}_key_path','{model}','$.headers.message_id','$.headers.sender_id',"
            f"'$.headers.signature','$.body','FALSE','')") in paths
    patterns = sql('registry-inbound-message-rules', 'incoming_model_semantic_patterns.sql')
    assert re.search(rf"\('{model}_pattern','{model}','{REGISTER}','{FORMS[form]['form']}',[^\n]*,'\$\.body',"
                     rf"'G2PPassThroughEnricherService'\)", patterns)
    enrichers = importlib.import_module(PACKAGE + '.ingestion_pipeline.enricher_services')
    assert hasattr(enrichers, 'G2PPassThroughEnricherService')
    assert 'ON CONFLICT ("semantic_pattern_id") DO UPDATE' in patterns.split('-- FILE_IMPORT_TO_CROP')[1]


@pytest.mark.parametrize('form', FORMS)
def test_template_row_document_and_file_are_registry_prefixed_and_exist(form):
    model = f'file_import_to_crop_{form}_intake'
    name = f'crop_file_import_{form}_intake.j2'
    templates = sql('registry-inbound-message-rules', 'incoming_templates.sql')
    assert f"('{model}_template','{REGISTER}','{model}','{model}_document','FALSE'" in templates
    documents = sql('register-metadata', 'g2p_registry_documents.sql')
    assert f"('{model}_document','{name}','templates','{name}','seeder'" in documents
    assert (ROOT / 'templates' / name).is_file()


def test_odk_connector_model_and_every_template_name_are_untouched_and_unique():
    paths = sql('registry-inbound-message-rules', 'incoming_model_key_paths.sql')
    assert re.search(r"'odk_to_crop_intake_key_path',\s*'odk_to_crop_intake',\s*'\$\.body\.header\.message_id',\s*"
                     r"'\$\.body\.header\.sender_id',\s*'\$\.body\.header\.signature',\s*'\$\.body\.message'", paths)
    assert re.search(r"'\$\.body\.message\.payload',\s*'G2PDciCropSownCreateEnricherService'", sql(
        'registry-inbound-message-rules', 'incoming_model_semantic_patterns.sql'))
    assert (ROOT / 'templates' / 'odk_to_crop_intake.j2').is_file()
    stores = re.findall(r"'([\w.]+\.j2)','templates'", sql('register-metadata', 'g2p_registry_documents.sql'))
    assert len(stores) == len(set(stores))
    assert all(n.startswith('crop_') for n in stores if 'file_import' in n)


@pytest.mark.parametrize('form', FORMS)
def test_blank_file_is_header_only_and_every_column_is_documented(form):
    path = REPO / 'import-templates' / f'crop_{form}_intake_import_template.csv'
    lines = path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 1, 'sample rows belong in openg2p-data'
    columns = lines[0].split(',')
    assert len(columns) == len(set(columns)) and IDENTITY <= set(columns)
    doc = (REPO / 'docs/file-import.md').read_text(encoding='utf-8')
    section = doc.split(f'## {form.capitalize()} intake')[1].split('\n## ')[0]
    rows = dict(re.findall(r'^\| `([\w<>]+)` \|[^|]*\| (Yes|No) \|', section, re.MULTILINE))
    # A child column is documented once as <prefix><n>_<field>, for n = 1 to CHILD_GROUPS.
    documented = {c: r for c, r in rows.items() if '<n>' not in c}
    for n in range(1, CHILD_GROUPS + 1):
        documented.update({c.replace('<n>', str(n)): r for c, r in rows.items() if '<n>' in c})
    assert list(documented) == columns
    assert {c for c, required in documented.items() if required == 'Yes'} == IDENTITY | FORMS[form]['required']


@pytest.mark.parametrize('form', FORMS)
def test_columns_are_the_register_fields_and_every_column_is_read(form):
    spec = FORMS[form]
    details = section_columns()[spec['details']]
    details = {**details, **{key: {} for key in OVERLAY_COLUMNS.get(spec['details'], ())}}
    # The numbered child columns fill the child table: test_child_columns_*.
    columns = set(header(form)) - set(child_columns(form))
    assert columns - IDENTITY - GEO <= set(details), 'a column that is no field of the register section'
    widget_required = {k for k, c in details.items() if c.get('widget-required')} - {'season'}
    assert widget_required <= spec['required']
    result = render(form, full_row(form))
    record = result[spec['details']][0]
    assert set(record) >= columns - IDENTITY - GEO
    assert set(record) <= set(details)
    assert result[spec['season']] == [{'crop_year': '2026', 'production_season': 'SEASON_MEHER'}]


def test_minimal_rows_render_what_the_odk_template_renders_for_the_same_intake():
    odk = (ROOT / 'templates/odk_to_crop_intake.j2').read_text(encoding='utf-8')
    identity = {'farmer_id': 'FR-000000000001', 'fayda_id': '0000123456789012'}
    season = {'crop_year': '2026', 'production_season': 'SEASON_MEHER'}
    cases = {
        'planning': {'address': {'region_display_id': 'ET04', 'kebele_display_id': 'ET040404888003'},
                     'planning': [{'land_info_id': 'L1', 'crop_details': {'crop_name_id': 'CROP_TEFF'}}]},
        'cultivation': {'cult_land_prep': [{'land_info_id': 'L1', 'crop_details': {'crop_name_id': 'CROP_TEFF'}}]},
        'sowing': {'sowing_details': [{'land_info_id': 'L1', 'independant_details': {
            'crop_name_id': 'CROP_TEFF', 'area_sown': 1.5, 'sowing_date_gc': '2026-06-01'}}]},
        'harvesting': {'harvesting': {'land_info_id': 'L1', 'cluster_status_ids': 'independent', 'independant_details': {
            'crop_name_id': 'CROP_TEFF', 'harvest_date': '2026-10-01', 'qty_harvested': 3}}},
    }
    rows = {
        'planning': {'land_id': 'L1', 'commodity': 'CROP_TEFF', 'region': 'ET04', 'kebele': 'ET040404888003'},
        'cultivation': {'land_id': 'L1', 'commodity': 'CROP_TEFF'},
        'sowing': {'land_id': 'L1', 'commodity': 'CROP_TEFF', 'area_sown': '1.5', 'sowing_date': '2026-06-01'},
        'harvesting': {'land_id': 'L1', 'commodity': 'CROP_TEFF', 'harvest_date': '2026-10-01', 'qty_harvested': '3',
                       'cluster_status': 'INDEPENDENT'},
    }
    for form, case in cases.items():
        expected = json.loads(Environment().from_string(odk).render(expanded={
            'farmer_identity': identity, 'production_season_info': season,
            '__system': {'submissionDate': '2026-12-31'}, **case}))
        actual = render(form, {**BASE, **rows[form]})
        assert set(actual) == set(expected) - CHILD_SECTIONS, form
        for key in ('farmer_id', 'fayda_fin', 'fayda_fan_id', 'status', 'lifecycle_stage'):
            assert actual['crop_farmer_lookup'][0][key] == expected['crop_farmer_lookup'][0][key], (form, key)
        assert actual[FORMS[form]['season']] == expected[FORMS[form]['season']]
        for key, value in actual[FORMS[form]['details']][0].items():
            if key in expected[FORMS[form]['details']][0] and key not in {'season', 'region', 'zone', 'woreda', 'kebele'}:
                assert value == expected[FORMS[form]['details']][0][key], (form, key)
        if form == 'planning':
            # the location rides on the farmer lookup; the Address section is not on the form
            assert actual['crop_farmer_lookup'][0]['geo_code_hierarchy_json'] == \
                expected['crop_farmer_lookup'][0]['geo_code_hierarchy_json']


def test_planning_row_maps_columns_to_the_sections_of_the_form():
    result = render('planning', {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', 'land_area': '1.5',
                                 'planned_labor': '4.0', 'is_plot_not_registered': 'No', 'cropping_system': 'CSYS_PURE',
                                 'start_gc': '2026-06-01 00:00:00', 'region': 'et04', 'zone': 'ET0404',
                                 'latitude': '9.0', 'longitude': '38.7'})
    assert result['crop_farmer_lookup'][0]['fayda_fan_id'] == '0000123456789012'
    assert result['crop_farmer_lookup'][0]['fayda_fin'] is None
    assert result['cs_planning_details'] == [{
        'land_id': 'L1', 'commodity': 'CROP_TEFF', 'land_area': 1.5, 'planned_labor': 4, 'is_plot_not_registered': False,
        'cropping_system': 'CSYS_PURE', 'start_gc': '2026-06-01', 'region': 'ET04', 'zone': 'ET0404',
        'latitude': '9.0', 'longitude': '38.7', 'season': 'SEASON_MEHER'}]
    assert 'cs_cropsown_location' not in result  # the Address comes from the Farmer Registry
    location = result['crop_farmer_lookup'][0]
    assert location['geo_lowest_level_value_id'] == 'ET0404'
    assert [h['level_value_id'] for h in location['geo_code_hierarchy_json']['hierarchy']] == ['ET04', 'ET0404']
    assert 'cs_cluster_details' not in result


def test_cultivation_land_prep_methods_and_fin_identity():
    result = render('cultivation', {**BASE, 'fayda_id': '123456789012', 'land_id': 'L1',
                                    'land_prep_method': 'LPM_OXEN; lpm_manual'})
    assert result['cs_cultivation_details'][0]['land_prep_method'] == \
        'LPM_OXEN,LPM_MANUAL'
    assert result['crop_farmer_lookup'][0]['fayda_fin'] == '123456789012'
    assert result['crop_farmer_lookup'][0]['fayda_fan_id'] is None


def test_sowing_and_harvest_cluster_status_are_lists_and_headers_ignore_case():
    sowing = render('sowing', {**BASE, 'Land_ID': ' L1 ', 'cluster_land_id': 'C1', 'cluster_status': 'cluster; independent'})
    assert sowing['cs_sowing_details'][0] == {'land_id': 'L1', 'cluster_land_id': 'C1',
                                              'cluster_status': ['CLUSTERED', 'INDEPENDENT'], 'season': 'SEASON_MEHER'}
    harvest = render('harvesting', {**BASE, 'land_id': 'L1', 'qty_harvested': '12'})
    assert harvest['cs_harvest_details'][0] == {'land_id': 'L1', 'qty_harvested': 12.0}


@pytest.mark.parametrize('form,change,message', [
    ('planning', {'farmer_id': 'FR-1'}, 'column farmer_id'),
    ('planning', {'fayda_id': '12345'}, 'column fayda_id'),
    ('planning', {'crop_year': '26'}, 'column crop_year'),
    ('planning', {'production_season': ''}, 'column production_season'),
    ('planning', {'land_area': 'many'}, 'column land_area must be a number'),
    ('planning', {'planned_labor': 'x'}, 'column planned_labor must be a whole number'),
    ('planning', {'start_gc': '01/06/2026'}, 'column start_gc must be a date'),
    ('planning', {'is_plot_not_registered': 'maybe'}, 'column is_plot_not_registered must be yes or no'),
    ('sowing', {'cluster_status': 'FIELD'}, 'column cluster_status takes CLUSTERED and INDEPENDENT'),
])
def test_a_value_the_register_cannot_take_fails_the_row_naming_the_column(form, change, message):
    with pytest.raises(UndefinedError, match=message):
        render(form, {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', **change})


def test_cultivation_yes_keeps_only_the_land_id_and_area():
    row = {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', 'land_area': '2', 'is_planning_record_created': 'yes',
           'plot_category': 'ANNUAL_CROP', 'region': 'et04', 'latitude': '9.01', 'crop_latitude': '9.02',
           'crop_longitude': '38.75'}
    record = render('cultivation', row)['cs_cultivation_details'][0]
    assert record['is_planning_record_created'] is True and (record['land_id'], record['land_area']) == ('L1', 2.0)
    assert not {'plot_category', 'region', 'latitude'} & set(record)
    assert (record['crop_latitude'], record['crop_longitude']) == ('9.02', '38.75')


def test_cultivation_no_keeps_the_land_columns():
    row = {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', 'is_planning_record_created': 'no',
           'plot_category': 'ANNUAL_CROP', 'region': 'et04', 'kebele': 'ET040404888003', 'latitude': '9.01',
           'longitude': '38.74'}
    record = render('cultivation', row)['cs_cultivation_details'][0]
    assert record['is_planning_record_created'] is False
    assert (record['plot_category'], record['region'], record['kebele'], record['latitude'], record['longitude']) == (
        'ANNUAL_CROP', 'ET04', 'ET040404888003', '9.01', '38.74')


@pytest.mark.parametrize('form', ('sowing', 'harvesting'))
def test_a_clustered_row_needs_its_cluster_land_id(form):
    # Required as on the web form and in ODK: a blank one is refused, not filled from land_id.
    for status in ('CLUSTER', 'CLUSTER;INDEPENDENT'):
        with pytest.raises(UndefinedError, match='column cluster_land_id is required for a Clustered row'):
            render(form, {**BASE, 'land_id': 'L1', 'cluster_status': status})
    record = render(form, {**BASE, 'cluster_land_id': 'C9', 'cluster_status': 'CLUSTER'})[FORMS[form]['details']][0]
    assert record['cluster_land_id'] == 'C9'
    record = render(form, {**BASE, 'land_id': 'L1', 'cluster_land_id': 'C9', 'cluster_status': 'CLUSTER;INDEPENDENT'})
    assert (record[FORMS[form]['details']][0]['land_id'], record[FORMS[form]['details']][0]['cluster_land_id']) == ('L1', 'C9')


@pytest.mark.parametrize('form', ('sowing', 'harvesting'))
def test_yes_keeps_only_the_land_id_and_no_keeps_the_land(form):
    row = {**BASE, 'land_id': 'L1', 'cluster_land_id': 'C1', 'cluster_status': 'CLUSTER;INDEPENDENT',
           'plot_category': 'ANNUAL_CROP', 'region': 'et04', 'latitude': '9.01', 'cluster_region': 'ET04',
           'cluster_sub_kebele': 'Goro'}
    record = render(form, {**row, 'is_land_recorded': 'yes', 'is_cluster_land_recorded': 'yes'})[FORMS[form]['details']][0]
    assert record['is_land_recorded'] is True and record['is_cluster_land_recorded'] is True
    assert not {'plot_category', 'region', 'latitude', 'cluster_region', 'cluster_sub_kebele'} & set(record)
    record = render(form, {**row, 'is_land_recorded': 'no', 'is_cluster_land_recorded': 'no'})[FORMS[form]['details']][0]
    assert (record['plot_category'], record['region'], record['latitude'], record['cluster_region'],
            record['cluster_sub_kebele']) == ('ANNUAL_CROP', 'ET04', '9.01', 'ET04', 'Goro')


def test_planning_rows_take_the_crop_location_as_text():
    # site-configuration/97c_planning_map_location.sql: Crop latitude and Crop longitude on each Planning row.
    record = render('planning', {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', 'season': 'SEASON_MEHER',
                                 'crop_latitude': '9.02', 'crop_longitude': '38.75'})['cs_planning_details'][0]
    assert (record['crop_latitude'], record['crop_longitude']) == ('9.02', '38.75')
    record = render('planning', {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF'})['cs_planning_details'][0]
    assert 'crop_latitude' not in record and 'crop_longitude' not in record  # blank: not given
    with pytest.raises(UndefinedError, match='column crop_latitude must be a number'):
        render('planning', {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', 'crop_latitude': 'north'})


@pytest.mark.parametrize('form', FORMS)
def test_the_template_knows_exactly_the_columns_of_its_blank_file(form):
    template = (ROOT / 'templates' / f'crop_file_import_{form}_intake.j2').read_text(encoding='utf-8')
    listed = re.search(r"\{% set file_columns = (\[.*?\]) %\}", template).group(1)
    assert json.loads(listed.replace("'", '"')) == header(form)


@pytest.mark.parametrize('form,other', [(f, o) for f in FORMS for o in FORMS if f != o])
def test_a_file_made_for_another_form_fails_the_row(form, other):
    # e.g. a Planning file uploaded under the Cultivation import must not become a Cultivation intake.
    label = {'harvesting': 'Harvest'}.get(form, form.capitalize())
    with pytest.raises(UndefinedError, match=rf'is not a {label} column: check that this file is for the {label} import'):
        render(form, full_row(other))


def test_the_upload_message_says_the_file_was_uploaded_not_imported():
    # The platform shows import_successful when the file is queued; rows are checked afterwards.
    names = sorted(p.name for p in (META / 'site-configuration').glob('*.sql'))
    overlay = 'site-configuration/97l_import_file_message.sql'
    assert names.index('30_label_casing.sql') < names.index('97l_import_file_message.sql') < names.index('98_ethiopian_dates.sql')
    text = (META / overlay).read_text(encoding='utf-8')
    assert '"import_successful": "File uploaded. Check Incoming Messages for the result of each row."' in text
    assert 'WHERE' not in text  # every language


def test_the_import_menu_shows_a_label_for_each_crop_import():
    # The menu translates an import configuration by its import_file_template_mnemonic.
    text = (META / 'site-configuration/97l_import_file_message.sql').read_text(encoding='utf-8')
    labels = json.loads('{' + text.split("'{\n", 1)[1].split("}'", 1)[0] + '}')  # the merged keys, not COALESCE's '{}'
    configurations = sql('registry-configurations', 'g2p_registry_import_file_configurations.sql')
    for form in FORMS:
        assert f"'file_import_to_crop_{form}_intake'" in configurations  # the mnemonic stays as it is
    assert {k: v for k, v in labels.items() if k.startswith('file_import_')} == {
        'file_import_to_crop_planning_intake': 'Planning (with clusters)',
        'file_import_to_crop_cultivation_intake': 'Cultivation (with cultivation clusters)',
        'file_import_to_crop_sowing_intake': 'Sowing (with infestations)',
        'file_import_to_crop_harvesting_intake': 'Harvest'}


# --- Child rows in the same row: up to three clusters, cultivation clusters or infestations -------------

@pytest.mark.parametrize('form', CHILD)
def test_child_columns_are_three_groups_of_the_child_fields_and_every_one_is_read(form):
    section = CHILD[form][0]
    child = section_columns()[section]
    groups = [child_columns(form, n) for n in range(1, CHILD_GROUPS + 1)]
    fields = [[child_field(form, c) for c in group] for group in groups]
    assert fields[0] == fields[1] == fields[2] and len(set(fields[0])) == len(fields[0])
    assert set(fields[0]) <= set(child)
    assert set(child) - set(fields[0]) == CHILD_NOT_IMPORTED[section]
    assert header(form)[-len(child_columns(form)):] == child_columns(form), 'the child groups come last, in order'
    result = render(form, full_row(form))
    assert len(result[FORMS[form]['details']]) == 1 and len(result[section]) == CHILD_GROUPS
    assert all(set(row) == set(fields[0]) for row in result[section])


@pytest.mark.parametrize('form', CHILD)
def test_a_row_without_child_values_has_no_child_rows(form):
    row = {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', **{c: '' for c in child_columns(form)}}
    assert CHILD[form][0] not in render(form, row)


def test_a_planning_row_carries_its_clusters_in_the_same_intake_and_skips_blank_groups():
    row = {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', 'cluster_1_land_id': 'C1', 'cluster_1_name': 'Gara',
           'cluster_1_fpc_type': 'green', 'cluster_1_region': 'et04', 'cluster_1_latitude': '9.1',
           'cluster_1_area_timad': '8', 'cluster_1_number_of_smallholders': '12.0',
           'cluster_1_start_gc': '2026-06-01 00:00:00', 'cluster_3_land_id': 'C3', 'cluster_3_plan': '1.5'}
    result = render('planning', row)
    assert result['cs_planning_details'][0]['land_id'] == 'L1'
    assert result['cs_cluster_details'] == [
        {'land_id': 'C1', 'cluster_name': 'Gara', 'fpc_type': 'GREEN', 'region': 'ET04', 'latitude': '9.1',
         'cluster_area_timad': 8.0, 'number_of_smallholders': 12, 'start_gc': '2026-06-01', 'season': 'SEASON_MEHER'},
        {'land_id': 'C3', 'cluster_plan': 1.5, 'season': 'SEASON_MEHER'}]  # blank season: the production season


def test_a_cultivation_row_carries_its_cultivation_clusters():
    row = {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', 'cluster_2_land_id': 'K2', 'cluster_2_season': 'SEASON_MEHER',
           'cluster_2_collected_land': '2'}
    assert render('cultivation', row)['cs_cultivation_cluster_details'] == [
        {'land_id': 'K2', 'season': 'SEASON_MEHER', 'collected_land': 2.0}]


def test_a_sowing_row_carries_its_infestations():
    row = {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', 'area_sown': '1', 'sowing_date': '2026-06-01',
           'infestation_1_land_id': 'L1', 'infestation_1_cluster_status': 'cluster', 'infestation_1_cluster_name': 'Gara',
           'infestation_1_type': 'INFT_PEST', 'infestation_1_pest_type': 'PEST_STALK_BORER',
           'infestation_1_pesticide_type': 'Insecticide', 'infestation_1_observation_date': '2026-07-01',
           'infestation_1_estimated_damage_pct': '20',
           'infestation_2_land_id': 'L1', 'infestation_2_type': 'INFT_WEED', 'infestation_2_weed_control_method': 'HAND_PICKING'}
    assert render('sowing', row)['cs_infestation_details'] == [
        {'land_id': 'L1', 'cluster_status': 'CLUSTERED', 'cluster_name': 'Gara', 'infestation_type': 'INFT_PEST',
         'pest_type': 'PEST_STALK_BORER', 'pesticide_type': 'insecticide', 'observation_date': '2026-07-01',
         'estimated_damage_pct': '20'},
        {'land_id': 'L1', 'infestation_type': 'INFT_WEED', 'weed_control_method': 'hand_picking'}]


@pytest.mark.parametrize('form,change,message', [
    ('planning', {'cluster_2_name': 'Gara'}, 'column cluster_2_land_id is required when the row has cluster 2'),
    ('planning', {'cluster_1_land_id': 'C1', 'cluster_1_area_timad': 'eight'}, 'column cluster_1_area_timad must be a number'),
    ('planning', {'cluster_1_land_id': 'C1', 'cluster_1_number_of_smallholders': 'x'},
     'column cluster_1_number_of_smallholders must be a whole number'),
    ('planning', {'cluster_3_land_id': 'C1', 'cluster_3_end_gc': '31/12/2026'}, 'column cluster_3_end_gc must be a date'),
    ('planning', {'cluster_1_land_id': 'C1', 'cluster_1_fpc_type': 'BLUE'}, 'column cluster_1_fpc_type must be one of GREEN'),
    ('planning', {'cluster_4_land_id': 'C4'}, 'column cluster_4_land_id is not a Planning column'),
    ('planning', {'cluster_land_id': 'C1'}, 'column cluster_land_id is not a Planning column'),
    ('cultivation', {'cluster_1_plan': '2'}, 'column cluster_1_land_id is required when the row has cultivation cluster 1'),
    ('sowing', {'infestation_1_type': 'INFT_PEST'}, 'column infestation_1_land_id is required when the row has infestation 1'),
    ('sowing', {'infestation_2_land_id': 'L1', 'infestation_2_pesticide_type': 'poison'},
     'column infestation_2_pesticide_type must be one of insecticide'),
    ('sowing', {'infestation_1_land_id': 'L1', 'infestation_1_observation_date': '01/07/2026'},
     'column infestation_1_observation_date must be a date'),
])
def test_a_child_value_the_register_cannot_take_fails_the_row_naming_the_column(form, change, message):
    with pytest.raises(UndefinedError, match=message):
        render(form, {**BASE, 'land_id': 'L1', 'commodity': 'CROP_TEFF', **change})
