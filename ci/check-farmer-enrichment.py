"""Check Crop lookup configuration without printing manifest or Secret values."""
import argparse
import base64
import json
import math
import subprocess
import sys
from urllib.parse import urlsplit

REQUIRED = ('CROPSOWN_DCI_SENDER_ID', 'CROPSOWN_DCI_RECEIVER_ID',
            'CROPSOWN_CM_SIGNING_KID', 'CROPSOWN_CM_ALG', 'CROPSOWN_CM_PARTNER_AUD',
            'CROPSOWN_CM_CONTROLLER_ID', 'CROPSOWN_CM_SCOPES', 'CROPSOWN_CM_PURPOSE',
            'CROPSOWN_FARMER_REGISTER_ID', 'CROPSOWN_FARMER_TAB_ID',
            'CROPSOWN_FARMER_SECTION_ID', 'CROPSOWN_TWO_CR_INTAKE_TABLE')


def resources(stream):
    decoder = json.JSONDecoder()
    text = stream.read().strip()
    result = []
    while text:
        document, end = decoder.raw_decode(text)
        result.extend(document.get('items', []) if document.get('kind') == 'List' else [document])
        text = text[end:].lstrip()
    return result


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, 'Cannot inspect required lookup resource'
    return result.stdout


def check(items, release, namespace, secret_loader=None, hook_loader=None):
    seen = []
    for suffix, container_name in [('staff-portal-api', 'staff-portal-api'), ('celery-worker', 'celery-worker')]:
        name = release + '-' + suffix
        targets = [d for d in items if d.get('kind') == 'Deployment' and d.get('metadata', {}).get('name') == name]
        assert len(targets) == 1, 'Required lookup Deployment missing or duplicated: ' + suffix
        deployment = targets[0]
        assert deployment['metadata'].get('namespace', namespace) == namespace, 'Wrong lookup namespace'
        target = [c for c in deployment['spec']['template']['spec']['containers'] if c['name'] == container_name]
        assert len(target) == 1, 'Required lookup container missing or duplicated'
        entries = target[0].get('env', [])
        env = {e['name']: e for e in entries}
        assert len(env) == len(entries), 'Duplicate environment variable'
        def value(key):
            return str(env.get(key, {}).get('value', '')).strip()
        for flag in ('CROPSOWN_TWO_CR_ENABLED', 'CROPSOWN_FARMER_ENRICHMENT_ENABLED'):
            assert value(flag).lower() in {'true', '1', 'yes'}, 'Required Crop lookup feature disabled'
        for key in REQUIRED:
            assert value(key), 'Required lookup setting missing: ' + key
        url = urlsplit(value('CROPSOWN_FARMER_DCI_URL'))
        assert url.scheme in {'http', 'https'} and url.hostname and url.path == '/dci/registry/sync/search', 'Invalid Farmer lookup URL'
        timeout = float(value('CROPSOWN_FARMER_DCI_TIMEOUT') or '10')
        assert math.isfinite(timeout) and timeout > 0, 'Invalid lookup timeout'
        assert value('CROPSOWN_TWO_CR_INTAKE_TABLE') == 'g2p_intake_form_crop_sowns', 'Unexpected lookup intake table'
        key = env.get('CROPSOWN_CM_SIGNING_KEY_PEM', {})
        ref = key.get('valueFrom', {}).get('secretKeyRef', {})
        assert 'value' not in key and ref.get('name') and ref.get('key') and not ref.get('optional'), 'Required private-key Secret reference missing'
        if secret_loader:
            secret = secret_loader(namespace, ref['name'])
            assert secret.get('metadata', {}).get('namespace') == namespace, 'Wrong signing Secret namespace'
            data = secret.get('data', {})
            assert base64.b64decode(data.get(ref['key'], ''), validate=True).strip(), 'Empty signing private key'
            for field, setting in [('kid', 'CROPSOWN_CM_SIGNING_KID'), ('algorithm', 'CROPSOWN_CM_ALG')]:
                assert base64.b64decode(data.get(field, ''), validate=True).decode().strip() == value(setting), 'Signing Secret metadata mismatch'
        if hook_loader:
            assert 'CropSown two-CR hooks installed (finalize + approve_register create-or-update)' in hook_loader(namespace, name), 'Crop Farmer hooks were not installed'
        seen.append(name)
    return {'cropFarmerEnrichmentGuard': 'passed', 'deployments': seen,
            'liveSecretChecked': secret_loader is not None, 'runtimeHooksChecked': hook_loader is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True)
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--check-live-secret', action='store_true')
    parser.add_argument('--check-runtime-hooks', action='store_true')
    args = parser.parse_args()
    try:
        report = check(resources(sys.stdin), args.release, args.namespace,
            (lambda ns, name: json.loads(run(['kubectl', 'get', 'secret', name, '-n', ns, '-o', 'json']))) if args.check_live_secret else None,
            (lambda ns, name: run(['kubectl', 'logs', 'deploy/' + name, '-n', ns, '--tail=10000'])) if args.check_runtime_hooks else None)
    except (AssertionError, ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as error:
        reason = str(error) if isinstance(error, AssertionError) else 'Invalid lookup configuration or unavailable resource'
        print('Crop enrichment guard failed: ' + reason, file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
