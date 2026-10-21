"""Render the pinned chart with generic, dev and representative staging values.

Requires Helm, PyYAML, Bash and built chart dependencies. No cluster access.
"""
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT=Path(__file__).resolve().parents[1]
CHART=ROOT/'helm/openg2p-cropsown-registry'
HELM=os.environ.get('HELM') or shutil.which('helm')
BASH=shutil.which('bash')
if os.name=='nt':BASH=str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Git/bin/bash.exe')
spec=importlib.util.spec_from_file_location('guard',ROOT/'ci/check-new-dev-routes.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)


@unittest.skipUnless(HELM and BASH,'Helm and Bash are required')
class ChartEnvironmentTests(unittest.TestCase):
    def render(self,*values,namespace='crop'):
        with tempfile.TemporaryDirectory(prefix='crop-chart-profile-') as folder:
            args=[]
            for i,value in enumerate(values):
                path=Path(folder)/('values-'+str(i)+'.yaml')
                path.write_text(yaml.safe_dump(value),encoding='utf-8')
                args.extend(['-f',str(path)])
            command=[HELM,'template','cropsown-registry',str(CHART),'-n',namespace,*args]
            r=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=40)
            self.assertEqual(r.returncode,0,r.stderr)
            lint=subprocess.run([HELM,'lint',str(CHART),'--strict',*args],capture_output=True,text=True,encoding='utf-8',timeout=40)
            self.assertEqual(lint.returncode,0,lint.stdout+lint.stderr)
            return [d for d in yaml.safe_load_all(r.stdout) if d]

    def no_dev(self,docs):
        raw=yaml.safe_dump_all(docs)
        self.assertNotIn('.development.oanstaging.com',raw)
        self.assertNotIn('-development.oanstaging.com',raw)
        self.assertNotIn('istio-system/development',raw)

    def test_shared_defaults_have_no_development_hosts_or_gateway(self):
        docs=self.render()
        self.no_dev(docs)
        routes=[d for d in docs if d['kind']=='VirtualService']
        self.assertTrue(routes)
        self.assertTrue(all(r['spec']['gateways']==['internal'] for r in routes))

    def test_dev_generated_overlay_wins_over_old_saved_routes(self):
        source=(ROOT/'ci/deploy-crop-dev.sh').read_text(encoding='utf-8')
        keys=['REGISTRY_HOST','STAFF_API_HOST','PARTNER_API_HOST','STAFF_IAM_URL','COOKIE_DOMAIN','KEYCLOAK_URL','MINIO_HOST']
        lines=[line for line in source.splitlines() if any(line.startswith(key+'=') for key in keys)]
        heredoc=re.search(r'cat > "\$WORK/ci-public.yaml" <<EOF\n(.*?)\nEOF',source,re.S).group(1)
        snippet='\n'.join(lines)+'\nHELM_RELEASE=cropsown-registry\nHELM_NAMESPACE=crop\ncat <<EOF\n'+heredoc+'\nEOF\n'
        env={k:v for k,v in os.environ.items() if k not in keys}
        generated=subprocess.run([BASH],input=snippet,capture_output=True,text=True,encoding='utf-8',env=env,timeout=10,check=True)
        stale={'global':{'registryHostname':'crop-registry-development.oanstaging.com'},'registry':{
            key:{'istio':{'virtualservice':{'host':'old-development.oanstaging.com','gateway':'internal'}}}
            for key in ['staffUi','staffApi','partnerApi']}}
        docs=self.render(stale,yaml.safe_load(generated.stdout))
        self.assertEqual(guard.check({'kind':'List','items':docs},'crop','cropsown-registry','crop')['routingGuard'],'passed')

    def test_staging_values_control_every_public_route_and_cookie(self):
        values={'global':{'registryHostname':'crop-registry.staging.example',
            'keycloakBaseUrl':'https://keycloak.staging.example','minioHost':'minio.staging.example'},
            'registry':{'staffUi':{'istio':{'virtualservice':{'gateway':'staging/public'}},
                'iamPublicUrl':'https://iam.staging.example','partnerIngestUrl':'https://partner-crop.staging.example/partner/ingest_data',
                'envVars':{'COOKIE_DOMAIN':'.staging.example'}},
                'staffApi':{'hostname':'staff-crop.staging.example','istio':{'virtualservice':{'host':'staff-crop.staging.example','gateway':'staging/public'}}},
                'partnerApi':{'hostname':'partner-crop.staging.example','istio':{'virtualservice':{'host':'partner-crop.staging.example','gateway':'staging/public'}}}}}
        for namespace in ['crop','staging-crop']:
            docs=self.render(values,namespace=namespace);self.no_dev(docs)
            expected={'cropsown-registry-staff-portal-ui':'crop-registry.staging.example',
                'cropsown-registry-staff-portal-api':'staff-crop.staging.example',
                'cropsown-registry-partner-api':'partner-crop.staging.example'}
            routes={d['metadata']['name']:d['spec'] for d in docs if d['kind']=='VirtualService'}
            for name,host in expected.items():
                self.assertEqual(routes[name]['hosts'],[host])
                self.assertEqual(routes[name]['gateways'],['staging/public'])
            ui=next(d for d in docs if d['kind']=='Deployment' and d['metadata']['name']=='cropsown-registry-staff-portal-ui')
            env={e['name']:e.get('value') for e in ui['spec']['template']['spec']['containers'][0]['env']}
            self.assertEqual(env['COOKIE_DOMAIN'],'.staging.example')
            self.assertEqual(env['IAM_URL'],'https://iam.staging.example')
            self.assertEqual(env['APP_URL'],'https://crop-registry.staging.example')


if __name__=='__main__':unittest.main()
