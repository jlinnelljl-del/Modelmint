from __future__ import annotations

ALLOWED_MODEL_STATUSES = [
    "Needs Review",
    "Needs Test Print",
    "Approved",
    "Rejected",
    "Drafted in Shopify",
    "Published",
    "Archived",
]

MODEL_EXTENSIONS = {".3mf", ".stl", ".obj", ".step"}
MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

DEFAULT_CATALOG = {
    "schema_version": 2,
    "creators": [],
    "releases": [],
    "models": [],
    "assets": [],
    "color_profiles": [],
    "material_finish_rules": [
        {
            "rule_id": "rule_extendable_katana_default",
            "product_category": "extendable katana",
            "allowed_finishes": ["matte", "standard"],
            "blocked_finishes": ["silk", "glow", "brittle filled"],
            "reason": "High-stress sliding parts need tougher materials and predictable friction.",
            "applies_to_mechanical_parts": True,
            "applies_to_articulated_parts": True,
            "applies_to_decorative_items": False,
        },
        {
            "rule_id": "rule_decorative_dragon_default",
            "product_category": "decorative dragon",
            "allowed_finishes": ["silk", "sparkle", "metallic", "color-shift", "matte", "standard"],
            "blocked_finishes": [],
            "reason": "Decorative display items can use premium visual finishes when articulation risk is low.",
            "applies_to_mechanical_parts": False,
            "applies_to_articulated_parts": False,
            "applies_to_decorative_items": True,
        },
        {
            "rule_id": "rule_hueforge_default",
            "product_category": "HueForge",
            "allowed_finishes": ["matte", "standard"],
            "blocked_finishes": ["high-glitter", "low-contrast translucent"],
            "reason": "Visual clarity and contrast matter more than novelty finish.",
            "applies_to_mechanical_parts": False,
            "applies_to_articulated_parts": False,
            "applies_to_decorative_items": True,
        },
    ],
    "custom_orders": [],
}
