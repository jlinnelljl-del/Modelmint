from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from modelmint.storefront import StorefrontHandler
from modelmint.storefront_data import (
    append_quote_request,
    build_line_item_attributes,
    build_mock_cart_line,
    product_by_handle,
    storefront_payload,
    validate_quote_request,
    valid_finish_for_product,
)


class StorefrontTests(unittest.TestCase):
    def test_payload_contains_sample_products_and_shopify_env_docs(self) -> None:
        payload = storefront_payload()

        self.assertGreaterEqual(len(payload["products"]), 3)
        self.assertFalse(payload["shopify"]["cart_checkout_enabled"])
        self.assertIn("SHOPIFY_STORE_DOMAIN", payload["shopify"]["required_env"])
        self.assertIn("SHOPIFY_API_VERSION", payload["shopify"]["required_env"])

    def test_finish_rules_block_invalid_cart_attributes(self) -> None:
        product = product_by_handle("extendable-katana")
        self.assertIsNotNone(product)
        assert product is not None

        self.assertTrue(valid_finish_for_product(product, "matte"))
        self.assertFalse(valid_finish_for_product(product, "silk"))

        with self.assertRaises(ValueError):
            build_line_item_attributes(product, {"Color 1": "Classic", "finish_preference": "silk"})

    def test_cart_attributes_preserve_color_finish_and_notes(self) -> None:
        product = product_by_handle("crystal-dragon")
        self.assertIsNotNone(product)
        assert product is not None

        attributes = build_line_item_attributes(
            product,
            {
                "Color 1": "Forest",
                "Color 2": "Galaxy",
                "Color 3": "Artist Choice",
                "finish_preference": "silk",
                "Customer Notes": "Prefer green as the main color.",
            },
        )

        self.assertEqual(attributes["Color 1"], "Forest")
        self.assertEqual(attributes["Color 3"], "Artist Choice")
        self.assertEqual(attributes["Finish Preference"], "silk")
        self.assertEqual(attributes["Customer Notes"], "Prefer green as the main color.")
        self.assertIn("Product Rule Warnings", attributes)

    def test_mock_cart_line_preserves_shopify_ready_attributes(self) -> None:
        product = product_by_handle("crystal-dragon")
        self.assertIsNotNone(product)
        assert product is not None

        line = build_mock_cart_line(
            product,
            {
                "Color 1": "Forest",
                "Color 2": "Galaxy",
                "Color 3": "Artist Choice",
                "finish_preference": "silk",
                "Customer Notes": "Make it dramatic.",
            },
        )

        self.assertEqual(line["product_handle"], "crystal-dragon")
        self.assertEqual(line["quantity"], 1)
        self.assertEqual(line["selections"]["Color 2"], "Galaxy")
        self.assertEqual(line["line_item_attributes"]["Color 1"], "Forest")
        self.assertEqual(line["line_item_attributes"]["Finish Preference"], "silk")
        self.assertEqual(line["shopify_ready"]["line_item_attributes"], line["line_item_attributes"])
        shopify_line = line["shopify_ready"]["cart_lines_add_input"]["lines"][0]
        self.assertIn("TODO-crystal-dragon", shopify_line["merchandiseId"])
        self.assertEqual(shopify_line["quantity"], 1)
        shopify_attributes = {item["key"]: item["value"] for item in shopify_line["attributes"]}
        self.assertEqual(shopify_attributes["Color 1"], "Forest")
        self.assertEqual(shopify_attributes["Color 2"], "Galaxy")
        self.assertEqual(shopify_attributes["Color 3"], "Artist Choice")
        self.assertEqual(shopify_attributes["Finish Preference"], "silk")
        self.assertEqual(shopify_attributes["Customer Notes"], "Make it dramatic.")
        self.assertIn("Product Rule Warnings", shopify_attributes)

    def test_mock_cart_line_rejects_manual_invalid_finish(self) -> None:
        product = product_by_handle("extendable-katana")
        self.assertIsNotNone(product)
        assert product is not None

        with self.assertRaises(ValueError):
            build_mock_cart_line(product, {"Color 1": "Classic", "finish_preference": "silk"})

    def test_quote_request_validation_and_persistence(self) -> None:
        payload = {
            "customer_name": "Jamie",
            "email": "jamie@example.com",
            "phone": "",
            "business_event_name": "North Taproom",
            "order_type": "branded coasters",
            "target_quantity": "48",
            "deadline": "2026-07-01",
            "budget_range": "$200-$400",
            "logo_artwork_note": "Vector logo available.",
            "notes": "Two-color coaster set with cork backs.",
            "fulfillment_preference": "Local pickup",
        }

        self.assertTrue(validate_quote_request(payload).valid)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quote-requests.json"
            record = append_quote_request(path, payload)
            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(record["quote_status"], "Needs Review")
        self.assertEqual(record["production_status"], "Not Started")
        self.assertEqual(saved[0]["target_quantity"], 48)

    def test_quote_request_rejects_bad_required_fields(self) -> None:
        result = validate_quote_request({"email": "bad", "target_quantity": "0"})

        self.assertFalse(result.valid)
        self.assertIn("customer_name", result.errors)
        self.assertIn("email_format", result.errors)
        self.assertIn("target_quantity_positive", result.errors)

    def test_storefront_routes_include_suggested_pages(self) -> None:
        self.assertTrue(StorefrontHandler.is_app_route("/shop"))
        self.assertTrue(StorefrontHandler.is_app_route("/shop/crystal-dragon"))
        self.assertTrue(StorefrontHandler.is_app_route("/cart"))
        self.assertTrue(StorefrontHandler.is_app_route("/custom-orders"))
        self.assertTrue(StorefrontHandler.is_app_route("/business"))
        self.assertTrue(StorefrontHandler.is_app_route("/events"))
        self.assertTrue(StorefrontHandler.is_app_route("/new"))
        self.assertTrue(StorefrontHandler.is_app_route("/about"))
        self.assertTrue(StorefrontHandler.is_app_route("/contact"))
        self.assertTrue(StorefrontHandler.is_app_route("/dev/shopify-status"))


if __name__ == "__main__":
    unittest.main()
