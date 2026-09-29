from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from modelmint.library_config import library_path_status, load_library_config, resolved_library_config


class LibraryConfigTests(unittest.TestCase):
    def test_env_paths_resolve_inside_library_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "MODEL_LIBRARY_PATH": tmp,
                "INCOMING_RELEASES_PATH": "Incoming Releases",
                "APPROVED_CATALOG_PATH": "catalog/approved.json",
                "REJECTED_ARCHIVE_PATH": "archive/rejected",
                "CUSTOM_ORDERS_PATH": "orders/custom.json",
                "REPORTS_PATH": "reports",
            }

            config = resolved_library_config(load_library_config(env))

            self.assertEqual(config.model_library_path, Path(tmp).resolve())
            self.assertEqual(config.incoming_releases_path, Path(tmp).resolve() / "Incoming Releases")
            self.assertEqual(config.approved_catalog_path, Path(tmp).resolve() / "catalog" / "approved.json")
            self.assertEqual(config.intake_report_path, Path(tmp).resolve() / "reports" / "intake-report.md")

    def test_status_reports_missing_and_existing_paths_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "incoming"
            incoming.mkdir()
            reports = root / "reports"
            reports.mkdir()
            catalog = root / "data" / "catalog.json"
            catalog.parent.mkdir()
            catalog.write_text("{}", encoding="utf-8")

            config = load_library_config(
                {
                    "MODEL_LIBRARY_PATH": str(root),
                    "INCOMING_RELEASES_PATH": "incoming",
                    "APPROVED_CATALOG_PATH": "data/catalog.json",
                    "REJECTED_ARCHIVE_PATH": "archive/rejected",
                    "CUSTOM_ORDERS_PATH": "orders/custom.json",
                    "REPORTS_PATH": "reports",
                }
            )

            status = library_path_status(config)
            by_env = {item["env_name"]: item for item in status["paths"]}

            self.assertFalse(status["ok"])
            self.assertTrue(by_env["MODEL_LIBRARY_PATH"]["exists"])
            self.assertTrue(by_env["INCOMING_RELEASES_PATH"]["exists"])
            self.assertTrue(by_env["APPROVED_CATALOG_PATH"]["exists"])
            self.assertFalse(by_env["REJECTED_ARCHIVE_PATH"]["exists"])
            self.assertFalse(by_env["CUSTOM_ORDERS_PATH"]["exists"])
            self.assertTrue(status["instructions"])


if __name__ == "__main__":
    unittest.main()
