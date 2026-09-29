from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from modelmint.intake import load_catalog, run_intake, save_catalog, utc_now
from modelmint.library_config import library_path_status, load_library_config, resolved_library_config
from modelmint.scanner import load_scanner_status, run_scan_once
from modelmint.schemas import ALLOWED_MODEL_STATUSES, MEDIA_EXTENSIONS


STATIC_ROOT = Path(__file__).parent / "web_static"
LIBRARY_CONFIG = resolved_library_config(load_library_config())
PROJECT_ROOT = LIBRARY_CONFIG.model_library_path
CATALOG_PATH = LIBRARY_CONFIG.approved_catalog_path
INCOMING_PATH = LIBRARY_CONFIG.incoming_releases_path
REPORT_PATH = LIBRARY_CONFIG.intake_report_path

EDITABLE_MODEL_FIELDS = {
    "status",
    "review_status",
    "model_type",
    "category",
    "subcategory",
    "license_status",
    "attribution_required",
    "estimated_complexity",
    "multi_color",
    "color_slot_count",
    "production_notes",
    "artisan_notes",
}


def catalog_snapshot(catalog_path: Path = CATALOG_PATH) -> dict[str, Any]:
    catalog = load_catalog(catalog_path)
    creators = {item["creator_id"]: item for item in catalog["creators"]}
    releases = {item["release_id"]: item for item in catalog["releases"]}
    assets_by_model: dict[str, list[dict[str, Any]]] = {}
    color_profiles_by_model = {item["model_id"]: item for item in catalog["color_profiles"]}

    for asset in catalog["assets"]:
        assets_by_model.setdefault(asset["model_id"], []).append(asset)

    models = []
    for model in catalog["models"]:
        creator = creators.get(model["creator_id"], {})
        release = releases.get(model["release_id"], {})
        model_assets = sorted(
            assets_by_model.get(model["model_id"], []),
            key=lambda item: (item.get("preview_priority", 999), item.get("file_name", "").lower()),
        )
        models.append(
            {
                **model,
                "creator_name": creator.get("creator_name", "Unknown Creator"),
                "release_name": release.get("release_name", "Unknown Release"),
                "release_date": release.get("release_date", ""),
                "assets": model_assets,
                "preview_assets": [item for item in model_assets if item.get("asset_type") == "preview_image"],
                "model_assets": [item for item in model_assets if item.get("asset_type") == "model_file"],
                "color_profile": color_profiles_by_model.get(model["model_id"]),
            }
        )

    return {
        "catalog": catalog,
        "models": sorted(models, key=lambda item: (item["status"], item["creator_name"], item["model_name"])),
        "allowed_statuses": ALLOWED_MODEL_STATUSES,
        "stats": {
            "creators": len(catalog["creators"]),
            "releases": len(catalog["releases"]),
            "models": len(catalog["models"]),
            "assets": len(catalog["assets"]),
            "needs_review": sum(1 for item in catalog["models"] if item.get("status") == "Needs Review"),
            "multi_color": sum(1 for item in catalog["models"] if item.get("multi_color")),
        },
    }


def update_model(catalog_path: Path, model_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    catalog = load_catalog(catalog_path)
    model = next((item for item in catalog["models"] if item["model_id"] == model_id), None)
    if not model:
        raise KeyError(model_id)

    for field, value in updates.items():
        if field not in EDITABLE_MODEL_FIELDS:
            continue
        if field in {"status", "review_status"} and value not in ALLOWED_MODEL_STATUSES:
            raise ValueError(f"Unsupported status: {value}")
        if field == "color_slot_count":
            value = max(0, int(value or 0))
        if field in {"attribution_required", "multi_color"}:
            value = bool(value)
        model[field] = value

    model["updated_at"] = utc_now()
    save_catalog(catalog_path, catalog)
    return model


def safe_asset_path(requested_path: str, project_root: Path = PROJECT_ROOT) -> Path:
    path = (project_root / requested_path).resolve()
    root = project_root.resolve()
    if root not in path.parents and path != root:
        raise ValueError("Asset path escapes project root.")
    if path.suffix.lower() not in MEDIA_EXTENSIONS:
        raise ValueError("Only preview media assets can be served.")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    return path


def validate_bind_host(host: str, allow_lan: bool) -> None:
    local_hosts = {"127.0.0.1", "localhost", "::1"}
    if allow_lan or host in local_hosts:
        return
    raise ValueError("ModelMint admin is internal-only by default. Use --allow-lan only for a trusted private network.")


class ModelMintHandler(BaseHTTPRequestHandler):
    server_version = "ModelMintWeb/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_static("index.html")
        elif parsed.path in {"/app.css", "/app.js"}:
            self.send_static(parsed.path.lstrip("/"))
        elif parsed.path == "/api/catalog":
            self.send_json(catalog_snapshot())
        elif parsed.path == "/api/library-status":
            self.send_json({**library_path_status(), "scanner": load_scanner_status()})
        elif parsed.path == "/asset":
            self.send_asset(parse_qs(parsed.query).get("path", [""])[0])
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/api/intake", "/api/scanner/run"}:
            scanner_status = run_scan_once()
            self.send_json({"summary": scanner_status.get("last_summary", {}), "scanner": scanner_status, "snapshot": catalog_snapshot()})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        prefix = "/api/models/"
        if not parsed.path.startswith(prefix):
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        model_id = unquote(parsed.path[len(prefix) :])
        try:
            body = self.read_json_body()
            model = update_model(CATALOG_PATH, model_id, body)
        except KeyError:
            self.send_error(HTTPStatus.NOT_FOUND, "Model not found.")
            return
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            self.send_error(HTTPStatus.BAD_REQUEST, str(error))
            return

        self.send_json({"model": model, "snapshot": catalog_snapshot()})

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        payload = json.loads(raw or "{}")
        if not isinstance(payload, dict):
            raise TypeError("Request body must be a JSON object.")
        return payload

    def send_static(self, name: str) -> None:
        path = (STATIC_ROOT / name).resolve()
        if STATIC_ROOT.resolve() not in path.parents and path != STATIC_ROOT.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def send_asset(self, requested_path: str) -> None:
        try:
            path = safe_asset_path(unquote(requested_path))
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, "Asset not found.")
            return
        except ValueError as error:
            self.send_error(HTTPStatus.BAD_REQUEST, str(error))
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def send_json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local ModelMint admin website.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", default=8765, type=int, help="Port to bind.")
    parser.add_argument("--allow-lan", action="store_true", help="Allow binding to a non-localhost address on a trusted private network.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    validate_bind_host(args.host, args.allow_lan)
    status = library_path_status()
    server = ThreadingHTTPServer((args.host, args.port), ModelMintHandler)
    print(f"ModelMint admin running at http://{args.host}:{args.port}")
    print("Internal admin only. Do not expose this server to the public internet.")
    if not status["ok"]:
        print("Library setup needs attention. Open /#library-status for details.")
        for item in status["missing"]:
            print(f"- Missing {item['label']}: {item['path']}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
