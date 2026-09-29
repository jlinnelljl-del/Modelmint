from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from modelmint.intake import relative_or_absolute, run_intake, slugify, stable_id


class IntakeTests(unittest.TestCase):
    def test_scans_release_and_preserves_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "incoming"
            release = incoming / "Creator One" / "2026-05 Release"
            images = release / "images"
            supported = release / "supported"
            images.mkdir(parents=True)
            supported.mkdir(parents=True)

            model_file = release / "Widget Dragon.3mf"
            preview_file = images / "preview.jpg"
            supported_file = supported / "Widget Dragon supported.stl"
            model_file.write_text("model", encoding="utf-8")
            preview_file.write_text("image", encoding="utf-8")
            supported_file.write_text("model", encoding="utf-8")

            catalog_path = root / "data" / "catalog.json"
            report_path = root / "reports" / "intake-report.md"
            summary = run_intake(incoming, catalog_path, report_path, root)

            self.assertEqual(summary["created_creators"], 1)
            self.assertEqual(summary["created_releases"], 1)
            self.assertEqual(summary["created_models"], 1)
            self.assertTrue(model_file.exists())
            self.assertTrue(preview_file.exists())
            self.assertTrue(supported_file.exists())

            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            self.assertEqual(catalog["schema_version"], 2)
            self.assertEqual(catalog["models"][0]["status"], "Needs Review")
            self.assertEqual(catalog["models"][0]["review_status"], "Needs Review")
            self.assertEqual(catalog["models"][0]["color_slot_count"], 3)
            self.assertEqual(len(catalog["color_profiles"]), 1)
            self.assertEqual(catalog["color_profiles"][0]["color_slot_count"], 3)
            self.assertGreaterEqual(len(catalog["assets"]), 3)
            self.assertIn("Source files were not renamed", report_path.read_text(encoding="utf-8"))

    def test_second_run_detects_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "incoming"
            release = incoming / "Creator One" / "Release"
            release.mkdir(parents=True)
            (release / "Coaster.stl").write_text("model", encoding="utf-8")

            catalog_path = root / "data" / "catalog.json"
            report_path = root / "reports" / "intake-report.md"
            first = run_intake(incoming, catalog_path, report_path, root)
            second = run_intake(incoming, catalog_path, report_path, root)

            self.assertEqual(first["created_models"], 1)
            self.assertEqual(second["created_models"], 0)
            self.assertEqual(second["duplicate_models"], 1)

    def test_primary_file_can_change_without_duplicating_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "incoming"
            release = incoming / "Creator One" / "Release"
            release.mkdir(parents=True)
            stl_file = release / "Widget Dragon.stl"
            stl_file.write_text("model", encoding="utf-8")

            catalog_path = root / "data" / "catalog.json"
            report_path = root / "reports" / "intake-report.md"
            run_intake(incoming, catalog_path, report_path, root)

            three_mf_file = release / "Widget Dragon.3mf"
            three_mf_file.write_text("model", encoding="utf-8")
            summary = run_intake(incoming, catalog_path, report_path, root)

            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["created_models"], 0)
            self.assertEqual(summary["duplicate_models"], 1)
            self.assertEqual(len(catalog["models"]), 1)
            self.assertEqual(catalog["models"][0]["primary_file_path"], "incoming/Creator One/Release/Widget Dragon.3mf")
            self.assertTrue(catalog["models"][0]["multi_color"])
            self.assertEqual(len(catalog["color_profiles"]), 1)

    def test_legacy_path_based_model_id_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "incoming"
            release = incoming / "Creator One" / "Release"
            release.mkdir(parents=True)
            model_file = release / "Coaster.stl"
            model_file.write_text("model", encoding="utf-8")

            catalog_path = root / "data" / "catalog.json"
            report_path = root / "reports" / "intake-report.md"
            catalog_path.parent.mkdir(parents=True)
            creator_id = stable_id("creator", slugify("Creator One"))
            release_id = stable_id("release", creator_id, relative_or_absolute(release, root))
            catalog_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "creators": [
                            {
                                "creator_id": creator_id,
                                "creator_name": "Creator One",
                                "source_platform": "",
                                "commercial_license_status": "Unknown",
                                "license_notes": "",
                                "active_status": "Active",
                                "default_attribution_text": "",
                                "notes": "",
                            }
                        ],
                        "releases": [
                            {
                                "release_id": release_id,
                                "creator_id": creator_id,
                                "release_name": "Release",
                                "release_date": "",
                                "source_folder_path": "incoming/Creator One/Release",
                                "intake_status": "Needs Review",
                                "notes": "",
                            }
                        ],
                        "models": [
                            {
                                "model_id": "model_legacy_path_based",
                                "release_id": release_id,
                                "creator_id": creator_id,
                                "model_name": "Coaster",
                                "source_folder_path": "incoming/Creator One/Release",
                                "primary_file_path": "incoming/Creator One/Release/Coaster.stl",
                                "model_type": "Coaster",
                                "category": "Home and Decor",
                                "subcategory": "",
                                "status": "Needs Review",
                                "review_status": "Needs Review",
                                "license_status": "Unknown",
                                "attribution_required": True,
                                "estimated_complexity": "Unknown",
                                "multi_color": False,
                                "color_slot_count": 0,
                                "production_notes": "",
                                "artisan_notes": "",
                                "created_at": "2026-05-17T00:00:00+00:00",
                                "updated_at": "2026-05-17T00:00:00+00:00",
                            }
                        ],
                        "assets": [],
                        "color_profiles": [],
                        "material_finish_rules": [],
                        "custom_orders": [],
                    }
                ),
                encoding="utf-8",
            )

            summary = run_intake(incoming, catalog_path, report_path, root)
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["created_models"], 0)
            self.assertEqual(summary["duplicate_models"], 1)
            self.assertEqual(len(catalog["models"]), 1)
            self.assertEqual(catalog["models"][0]["model_id"], "model_legacy_path_based")


if __name__ == "__main__":
    unittest.main()
