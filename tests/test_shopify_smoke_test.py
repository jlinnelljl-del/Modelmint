from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from modelmint.shopify_smoke_test import build_known_valid_cart_line, run_smoke_test


class ShopifySmokeTestTests(unittest.TestCase):
    def test_build_known_valid_cart_line_uses_shopify_ready_attributes(self) -> None:
        line = build_known_valid_cart_line()

        self.assertEqual(line["product_handle"], "crystal-dragon")
        self.assertEqual(line["line_item_attributes"]["Color 1"], "Forest")
        self.assertEqual(line["line_item_attributes"]["Color 2"], "Galaxy")
        self.assertEqual(line["line_item_attributes"]["Color 3"], "Artist Choice")
        self.assertEqual(line["line_item_attributes"]["Finish Preference"], "silk")
        self.assertIn("Product Rule Warnings", line["line_item_attributes"])

    def test_dry_run_reports_missing_setup_without_calling_shopify_or_printing_token(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("modelmint.shopify_smoke_test.create_cart") as create_cart:
            exit_code = run_smoke_test(env={}, stdout=stdout, stderr=stderr)

        output = stdout.getvalue()
        self.assertEqual(exit_code, 2)
        create_cart.assert_not_called()
        self.assertIn("Dry run complete. No Shopify API call was made.", output)
        self.assertIn("FAIL: Sample product still has a missing/TODO Shopify variant GID.", output)
        self.assertIn("Missing Shopify Storefront API configuration", output)
        self.assertNotIn("secret-token-value", output)
        self.assertEqual(stderr.getvalue(), "")

    def test_dry_run_with_configured_variant_is_ready_without_calling_shopify(self) -> None:
        product = {
            "handle": "crystal-dragon",
            "title": "Crystal Dragon",
            "price": "28.00",
            "images": [],
            "customizable": True,
            "color_slot_count": 3,
            "allowed_finishes": ["matte", "standard", "silk"],
            "blocked_finishes": ["glow"],
            "shopify_variant_id": "gid://shopify/ProductVariant/123456789",
        }
        env = {
            "SHOPIFY_STORE_DOMAIN": "https://example.myshopify.com/",
            "SHOPIFY_STOREFRONT_ACCESS_TOKEN": "secret-token-value",
            "SHOPIFY_API_VERSION": "2026-01",
        }
        stdout = io.StringIO()

        with patch("modelmint.shopify_smoke_test.product_by_handle", return_value=product):
            with patch("modelmint.shopify_smoke_test.create_cart") as create_cart:
                exit_code = run_smoke_test(env=env, stdout=stdout)

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        create_cart.assert_not_called()
        self.assertIn("PASS: Shopify env vars are present.", output)
        self.assertIn("PASS: Sample product has a configured Shopify variant GID.", output)
        self.assertIn("Store domain: example.myshopify.com", output)
        self.assertNotIn("secret-token-value", output)


if __name__ == "__main__":
    unittest.main()
