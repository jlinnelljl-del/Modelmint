from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from modelmint.intake import run_intake
from modelmint.web import catalog_snapshot, safe_asset_path, update_model, validate_bind_host


class WebTests(unittest.TestCase):
    def test_catalog_snapshot_joins_related_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "incoming"
            release = incoming / "Creator One" / "Release"
            release.mkdir(parents=True)
            (release / "Dragon.3mf").write_text("model", encoding="utf-8")
            (release / "preview.png").write_text("image", encoding="utf-8")

            catalog_path = root / "data" / "catalog.json"
            run_intake(incoming, catalog_path, root / "reports" / "intake-report.md", root)

            snapshot = catalog_snapshot(catalog_path)

            self.assertEqual(snapshot["stats"]["models"], 1)
            self.assertEqual(snapshot["stats"]["multi_color"], 1)
            self.assertEqual(snapshot["models"][0]["creator_name"], "Creator One")
            self.assertEqual(len(snapshot["models"][0]["preview_assets"]), 1)
            self.assertIsNotNone(snapshot["models"][0]["color_profile"])

    def test_update_model_saves_review_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "incoming"
            release = incoming / "Creator One" / "Release"
            release.mkdir(parents=True)
            (release / "Coaster.stl").write_text("model", encoding="utf-8")

            catalog_path = root / "data" / "catalog.json"
            run_intake(incoming, catalog_path, root / "reports" / "intake-report.md", root)
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            model_id = catalog["models"][0]["model_id"]

            update_model(
                catalog_path,
                model_id,
                {
                    "status": "Needs Test Print",
                    "category": "Home and Decor",
                    "production_notes": "Check cork backing fit.",
                    "ignored_field": "nope",
                },
            )

            updated = json.loads(catalog_path.read_text(encoding="utf-8"))["models"][0]
            self.assertEqual(updated["status"], "Needs Test Print")
            self.assertEqual(updated["production_notes"], "Check cork backing fit.")
            self.assertNotIn("ignored_field", updated)

    def test_update_model_rejects_unknown_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "incoming"
            release = incoming / "Creator One" / "Release"
            release.mkdir(parents=True)
            (release / "Coaster.stl").write_text("model", encoding="utf-8")

            catalog_path = root / "data" / "catalog.json"
            run_intake(incoming, catalog_path, root / "reports" / "intake-report.md", root)
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

            with self.assertRaises(ValueError):
                update_model(catalog_path, catalog["models"][0]["model_id"], {"status": "Auto Publish"})

    def test_safe_asset_path_blocks_non_media_and_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "incoming"
            incoming.mkdir()
            image = incoming / "preview.png"
            image.write_text("image", encoding="utf-8")
            model_file = incoming / "model.stl"
            model_file.write_text("model", encoding="utf-8")

            self.assertEqual(safe_asset_path("incoming/preview.png", root), image.resolve())
            with self.assertRaises(ValueError):
                safe_asset_path("incoming/model.stl", root)
            with self.assertRaises(ValueError):
                safe_asset_path("../outside.png", root)

    def test_bind_host_is_internal_by_default(self) -> None:
        validate_bind_host("127.0.0.1", False)
        validate_bind_host("localhost", False)
        validate_bind_host("0.0.0.0", True)
        with self.assertRaises(ValueError):
            validate_bind_host("0.0.0.0", False)


if __name__ == "__main__":
    unittest.main()
