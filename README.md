# ModelMint

ModelMint is a local intake and review-queue tool for a small 3D printing catalog.

MVP 1 scans messy creator release folders, detects printable model files and preview images, creates normalized JSON records, marks every model as `Needs Review`, and writes a human-readable intake report.

It never renames, moves, deletes, or modifies incoming source files.

## What This Does

- Scans `incoming/`
- Detects creator and release folders
- Finds model files: `.3mf`, `.stl`, `.obj`, `.step`
- Finds media files: `.jpg`, `.jpeg`, `.png`, `.webp`
- Creates records for creators, releases, models, and assets
- Creates starter color-profile records for multi-color candidates
- Avoids duplicates across repeated runs
- Writes output to `data/catalog.json`
- Writes a report to `reports/intake-report.md`

## Requirements

Python 3.10 or newer.

No extra packages are required.

## Quick Start

From this folder:

```powershell
python -m modelmint.intake --incoming incoming --catalog data/catalog.json --report reports/intake-report.md
```

If `python` is not available, try:

```powershell
py -m modelmint.intake --incoming incoming --catalog data/catalog.json --report reports/intake-report.md
```

For a cloud-synced workstation setup, configure the library paths in environment variables instead of relying on the local defaults:

```text
MODEL_LIBRARY_PATH=
INCOMING_RELEASES_PATH=
APPROVED_CATALOG_PATH=
REJECTED_ARCHIVE_PATH=
CUSTOM_ORDERS_PATH=
REPORTS_PATH=
SCAN_INTERVAL_MINUTES=
AUTO_SCAN_ENABLED=
```

See `README_LOCAL_INSTALL.md` for the shared cloud library setup. The cloud drive is the master library, but ModelMint reads the local synced copy on the print workstation.

## Review The Results

Open:

- `data/catalog.json`
- `reports/intake-report.md`

Every new model is marked `Needs Review`.

## Run The Local Website

After running intake, start the local admin website:

```powershell
python -m modelmint.web
```

Then open:

```text
http://127.0.0.1:8765
```

The website shows the review queue, preview images, catalog counts, filters, editable review statuses, production notes, artisan notes, and a button to run intake again. It is an internal admin tool only. It binds to localhost by default, does not publish products, does not send emails, and does not touch original source files.

Do not expose this admin server to the public internet. Binding to a non-localhost address requires the explicit `--allow-lan` flag and should only be used on a trusted private network.

Open `http://127.0.0.1:8765/#library-status` to review configured cloud-library paths and see whether each path exists locally.

## Safe Library Scanner

The scanner safely reruns intake against the configured local cloud-synced incoming folder. It writes catalog updates and reports, but it never moves, deletes, renames, publishes, emails, or requires Shopify.

Run one scan:

```powershell
python -m modelmint.scanner --once
```

Run continuously:

```powershell
python -m modelmint.scanner --watch
```

The continuous scanner uses:

```text
SCAN_INTERVAL_MINUTES=30
AUTO_SCAN_ENABLED=false
```

If you run `python -m modelmint.scanner` with `AUTO_SCAN_ENABLED=true`, it starts continuous scanning. Otherwise it runs once and exits.

Scanner state is saved to:

```text
REPORTS_PATH/scanner-status.json
```

The latest scan result is also shown on the admin Library Paths page. The `Run Scan Now` button triggers the same safe scanner flow manually.

Repeated scans are protected by stable IDs and duplicate detection, so the same release/model/assets are not recreated every interval.

## Run The Customer-Facing Storefront

Website-1 is a local sample storefront. It uses sample product data, local color/finish rules, a sample cart, and local quote request records.

This storefront is the bright consumer side of the business: playful gifts, collectibles, craft-fair products, and friendly custom keepsakes. Commercial/B2B workflows should remain a separate section or future subsite so the main shop does not become overly corporate.

Current storefront branding uses a ModelMint3D placeholder SVG mark and the brand-board palette:

- plum `#4B256D`
- violet `#7C4DFF`
- mint `#7EE7C1`
- charcoal `#1E1E24`
- soft lavender `#F3F0FF`
- white `#FFFFFF`

The placeholder logo should be replaced when a final designer/exported logo asset is available.

