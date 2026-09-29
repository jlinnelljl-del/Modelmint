from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from modelmint.shopify_adapter import product_variant_status


CART_CREATE_MUTATION = """
mutation ModelMintCartCreate($input: CartInput!) {
  cartCreate(input: $input) {
    cart {
      id
      checkoutUrl
    }
    userErrors {
      field
      message
    }
  }
}
"""


@dataclass(frozen=True)
class ShopifyConfig:
    store_domain: str
    storefront_access_token: str
    api_version: str

    @property
    def endpoint(self) -> str:
        return f"https://{self.store_domain}/api/{self.api_version}/graphql.json"


class ShopifyConfigError(RuntimeError):
    pass


class ShopifyAPIError(RuntimeError):
    pass


def load_shopify_config(env: dict[str, str] | None = None) -> ShopifyConfig:
    source = env if env is not None else os.environ
    store_domain = source.get("SHOPIFY_STORE_DOMAIN", "").strip()
    token = source.get("SHOPIFY_STOREFRONT_ACCESS_TOKEN", "").strip()
    api_version = source.get("SHOPIFY_API_VERSION", "").strip()

    missing = [
        name
        for name, value in {
            "SHOPIFY_STORE_DOMAIN": store_domain,
            "SHOPIFY_STOREFRONT_ACCESS_TOKEN": token,
            "SHOPIFY_API_VERSION": api_version,
        }.items()
        if not value
    ]
    if missing:
        raise ShopifyConfigError(f"Missing Shopify Storefront API configuration: {', '.join(missing)}")

    store_domain = store_domain.removeprefix("https://").removeprefix("http://").rstrip("/")
    return ShopifyConfig(store_domain=store_domain, storefront_access_token=token, api_version=api_version)


def shopify_status(env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        config = load_shopify_config(env)
    except ShopifyConfigError as error:
        return {"configured": False, "message": str(error)}
    return {"configured": True, "store_domain": config.store_domain, "api_version": config.api_version}


def shopify_debug_status(products: list[dict[str, Any]], env: dict[str, str] | None = None) -> dict[str, Any]:
    status = shopify_status(env)
    return {
        **status,
        "token_visible": False,
        "products": [product_variant_status(product) for product in products],
    }


def execute_storefront_graphql(config: ShopifyConfig, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = Request(
        config.endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Storefront-Access-Token": config.storefront_access_token,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ShopifyAPIError(f"Shopify Storefront API returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise ShopifyAPIError(f"Could not reach Shopify Storefront API: {error.reason}") from error


def create_cart(config: ShopifyConfig, cart_input: dict[str, Any]) -> dict[str, Any]:
    payload = execute_storefront_graphql(config, CART_CREATE_MUTATION, {"input": cart_input})
    if payload.get("errors"):
        raise ShopifyAPIError(f"Shopify GraphQL error: {payload['errors']}")

    result = payload.get("data", {}).get("cartCreate", {})
    user_errors = result.get("userErrors") or []
    if user_errors:
        messages = "; ".join(error.get("message", "Unknown cart error") for error in user_errors)
        raise ShopifyAPIError(f"Shopify cartCreate rejected the cart: {messages}")

    cart = result.get("cart")
    if not cart or not cart.get("checkoutUrl"):
        raise ShopifyAPIError("Shopify cartCreate response did not include checkoutUrl.")
    return cart
