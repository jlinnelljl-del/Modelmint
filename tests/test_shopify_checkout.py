from __future__ import annotations

import unittest
from unittest.mock import patch

from modelmint.shopify_adapter import ShopifyVariantMappingError
from modelmint.shopify_checkout import create_shopify_cart_for_product
from modelmint.shopify_client import ShopifyConfig


class ShopifyCheckoutTests(unittest.TestCase):
    def test_todo_variant_is_blocked_before_shopify_call(self) -> None:
        product = {
            "handle": "crystal-dragon",
            "title": "Crystal Dragon",
            "price": "28.00",
            "images": [],
            "color_slot_count": 1,
            "allowed_finishes": ["matte"],
            "blocked_finishes": [],
        }
        config = ShopifyConfig("example.myshopify.com", "token", "2026-01")

        with patch("modelmint.shopify_checkout.create_cart") as create_cart:
            with self.assertRaises(ShopifyVariantMappingError):
                create_shopify_cart_for_product(product, {"Color 1": "Forest", "finish_preference": "matte"}, config)

        create_cart.assert_not_called()

    def test_configured_variant_reaches_mocked_shopify_client(self) -> None:
        product = {
            "handle": "crystal-dragon",
            "title": "Crystal Dragon",
            "price": "28.00",
            "images": [],
            "color_slot_count": 3,
            "allowed_finishes": ["silk"],
            "blocked_finishes": ["glow"],
            "shopify_variant_id": "gid://shopify/ProductVariant/123456789",
        }
        config = ShopifyConfig("example.myshopify.com", "token", "2026-01")

        with patch("modelmint.shopify_checkout.create_cart", return_value={"id": "gid://shopify/Cart/1", "checkoutUrl": "https://checkout.example"}) as create_cart:
            result = create_shopify_cart_for_product(
                product,
                {
                    "Color 1": "Forest",
                    "Color 2": "Galaxy",
                    "Color 3": "Artist Choice",
                    "finish_preference": "silk",
                    "Customer Notes": "Make it dramatic.",
                },
                config,
            )

        create_cart.assert_called_once()
        cart_input = create_cart.call_args.args[1]
        line = cart_input["lines"][0]
        self.assertEqual(line["merchandiseId"], "gid://shopify/ProductVariant/123456789")
        self.assertEqual(result["checkoutUrl"], "https://checkout.example")

    def test_invalid_finish_fails_before_shopify_client(self) -> None:
        product = {
            "handle": "extendable-katana",
            "title": "Extendable Katana",
            "price": "24.00",
            "images": [],
            "color_slot_count": 1,
            "allowed_finishes": ["matte"],
            "blocked_finishes": ["silk"],
            "shopify_variant_id": "gid://shopify/ProductVariant/999",
        }
        config = ShopifyConfig("example.myshopify.com", "token", "2026-01")

        with patch("modelmint.shopify_checkout.create_cart") as create_cart:
            with self.assertRaises(ValueError):
                create_shopify_cart_for_product(product, {"Color 1": "Classic", "finish_preference": "silk"}, config)

        create_cart.assert_not_called()


if __name__ == "__main__":
    unittest.main()
