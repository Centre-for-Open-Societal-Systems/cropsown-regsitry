"""Execute the production lookup functions against the Postman HTTP simulation."""
import ast
import asyncio
from datetime import date,datetime,timedelta,timezone
import logging
import os
from pathlib import Path
import re
import uuid
from unittest.mock import patch

import httpx
import jwt
import orjson
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,NoEncryption

EXT=Path(__file__).resolve().parents[1]/'cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services'
FID='FR-123456789012'
FAN='9999102220260001'

@pytest.fixture
def helper():
    scope=dict(os=os,re=re,uuid=uuid,datetime=datetime,date=date,timedelta=timedelta,timezone=timezone,
               httpx=httpx,jwt=jwt,orjson=orjson,_SEX_TO_GENDER={'male':'MALE','female':'FEMALE','other':'OTHER'},
               _logger=logging.getLogger('lookup-test'))
    for path,names in [(EXT/'domain_validation_utils.py',{'is_blank','parse_date'}),
                       (EXT/'farmer_registry_enrichment.py',None)]:
        nodes=[n for n in ast.parse(path.read_text(encoding='utf-8')).body
               if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (names is None or n.name in names)]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),scope)
    key=Ed25519PrivateKey.generate().private_bytes(Encoding.PEM,PrivateFormat.PKCS8,NoEncryption()).decode()
    env={'CROPSOWN_FARMER_ENRICHMENT_ENABLED':'true','CROPSOWN_FARMER_DCI_URL':'http://127.0.0.1:49180/farmer/success',
         'CROPSOWN_DCI_SENDER_ID':'test-crop','CROPSOWN_CM_SIGNING_KEY_PEM':key,'CROPSOWN_CM_SIGNING_KID':'test-only',
         'CROPSOWN_CM_ALG':'EdDSA','CROPSOWN_CM_PARTNER_AUD':'crop-registry','CROPSOWN_CM_CONTROLLER_ID':'farmer-registry',
         'CROPSOWN_CM_SCOPES':'farmer_personal_details','CROPSOWN_CM_PURPOSE':'registry_intake','CROPSOWN_FARMER_DCI_TIMEOUT':'0.15'}
    with patch.dict(os.environ,env):yield scope

def test_canonical_pair_and_fresh_consent_are_signed(helper):
    cfg=helper['_config']()
    a=helper['build_search_request']('  '+FID+'\t','9999\u00a01022 2026\t0001',cfg)
    b=helper['build_search_request'](FID,FAN,cfg)
    ca=a['message']['search_request'][0]['search_criteria']
    assert ca['query']['value']['expression']['query']=={'functional_record_id':{'$eq':FID},'foundational_id':{'$eq':FAN}}
    consent=jwt.decode(ca['authorize']['consent_jws'],options={'verify_signature':False})
    assert consent['subject_id']=={'type':'fayda_fan_id','value':FAN}
    cb=jwt.decode(b['message']['search_request'][0]['search_criteria']['authorize']['consent_jws'],options={'verify_signature':False})
    assert consent['jti']!=cb['jti'] and a['header']['message_id']!=b['header']['message_id']
    protected,_,signature=a['signature'].split('.')
    token=protected+'.'+jwt.utils.base64url_encode(orjson.dumps({'header':a['header'],'message':a['message']},option=orjson.OPT_SORT_KEYS)).decode()+'.'+signature
    public=__import__('cryptography.hazmat.primitives.serialization',fromlist=['load_pem_private_key']).load_pem_private_key(cfg['signing_key'].encode(),None).public_key()
    assert jwt.api_jws.PyJWS().decode(token,public,algorithms=['EdDSA'])

@pytest.mark.parametrize('fid,fan',[(None,FAN),(FID,None),('',FAN),(FID,''),('FR-1234567890',FAN),('FR-1234567890123',FAN),('fr-123456789012',FAN),(FID,'1234'),(FID,'９'*16)])
def test_incomplete_or_invalid_identifiers_cannot_form_a_lookup(helper,fid,fan):
    with pytest.raises(ValueError):helper['build_search_request'](fid,fan,helper['_config']())
    assert asyncio.run(helper['fetch_farmer_record'](fid,fan)) is None

@pytest.mark.parametrize('value',['0','-1','NaN','inf','10s',''])
def test_bad_timeout_configuration_is_safe(helper,value):
    with patch.dict(os.environ,{'CROPSOWN_FARMER_DCI_TIMEOUT':value}):
        # Empty uses the documented default; the other invalid values disable lookup.
        assert bool(helper['_config']())==(value=='')

