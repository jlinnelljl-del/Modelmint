from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modelmint.library_config import library_path_status, load_library_config, resolved_library_config
from modelmint.schemas import DEFAULT_CATALOG, MEDIA_EXTENSIONS, MODEL_EXTENSIONS


@dataclass(frozen=True)
class IntakeFile:
    path: Path
    extension: str
    kind: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "unknown"


def stable_id(prefix: str, *parts: str) -> str:
    joined = "|".join(parts)
    digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def load_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return deepcopy(DEFAULT_CATALOG)
    with path.open("r", encoding="utf-8") as handle:
        catalog = json.load(handle)
    for key, value in DEFAULT_CATALOG.items():
        catalog.setdefault(key, deepcopy(value))
    catalog["schema_version"] = DEFAULT_CATALOG["schema_version"]
    return catalog


def save_catalog(path: Path, catalog: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(catalog, handle, indent=2, sort_keys=True)
        handle.write("\n")


def relative_or_absolute(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def detect_release_date(release_name: str) -> str:
    match = re.search(r"(20\d{2})[-_ ]?([01]\d)", release_name)
    if not match:
        return ""
    year, month = match.groups()
    return f"{year}-{month}-01"


def infer_model_name(file_path: Path) -> str:
    name = file_path.stem
    name = re.sub(r"[-_ ]?(supported|unsupported|presupported|pre-supported)$", "", name, flags=re.I)
    name = re.sub(r"[_-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title() if name else file_path.stem


def infer_model_type(file_path: Path) -> str:
    lower = " ".join(part.lower() for part in file_path.parts)
    if "hueforge" in lower:
        return "HueForge"
    if "coaster" in lower:
        return "Coaster"
    if "dragon" in lower:
        return "Dragon"
    if "dice" in lower and "tower" in lower:
        return "Dice Tower"
    if "flexi" in lower or "articulated" in lower:
        return "Articulated"
    return "Model"


def infer_category(model_type: str) -> str:
    if model_type in {"Coaster", "HueForge"}:
        return "Home and Decor"
    if model_type in {"Dragon", "Articulated"}:
        return "Figures and Toys"
    if model_type == "Dice Tower":
        return "Tabletop Gaming"
    return "Unreviewed"


def is_multi_color(file_path: Path) -> bool:
    lower = " ".join(part.lower() for part in file_path.parts)
    return file_path.suffix.lower() == ".3mf" or "multi" in lower or "hueforge" in lower


def infer_color_slot_count(file_path: Path) -> int:
    lower = " ".join(part.lower() for part in file_path.parts)
    if "hueforge" in lower:
        return 4
    if file_path.suffix.lower() == ".3mf" or "multi" in lower:
        return 3
    return 0


def collect_release_files(release_folder: Path) -> list[IntakeFile]:
    files: list[IntakeFile] = []
    for path in sorted(release_folder.rglob("*")):
        if not path.is_file():
            continue
        extension = path.suffix.lower()
        if extension in MODEL_EXTENSIONS:
            files.append(IntakeFile(path=path, extension=extension, kind="model"))
        elif extension in MEDIA_EXTENSIONS:
            files.append(IntakeFile(path=path, extension=extension, kind="media"))
    return files


def has_direct_intake_files(folder: Path) -> bool:
    for path in folder.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() in MODEL_EXTENSIONS or path.suffix.lower() in MEDIA_EXTENSIONS:
            return True
    return False


def ensure_creator(catalog: dict[str, Any], creator_name: str) -> tuple[dict[str, Any], bool]:
    creator_id = stable_id("creator", slugify(creator_name))
    existing = next((item for item in catalog["creators"] if item["creator_id"] == creator_id), None)
    if existing:
        return existing, False
    record = {
        "creator_id": creator_id,
        "creator_name": creator_name,
        "source_platform": "",
        "commercial_license_status": "Unknown",
        "license_notes": "",
        "active_status": "Active",
        "default_attribution_text": "",
        "notes": "",
    }
    catalog["creators"].append(record)
    return record, True


def ensure_release(
    catalog: dict[str, Any],
    creator_id: str,
    creator_name: str,
    release_folder: Path,
    project_root: Path,
) -> tuple[dict[str, Any], bool]:
    source_folder_path = relative_or_absolute(release_folder, project_root)
    release_name = release_folder.name
    release_id = stable_id("release", creator_id, source_folder_path)
    existing = next((item for item in catalog["releases"] if item["release_id"] == release_id), None)
    if existing:
        return existing, False
    record = {
        "release_id": release_id,
        "creator_id": creator_id,
        "release_name": release_name,
        "release_date": detect_release_date(release_name),
        "source_folder_path": source_folder_path,
        "intake_status": "Needs Review",
        "notes": f"Detected under creator folder: {creator_name}",
    }
    catalog["releases"].append(record)
    return record, True


def choose_primary_model_file(model_files: list[IntakeFile]) -> IntakeFile:
    priority = {".3mf": 0, ".stl": 1, ".obj": 2, ".step": 3}
    return sorted(model_files, key=lambda item: (priority.get(item.extension, 99), len(item.path.parts), item.path.name.lower()))[0]


def group_model_files(model_files: list[IntakeFile]) -> list[list[IntakeFile]]:
    grouped: dict[str, list[IntakeFile]] = {}
    for model_file in model_files:
        key = slugify(infer_model_name(model_file.path))
        grouped.setdefault(key, []).append(model_file)
    return [grouped[key] for key in sorted(grouped)]


def ensure_model(
    catalog: dict[str, Any],
    creator_id: str,
    release_id: str,
    model_file: IntakeFile,
    release_folder: Path,
    project_root: Path,
) -> tuple[dict[str, Any], bool]:
    source_folder_path = relative_or_absolute(model_file.path.parent, project_root)
    primary_file_path = relative_or_absolute(model_file.path, project_root)
    model_name = infer_model_name(model_file.path)
    model_id = stable_id("model", creator_id, release_id, slugify(model_name))
    existing = next(
        (
            item
            for item in catalog["models"]
            if item["model_id"] == model_id
            or (
                item.get("creator_id") == creator_id
                and item.get("release_id") == release_id
                and slugify(item.get("model_name", "")) == slugify(model_name)
            )
        ),
        None,
    )
    if existing:
        existing["primary_file_path"] = primary_file_path
        existing["source_folder_path"] = source_folder_path
        existing["multi_color"] = existing.get("multi_color", False) or is_multi_color(model_file.path)
        existing["color_slot_count"] = max(existing.get("color_slot_count", 0), infer_color_slot_count(model_file.path))
        existing["updated_at"] = utc_now()
        return existing, False

    model_type = infer_model_type(model_file.path.relative_to(release_folder))
    color_slot_count = infer_color_slot_count(model_file.path)
    now = utc_now()
    record = {
        "model_id": model_id,
        "release_id": release_id,
        "creator_id": creator_id,
        "model_name": model_name,
        "source_folder_path": source_folder_path,
        "primary_file_path": primary_file_path,
        "model_type": model_type,
        "category": infer_category(model_type),
        "subcategory": "",
        "status": "Needs Review",
        "review_status": "Needs Review",
        "license_status": "Unknown",
        "attribution_required": True,
        "estimated_complexity": "Unknown",
        "multi_color": is_multi_color(model_file.path),
        "color_slot_count": color_slot_count,
        "production_notes": "",
        "artisan_notes": "",
        "created_at": now,
        "updated_at": now,
    }
    catalog["models"].append(record)
    return record, True


def ensure_color_profile(catalog: dict[str, Any], model: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    color_profile_id = stable_id("color_profile", model["model_id"])
    existing = next((item for item in catalog["color_profiles"] if item["color_profile_id"] == color_profile_id), None)
    if existing:
        existing["color_slot_count"] = model.get("color_slot_count", 0)
        return existing, False

    record = {
        "color_profile_id": color_profile_id,
        "model_id": model["model_id"],
        "color_slot_count": model.get("color_slot_count", 0),
        "slot_1_label": "Color 1",
        "slot_2_label": "Color 2",
        "slot_3_label": "Color 3",
        "slot_4_label": "Color 4",
        "allowed_color_families": [
            "Classic",
            "Pastel",
            "Dark/Gothic",
            "Rainbow",
            "Forest",
            "Fire/Ice",
            "Galaxy",
            "Artist Choice",
            "Custom Notes",
        ],
        "allowed_finishes": [],
        "blocked_finishes": [],
        "finish_notes": "Needs review before customer-facing finish options are enabled.",
        "customer_color_description": "",
        "internal_color_notes": "",
        "artisan_filament_notes": "",
    }
    catalog["color_profiles"].append(record)
    return record, True


def ensure_asset(
    catalog: dict[str, Any],
    model_id: str,
    intake_file: IntakeFile,
    project_root: Path,
    preview_priority: int,
) -> tuple[dict[str, Any], bool]:
    file_path = relative_or_absolute(intake_file.path, project_root)
    asset_id = stable_id("asset", model_id, file_path)
    existing = next((item for item in catalog["assets"] if item["asset_id"] == asset_id), None)
    if existing:
        return existing, False
    record = {
        "asset_id": asset_id,
        "model_id": model_id,
        "asset_type": "model_file" if intake_file.kind == "model" else "preview_image",
        "file_path": file_path,
        "file_name": intake_file.path.name,
        "file_extension": intake_file.extension,
        "preview_priority": preview_priority,
        "notes": "",
    }
    catalog["assets"].append(record)
    return record, True


def release_folders(incoming_root: Path) -> list[tuple[str, Path]]:
    releases: list[tuple[str, Path]] = []
    if not incoming_root.exists():
        return releases

    for creator_folder in sorted(item for item in incoming_root.iterdir() if item.is_dir()):
        direct_files = has_direct_intake_files(creator_folder)
        child_dirs = sorted(item for item in creator_folder.iterdir() if item.is_dir())

        if direct_files:
            releases.append((creator_folder.name, creator_folder))

        for child in child_dirs:
            if collect_release_files(child):
                releases.append((creator_folder.name, child))

    return releases


def run_intake(incoming_root: Path, catalog_path: Path, report_path: Path, project_root: Path) -> dict[str, Any]:
    catalog = load_catalog(catalog_path)
    summary = {
        "created_creators": 0,
        "created_releases": 0,
        "created_models": 0,
        "created_assets": 0,
        "created_color_profiles": 0,
        "duplicate_creators": 0,
        "duplicate_releases": 0,
        "duplicate_models": 0,
        "duplicate_assets": 0,
        "duplicate_color_profiles": 0,
        "releases": [],
    }

    for creator_name, release_folder in release_folders(incoming_root):
        files = collect_release_files(release_folder)
        model_files = [item for item in files if item.kind == "model"]
        media_files = [item for item in files if item.kind == "media"]
        if not model_files:
            continue

        creator, created_creator = ensure_creator(catalog, creator_name)
        summary["created_creators" if created_creator else "duplicate_creators"] += 1

        release, created_release = ensure_release(catalog, creator["creator_id"], creator_name, release_folder, project_root)
        summary["created_releases" if created_release else "duplicate_releases"] += 1

        release_summary = {
            "creator_name": creator_name,
            "release_name": release["release_name"],
            "source_folder_path": release["source_folder_path"],
            "models": [],
        }

        for model_file_group in group_model_files(model_files):
            model_file = choose_primary_model_file(model_file_group)
            model, created_model = ensure_model(
                catalog,
                creator["creator_id"],
                release["release_id"],
                model_file,
                release_folder,
                project_root,
            )
            summary["created_models" if created_model else "duplicate_models"] += 1

            if model["multi_color"]:
                _, created_color_profile = ensure_color_profile(catalog, model)
                summary["created_color_profiles" if created_color_profile else "duplicate_color_profiles"] += 1

            created_asset_count = 0
            all_assets = [*model_file_group, *media_files]
            for index, intake_file in enumerate(all_assets, start=1):
                _, created_asset = ensure_asset(catalog, model["model_id"], intake_file, project_root, index)
                if created_asset:
                    created_asset_count += 1
                    summary["created_assets"] += 1
                else:
                    summary["duplicate_assets"] += 1

            release_summary["models"].append(
                {
                    "model_name": model["model_name"],
                    "status": model["status"],
                    "primary_file_path": model["primary_file_path"],
                    "multi_color": model["multi_color"],
                    "color_slot_count": model["color_slot_count"],
                    "created": created_model,
                    "asset_count_added": created_asset_count,
                }
            )

        summary["releases"].append(release_summary)

    catalog["creators"].sort(key=lambda item: item["creator_name"].lower())
    catalog["releases"].sort(key=lambda item: (item["creator_id"], item["release_name"].lower()))
    catalog["models"].sort(key=lambda item: item["model_name"].lower())
    catalog["assets"].sort(key=lambda item: (item["model_id"], item["preview_priority"], item["file_name"].lower()))
    catalog["color_profiles"].sort(key=lambda item: item["model_id"])

    save_catalog(catalog_path, catalog)
    write_report(report_path, summary)
    return summary


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ModelMint Intake Report",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Summary",
        "",
        f"- Creators created: {summary['created_creators']}",
        f"- Releases created: {summary['created_releases']}",
        f"- Models created: {summary['created_models']}",
        f"- Assets created: {summary['created_assets']}",
        f"- Color profiles created: {summary['created_color_profiles']}",
        f"- Duplicate creators seen: {summary['duplicate_creators']}",
        f"- Duplicate releases seen: {summary['duplicate_releases']}",
        f"- Duplicate models seen: {summary['duplicate_models']}",
        f"- Duplicate assets seen: {summary['duplicate_assets']}",
        f"- Duplicate color profiles seen: {summary['duplicate_color_profiles']}",
        "",
        "## Releases Scanned",
        "",
    ]

    if not summary["releases"]:
        lines.append("No model files were found.")
    else:
        for release in summary["releases"]:
            lines.extend(
                [
                    f"### {release['creator_name']} - {release['release_name']}",
                    "",
                    f"Source: `{release['source_folder_path']}`",
                    "",
                ]
            )
            for model in release["models"]:
                created = "new" if model["created"] else "duplicate/update"
                color_note = ""
                if model["multi_color"]:
                    color_note = f" - multi-color candidate ({model['color_slot_count']} slots estimated)"
                lines.append(f"- `{model['model_name']}` ({created}) - {model['status']}{color_note} - `{model['primary_file_path']}`")
            lines.append("")

    lines.extend(
        [
            "## Safety Notes",
            "",
            "- Source files were not renamed.",
            "- Source files were not moved.",
            "- Source files were not deleted.",
            "- No products were published.",
            "- No emails were sent.",
            "- Human review is still required.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    config = resolved_library_config(load_library_config())
    parser = argparse.ArgumentParser(description="Scan incoming 3D model releases and create review records.")
    parser.add_argument("--incoming", default=config.incoming_releases_path, type=Path, help="Folder containing creator release folders.")
    parser.add_argument("--catalog", default=config.approved_catalog_path, type=Path, help="Catalog JSON output path.")
    parser.add_argument("--report", default=config.intake_report_path, type=Path, help="Human-readable report output path.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    project_root = resolved_library_config(load_library_config()).model_library_path
    status = library_path_status()
    if not status["ok"]:
        print("Library setup needs attention. Intake will still run with the configured paths that are available.")
        for item in status["missing"]:
            print(f"- Missing {item['label']}: {item['path']}")
    summary = run_intake(args.incoming, args.catalog, args.report, project_root)
    print("ModelMint intake complete.")
    print(f"Creators created: {summary['created_creators']}")
    print(f"Releases created: {summary['created_releases']}")
    print(f"Models created: {summary['created_models']}")
    print(f"Assets created: {summary['created_assets']}")
    print(f"Color profiles created: {summary['created_color_profiles']}")
    print(f"Catalog: {args.catalog}")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