See `BRANDING.md` for the locked storefront brand direction and theme token guidance.

```powershell
python -m modelmint.storefront
```

Then open:

```text
http://127.0.0.1:8780
```

Routes included in Website-1:

- `/`
- `/shop`
- `/shop/[handle]`
- `/cart`
- `/custom-orders`
- `/business`
- `/events`
- `/new`
- `/about`
- `/contact`

Quote requests are saved to:

```text
data/quote-requests.json
```

The mock cart is intentionally local. It stores customized product selections in browser session storage so we can prove the customer workflow before connecting Shopify. Mock cart lines are shaped like future Shopify line item attributes:

- `Color 1`
- `Color 2`
- `Color 3`
- `Finish Preference`
- `Customer Notes`
- `Product Rule Warnings`

Invalid finish selections are filtered out of the UI and rejected again by the local API if manually submitted.

Website-1 does not connect to Shopify yet. The future Shopify integration should use environment variables like:

```text
SHOPIFY_STORE_DOMAIN=
SHOPIFY_STOREFRONT_ACCESS_TOKEN=
SHOPIFY_API_VERSION=
```

Website-2 should use the Shopify Storefront API for products, collections, carts, and checkout URL handoff. Website-3 should map approved internal catalog records to Shopify draft products and Shopify metafields.

The Shopify adapter scaffold lives in:

```text
modelmint/shopify_adapter.py
```

Current behavior:

- Builds Storefront API-style cart line payloads from validated local selections.
- Uses placeholder variant IDs like `gid://shopify/ProductVariant/TODO-crystal-dragon`.
- Keeps the UI isolated from Shopify API details.
- Keeps the mock cart local until real credentials and variant IDs exist.

Later Shopify cart flow:

1. Load real products and variants from the Shopify Storefront API.
2. Replace placeholder `merchandiseId` values with real Shopify variant IDs.
3. Use `cartCreate` when the customer starts a cart.
4. Use `cartLinesAdd` for additional customized products.
5. Send color slots, finish preference, customer notes, and rule warnings as Shopify line item attributes.
6. Send the customer to Shopify's returned `checkoutUrl`.
7. Leave payment, tax, shipping, and order handling inside Shopify.

## Shopify One-Product Proof

The storefront includes an optional server-side proof endpoint:

```text
POST /api/shopify/cart/create
```

It validates the same local customization payload, builds a Shopify `cartCreate` input, calls the Shopify Storefront API from the server, and returns Shopify's `checkoutUrl`. If credentials are missing or Shopify rejects the request, the endpoint returns a clear error and the local mock cart remains untouched.

Required environment variables:

```text
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_STOREFRONT_ACCESS_TOKEN=your-storefront-token
SHOPIFY_API_VERSION=2026-01
```

These are also listed in `.env.example`. Do not put real tokens in committed files.

One test product setup:

1. Create one unpublished/manual test product in Shopify.
2. Keep it simple with one purchasable variant.
3. Copy that variant's Storefront API GID, shaped like `gid://shopify/ProductVariant/123456789`.
4. Paste it into the matching sample product's `shopify_variant_id` field in `modelmint/storefront_data.py`.
5. Start the storefront with the environment variables set.
6. Submit a local customization payload to `/api/shopify/cart/create`.
7. Confirm the response includes `checkoutUrl`.
8. Open the `checkoutUrl` and confirm it lands on Shopify checkout with the selected line item attributes.

Safety checks:

- Visit `/dev/shopify-status` to confirm env vars are present without revealing the token.
- Confirm the test sample product says `configured` for its variant mapping.
- Products with missing/TODO variant IDs are blocked before Shopify checkout.
- Missing credentials return a clear error and do not remove the local mock cart.

Live-test checklist:

1. Start the storefront with `python -m modelmint.storefront`.
2. Open `http://127.0.0.1:8780/dev/shopify-status`.
3. Confirm the page says Shopify env vars are present.
4. Confirm the chosen sample product has a configured variant GID.
5. Add the same product to the local mock cart.
6. Use the cart page's Shopify checkout button or run the smoke test below.
7. Confirm Shopify returns a `checkoutUrl`.
8. Open the `checkoutUrl` and confirm the line item carries the selected color, finish, notes, and rule-warning attributes.

