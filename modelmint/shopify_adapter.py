from __future__ import annotations

from typing import Any


SHOPIFY_VARIANT_TODO = "TODO: replace with real Shopify Storefront API merchandiseId / product variant ID."


class ShopifyVariantMappingError(RuntimeError):
    pass


def product_variant_placeholder(product: dict[str, Any]) -> str:
    variant_id = str(product.get("shopify_variant_id", "")).strip()
    if variant_id:
        return variant_id
    handle = str(product.get("handle", "unknown-product")).strip() or "unknown-product"
    return f"gid://shopify/ProductVariant/TODO-{handle}"


def product_has_real_shopify_variant(product: dict[str, Any]) -> bool:
    variant_id = str(product.get("shopify_variant_id", "")).strip()
    return bool(variant_id) and "TODO" not in variant_id


def product_variant_status(product: dict[str, Any]) -> dict[str, Any]:
    variant_id = product_variant_placeholder(product)
    configured = product_has_real_shopify_variant(product)
    return {
        "handle": product.get("handle", ""),
        "title": product.get("title", ""),
        "variant_configured": configured,
        "variant_status": "configured" if configured else "TODO placeholder",
        "variant_id": variant_id if configured else "",
    }


def require_real_shopify_variant(product: dict[str, Any]) -> None:
    if not product_has_real_shopify_variant(product):
        handle = product.get("handle", "unknown-product")
        raise ShopifyVariantMappingError(f"Shopify checkout requires a real variant GID for sample product: {handle}")


def line_item_attributes_to_shopify(attributes: dict[str, str]) -> list[dict[str, str]]:
    return [{"key": key, "value": value} for key, value in attributes.items() if str(value).strip()]


def build_cart_line_input(product: dict[str, Any], attributes: dict[str, str], quantity: int = 1) -> dict[str, Any]:
    return {
        "merchandiseId": product_variant_placeholder(product),
        "quantity": quantity,
        "attributes": line_item_attributes_to_shopify(attributes),
    }


def build_cart_lines_add_input(product: dict[str, Any], attributes: dict[str, str], quantity: int = 1) -> dict[str, Any]:
    return {
        "lines": [build_cart_line_input(product, attributes, quantity)],
        "todo": SHOPIFY_VARIANT_TODO,
    }


def build_cart_create_input(product: dict[str, Any], attributes: dict[str, str], quantity: int = 1) -> dict[str, Any]:
    return {
        "input": {
            "lines": [build_cart_line_input(product, attributes, quantity)],
        },
        "todo": SHOPIFY_VARIANT_TODO,
    }


def build_cart_create_variables(product: dict[str, Any], attributes: dict[str, str], quantity: int = 1) -> dict[str, Any]:
    return build_cart_create_input(product, attributes, quantity)["input"]
