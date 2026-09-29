# Project: 3D Printing Catalog, Intake, and Custom Order System

## Goal

Build a modular web system for our 3D printing business.

This is not a generic ecommerce website. It is a catalog, intake, customization, review, and order-prep system for a small 3D printing company that sells:

- consumer 3D printed products
- multi-color models
- custom coasters
- batch orders
- branded business/tabletop products
- event and craft fair products

The first priority is internal automation and catalog control, not visual polish.

## Core Principle

Do not auto-publish anything.

The system may collect, organize, draft, generate, and prepare records, but a human must review before:

- publishing a product
- sending an email/newsletter
- approving a custom order
- creating final customer-facing product listings

## Current Business Context

We subscribe to many Patreon/MMF/Tribes-style creators and regularly receive new printable models.

We want the system to automatically gather new creator content, organize it, extract useful metadata, create review records, and help us decide what to add to our catalog.

We also sell finished products at craft fairs and online. Coasters, themed coaster sets, dragons, animals, dice towers, HueForge items, clickers, and custom/batch orders are all relevant.

## System Architecture

Recommended stack:

- Shopify for ecommerce, checkout, shipping, taxes, and customer orders
- Airtable or equivalent database as the catalog/review brain
- Local/shared file storage for source files
- Automation/scripts for intake and metadata extraction
- Later: custom frontend modules for multi-color model preview and custom order workflows

Codex should build incrementally.

## Phase 1: Intake MVP

Build a local/admin tool that scans incoming creator release folders and creates catalog review records.

### Input

A root folder containing creator release folders.

Example structure:

```text
/Incoming Releases/
  /Creator Name/
    /2026-05 Release/
      preview.jpg
      model-name.3mf
      model-name.stl
      images/
      supported/
      unsupported/
```

Folder structures will vary. Do not assume perfect naming.

### Required Behavior

The intake tool should:

1. Scan incoming folders.
2. Detect new releases.
3. Identify candidate model files:
   - .3mf
   - .stl
   - .obj if present
   - .step if present
4. Identify preview/media files:
   - .jpg
   - .jpeg
   - .png
   - .webp
5. Create or update catalog records.
6. Avoid duplicates.
7. Preserve original files.
8. Never rename, move, or delete source files without explicit approval.
9. Mark all new records as `Needs Review`.
10. Store path references to assets.
11. Generate a human-readable intake report.

## Phase 1 Data Model

Create database/table schemas for:

### Creators

Fields:

- creator_id
- creator_name
- source_platform
- commercial_license_status
- license_notes
- active_status
- default_attribution_text
- notes

### Releases

Fields:

- release_id
- creator_id
- release_name
- release_date
- source_folder_path
- intake_status
- notes

### Models

Fields:

- model_id
- release_id
- creator_id
- model_name
- source_folder_path
- primary_file_path
- model_type
- category
- subcategory
- status
- review_status
- license_status
- attribution_required
- estimated_complexity
- multi_color
- color_slot_count
- production_notes
- artisan_notes
- created_at
- updated_at

Allowed statuses:

- Needs Review
- Needs Test Print
- Approved
- Rejected
- Drafted in Shopify
- Published
- Archived

### Assets

Fields:

- asset_id
- model_id
- asset_type
- file_path
- file_name
- file_extension
- preview_priority
- notes

### Color Profiles

Important: We do not sell exact filament recipes.

We use color intent and finish restrictions.

Fields:

- color_profile_id
- model_id
- color_slot_count
- slot_1_label
- slot_2_label
- slot_3_label
- slot_4_label
- allowed_color_families
- allowed_finishes
- blocked_finishes
- finish_notes
- customer_color_description
- internal_color_notes
- artisan_filament_notes

Example:
A model may have 3 color slots, but they do not need customer-facing names. The customer can choose Color 1, Color 2, and Color 3 and see the preview update.

### Material / Finish Rules

Fields:

- rule_id
- product_category
- allowed_finishes
- blocked_finishes
- reason
- applies_to_mechanical_parts
- applies_to_articulated_parts
- applies_to_decorative_items

Example rules:

- Extendable katana: block silk, glow, brittle filled filaments.
- Decorative dragon: allow silk, sparkle, metallic, color-shift.
- Flexi toys: avoid brittle silk unless specifically approved.
- HueForge: finish restrictions based on visual clarity.

### Custom Orders

Fields:

- custom_order_id
- customer_name
- customer_email
- order_type
- quantity
- deadline
- budget_target
- logo_upload_path
- text_data_path
- notes
- quote_status
- production_status

Order types:

