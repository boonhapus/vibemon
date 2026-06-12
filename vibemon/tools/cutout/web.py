"""HTTP routes for the cutout web UI."""

import base64
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlparse

import structlog

from core import (
    CutoutOptions,
    RembgModel,
    cutout_from_image,
    image_to_png_bytes,
    load_image,
    load_image_bytes,
    model_catalog,
    parse_bbox,
    resolve_output,
    save_image,
)
from paths import REPO_ROOT, STATIC_DIR

_LOGGER = structlog.get_logger(__name__)


def resolve_repo_path(raw_path: str, *, must_exist: bool = True):
    import pathlib

    candidate = (
        (REPO_ROOT / raw_path).resolve()
        if not pathlib.Path(raw_path).is_absolute()
        else pathlib.Path(raw_path).resolve()
    )
    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Path must stay inside the repository: {REPO_ROOT}") from exc
    if must_exist and not candidate.is_file():
        raise FileNotFoundError(f"File not found: {candidate}")
    return candidate


def parse_cutout_options(payload: dict[str, Any]) -> CutoutOptions:
    bbox = parse_bbox(payload.get("bbox"))
    model_name = payload.get("model", RembgModel.ISNET_ANIME.value)
    try:
        model = RembgModel(model_name)
    except ValueError as exc:
        raise ValueError(f"Unknown model: {model_name}") from exc

    return CutoutOptions(
        model=model,
        matting=bool(payload.get("matting", True)),
        pad=int(payload.get("pad", 4)),
        bbox=bbox,
        auto_crop=bool(payload.get("auto_crop", True)),
        foreground_threshold=int(payload.get("foreground_threshold", 240)),
        background_threshold=int(payload.get("background_threshold", 15)),
        erode_size=int(payload.get("erode_size", 2)),
        crop_alpha_threshold=int(payload.get("crop_alpha_threshold", 8)),
        post_process_mask=bool(payload.get("post_process_mask", True)),
    )


def decode_image_payload(payload: dict[str, Any]) -> tuple[bytes | None, str | None]:
    image_b64 = payload.get("image_base64")
    if isinstance(image_b64, str) and image_b64:
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        return base64.b64decode(image_b64), None
    return None, payload.get("path")


class CutoutHandler(BaseHTTPRequestHandler):
    server_version = "VibemonCutout/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        _LOGGER.info("http_request", message=format % args)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("Expected a JSON object.")
        return parsed

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        if route in {"/", "/index.html"}:
            index = STATIC_DIR / "index.html"
            self._send_bytes(HTTPStatus.OK, index.read_bytes(), "text/html; charset=utf-8")
            return

        if route == "/api/health":
            self._send_json(
                HTTPStatus.OK,
                {"ok": True, "repo_root": str(REPO_ROOT), "static_dir": str(STATIC_DIR)},
            )
            return

        if route == "/api/models":
            self._send_json(HTTPStatus.OK, {"models": model_catalog()})
            return

        if route == "/api/source":
            query = parse_qs(parsed.query)
            raw_path = query.get("path", [None])[0]
            if not raw_path:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing path query parameter."})
                return
            try:
                source = resolve_repo_path(raw_path)
                mime, _ = mimetypes.guess_type(source)
                self._send_bytes(
                    HTTPStatus.OK,
                    source.read_bytes(),
                    mime or "application/octet-stream",
                )
            except (FileNotFoundError, ValueError) as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Unknown route: {route}"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        try:
            payload = self._read_json()
        except (json.JSONDecodeError, ValueError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON body: {exc}"})
            return

        if route == "/api/cutout":
            self._handle_cutout(payload, save_path=None)
            return

        if route == "/api/cutout-save":
            save_path = payload.get("output_path")
            if not isinstance(save_path, str) or not save_path:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "output_path is required."})
                return
            self._handle_cutout(payload, save_path=save_path)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Unknown route: {route}"})

    def _handle_cutout(self, payload: dict[str, Any], *, save_path: str | None) -> None:
        try:
            options = parse_cutout_options(payload)
            image_bytes, path = decode_image_payload(payload)
            if image_bytes is not None:
                image = load_image_bytes(image_bytes)
                source_label = "upload"
            elif path:
                source = resolve_repo_path(path)
                image = load_image(source)
                source_label = str(source)
            else:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Provide image_base64 or path."})
                return

            _LOGGER.info("web_cutout_request", source=source_label, model=options.model.value)
            result = cutout_from_image(image, options)
            png = image_to_png_bytes(result.image)

            saved_to = None
            if save_path is not None:
                destination = resolve_output(resolve_repo_path(save_path, must_exist=False))
                save_image(result.image, destination)
                saved_to = str(destination)

            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "image_base64": base64.b64encode(png).decode("ascii"),
                    "width": result.image.width,
                    "height": result.image.height,
                    "duration_ms": result.duration_ms,
                    "pre_crop_bbox": None
                    if result.pre_crop_bbox is None
                    else {
                        "x": result.pre_crop_bbox.x,
                        "y": result.pre_crop_bbox.y,
                        "width": result.pre_crop_bbox.width,
                        "height": result.pre_crop_bbox.height,
                    },
                    "post_crop_bounds": result.post_crop_bounds,
                    "saved_to": saved_to,
                },
            )
        except (FileNotFoundError, ValueError) as exc:
            _LOGGER.warning("web_cutout_failed", error=str(exc))
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
