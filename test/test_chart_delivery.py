"""The develop build deploys the chart it packaged and publishes that same archive."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = (ROOT / "ci/pipelines/dev.groovy").read_text(encoding="utf-8")


class ChartDeliveryTests(unittest.TestCase):
    def test_the_stages_run_in_order(self):
        order = [PIPELINE.index("stage('%s')" % name) for name in ("Build & Push", "Package chart", "Deploy", "Publish chart")]
        self.assertEqual(order, sorted(order))

    def test_the_deploy_installs_the_packaged_chart(self):
        deploy = PIPELINE.split("stage('Deploy')", 1)[1].split("stage('Update staging images')", 1)[0]
        self.assertIn("unstash 'built-chart'", deploy)
        self.assertEqual(deploy.count('BUILT_CHART_DIR="$PWD/built-chart"'), 2)

    def test_a_failed_deploy_publishes_nothing(self):
        publish = PIPELINE.split("stage('Publish chart')", 1)[1].split("\n    post {", 1)[0]
        self.assertIn("currentBuild.currentResult == 'SUCCESS'", publish)
        self.assertIn("unstash 'built-chart'", publish)

    def test_images_are_named_by_ci_image_names(self):
        build = PIPELINE.split("stage('Resolve version')", 1)[1].split("stage('Resolve connector image')", 1)[0]
        self.assertIn('python3 ci/image_names.py tag "$BRANCH_NAME" "$BUILD_NUMBER"', build)
        self.assertIn('REPOSITORY=$(python3 ci/image_names.py repository "${SVC}")', build)
        self.assertIn('IMAGE="${ECR_REGISTRY}/${REPOSITORY}"', build)

    def test_the_connector_actions_resolve_the_connector_images_of_ci_image_names(self):
        resolve = PIPELINE.split("stage('Resolve connector image')", 1)[1].split("stage('Stash deploy')", 1)[0]
        self.assertIn('sh(returnStdout: true, script: "python3 ci/image_names.py repository ${name}").trim()', resolve)
        self.assertNotIn("ECR_BASE", PIPELINE)

    def test_the_deploy_stash_carries_what_ci_image_names_reads(self):
        # The deploy node runs from this stash, and ci/image_names.py reads init.yaml and the chart's Chart.yaml.
        self.assertIn('stash name: \'deploy\', includes: "init.yaml,ci/**,.central-charts/**,.ecr-token,.ecr-registry,'
                      'helm/openg2p-cropsown-registry/Chart.yaml"', PIPELINE)

    def test_every_pushed_repository_gets_the_standard_ecr_settings_first(self):
        self.assertIn('python3 ci/ecr_repository.py ensure "$2" "$(python3 ci/image_names.py legacy "$1")"', PIPELINE)
        self.assertNotIn("create-repository", PIPELINE)        # only ci/ecr_repository.py creates repositories
        for call in ('ensure_repository "${SVC}" "${REPOSITORY}"', 'ensure_repository dashboard-ui "${DASHBOARD_UI_ECR}"',
                     'ensure_repository dashboard-api "${DASHBOARD_API_ECR}"'):
            self.assertIn(call, PIPELINE)
        self.assertLess(PIPELINE.index('ensure_repository "${SVC}"'), PIPELINE.index('docker push "${IMAGE}:${IMAGE_TAG}"'))
        self.assertIn("credentialsId: 'aws-ecr-creds'", PIPELINE)
        self.assertIn("python3 -m unittest discover -s test -p test_ecr_repository.py -v", PIPELINE)

    def test_tags_are_immutable_so_nothing_pushes_a_moving_tag(self):
        self.assertNotIn("${IMAGE}:${BRANCH_NAME}", PIPELINE)
        self.assertNotIn("--cache-from", PIPELINE)
        self.assertIn('UI_IMAGE="${ECR_REGISTRY}/${DASHBOARD_UI_ECR}:${IMAGE_TAG}"', PIPELINE)
        self.assertIn("DASHBOARD_API_ECR = 'eoan/cropsown-registry/dashboard-api'", PIPELINE)
        self.assertIn("DASHBOARD_UI_ECR = 'eoan/cropsown-registry/dashboard-ui'", PIPELINE)

    def test_the_connector_actions_take_the_pinned_build_and_digests(self):
        import json, re, subprocess, sys
        pin = json.loads((ROOT / "ci/deploy/connector-image.newdev.json").read_text(encoding="utf-8"))
        self.assertRegex(pin["tag"], r"^\d+\.\d+\.\d+-develop\.[1-9]\d*$")       # a build tag, never a moving one
        self.assertEqual(sorted(pin["digests"]), ["registry-connector-api", "registry-connector-ui"])
        for name, digest in pin["digests"].items():
            self.assertRegex(digest, r"^sha256:[0-9a-f]{64}$")
            done = subprocess.run([sys.executable, str(ROOT / "ci/deploy/connector_image.py"), name],
                                  stdout=subprocess.PIPE, universal_newlines=True, check=True)
            self.assertEqual(done.stdout.strip(), digest)
        self.assertIn('python3 ci/deploy/connector_image.py ${field}', PIPELINE)
        self.assertIn("is ${digest} in ECR, not the pinned ${pinned}", PIPELINE)
        self.assertNotIn("CONNECTOR_IMAGE_TAG", PIPELINE)
        self.assertNotIn("CONNECTOR_IMAGE_TAG", (ROOT / "ci/pipelines/operator.groovy").read_text(encoding="utf-8"))

    def test_every_build_tests_the_image_names(self):
        self.assertIn("python3 -m unittest discover -s test -p test_image_names.py -v", PIPELINE)
        self.assertIn("python3 -m unittest discover -s test -p test_image_name_scripts.py -v", PIPELINE)
        self.assertNotIn("openg2p/cropsown-registry/*", PIPELINE)

    def test_every_chart_image_is_recorded(self):
        for path in ("staffApi", "staffUi", "partnerApi", "celeryWorker", "celeryBeat", "dbSeed", "sanity"):
            self.assertIn("record_image registry.%s.image" % path, PIPELINE)
        self.assertIn("record_image dashboardApi.image", PIPELINE)
        self.assertIn("record_image dashboardUi.image", PIPELINE)

    def test_the_chart_has_no_fixed_version_and_no_old_image_paths(self):
        chart = ROOT / "helm/openg2p-cropsown-registry"
        self.assertIn("version: 0.0.0\n", (chart / "Chart.yaml").read_text(encoding="utf-8"))
        self.assertNotIn("/gen2/", (chart / "values.yaml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