@pytest.mark.parametrize('mode',['zero','multiple','no-scope','wrong-identity','missing-identifier','scalar-record',
    'rejected','header-rejected','multiple-responses','no-message','scalar-message','array','invalid-json',
    'unauthorized','rate-limit','server-error','html','timeout','success'])
def test_actual_http_failure_and_success_contract(helper,mode,caplog):
    base=os.environ.get('CROP_FARMER_SIMULATION_URL')
    if not base:pytest.skip('Start the Postman simulation to run HTTP fault scenarios')
    with patch.dict(os.environ,{'CROPSOWN_FARMER_DCI_URL':base+'/'+mode}):
        result=asyncio.run(helper['fetch_farmer_record'](FID,FAN))
    assert bool(result)==(mode=='success')
    if result:
        fields=helper['to_farmer_fields'](result)
        assert fields['first_name']=='Synthetic' and fields['fayda_fan_id']==FAN
    assert FAN not in caplog.text and FID not in caplog.text

def test_connection_failure_does_not_escape(helper):
    with patch.dict(os.environ,{'CROPSOWN_FARMER_DCI_URL':'http://127.0.0.1:1/unreachable'}):
        assert asyncio.run(helper['fetch_farmer_record'](FID,FAN)) is None

@pytest.mark.parametrize('mode',['success','zero','wrong-identity','timeout'])
def test_notification_uses_current_lookup_and_raises_for_pipeline_retry(helper,mode):
    base=os.environ.get('CROP_FARMER_SIMULATION_URL')
    if not base:pytest.skip('Start the Postman simulation')
    path=EXT.parents[1]/'ingestion_pipeline/enricher_services/farmer_reference.py'
    node=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef))
    scope={**helper,'G2PPayloadEnricherInterface':object,'asyncio':asyncio}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),scope)
    service=scope['G2PFarmerReferenceNotificationEnricher']()
    with patch.dict(os.environ,{'CROPSOWN_FARMER_DCI_URL':base+'/'+mode}):
        event={'farmer_id':FID,'fayda_fan_id':FAN,'first_name':'Stale Event Name'}
        if mode=='success':
            fields=service.enrich(event,None)
            assert fields['first_name']=='Synthetic' and fields['first_name']!=event['first_name']
        else:
            with pytest.raises(ValueError,match='LOOKUP_NOT_RESOLVED'):service.enrich(event,None)

@pytest.mark.parametrize('resolved,active,expected',[(False,False,0),(False,True,0),(True,True,0),(True,False,2)])
def test_staging_requires_resolved_identity_skips_active_and_serialises_per_farmer(resolved,active,expected):
    from unittest.mock import AsyncMock
    async def main():
        lock=asyncio.Lock();order=[]
        class Session:
            def begin_nested(self):return Transaction()
        class Transaction:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):
                if lock.locked():lock.release()
        async def lock_farmer(session,farmer_id):
            await lock.acquire();order.append(('lock',farmer_id))
        async def stage(session,farmer_id,fields,name,created_by):
            assert lock.locked()
            await asyncio.sleep(0.01)
            order.append(('stage',farmer_id,name,created_by))
            return 'shell'
        scope={'_enabled':lambda:True,'_config':lambda:{'created_by':'test'},
            '_intake_farmer_ids':AsyncMock(return_value=[{'farmer_id':' '+FID+' ','fayda_fan_id':FAN}]),
            '_farmer_exists_active':AsyncMock(return_value=active),
            'fetch_farmer_record':AsyncMock(return_value={'demographic_info':{}} if resolved else None),
            'to_farmer_fields':lambda _: {'first_name':'Synthetic'},'compose_farmer_name':lambda *a:'Synthetic',
            '_lock_farmer':lock_farmer,'_stage_reference':stage,
            '_logger':logging.getLogger('test-crossref')}
        path=EXT/'farmer_register_crossref.py'
        node=next(n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='stage_farmer_reference')
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),scope)
        await asyncio.gather(*(scope['stage_farmer_reference']('marked-submission',Session()) for _ in range(2)))
        staged=[o for o in order if o[0]=='stage']
        assert len(staged)==expected
        assert all(o==('stage',FID,'Synthetic','test') for o in staged)
        assert scope['fetch_farmer_record'].await_count==2
        if not resolved:scope['_farmer_exists_active'].assert_not_awaited()
        assert not lock.locked()
    asyncio.run(main())


def test_fan_mapping_uses_uin_even_after_another_identifier(helper):
    result=helper['to_farmer_fields']({'member_identifier':[{'identifier_type':'OTHER','identifier_value':'another-id'},{'identifier_type':'UIN','identifier_value':FAN}]})
    assert result['fayda_fan_id']==FAN
