from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from modelmint.library_config import load_library_config
from modelmint.scanner import load_scanner_status, run_scan_once, scanner_status_path


class ScannerTests(unittest.TestCase):
    def test_repeated_scan_is_idempotent_and_updates_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "incoming" / "Creator One" / "Release"
            release.mkdir(parents=True)
            (release / "Dragon.3mf").write_text("model", encoding="utf-8")
            (release / "preview.png").write_text("image", encoding="utf-8")
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

            first = run_scan_once(config)
            second = run_scan_once(config)

            catalog = json.loads((root / "data" / "catalog.json").read_text(encoding="utf-8"))
            self.assertEqual(first["new_models"], 1)
            self.assertEqual(second["new_models"], 0)
            self.assertEqual(len(catalog["models"]), 1)
            self.assertEqual(second["last_scan_result"], "Completed")

    def test_missing_incoming_path_is_reported_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = load_library_config(
                {
                    "MODEL_LIBRARY_PATH": str(root),
                    "INCOMING_RELEASES_PATH": "missing-incoming",
                    "APPROVED_CATALOG_PATH": "data/catalog.json",
                    "REPORTS_PATH": "reports",
                }
            )

            status = run_scan_once(config)

            self.assertIn("Skipped", status["last_scan_result"])
            self.assertIn("Missing incoming releases path", status["recent_errors"][0])
            self.assertTrue(scanner_status_path(config).exists())

    def test_report_and_scanner_status_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "incoming" / "Creator One" / "Release"
            release.mkdir(parents=True)
            (release / "Coaster.stl").write_text("model", encoding="utf-8")
            config = load_library_config(
                {
                    "MODEL_LIBRARY_PATH": str(root),
                    "INCOMING_RELEASES_PATH": "incoming",
                    "APPROVED_CATALOG_PATH": "data/catalog.json",
                    "REPORTS_PATH": "reports",
                }
            )

            run_scan_once(config)
            saved_status = load_scanner_status(config)

            self.assertTrue((root / "reports" / "intake-report.md").exists())
            self.assertTrue((root / "reports" / "scanner-status.json").exists())
            self.assertEqual(saved_status["last_scan_result"], "Completed")
            self.assertEqual(saved_status["new_assets"], 1)


if __name__ == "__main__":
    unittest.main()
