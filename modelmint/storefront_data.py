from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modelmint.shopify_adapter import build_cart_create_input, build_cart_lines_add_input


COLOR_INTENTS = [
    "Classic",
    "Pastel",
    "Dark/Gothic",
    "Rainbow",
    "Forest",
    "Fire/Ice",
    "Galaxy",
    "Artist Choice",
    "Custom Notes",
]

FINISH_OPTIONS = [
    "matte",
    "standard",
    "silk",
    "sparkle",
    "metallic",
    "color-shift",
    "glow",
    "brittle filled",
]

QUOTE_ORDER_TYPES = [
    "branded coasters",
    "coaster holders",
    "restaurant/brewery table sets",
    "QR stands",
    "sports team tags",
    "birthday party favors",
    "wedding/event tags",
    "custom text/name plates",
]

SAMPLE_PRODUCTS = [
    {
        "handle": "crystal-dragon",
        "title": "Crystal Dragon",
        "description": "A display-ready articulated dragon with broad color styling options and review-safe finish guidance.",
        "images": ["https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?auto=format&fit=crop&w=1200&q=80"],
        "price": "28.00",
        "category": "Gifts and Collectibles",
        "product_type": "Decorative Dragon",
        "customizable": True,
        "color_slot_count": 3,
        "allowed_finishes": ["matte", "standard", "silk", "sparkle", "metallic", "color-shift"],
        "blocked_finishes": ["glow", "brittle filled"],
        "blocked_finish_reasons": {
            "glow": "Reserved for reviewed designs where glow material will not reduce detail.",
            "brittle filled": "Brittle filled materials are not approved for articulated display pieces.",
        },
        "material_notes": "Premium visual finishes are available after review for each design.",
        "production_notes": "Confirm articulation tolerance before enabling unusual finishes.",
        "creator_attribution": "Sample creator attribution",
        "license_status": "Sample commercial license pending review",
        "shopify_product_id": "",
        "shopify_variant_id": "",
        "status": "sample",
    },
    {
        "handle": "brewery-logo-coaster-set",
        "title": "Brewery Logo Coaster Set",
        "description": "A polished coaster set for local brands, taprooms, coffee shops, events, and merch tables.",
        "images": ["https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=1200&q=80"],
        "price": "32.00",
        "category": "Coasters and Tabletop",
        "product_type": "Custom Coaster",
        "customizable": True,
        "color_slot_count": 2,
        "allowed_finishes": ["matte", "standard", "silk"],
        "blocked_finishes": ["glow", "brittle filled"],
        "blocked_finish_reasons": {
            "glow": "Glow materials are not ideal for crisp logo contrast.",
            "brittle filled": "Brittle filled materials are not approved for thin coaster details.",
        },
        "material_notes": "Cork backing can be added after quote review.",
        "production_notes": "Logo artwork should be reviewed before checkout products are published.",
        "creator_attribution": "ModelMint original sample",
        "license_status": "Owner-created",
        "shopify_product_id": "",
        "shopify_variant_id": "",
        "status": "sample",
    },
    {
        "handle": "extendable-katana",
        "title": "Extendable Katana",
        "description": "A mechanically sensitive print with intentionally narrow material choices for reliable motion.",
        "images": ["https://images.unsplash.com/photo-1595069906974-f8ae7ffc3e7a?auto=format&fit=crop&w=1200&q=80"],
        "price": "24.00",
        "category": "Props and Toys",
        "product_type": "Extendable Katana",
        "customizable": True,
        "color_slot_count": 1,
        "allowed_finishes": ["matte", "standard"],
        "blocked_finishes": ["silk", "glow", "brittle filled", "sparkle", "metallic", "color-shift"],
        "blocked_finish_reasons": {
            "silk": "Silk can be brittle and may bind in sliding parts.",
            "glow": "Glow material is not approved for high-friction moving parts.",
            "brittle filled": "Filled filaments can crack under extension stress.",
            "sparkle": "Decorative particles can affect sliding tolerances.",
            "metallic": "Decorative particles can affect sliding tolerances.",
            "color-shift": "Decorative blends need review before mechanical use.",
        },
        "material_notes": "Mechanical parts use conservative finish options.",
        "production_notes": "Needs test print approval before customer-facing publish.",
        "creator_attribution": "Sample creator attribution",
        "license_status": "Sample commercial license pending review",
        "shopify_product_id": "",
        "shopify_variant_id": "",
        "status": "sample",
    },
    {
        "handle": "skull-dice-tower",
        "title": "Skull Dice Tower",
        "description": "A tabletop gaming print for craft fairs, gifts, and game-night bundles.",
        "images": ["https://images.unsplash.com/photo-1611996575749-79a3a250f948?auto=format&fit=crop&w=1200&q=80"],
        "price": "35.00",
        "category": "Tabletop Gaming",
        "product_type": "Dice Tower",
        "customizable": False,
        "color_slot_count": 0,
        "allowed_finishes": ["matte", "standard", "silk", "metallic"],
        "blocked_finishes": ["brittle filled"],
        "blocked_finish_reasons": {
            "brittle filled": "Thin decorative details need reviewed material choices.",
        },
        "material_notes": "Artist choice colorways are available.",
        "production_notes": "Check dice path clearance after scaling.",
        "creator_attribution": "Sample creator attribution",
        "license_status": "Sample commercial license pending review",
        "shopify_product_id": "",
        "shopify_variant_id": "",
        "status": "sample",
    },
]


