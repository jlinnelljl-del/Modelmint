# ModelMint Local Install

ModelMint should treat the cloud drive as the master library. The print workstation runs the app against the local synced copy of that cloud library.

## Cloud Library Setup

1. Create a shared cloud-drive folder for the ModelMint library.
2. On the print workstation, make sure that folder is synced locally.
3. Mark the ModelMint folders as available offline in the cloud-drive app.
4. Point `MODEL_LIBRARY_PATH` at the local synced folder.
5. Keep incoming releases, catalog data, rejected archive, custom orders, and reports inside that library.

The app watches and scans local files only. Cloud sync is responsible for moving those local changes back to the shared master library.

## Required Paths

Configure these environment variables before production use:

```text
MODEL_LIBRARY_PATH=C:\Users\YourName\CloudDrive\ModelMint Library
INCOMING_RELEASES_PATH=incoming
APPROVED_CATALOG_PATH=data\catalog.json
REJECTED_ARCHIVE_PATH=archive\rejected
CUSTOM_ORDERS_PATH=data\quote-requests.json
REPORTS_PATH=reports
SCAN_INTERVAL_MINUTES=30
AUTO_SCAN_ENABLED=false
```

Relative paths are resolved inside `MODEL_LIBRARY_PATH`. Absolute paths are used as-is.

## Offline Availability

The print workstation should keep these folders available offline:

- incoming creator releases
- approved catalog data
- rejected/archive folder
- custom order records
- reports
- preview images and source model files

If cloud files are online-only, intake may appear empty or previews may fail to load.

## Safety Rule

Source files must never be moved, renamed, or deleted automatically.

The intake system only reads source files and writes catalog/report records. Human review is still required before publishing, archiving, deleting, or creating Shopify products.

## Local Status Page

Start the internal admin app:

```powershell
python -m modelmint.web
```

Then open:

```text
http://127.0.0.1:8765/#library-status
```

The Library Paths section shows each configured path and whether it currently exists on the workstation.

## Safe Auto Scanning

Run a one-time scan:

```powershell
python -m modelmint.scanner --once
```

Run periodic scans:

```powershell
python -m modelmint.scanner --watch
```

The scanner uses `SCAN_INTERVAL_MINUTES` for the delay between scans. It records the last scan time, result, new release/model/asset counts, and recent errors in `scanner-status.json` under the reports folder.

If `AUTO_SCAN_ENABLED=true`, running `python -m modelmint.scanner` without flags starts continuous scanning. Keep this off until the local synced folders are confirmed available offline.

The scanner is intentionally boring and safe:

- source files are never moved
- source files are never renamed
- source files are never deleted
- duplicate records are not recreated on repeated scans
- missing cloud-sync folders are reported instead of crashing
- Shopify is not required
