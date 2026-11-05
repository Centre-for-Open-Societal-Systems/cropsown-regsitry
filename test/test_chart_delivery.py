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