@dataclass(frozen=True)
class QuoteValidationResult:
    valid: bool
    errors: list[str]


def storefront_payload() -> dict[str, Any]:
    return {
        "products": deepcopy(SAMPLE_PRODUCTS),
        "color_intents": COLOR_INTENTS,
        "finish_options": FINISH_OPTIONS,
        "quote_order_types": QUOTE_ORDER_TYPES,
        "shopify": {
            "mode": "sample",
            "cart_checkout_enabled": False,
            "todos": [
                "Load products and collections from the Shopify Storefront API.",
                "Create Shopify carts from selected product options.",
                "Send color slots, finish preference, customer notes, and rule warnings as line item attributes.",
                "Use Shopify checkout URLs for payment, taxes, shipping, and order handling.",
                "Map approved internal catalog records to Shopify draft products and metafields.",
            ],
            "required_env": [
                "SHOPIFY_STORE_DOMAIN",
                "SHOPIFY_STOREFRONT_ACCESS_TOKEN",
                "SHOPIFY_API_VERSION",
            ],
        },
    }


def product_by_handle(handle: str) -> dict[str, Any] | None:
    return next((deepcopy(item) for item in SAMPLE_PRODUCTS if item["handle"] == handle), None)


def valid_finish_for_product(product: dict[str, Any], finish: str) -> bool:
    return finish in product["allowed_finishes"] and finish not in product["blocked_finishes"]


def build_line_item_attributes(product: dict[str, Any], selections: dict[str, Any]) -> dict[str, str]:
    finish = selections.get("finish_preference", "")
    if finish and not valid_finish_for_product(product, finish):
        raise ValueError("Finish preference is not available for this product.")

    attributes: dict[str, str] = {}
    for index in range(1, int(product.get("color_slot_count", 0)) + 1):
        value = str(selections.get(f"Color {index}", "")).strip()
        if value:
            attributes[f"Color {index}"] = value

    if finish:
        attributes["Finish Preference"] = str(finish)

    notes = str(selections.get("Customer Notes", "")).strip()
    if notes:
        attributes["Customer Notes"] = notes

    if product.get("blocked_finishes"):
        attributes["Product Rule Warnings"] = "Only validated finish options were shown for this product."

    return attributes


def build_mock_cart_line(product: dict[str, Any], selections: dict[str, Any]) -> dict[str, Any]:
    attributes = build_line_item_attributes(product, selections)
    quantity = 1
    return {
        "mock_line_id": f"mock_{product['handle']}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "product_handle": product["handle"],
        "title": product["title"],
        "price": product["price"],
        "image": product["images"][0] if product.get("images") else "",
        "quantity": quantity,
        "selections": dict(selections),
        "line_item_attributes": attributes,
        "shopify_ready": {
            "line_item_attributes": attributes,
            "cart_create_input": build_cart_create_input(product, attributes, quantity),
            "cart_lines_add_input": build_cart_lines_add_input(product, attributes, quantity),
            "checkout_enabled": False,
        },
    }


def validate_quote_request(payload: dict[str, Any]) -> QuoteValidationResult:
    required = ["customer_name", "email", "business_event_name", "order_type", "target_quantity", "deadline", "notes", "fulfillment_preference"]
    errors = [field for field in required if not str(payload.get(field, "")).strip()]

    email = str(payload.get("email", ""))
    if email and not re.search(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("email_format")

    quantity = str(payload.get("target_quantity", "")).strip()
    if quantity:
        try:
            if int(quantity) <= 0:
                errors.append("target_quantity_positive")
        except ValueError:
            errors.append("target_quantity_number")

    if payload.get("order_type") and payload["order_type"] not in QUOTE_ORDER_TYPES:
        errors.append("order_type_supported")

    return QuoteValidationResult(valid=not errors, errors=errors)


def append_quote_request(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    validation = validate_quote_request(payload)
    if not validation.valid:
        raise ValueError(",".join(validation.errors))

    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))

    record = {
        "quote_request_id": f"quote_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "quote_status": "Needs Review",
        "production_status": "Not Started",
        "customer_name": str(payload["customer_name"]).strip(),
        "email": str(payload["email"]).strip(),
        "phone": str(payload.get("phone", "")).strip(),
        "business_event_name": str(payload["business_event_name"]).strip(),
        "order_type": payload["order_type"],
        "target_quantity": int(payload["target_quantity"]),
        "deadline": str(payload["deadline"]).strip(),
        "budget_range": str(payload.get("budget_range", "")).strip(),
        "logo_artwork_note": str(payload.get("logo_artwork_note", "")).strip(),
        "notes": str(payload["notes"]).strip(),
        "fulfillment_preference": str(payload["fulfillment_preference"]).strip(),
    }
    existing.append(record)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
