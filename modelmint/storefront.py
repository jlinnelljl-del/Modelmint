from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from modelmint.library_config import library_path_status, load_library_config, resolved_library_config
from modelmint.shopify_adapter import ShopifyVariantMappingError
from modelmint.shopify_checkout import create_shopify_cart_for_product
from modelmint.shopify_client import ShopifyAPIError, ShopifyConfigError, shopify_debug_status, shopify_status
from modelmint.storefront_data import append_quote_request, build_mock_cart_line, product_by_handle, storefront_payload
from modelmint.web import validate_bind_host


STATIC_ROOT = Path(__file__).parent / "storefront_static"
LIBRARY_CONFIG = resolved_library_config(load_library_config())
QUOTE_REQUESTS_PATH = LIBRARY_CONFIG.custom_orders_path


class StorefrontHandler(BaseHTTPRequestHandler):
    server_version = "ModelMintStorefront/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/app.css", "/app.js", "/theme.css"}:
            self.send_static(parsed.path.lstrip("/"))
        elif parsed.path.startswith("/assets/"):
            self.send_static(parsed.path.lstrip("/"))
        elif parsed.path == "/api/storefront":
            payload = storefront_payload()
            payload["shopify"]["connection"] = shopify_status()
            self.send_json(payload)
        elif parsed.path == "/api/shopify/status":
            payload = storefront_payload()
            self.send_json(shopify_debug_status(payload["products"]))
        elif parsed.path == "/" or self.is_app_route(parsed.path):
            self.send_static("index.html")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/quote-requests":
            try:
                record = append_quote_request(QUOTE_REQUESTS_PATH, self.read_json_body())
            except (ValueError, KeyError, json.JSONDecodeError) as error:
                self.send_error(HTTPStatus.BAD_REQUEST, str(error))
                return
            self.send_json({"quote_request": record})
            return

        if parsed.path == "/api/cart-lines":
            try:
                payload = self.read_json_body()
                product = product_by_handle(payload["handle"])
                if not product:
                    raise KeyError("Product not found.")
                cart_line = build_mock_cart_line(product, payload.get("selections", {}))
            except (ValueError, KeyError, json.JSONDecodeError) as error:
                self.send_error(HTTPStatus.BAD_REQUEST, str(error))
                return
            self.send_json({"cart_line": cart_line, "checkout_enabled": False})
            return

        if parsed.path == "/api/shopify/cart/create":
            try:
                payload = self.read_json_body()
                product = product_by_handle(payload["handle"])
                if not product:
                    raise KeyError("Product not found.")
                result = create_shopify_cart_for_product(product, payload.get("selections", {}))
            except ShopifyConfigError as error:
                self.send_json({"ok": False, "error": str(error), "mock_cart_preserved": True}, status=HTTPStatus.SERVICE_UNAVAILABLE)
                return
            except ShopifyVariantMappingError as error:
                self.send_json({"ok": False, "error": str(error), "mock_cart_preserved": True}, status=HTTPStatus.CONFLICT)
                return
            except ShopifyAPIError as error:
                self.send_json({"ok": False, "error": str(error), "mock_cart_preserved": True}, status=HTTPStatus.BAD_GATEWAY)
                return
            except (ValueError, KeyError, json.JSONDecodeError) as error:
                self.send_error(HTTPStatus.BAD_REQUEST, str(error))
                return
            self.send_json({"ok": True, "checkoutUrl": result["checkoutUrl"], "cart": result["cart"], "mock_cart_preserved": True})
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    @staticmethod
    def is_app_route(path: str) -> bool:
        return path in {"/shop", "/cart", "/custom-orders", "/business", "/events", "/new", "/about", "/contact", "/dev/shopify-status"} or path.startswith("/shop/")

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def send_static(self, name: str) -> None:
        path = (STATIC_ROOT / name).resolve()
        if STATIC_ROOT.resolve() not in path.parents and path != STATIC_ROOT.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local ModelMint customer-facing storefront.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", default=8780, type=int, help="Port to bind.")
    parser.add_argument("--allow-lan", action="store_true", help="Allow binding to a non-localhost address on a trusted private network.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    validate_bind_host(args.host, args.allow_lan)
    status = library_path_status()
    server = ThreadingHTTPServer((args.host, args.port), StorefrontHandler)
    print(f"ModelMint storefront running at http://{args.host}:{args.port}")
    print("Website-1 uses sample data and local quote records; Shopify checkout is not connected yet.")
    if not status["ok"]:
        print("Library setup needs attention before production use:")
        for item in status["missing"]:
            print(f"- Missing {item['label']}: {item['path']}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
