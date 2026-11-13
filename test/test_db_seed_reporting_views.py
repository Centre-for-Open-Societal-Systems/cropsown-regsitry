"""The db-seed image must carry the reporting views the Helm hook applies."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "docker" / "db-seed"


class DbSeedReportingViewsTests(unittest.TestCase):
    def test_dockerfile_copies_reporting_views_after_seed_cleanup(self):
        text = (SEED / "Dockerfile").read_text()
        copy = "COPY docker/db-seed/reporting_views.sql /seed/reporting_views.sql"
        self.assertIn(copy, text)
        self.assertGreater(text.index(copy), text.index("rm -rf /seed/"))

    def test_reporting_views_are_idempotent_and_named_for_dashboard(self):
        sql = (SEED / "reporting_views.sql").read_text()
        for view in ("cs_rpt_crop_sown", "cs_rpt_sowing"):
            self.assertIn(f"DROP MATERIALIZED VIEW IF EXISTS {view}", sql)
            self.assertIn(f"CREATE MATERIALIZED VIEW {view}", sql)
        self.assertNotIn("\r", sql)
        for line in sql.splitlines():
            if line.startswith("CREATE") and "INDEX" in line:
                self.assertIn("IF NOT EXISTS", line)

    def test_the_hook_waits_for_every_table_the_views_read(self):
        # Crop staging 33: the hook waited only for g2p_register_cultivations, which an older register
        # already has, and then failed on g2p_attribute_values before staff-api had migrated.
        import re
        sql = (SEED / "reporting_views.sql").read_text()
        hook = (ROOT / "helm/openg2p-cropsown-registry/templates/reporting-views.yaml").read_text()
        for table in sorted(set(re.findall(r"\b(?:FROM|JOIN)\s+(g2p_\w+)", sql))):
            self.assertIn("'" + table + "'", hook, table)

    def test_the_views_do_not_need_the_legacy_attribute_table(self):
        # Crop staging 53: a register installed on the current platform has no g2p_attribute_values, so the
        # hook waited for it until it gave up. Labels go through cs_rpt_attribute_labels, empty without it.
        sql = (SEED / "reporting_views.sql").read_text()
        hook = (ROOT / "helm/openg2p-cropsown-registry/templates/reporting-views.yaml").read_text()
        self.assertNotIn("JOIN g2p_attribute_values", sql)
        self.assertIn("to_regclass('public.g2p_attribute_values') IS NOT NULL", sql)
        self.assertIn("WHERE false", sql)
        self.assertNotIn("'g2p_attribute_values'", hook)
        self.assertLess(sql.index("CREATE VIEW cs_rpt_attribute_labels"), sql.index("CREATE MATERIALIZED VIEW cs_rpt_crop_sown"))


if __name__ == "__main__":
    unittest.main()
