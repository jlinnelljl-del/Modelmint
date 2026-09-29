from __future__ import annotations

import unittest

from modelmint.shopify_adapter import build_cart_create_input, build_cart_create_variables, build_cart_line_input, build_cart_lines_add_input, product_variant_status


class ShopifyAdapterTests(unittest.TestCase):
    def test_cart_line_input_uses_placeholder_variant_and_attributes(self) -> None:
        product = {"handle": "crystal-dragon"}
        attributes = {
            "Color 1": "Forest",
            "Color 2": "Galaxy",
            "Color 3": "Artist Choice",
            "Finish Preference": "silk",
            "Customer Notes": "Make it dramatic.",
            "Product Rule Warnings": "Only validated finish options were shown for this product.",
        }

        line = build_cart_line_input(product, attributes)
        mapped_attributes = {item["key"]: item["value"] for item in line["attributes"]}

        self.assertEqual(line["merchandiseId"], "gid://shopify/ProductVariant/TODO-crystal-dragon")
        self.assertEqual(line["quantity"], 1)
        self.assertEqual(mapped_attributes["Color 1"], "Forest")
        self.assertEqual(mapped_attributes["Color 2"], "Galaxy")
        self.assertEqual(mapped_attributes["Color 3"], "Artist Choice")
        self.assertEqual(mapped_attributes["Finish Preference"], "silk")
        self.assertEqual(mapped_attributes["Customer Notes"], "Make it dramatic.")
        self.assertIn("Product Rule Warnings", mapped_attributes)

    def test_cart_line_input_uses_real_variant_when_present(self) -> None:
        product = {
            "handle": "crystal-dragon",
            "shopify_variant_id": "gid://shopify/ProductVariant/123456789",
        }

        line = build_cart_line_input(product, {"Finish Preference": "matte"}, quantity=2)

        self.assertEqual(line["merchandiseId"], "gid://shopify/ProductVariant/123456789")
        self.assertEqual(line["quantity"], 2)

    def test_cart_create_and_lines_add_shapes_are_separate(self) -> None:
        product = {"handle": "crystal-dragon"}
        attributes = {"Color 1": "Forest"}

        create_input = build_cart_create_input(product, attributes)
        add_input = build_cart_lines_add_input(product, attributes)

        self.assertIn("input", create_input)
        self.assertIn("lines", create_input["input"])
        self.assertIn("lines", add_input)
        self.assertIn("todo", add_input)

    def test_cart_create_variables_are_ready_for_storefront_api(self) -> None:
        variables = build_cart_create_variables({"handle": "crystal-dragon"}, {"Color 1": "Forest"})

        self.assertIn("lines", variables)
        self.assertEqual(variables["lines"][0]["attributes"][0]["key"], "Color 1")

    def test_product_variant_status_reports_placeholder_or_configured(self) -> None:
        placeholder = product_variant_status({"handle": "crystal-dragon", "title": "Crystal Dragon"})
        configured = product_variant_status(
            {
                "handle": "crystal-dragon",
                "title": "Crystal Dragon",
                "shopify_variant_id": "gid://shopify/ProductVariant/123",
            }
        )

        self.assertFalse(placeholder["variant_configured"])
        self.assertEqual(placeholder["variant_status"], "TODO placeholder")
        self.assertTrue(configured["variant_configured"])
        self.assertEqual(configured["variant_id"], "gid://shopify/ProductVariant/123")


if __name__ == "__main__":
    unittest.main()
