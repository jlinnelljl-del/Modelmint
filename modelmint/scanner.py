from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modelmint.intake import run_intake
from modelmint.library_config import LibraryConfig, library_path_status, load_library_config, resolved_library_config


SCANNER_STATUS_FILE = "scanner-status.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def scanner_status_path(config: LibraryConfig | None = None) -> Path:
    active = resolved_library_config(config)
    reports_root = active.reports_path.parent if active.reports_path.suffix else active.reports_path
    return reports_root / SCANNER_STATUS_FILE


def default_scanner_status(config: LibraryConfig | None = None) -> dict[str, Any]:
    active = resolved_library_config(config)
    return {
        "auto_scan_enabled": active.auto_scan_enabled,
        "scan_interval_minutes": active.scan_interval_minutes,
        "last_scan_time": "",
        "last_scan_result": "Never run",
        "new_releases": 0,
        "new_models": 0,
        "new_assets": 0,
        "last_summary": {},
        "recent_errors": [],
    }


def load_scanner_status(config: LibraryConfig | None = None) -> dict[str, Any]:
    active = resolved_library_config(config)
    path = scanner_status_path(active)
    status = default_scanner_status(active)
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                status.update(loaded)
        except (OSError, json.JSONDecodeError):
            status["recent_errors"] = ["Could not read scanner status file."]
    status["auto_scan_enabled"] = active.auto_scan_enabled
    status["scan_interval_minutes"] = active.scan_interval_minutes
    return status


def save_scanner_status(status: dict[str, Any], config: LibraryConfig | None = None) -> None:
    path = scanner_status_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _with_recent_error(status: dict[str, Any], message: str) -> dict[str, Any]:
    errors = [message, *status.get("recent_errors", [])]
    status["recent_errors"] = errors[:5]
    return status


def run_scan_once(config: LibraryConfig | None = None) -> dict[str, Any]:
    active = resolved_library_config(config)
    status = load_scanner_status(active)
    status["last_scan_time"] = utc_now()
    status["new_releases"] = 0
    status["new_models"] = 0
    status["new_assets"] = 0

    path_status = library_path_status(active)
    incoming_status = next((item for item in path_status["paths"] if item["env_name"] == "INCOMING_RELEASES_PATH"), None)
    if incoming_status and not incoming_status["exists"]:
        status["last_scan_result"] = "Skipped: incoming releases path is missing."
        _with_recent_error(status, f"Missing incoming releases path: {incoming_status['path']}")
        save_scanner_status(status, active)
        return status

    try:
        summary = run_intake(active.incoming_releases_path, active.approved_catalog_path, active.intake_report_path, active.model_library_path)
    except (OSError, PermissionError) as error:
        status["last_scan_result"] = "Failed: could not read or write library files."
        _with_recent_error(status, str(error))
        save_scanner_status(status, active)
        return status

    status["last_scan_result"] = "Completed"
    status["new_releases"] = int(summary.get("created_releases", 0))
    status["new_models"] = int(summary.get("created_models", 0))
    status["new_assets"] = int(summary.get("created_assets", 0))
    status["last_summary"] = summary
    status["recent_errors"] = []
    save_scanner_status(status, active)
    return status


def run_scan_loop(config: LibraryConfig | None = None) -> None:
    active = resolved_library_config(config)
    while True:
        status = run_scan_once(active)
        print(f"{status['last_scan_time']} - {status['last_scan_result']} ({status['new_models']} new models)")
        time.sleep(active.scan_interval_minutes * 60)


def build_parser() -> argparse.ArgumentParser:
    config = load_library_config()
    parser = argparse.ArgumentParser(description="Safely scan the local cloud-synced ModelMint library.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Run one scan and exit.")
    mode.add_argument("--watch", action="store_true", help="Run continuously using SCAN_INTERVAL_MINUTES.")
    parser.add_argument("--interval-minutes", type=int, default=config.scan_interval_minutes, help="Override scan interval for --watch.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_library_config()
    if args.interval_minutes:
        config = LibraryConfig(
            model_library_path=config.model_library_path,
            incoming_releases_path=config.incoming_releases_path,
            approved_catalog_path=config.approved_catalog_path,
            rejected_archive_path=config.rejected_archive_path,
            custom_orders_path=config.custom_orders_path,
            reports_path=config.reports_path,
            scan_interval_minutes=max(1, args.interval_minutes),
            auto_scan_enabled=config.auto_scan_enabled,
        )

    if args.watch or (not args.once and config.auto_scan_enabled):
        run_scan_loop(config)
        return

    status = run_scan_once(config)
    print(f"Scan result: {status['last_scan_result']}")
    print(f"Last scan time: {status['last_scan_time']}")
    print(f"New releases: {status['new_releases']}")
    print(f"New models: {status['new_models']}")
    print(f"New assets: {status['new_assets']}")
    if status.get("recent_errors"):
        print("Recent errors:")
        for error in status["recent_errors"]:
            print(f"- {error}")


if __name__ == "__main__":
    main()
