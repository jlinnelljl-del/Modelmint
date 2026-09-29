from __future__ import annotations

from typing import Any

from modelmint.shopify_adapter import require_real_shopify_variant
from modelmint.shopify_client import ShopifyConfig, create_cart, load_shopify_config
from modelmint.storefront_data import build_mock_cart_line


def create_shopify_cart_for_product(
    product: dict[str, Any],
    selections: dict[str, Any],
    config: ShopifyConfig | None = None,
) -> dict[str, Any]:
    active_config = config or load_shopify_config()
    cart_line = build_mock_cart_line(product, selections)
    require_real_shopify_variant(product)
    cart_input = cart_line["shopify_ready"]["cart_create_input"]["input"]
    cart = create_cart(active_config, cart_input)
    return {
        "checkoutUrl": cart["checkoutUrl"],
        "cart": cart,
        "cart_line": cart_line,
    }
