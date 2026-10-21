"""Exercise the real manual deployment scripts with fake Helm/kubectl binaries.

No cluster, image registry or network calls are made. Fixtures copy scripts into
an isolated directory so dependency cleanup cannot touch checkout artifacts.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
BASH=shutil.which('bash')
if os.name=='nt':BASH=str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Git/bin/bash.exe')


def shellpath(path):
    path=Path(path).resolve().as_posix()
    return '/'+path[0].lower()+path[2:] if os.name=='nt' else path


@unittest.skipUnless(BASH and Path(BASH).exists(),'Bash is required')
class StagingValuesTests(unittest.TestCase):
    def exercise(self,mode='success',staging=True):
        with tempfile.TemporaryDirectory(prefix='crop-staging-values-') as temporary:
            root=Path(temporary);(root/'ci').mkdir();(root/'bin').mkdir();(root/'tmp').mkdir()
            chart=root/'helm/openg2p-cropsown-registry';chart.mkdir(parents=True)
            (chart/'Chart.yaml').write_text('apiVersion: v2\nname: test\nversion: 0.1.0\n')
            for name in ['deploy-dev.sh','deploy-staging.sh']:
                shutil.copyfile(ROOT/'ci'/name,root/'ci'/name);(root/'ci'/name).chmod(0o755)
            (root/'values.yaml').write_text('global:\n  registryHostname: crop-registry.staging.example\n  privateMarker: preserved\n')
            helm='''#!/usr/bin/env bash
set -eu
printf '%s|' "$@" >> "$TEST_LOG"; printf '\n' >> "$TEST_LOG"
if [ "${1:-}" = get ] && [ "${2:-}" = values ]; then
  case "$TEST_MODE" in missing) exit 1;; empty) exit 0;; esac
  case " $* " in *' --all '*) ;; *) exit 7;; esac
  cat "$TEST_VALUES"
elif [ "${1:-}" = upgrade ]; then
  while [ "$#" -gt 0 ]; do
    if [ "$1" = -f ]; then
      cp "$2" "$TEST_CAPTURE"; printf '%s' "$2" > "$TEST_SNAPSHOT"
      # mktemp must not expose complete release values to other users.
      if [ "$(uname -s)" != MINGW64_NT ] && command -v stat >/dev/null; then
        stat -c '%a' "$2" > "$TEST_MODE_FILE" || true
      fi
    fi
    shift
  done
elif [ "${1:-}" = version ]; then echo test-helm; fi
'''
            kubectl='''#!/usr/bin/env bash
set -eu
case "$*" in
 'config view '*) echo https://staging.example:6443;;
 'config current-context') echo staging-test;;
 *) echo ok;;
esac
'''
            for name,code in [('helm',helm),('kubectl',kubectl)]:
                p=root/'bin'/name;p.write_text(code,encoding='utf-8',newline='\n');p.chmod(0o755)
            env={k:v for k,v in os.environ.items() if k not in ['TAG','RELEASE_NAME','NAMESPACE','CHART_DIR','PRESERVE_RELEASE_VALUES','STAGING_RELEASE','STAGING_NAMESPACE']}
            env.update({'TEST_BIN':shellpath(root/'bin'),'TEST_SCRIPT':shellpath(root/'ci'/('deploy-staging.sh' if staging else 'deploy-dev.sh')),
                'TEST_LOG':shellpath(root/'calls.log'),'TEST_VALUES':shellpath(root/'values.yaml'),
                'TEST_CAPTURE':shellpath(root/'captured.yaml'),'TEST_SNAPSHOT':shellpath(root/'snapshot-path'),
                'TEST_MODE_FILE':shellpath(root/'snapshot-mode'),'TEST_MODE':mode,'TMPDIR':shellpath(root/'tmp'),
                'ECR_REGISTRY':'example.invalid','KUBECONFIG':'fake-kubeconfig'})
            # A caller cannot disable preservation through the staging wrapper.
            if staging:env['PRESERVE_RELEASE_VALUES']='false'
            r=subprocess.run([BASH,'-c','export PATH="$TEST_BIN:$PATH"; exec bash "$TEST_SCRIPT" staging-validation'],env=env,capture_output=True,text=True,encoding='utf-8',timeout=20)
            calls=(root/'calls.log').read_text() if (root/'calls.log').exists() else ''
            captured=(root/'captured.yaml').read_text() if (root/'captured.yaml').exists() else None
            permissions=(root/'snapshot-mode').read_text().strip() if (root/'snapshot-mode').exists() else None
            return r.returncode,calls,captured,list((root/'tmp').iterdir()),permissions

    def test_manual_staging_preserves_all_values_before_images(self):
        code,calls,values,remaining,permissions=self.exercise()
        self.assertEqual(code,0)
        self.assertIn('get|values|cropsown-registry|--namespace|crop|--all|-o|yaml|',calls)
        self.assertIn('registryHostname: crop-registry.staging.example',values)
        upgrade=next(line for line in calls.splitlines() if line.startswith('upgrade|'))
        self.assertLess(upgrade.index('|-f|'),upgrade.index('|--set|'))
        self.assertEqual(remaining,[])
        if os.name!='nt':self.assertEqual(permissions,'600')

    def test_missing_or_empty_staging_release_never_upgrades(self):
        for mode in ['missing','empty']:
            code,calls,values,remaining,_=self.exercise(mode)
            self.assertNotEqual(code,0)
            self.assertNotIn('upgrade|',calls)
            self.assertNotIn('dependency|build|',calls)
            self.assertIsNone(values)
            self.assertEqual(remaining,[])

    def test_generic_helper_retains_opt_in_behavior(self):
        code,calls,values,remaining,_=self.exercise(staging=False)
        self.assertEqual(code,0)
        self.assertNotIn('get|values|',calls)
        self.assertIn('upgrade|',calls)
        self.assertIsNone(values)
        self.assertEqual(remaining,[])


if __name__=='__main__':unittest.main()
