"""The deploy scripts name the registry images with ci/image_names.py, never with a path of their own.

Standard library only (runs on the Jenkins agent's stock Python).
    python3 -m unittest discover -s test -p test_image_name_scripts.py -v
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def script(path):
    return (ROOT / path).read_text(encoding="utf-8")


class ImageNameScriptTests(unittest.TestCase):
    def test_the_dev_deploy_resolves_every_image_before_it_changes_anything(self):
        deploy = script("ci/deploy-crop-dev.sh")
        self.assertNotIn("ECR_BASE", deploy)
        for component in ("staff-api", "staff-ui", "partner-api", "celery", "db-seed", "sanity-tests"):
            self.assertIn("image: {repository: '${IMAGE[%s]}', tag: '${TAG}'}" % component, deploy)

    def test_the_staging_image_update_takes_the_repositories_of_ci_image_names(self):
        staging = script("ci/staging-set-images.sh")
        self.assertNotIn("openg2p/cropsown-registry", staging)
        self.assertIn('IMG="${ECR_HOST}/$(python3 ci/image_names.py repository "${PAIR#*=}"):${TAG}"', staging)

    def test_the_staging_seed_runs_the_db_seed_image_of_ci_image_names(self):
        seed = script("ci/staging-run-db-seed.sh")
        self.assertNotIn("openg2p/cropsown-registry", seed)
        self.assertIn('SEED_REPOSITORY="$(python3 ci/image_names.py repository db-seed)"', seed)

    def test_the_staging_connector_follows_the_platform_suffix_and_the_build_tag_of_staff_api(self):
        upgrade = script("ci/deploy/upgrade-crop-connector-staging.sh")
        self.assertIn("BUILD_TAG_PATTERN='^([0-9]+\\.[0-9]+\\.[0-9]+-develop\\.[0-9]+|develop-[0-9]+)$'", upgrade)
        # registry-connector-api/-ui (no suffix) first, then the suffixed names of the builds before init.yaml.
        self.assertIn('CONNECTOR_NAMES="registry-connector-api:registry-connector-ui '
                      'registry-connector$PLATFORM_SUFFIX:registry-connector-ui$PLATFORM_SUFFIX"', upgrade)
        self.assertIn('CONNECTOR_IMAGE_REPOSITORY="$IMAGE_PREFIX/${names%%:*}"', upgrade)
        self.assertIn('ecr_digest "$ECR_BASE/${names#*:}" "$tag"', upgrade)


if __name__ == "__main__":
    unittest.main()
