from __future__ import annotations

import argparse
import json
import sys
from typing import Any, TextIO

from modelmint.shopify_adapter import product_variant_status
from modelmint.shopify_client import ShopifyAPIError, ShopifyConfigError, create_cart, load_shopify_config
from modelmint.storefront_data import build_mock_cart_line, product_by_handle


DEFAULT_PRODUCT_HANDLE = "crystal-dragon"
DEFAULT_SELECTIONS = {
    "Color 1": "Forest",
    "Color 2": "Galaxy",
    "Color 3": "Artist Choice",
    "finish_preference": "silk",
    "Customer Notes": "Smoke test customization payload.",
}


def build_known_valid_cart_line(product_handle: str = DEFAULT_PRODUCT_HANDLE) -> dict[str, Any]:
    product = product_by_handle(product_handle)
    if not product:
        raise ValueError(f"Unknown sample product: {product_handle}")
    return build_mock_cart_line(product, DEFAULT_SELECTIONS)


def run_smoke_test(
    *,
    live: bool = False,
    product_handle: str = DEFAULT_PRODUCT_HANDLE,
    env: dict[str, str] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    product = product_by_handle(product_handle)
    if not product:
        print(f"FAIL: Unknown sample product: {product_handle}", file=stderr)
        return 2

    print("ModelMint Shopify smoke test", file=stdout)
    print(f"Product: {product['title']} ({product['handle']})", file=stdout)

    cart_line = build_mock_cart_line(product, DEFAULT_SELECTIONS)
    cart_input = cart_line["shopify_ready"]["cart_create_input"]["input"]
    print("PASS: Built known valid local customization payload.", file=stdout)
    print("Line item attributes:", file=stdout)
    for key, value in cart_line["line_item_attributes"].items():
        print(f"  - {key}: {value}", file=stdout)

    status = product_variant_status(product)
    variant_ready = bool(status["variant_configured"])
    if variant_ready:
        print("PASS: Sample product has a configured Shopify variant GID.", file=stdout)
    else:
        print("FAIL: Sample product still has a missing/TODO Shopify variant GID.", file=stdout)

    try:
        config = load_shopify_config(env)
    except ShopifyConfigError as error:
        config = None
        print(f"FAIL: {error}", file=stdout)
    else:
        print("PASS: Shopify env vars are present.", file=stdout)
        print(f"Store domain: {config.store_domain}", file=stdout)
        print(f"API version: {config.api_version}", file=stdout)

    if not live:
        print("Dry run complete. No Shopify API call was made.", file=stdout)
        print("CartCreate input preview:", file=stdout)
        print(json.dumps({"input": cart_input}, indent=2, sort_keys=True), file=stdout)
        return 0 if config and variant_ready else 2

    if not config or not variant_ready:
        print("Live smoke test blocked until env vars and a real variant GID are configured.", file=stderr)
        return 2

    try:
        cart = create_cart(config, cart_input)
    except ShopifyAPIError as error:
        print(f"FAIL: Shopify cartCreate failed: {error}", file=stderr)
        return 1

    print("PASS: Shopify cartCreate returned a checkoutUrl.", file=stdout)
    print(f"checkoutUrl: {cart['checkoutUrl']}", file=stdout)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the ModelMint Shopify one-product proof flow.")
    parser.add_argument("--live", action="store_true", help="Call Shopify cartCreate. Without this flag, the test is a dry run.")
    parser.add_argument("--product", default=DEFAULT_PRODUCT_HANDLE, help="Sample product handle to test.")
    args = parser.parse_args(argv)
    return run_smoke_test(live=args.live, product_handle=args.product)


if __name__ == "__main__":
    raise SystemExit(main())
