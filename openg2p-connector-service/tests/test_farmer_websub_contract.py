import hashlib,hmac,json
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,NoEncryption
from jwt.api_jws import PyJWS
from jwt.utils import base64url_encode
from openg2p_connector_service.controllers.webhook import _extract_payload
from openg2p_connector_service.services.ingestion_service import IngestionService
from openg2p_connector_service.webhooks.verifiers import verify_webhook

def connector(**config):
    return SimpleNamespace(transport_type='websub',g2p_sender_id='test-partner',g2p_register_mnemonic='Farmer',
                           get_source_config=lambda:{'websub_content_envelope':True,**config})

@pytest.mark.parametrize('header',['X-Hub-Signature','X-Hub-Signature-256','x-hub-signature'])
def test_mosip_raw_body_signature_and_tampering(header):
    raw=b'{"hub.content":"{\\"event_id\\":\\"test\\"}"}'
    signature='sha256='+hmac.new(b'test-secret',raw,hashlib.sha256).hexdigest()
    verify_webhook('hmac_sha256','test-secret',raw,{header:signature})
    with pytest.raises(HTTPException) as error:verify_webhook('hmac_sha256','test-secret',raw+b' ',{header:signature})
    assert error.value.status_code==403

@pytest.mark.parametrize('secret,headers,status',[('',{},503),('s',{},401),('s',{'x-hub-signature':'sha1=x'},403),
    ('s',{'x-hub-signature':'sha256=x','x-hub-signature-256':'sha256=y'},403)])
def test_missing_or_invalid_signature_fails_closed(secret,headers,status):
    with pytest.raises(HTTPException) as error:verify_webhook('hmac_sha256',secret,b'{}',headers)
    assert error.value.status_code==status

@pytest.mark.parametrize('as_string',[False,True])
def test_hub_envelope_preserves_event_id_in_api_and_worker(as_string):
    event={'event_id':'source-version-123','farmer_id':'FR-123456789012','fayda_fan_id':'9988102220260002'}
    raw={'hub.mode':'publish','hub.topic':'farmer-reference-v1','hub.content':json.dumps(event) if as_string else event}
    assert _extract_payload(raw,connector())==('source-version-123',event)
    assert IngestionService()._extract_envelope(connector(),raw)==event

@pytest.mark.parametrize('content',[None,[],{},'{',{'event_id':None},{'event_id':3}])
def test_missing_event_or_non_object_is_rejected(content):
    with pytest.raises(HTTPException):_extract_payload({'hub.content':content},connector())

def test_registry_ingest_is_signed_over_the_configured_payload(monkeypatch):
    key=Ed25519PrivateKey.generate()
    monkeypatch.setenv('CONNECTOR_SIGNING_KEY_PEM',key.private_bytes(Encoding.PEM,PrivateFormat.PKCS8,NoEncryption()).decode())
    monkeypatch.setenv('CONNECTOR_SIGNING_KID','test-only')
    data={'event_id':'stable-event','farmer_id':'FR-123456789012'}
    result=IngestionService()._wrap_in_g2p_envelope(connector(sign_registry_payload=True),data,'stable-event')
    assert result['header']['message_id']=='stable-event'
    protected,_,sig=result['header']['signature'].split('.')
    raw=json.dumps(result['message']['payload'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    token=protected+'.'+base64url_encode(raw).decode()+'.'+sig
    assert PyJWS().decode(token,key.public_key(),algorithms=['EdDSA'])==raw
    with pytest.raises(ValueError):IngestionService()._wrap_in_g2p_envelope(connector(sign_registry_payload=True),{'header':{'sender_id':'forged'}},'stable-event')
    monkeypatch.delenv('CONNECTOR_SIGNING_KEY_PEM')
    with pytest.raises(ValueError):IngestionService()._wrap_in_g2p_envelope(connector(sign_registry_payload=True),data,'stable-event')
