from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_INTAKE_REPORT_NAME = "intake-report.md"


@dataclass(frozen=True)
class LibraryConfig:
    model_library_path: Path
    incoming_releases_path: Path
    approved_catalog_path: Path
    rejected_archive_path: Path
    custom_orders_path: Path
    reports_path: Path
    scan_interval_minutes: int
    auto_scan_enabled: bool

    @property
    def intake_report_path(self) -> Path:
        if self.reports_path.suffix:
            return self.reports_path
        return self.reports_path / DEFAULT_INTAKE_REPORT_NAME


def _path_from_env(name: str, default: str, env: dict[str, str] | None = None) -> Path:
    source = env if env is not None else os.environ
    return Path(source.get(name, default)).expanduser()


def _int_from_env(name: str, default: int, env: dict[str, str] | None = None) -> int:
    source = env if env is not None else os.environ
    try:
        return max(1, int(str(source.get(name, default)).strip()))
    except ValueError:
        return default


def _bool_from_env(name: str, default: bool, env: dict[str, str] | None = None) -> bool:
    source = env if env is not None else os.environ
    value = str(source.get(name, str(default))).strip().lower()
    return value in {"1", "true", "yes", "on"}


def load_library_config(env: dict[str, str] | None = None) -> LibraryConfig:
    library_root = _path_from_env("MODEL_LIBRARY_PATH", ".", env)
    return LibraryConfig(
        model_library_path=library_root,
        incoming_releases_path=_path_from_env("INCOMING_RELEASES_PATH", "incoming", env),
        approved_catalog_path=_path_from_env("APPROVED_CATALOG_PATH", "data/catalog.json", env),
        rejected_archive_path=_path_from_env("REJECTED_ARCHIVE_PATH", "archive/rejected", env),
        custom_orders_path=_path_from_env("CUSTOM_ORDERS_PATH", "data/quote-requests.json", env),
        reports_path=_path_from_env("REPORTS_PATH", "reports", env),
        scan_interval_minutes=_int_from_env("SCAN_INTERVAL_MINUTES", 30, env),
        auto_scan_enabled=_bool_from_env("AUTO_SCAN_ENABLED", False, env),
    )


def resolve_library_path(path: Path, library_root: Path) -> Path:
    if path.is_absolute():
        return path
    return library_root / path


def resolved_library_config(config: LibraryConfig | None = None) -> LibraryConfig:
    active = config or load_library_config()
    root = active.model_library_path.resolve()
    return LibraryConfig(
        model_library_path=root,
        incoming_releases_path=resolve_library_path(active.incoming_releases_path, root),
        approved_catalog_path=resolve_library_path(active.approved_catalog_path, root),
        rejected_archive_path=resolve_library_path(active.rejected_archive_path, root),
        custom_orders_path=resolve_library_path(active.custom_orders_path, root),
        reports_path=resolve_library_path(active.reports_path, root),
        scan_interval_minutes=active.scan_interval_minutes,
        auto_scan_enabled=active.auto_scan_enabled,
    )


def library_path_status(config: LibraryConfig | None = None) -> dict[str, Any]:
    active = resolved_library_config(config)
    checks = [
        ("MODEL_LIBRARY_PATH", "Model library root", active.model_library_path, "directory"),
        ("INCOMING_RELEASES_PATH", "Incoming releases", active.incoming_releases_path, "directory"),
        ("APPROVED_CATALOG_PATH", "Approved catalog", active.approved_catalog_path, "file"),
        ("REJECTED_ARCHIVE_PATH", "Rejected archive", active.rejected_archive_path, "directory"),
        ("CUSTOM_ORDERS_PATH", "Custom orders", active.custom_orders_path, "file"),
        ("REPORTS_PATH", "Reports", active.reports_path, "directory" if not active.reports_path.suffix else "file"),
    ]
    paths = []
    for env_name, label, path, expected_type in checks:
        paths.append(
            {
                "env_name": env_name,
                "label": label,
                "path": str(path),
                "expected_type": expected_type,
                "exists": path.exists(),
                "parent_exists": path.parent.exists(),
            }
        )

    missing = [item for item in paths if not item["exists"]]
    return {
        "ok": not missing,
        "paths": paths,
        "missing": missing,
        "scanner_config": {
            "auto_scan_enabled": active.auto_scan_enabled,
            "scan_interval_minutes": active.scan_interval_minutes,
        },
        "instructions": library_setup_instructions(),
    }


def library_setup_instructions() -> list[str]:
    return [
        "Choose the local synced cloud-drive folder for MODEL_LIBRARY_PATH.",
        "Keep the incoming, approved catalog, rejected archive, custom orders, and reports paths available offline on the print workstation.",
        "Create missing folders or files before relying on the watcher/intake workflow.",
        "Source model files must never be moved, renamed, or deleted automatically.",
    ]
