"""Guard the enabled Crop workflow, its real chart, and finalize wrapper."""
import ast
import asyncio
import base64
import copy
import importlib.util
import io
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sqlite3
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT/'cropsown-extension/src/openg2p_registry_cropsown_extension'
spec = importlib.util.spec_from_file_location('guard', ROOT/'ci/check-farmer-enrichment.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def manifest():
    values = yaml.safe_load((ROOT/'helm/environments/dev/farmer-enrichment.yaml').read_text(encoding='utf-8'))['registry']
    result = []
    for component, suffix in [('staffApi', 'staff-portal-api'), ('celeryWorker', 'celery-worker')]:
        cfg = values[component]
        env = [{'name':k, 'value':v} for k,v in cfg['envVars'].items()]
        env += [{'name':k, 'valueFrom':v} for k,v in cfg['envVarsFrom'].items()]
        result.append({'kind':'Deployment','metadata':{'name':'cropsown-registry-'+suffix,'namespace':'crop'},
            'spec':{'template':{'spec':{'containers':[{'name':suffix,'env':env}]}}}})
    return result


def check(items, secret=None, hooks=None):
    return guard.check(items,'cropsown-registry','crop',secret,hooks)


def test_config_and_secret_metadata():
    data = yaml.safe_load((ROOT/'helm/environments/dev/farmer-enrichment.yaml').read_text(encoding='utf-8'))
    env = data['registry']['staffApi']['envVars']
    secret = {'metadata':{'namespace':'crop'},'data':{
        k:base64.b64encode(v.encode()).decode() for k,v in {
            'private-key.pem':'test-only-private-key','kid':env['CROPSOWN_CM_SIGNING_KID'],'algorithm':'EdDSA'}.items()}}
    loader = lambda *_: copy.deepcopy(secret)
    logs = lambda *_: 'CropSown two-CR hooks installed (finalize + approve_register create-or-update)'
    assert check(manifest(),loader,logs)['runtimeHooksChecked']
    for key in ['private-key.pem','kid','algorithm']:
        bad = copy.deepcopy(secret);bad['data'][key] = base64.b64encode(b'wrong' if key!='private-key.pem' else b'').decode()
        with pytest.raises(AssertionError):check(manifest(),lambda *_: bad)
    with pytest.raises(AssertionError):check(manifest(),loader,lambda *_:'no hooks installed')


@pytest.mark.parametrize('setting',['CROPSOWN_TWO_CR_ENABLED','CROPSOWN_FARMER_ENRICHMENT_ENABLED',*guard.REQUIRED,'CROPSOWN_CM_SIGNING_KEY_PEM'])
def test_missing_settings_are_blocked(setting):
    docs = manifest()
    docs[0]['spec']['template']['spec']['containers'][0]['env'] = [
        e for e in docs[0]['spec']['template']['spec']['containers'][0]['env'] if e['name']!=setting]
    with pytest.raises(AssertionError):check(docs)


def test_duplicate_wrong_namespace_disabled_and_inline_private_key_rejected():
    for mode in ['namespace','duplicate','disabled','inline','optional','timeout','missing-worker']:
        docs = manifest();env=docs[0]['spec']['template']['spec']['containers'][0]['env']
        if mode=='namespace':docs[0]['metadata']['namespace']='live'
        if mode=='duplicate':env.append(env[0])
        if mode=='disabled':env[0]['value']='false'
        if mode=='inline':env[-1]={'name':'CROPSOWN_CM_SIGNING_KEY_PEM','value':'test-private-key'}
        if mode=='optional':env[-1]['valueFrom']['secretKeyRef']['optional']=True
        if mode=='timeout':next(e for e in env if e['name']=='CROPSOWN_FARMER_DCI_TIMEOUT')['value']='nan'
        if mode=='missing-worker':docs.pop()
        with pytest.raises(AssertionError):check(docs)
    with pytest.raises(AssertionError):check([])
    with pytest.raises(ValueError):guard.resources(io.StringIO('{"kind":'))
    assert check(guard.resources(io.StringIO(json.dumps({'kind':'List','items':manifest()}))))


@pytest.mark.skipif(not shutil.which('helm'),reason='Helm required')
def test_real_chart_renders_both_workloads_with_enrichment():
    r = subprocess.run(['helm','template','cropsown-registry',str(ROOT/'helm/openg2p-cropsown-registry'),
        '-n','crop','-f',str(ROOT/'helm/environments/dev/farmer-enrichment.yaml')],capture_output=True,text=True,encoding='utf-8',check=True)
    assert check([d for d in yaml.safe_load_all(r.stdout) if d])['cropFarmerEnrichmentGuard']=='passed'


def hook_scope():
    path=EXT/'register_domain/services/farmer_register_crossref.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'_enabled','_setting','install'}]
    scope={'os':os,'_logger':logging.getLogger('test-hooks'),'_install_approve_register':Mock(),
           '_config':lambda:{'register_id':'farmer-register'},'raise_farmer_change_request':AsyncMock()}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),scope)
    return scope


