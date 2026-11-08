"""One helper reads the Farmer-reference settings: new names first, old names as a fallback."""
import importlib
import logging
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

PACKAGE = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_cropsown_extension")
sys.modules.setdefault("openg2p_registry_extensions", importlib.import_module(PACKAGE))
configuration = importlib.import_module(PACKAGE + ".farmer_reference.configuration")
ROOT = Path(importlib.import_module(PACKAGE).__file__).parent


def clean_environment():
    return {key: value for key, value in os.environ.items()
            if not key.startswith(("REGISTRY_FARMER_REFERENCE_", "COSS_FARMER_"))}


class SettingTests(unittest.TestCase):
    def setUp(self):
        configuration._legacy_warned = False

    def test_the_new_name_wins_and_does_not_warn(self):
        env = {**clean_environment(), "REGISTRY_FARMER_REFERENCE_DCI_URL": "https://new", "COSS_FARMER_DCI_URL": "https://old"}
        with patch.dict(os.environ, env, clear=True), self.assertNoLogs(configuration._logger, logging.WARNING):
            self.assertEqual(configuration.setting("DCI_URL"), "https://new")

    def test_the_old_name_still_works_and_warns_once_per_process(self):
        env = {**clean_environment(), "COSS_FARMER_DCI_URL": "https://old", "COSS_FARMER_SENDER_ID": "sender"}
        with patch.dict(os.environ, env, clear=True), self.assertLogs(configuration._logger, logging.WARNING) as logged:
            self.assertEqual(configuration.setting("DCI_URL"), "https://old")
            self.assertEqual(configuration.setting("SENDER_ID"), "sender")
            self.assertEqual(configuration.setting("DCI_URL"), "https://old")
        self.assertEqual(len(logged.records), 1)

    def test_default_when_neither_is_set(self):
        with patch.dict(os.environ, clean_environment(), clear=True):
            self.assertIsNone(configuration.setting("SOURCE_ID"))
            self.assertEqual(configuration.setting("SIGNING_ALGORITHM", "RS256"), "RS256")

    def test_no_other_module_reads_these_variables(self):
        reads = []
        for path in ROOT.rglob("*.py"):
            if path.name == "configuration.py":
                continue
            if re.search(r"COSS_FARMER_|REGISTRY_FARMER_REFERENCE_", path.read_text(encoding="utf-8")):
                reads.append(path.name)
        self.assertEqual(reads, [])

    def test_lookup_configuration_uses_the_old_names_too(self):
        env = {**clean_environment(), "COSS_FARMER_DCI_URL": "https://old"}
        with patch.dict(os.environ, env, clear=True), self.assertRaises(configuration.FarmerReferenceError):
            configuration.configured_lookup()  # fails closed: the rest of the settings are absent


if __name__ == "__main__":
    unittest.main()
