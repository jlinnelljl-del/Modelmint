from __future__ import annotations

import unittest
from unittest.mock import patch

from modelmint.shopify_client import ShopifyAPIError, ShopifyConfigError, ShopifyConfig, create_cart, load_shopify_config, shopify_debug_status, shopify_status


class ShopifyClientTests(unittest.TestCase):
    def test_missing_config_is_reported_gracefully(self) -> None:
        with self.assertRaises(ShopifyConfigError):
            load_shopify_config({})

        status = shopify_status({})
        self.assertFalse(status["configured"])
        self.assertIn("SHOPIFY_STORE_DOMAIN", status["message"])

    def test_config_normalizes_store_domain(self) -> None:
        config = load_shopify_config(
            {
                "SHOPIFY_STORE_DOMAIN": "https://example.myshopify.com/",
                "SHOPIFY_STOREFRONT_ACCESS_TOKEN": "token",
                "SHOPIFY_API_VERSION": "2026-01",
            }
        )

        self.assertEqual(config.store_domain, "example.myshopify.com")
        self.assertEqual(config.endpoint, "https://example.myshopify.com/api/2026-01/graphql.json")

    def test_debug_status_never_exposes_token(self) -> None:
        status = shopify_debug_status(
            [{"handle": "crystal-dragon", "title": "Crystal Dragon", "shopify_variant_id": ""}],
            {
                "SHOPIFY_STORE_DOMAIN": "example.myshopify.com",
                "SHOPIFY_STOREFRONT_ACCESS_TOKEN": "super-secret-token",
                "SHOPIFY_API_VERSION": "2026-01",
            },
        )

        rendered = str(status)
        self.assertTrue(status["configured"])
        self.assertFalse(status["token_visible"])
        self.assertNotIn("super-secret-token", rendered)
        self.assertEqual(status["products"][0]["variant_status"], "TODO placeholder")

    def test_create_cart_returns_checkout_url_from_mocked_response(self) -> None:
        config = ShopifyConfig("example.myshopify.com", "token", "2026-01")
        captured = {}

        def fake_execute(received_config, query, variables):
            captured["config"] = received_config
            captured["query"] = query
            captured["variables"] = variables
            return {
                "data": {
                    "cartCreate": {
                        "cart": {
                            "id": "gid://shopify/Cart/abc",
                            "checkoutUrl": "https://example.myshopify.com/checkouts/abc",
                        },
                        "userErrors": [],
                    }
                }
            }

        with patch("modelmint.shopify_client.execute_storefront_graphql", fake_execute):
            cart = create_cart(config, {"lines": [{"merchandiseId": "gid://shopify/ProductVariant/1", "quantity": 1}]})

        self.assertEqual(cart["checkoutUrl"], "https://example.myshopify.com/checkouts/abc")
        self.assertEqual(captured["config"], config)
        self.assertIn("cartCreate", captured["query"])
        self.assertEqual(captured["variables"]["input"]["lines"][0]["quantity"], 1)

    def test_create_cart_surfaces_user_errors(self) -> None:
        config = ShopifyConfig("example.myshopify.com", "token", "2026-01")

        def fake_execute(_config, _query, _variables):
            return {
                "data": {
                    "cartCreate": {
                        "cart": None,
                        "userErrors": [{"field": ["lines"], "message": "Merchandise is invalid"}],
                    }
                }
            }

        with patch("modelmint.shopify_client.execute_storefront_graphql", fake_execute):
            with self.assertRaises(ShopifyAPIError):
                create_cart(config, {"lines": []})


if __name__ == "__main__":
    unittest.main()