def test_hook_feature_flag_idempotency_arguments_and_failure_boundaries():
    async def main():
        original=AsyncMock(return_value='original-result')
        class Intake:
            finalize_submission_with_session=original
        scope=hook_scope()
        with patch.dict(os.environ,{'CROPSOWN_TWO_CR_ENABLED':'false'}):
            scope['install'](Intake)
            assert Intake.finalize_submission_with_session is original
        with patch.dict(os.environ,{'CROPSOWN_TWO_CR_ENABLED':'true'}):
            scope['install'](Intake);wrapped=Intake.finalize_submission_with_session
            scope['install'](Intake)
            assert Intake.finalize_submission_with_session is wrapped
            scope['_install_approve_register'].assert_called_once_with('farmer-register')
            assert await Intake().finalize_submission_with_session('submission','session',bearer_token='token',requester_sub='actor')=='original-result'
            scope['raise_farmer_change_request'].assert_awaited_once_with('submission','token','actor')
            scope['raise_farmer_change_request'].side_effect=RuntimeError('lookup unavailable')
            assert await Intake().finalize_submission_with_session('submission','session')=='original-result'
            scope['raise_farmer_change_request'].reset_mock()
            original.side_effect=RuntimeError('finalize failed')
            with pytest.raises(RuntimeError,match='finalize failed'):
                await Intake().finalize_submission_with_session('submission','session')
            scope['raise_farmer_change_request'].assert_not_awaited()
    asyncio.run(main())


def test_initializer_installs_after_existing_validation_hooks():
    tree=ast.parse((EXT/'app.py').read_text(encoding='utf-8'))
    initialize=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='initialize')
    calls=[(n.func.id,n.lineno) for n in ast.walk(initialize) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
    assert next(line for name,line in calls if name=='install') > next(line for name,line in calls if name=='setup_intake_hooks')


def test_display_fan_is_canonical_in_query_and_consent():
    from datetime import datetime,timezone
    import uuid
    path=EXT/'register_domain/services/farmer_registry_enrichment.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_search_request')
    signed=[];subjects=[]
    scope={'datetime':datetime,'timezone':timezone,'uuid':uuid,
           'is_blank':lambda v:v is None or not str(v).strip(),
           '_consent_jws':lambda subject,*_:subjects.append(subject) or 'consent',
           '_sign':lambda payload,*a,**k:signed.append(payload) or 'signature',
           'orjson':type('JSON',(),{'OPT_SORT_KEYS':1,'dumps':staticmethod(lambda value,**kw:json.dumps(value,sort_keys=True).encode())})}
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(path),'exec'),scope)
    cfg={'sender_id':'crop','receiver_id':'farmer-registry'}
    envelope=scope['build_search_request']('FR-123456789012','1234 5678 9000 3456',cfg)
    query=envelope['message']['search_request'][0]['search_criteria']['query']['value']['expression']['query']
    assert query['foundational_id']['$eq']=='1234567890003456'
    assert subjects==['1234567890003456'] and signed


def test_worker_signal_registration_and_feature_flag():
    import types
    import sys
    path=EXT/'worker_hooks.py'
    spec=importlib.util.spec_from_file_location('worker_hooks',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    signal=Mock()
    with patch.dict(sys.modules,{'celery.signals':types.SimpleNamespace(worker_init=signal)}):
        module.connect()
    signal.connect.assert_called_once_with(module.install_farmer_worker_hooks,weak=False)
    with patch.dict(os.environ,{'CROPSOWN_TWO_CR_ENABLED':'false'}):
        module.install_farmer_worker_hooks()
    # The enabled callback uses the same tested installer after core bootstrap.
    assert 'install(G2PIntakeFormDataService)' in path.read_text()


def test_policy_seed_removes_known_duplicates_and_preserves_custom_configuration():
    source=(EXT/'meta_data/awe-integration/g2p_registry_awe_policy_configurations.sql').read_text().replace('"public".','')
    c=sqlite3.connect(':memory:')
    c.execute('CREATE TABLE g2p_registry_awe_policy_configurations (awe_policy_config_id TEXT PRIMARY KEY,policy_scope TEXT,register_id TEXT,intake_form_id TEXT,section_id TEXT,policy_type TEXT,policy_key TEXT,context_field_names TEXT)')
    old=('d126d7ff-8fb9-48e2-ab71-a48db3bf261a','INTAKE_FORM','6b06a95a-9a6c-5a33-a33d-c1625716c59c','5bf0068c-ce19-46f8-874c-7147997f793b','','registry.intake_form','registry.intake_form.devplanning_cropsown',None)
    c.execute('INSERT INTO g2p_registry_awe_policy_configurations VALUES (?,?,?,?,?,?,?,?)',old)
    custom=('custom',*old[1:])
    c.execute('INSERT INTO g2p_registry_awe_policy_configurations VALUES (?,?,?,?,?,?,?,?)',custom)
    c.executescript(source);c.executescript(source)
    assert not c.execute('SELECT 1 FROM g2p_registry_awe_policy_configurations WHERE awe_policy_config_id=?',(old[0],)).fetchone()
    assert c.execute('SELECT 1 FROM g2p_registry_awe_policy_configurations WHERE awe_policy_config_id=?',('custom',)).fetchone()
    assert c.execute("SELECT policy_key FROM g2p_registry_awe_policy_configurations WHERE register_id='fa120001-0000-4000-8000-000000000001'").fetchone()==('registry.change_request.cropsown',)
