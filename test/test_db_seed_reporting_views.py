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


if __name__ == "__main__":
    unittest.main()