Run the smoke test dry-run:

```powershell
python -m modelmint.shopify_smoke_test
```

Expected dry-run success:

- Prints `PASS: Built known valid local customization payload.`
- Prints `PASS: Shopify env vars are present.`
- Prints `PASS: Sample product has a configured Shopify variant GID.`
- Prints `Dry run complete. No Shopify API call was made.`
- Prints a `cartCreate` input preview.
- Never prints the Storefront access token.

Expected dry-run setup failure:

- Prints the missing Shopify env vars, or says the sample product still has a missing/TODO variant GID.
- Still prints the local `cartCreate` input preview when the customization payload is valid.
- Does not call Shopify.
- Never prints the Storefront access token.

Run the smoke test live:

```powershell
python -m modelmint.shopify_smoke_test --live
```

Expected live success:

- Prints `PASS: Shopify cartCreate returned a checkoutUrl.`
- Prints `checkoutUrl: ...`
- Does not print the Storefront access token.

Expected live setup failure:

- Blocks before calling Shopify if env vars are missing or the product still uses a TODO variant GID.
- Prints a clear failure message.
- Does not remove or alter the local mock cart.

Do not migrate the catalog yet. Do not create products automatically yet. This proof is only for confirming that one validated local customization can become a real Shopify cart line with line item attributes.

Shopify TODOs:

- Load products and collections from the Shopify Storefront API.
- Create Shopify carts from storefront selections.
- Send color slots, finish preference, customer notes, and rule warnings as line item attributes.
- Use Shopify checkout URLs for payment, taxes, shipping, and order handling.
- Map approved internal catalog records to Shopify draft products.
- Store custom catalog fields in Shopify metafields.

Tracked examples are included here:

- `samples/output/catalog.sample.json`
- `samples/output/intake-report.sample.md`

## Add Real Releases

Drop folders into `incoming/` using any rough structure like:

```text
incoming/
  Creator Name/
    2026-05 Release/
      preview.jpg
      model-name.3mf
      supported/
        model-name-supported.stl
```

Folder structures can be messy. The scanner preserves the original files and stores path references only.

## Safety Rules

- No source files are renamed.
- No source files are moved.
- No source files are deleted.
- Nothing is published to Shopify.
- No emails are sent.
- Human review remains required.

## How Duplicate Handling Works

The scanner uses stable IDs based on creator names, release paths, and normalized model names. Running the same intake command twice updates the catalog without creating duplicate creator, release, model, asset, or color-profile records.

Related files with the same normalized model name are grouped into one model record. For example, `Crystal Dragon.3mf` and `Crystal Dragon supported.stl` become one review model with multiple assets.

If a better primary file appears later, such as a `.3mf` arriving after an `.stl`, the existing model record is updated instead of duplicated.

## Multi-Color Candidates

Models that look multi-color, such as `.3mf` files or HueForge-style folders, receive a starter color profile. These profiles use broad customer-facing color families and empty finish rules so the owner can review them before enabling customer choices.

## Future Extension Points

The MVP writes local JSON, but the record shapes are intentionally table-like so they can later map to Airtable tables or a thin Shopify draft-product workflow after human approval.

## Run Tests

```powershell
python -m unittest discover tests
```

## Git publication safety

Keep real credentials and local library paths in your environment or an ignored
`.env` file. The application reads environment variables; it does not automatically
load `.env`. `.env.example` contains placeholders only.

Git excludes incoming releases, local catalog/customer data, reports, archives,
production geometry, credentials, and Python runtime files. Keep any externally
configured library outside the repository. Do not force-add ignored files.

A fresh clone contains source, tests, and safe sample output, but no incoming
assets or local catalog. Create an `incoming/` folder and add your own releases
before running intake. The tests create their own temporary fixtures.

Before each publication, run `python -m unittest discover tests`, inspect
`git status --short --untracked-files=all` and `git diff --cached`, and review the
complete file list. Ignore rules do not detect secrets embedded in source or
remove files that are already tracked. Never commit real tokens, customer records,
or local absolute paths. Human approval is required before the first commit/push.

Deploy the public storefront separately from the private admin/scanner and model
library. Do not copy private library folders to the public host.