- batch coasters
- restaurant/brewery table products
- sports team order
- birthday party order
- wedding/event tags
- custom text tags
- quote-based custom request

## Product Philosophy

The catalog sells curated manufacturable variants, not infinite arbitrary customization.

A product defines:

- what aesthetics are allowed
- what finishes are allowed
- what material behaviors are safe
- what customization boundaries exist

Do not allow customers to create combinations that are mechanically unsuitable.

Examples:

- Do not allow silk filament for extendable katanas.
- Do not allow brittle filled filaments for high-stress articulated objects.
- Allow premium finishes for decorative dragons.
- Use exact filament notes only as internal artisan notes.

## Color System

Customer-facing color choices should use broad intent:

- Classic
- Pastel
- Dark/Gothic
- Rainbow
- Forest
- Fire/Ice
- Galaxy
- Artist Choice
- Custom Notes

For multi-color models:

- Store number of color slots.
- Allow broad color family selection per slot.
- Allow finish preference only when product rules permit it.
- Do not require exact filament SKUs.
- Optional artisan note field may mention exact filament discoveries.

Example:
"Sally from Nightmare Before Christmas: this pale blue filament worked especially well for skin."

That is an internal note, not a required production recipe.

## Custom Batch Products

The system should support quote-based custom orders.

Examples:

- custom restaurant coasters
- brewery table sets
- QR tabletop stands
- sports team tags
- birthday party favors
- wedding/event seating tags
- custom text nameplates

Custom and batch orders should not go straight to checkout unless the product is a standardized configurable template.

Most custom orders should follow:

Request -> Review -> Quote -> Customer approval -> Production

## Coaster/Table Product Direction

We already sell coaster sets at craft fairs.

Important product details:

- Coasters may have cork bottoms.
- Face-down printing on textured plates creates a premium surface.
- We can produce detailed multi-color logos.
- Branded coaster sets and tabletop products are a B2B opportunity.
- Breweries, coffee shops, tabletop cafes, restaurants, and wedding/event venues are target markets.

Potential product categories:

- branded coasters
- coaster holders
- QR table stands
- table number holders
- condiment/table organizers
- modular faceplate systems
- custom event tags
- seating/name tags
- menu choice tags

## Event/Wedding System Concept

This is not Phase 1, but the database should not block it later.

Future system may support:

- reusable table bases
- magnetic faceplates
- replaceable QR inserts
- table numbers
- personalized name tags
- double-sided keepsake tags
- menu choice tags
- question/follow-up markers for staff

Important framing:

- Allergy/dietary markers are staff attention cues only.
- They do not confirm allergy safety.
- They mean "staff should ask this guest a question."

## MVP Build Order

Do not build everything at once.

### MVP 1

Creator release intake -> review queue.

### MVP 2

Approved catalog model -> Shopify draft product.

### MVP 3

Approved new products -> newsletter/social draft list.

### MVP 4

Custom batch quote request workflow.

### MVP 5

Multi-color 3MF/GLB preview and color slot picker.

## 3MF / Preview Notes

Many models come as multi-color 3MF files already.

Future browser preview should:

- load 3MF or converted GLB preview
- detect material/color slots
- expose Color 1, Color 2, Color 3, etc.
- allow customer to change visible colors
- store selected color intent in the order

Do not try to slice in the browser.
Do not generate toolpaths in the browser.
Do not modify production geometry in the storefront.

Preferred long-term approach:

- production asset: 3MF/STL
- web preview asset: optimized GLB/GLTF with named or mapped material slots

## Rules for Codex

1. Build incrementally.
2. Make small commits.
3. Do not create a giant monolithic app.
4. Prefer clear schemas and boring reliability.
5. Preserve source files.
6. Never auto-publish products.
7. Never auto-send emails.
8. Keep human approval steps explicit.
9. Document assumptions.
10. Create sample data.
11. Create tests where practical.
12. Keep setup simple for a non-programmer owner/operator.
13. Use plain-language README instructions.

## First Deliverable

Create a working local project that:

1. Scans a sample `/incoming` folder.
2. Detects model files and images.
3. Creates normalized JSON records or database records.
4. Marks everything as `Needs Review`.
5. Produces an intake report.
6. Has a README explaining how to run it.
7. Includes sample folders and sample output.
8. Does not require Shopify integration yet.

## Definition of Done for MVP 1

MVP 1 is done when we can drop several messy creator release folders into `/incoming`, run one command, and get:

- creator records
- release records
- model records
- asset records
- file path references
- duplicate detection
- review statuses
- intake report

without altering the original source files.
