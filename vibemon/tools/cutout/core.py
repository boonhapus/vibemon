"""Shared rembg cutout logic for CLI and web UI."""

import dataclasses
import enum
import gc
import logging
import pathlib
import time

import numpy as np
import structlog
from PIL import Image
from rembg import new_session, remove

_LOGGER = structlog.get_logger(__name__)

_ACTIVE_MODEL: str | None = None
_SESSION_CACHE: dict[str, object] = {}


class RembgModel(enum.StrEnum):
    ISNET_ANIME = "isnet-anime"
    ISNET_GENERAL = "isnet-general-use"
    U2NET_HUMAN = "u2net_human_seg"
    BIRFNET_GENERAL = "birefnet-general"
    BIRFNET_PORTRAIT = "birefnet-portrait"
    BIRFNET_DIS = "birefnet-dis"
    BIRFNET_HRSOD = "birefnet-hrsod"
    BIRFNET_COD = "birefnet-cod"
    BIRFNET_MASSIVE = "birefnet-massive"
    BRIA_RMBG = "bria-rmbg"
    SAM = "sam"


@dataclasses.dataclass(frozen=True, slots=True)
class ModelInfo:
    id: str
    label: str
    size: str
    speed: str
    quality: str
    best_for: str
    note: str = ""


MODEL_CATALOG: tuple[ModelInfo, ...] = (
    ModelInfo("isnet-anime", "isnet-anime", "~43 MB", "Medium", "Very high", "Anime and illustrated characters.", "Default for Pokémon-style trainer sprites."),
    ModelInfo("isnet-general-use", "isnet-general-use", "~43 MB", "Medium", "Very high", "General scenes with crisp edges."),
    ModelInfo("u2net_human_seg", "u2net_human_seg", "~176 MB", "Medium", "High", "Human figures and portraits."),
    ModelInfo("birefnet-general", "birefnet-general", "~43 MB", "Medium", "Very high", "Newer general-purpose model."),
    ModelInfo("birefnet-portrait", "birefnet-portrait", "~43 MB", "Medium", "Very high", "Human portraits and character busts."),
    ModelInfo("birefnet-dis", "birefnet-dis", "~43 MB", "Medium", "High", "Dichotomous segmentation with clean object edges."),
    ModelInfo("birefnet-hrsod", "birefnet-hrsod", "~43 MB", "Medium", "High", "High-resolution salient object detection."),
    ModelInfo("birefnet-cod", "birefnet-cod", "~43 MB", "Medium", "High", "Concealed or low-contrast object edges."),
    ModelInfo("birefnet-massive", "birefnet-massive", "~43 MB", "Slow", "Very high", "Multi-dataset BiRefNet; often excellent but heavy."),
    ModelInfo("bria-rmbg", "bria-rmbg", "~43 MB", "Medium", "Very high", "Recent general background-removal model."),
    ModelInfo("sam", "sam", "~374 MB", "Slow", "Very high", "Segment Anything; slowest, most flexible."),
)


def model_catalog() -> list[dict[str, str]]:
    return [
        {
            "id": item.id,
            "label": item.label,
            "size": item.size,
            "speed": item.speed,
            "quality": item.quality,
            "best_for": item.best_for,
            "note": item.note,
        }
        for item in MODEL_CATALOG
    ]


@dataclasses.dataclass(frozen=True, slots=True)
class Bbox:
    """Region to process, in source-image pixel coordinates."""

    x: int
    y: int
    width: int
    height: int

    def as_box(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def clamp(self, *, width: int, height: int) -> Bbox:
        x0 = max(0, min(self.x, width))
        y0 = max(0, min(self.y, height))
        x1 = max(x0, min(self.x + self.width, width))
        y1 = max(y0, min(self.y + self.height, height))
        return Bbox(x=x0, y=y0, width=x1 - x0, height=y1 - y0)


@dataclasses.dataclass(frozen=True, slots=True)
class CutoutOptions:
    model: RembgModel = RembgModel.ISNET_ANIME
    matting: bool = True
    pad: int = 4
    bbox: Bbox | None = None
    auto_crop: bool = True
    foreground_threshold: int = 240
    background_threshold: int = 15
    erode_size: int = 2
    crop_alpha_threshold: int = 8
    post_process_mask: bool = True


@dataclasses.dataclass(frozen=True, slots=True)
class CutoutResult:
    image: Image.Image
    pre_crop_bbox: Bbox | None
    post_crop_bounds: dict[str, int] | None
    duration_ms: float


def configure_logging(*, verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )


def resolve_input(path: pathlib.Path) -> pathlib.Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Input file does not exist: {resolved}")
    return resolved


def resolve_output(path: pathlib.Path) -> pathlib.Path:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def load_image(path: pathlib.Path) -> Image.Image:
    _LOGGER.info("loading_image", path=str(path))
    started = time.perf_counter()
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    _LOGGER.info(
        "image_loaded",
        path=str(path),
        width=image.width,
        height=image.height,
        mode=image.mode,
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return image


def load_image_bytes(data: bytes) -> Image.Image:
    _LOGGER.info("loading_image_bytes", byte_length=len(data))
    started = time.perf_counter()
    from io import BytesIO

    with Image.open(BytesIO(data)) as opened:
        image = opened.convert("RGB")
    _LOGGER.info(
        "image_loaded",
        source="bytes",
        width=image.width,
        height=image.height,
        mode=image.mode,
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return image


def release_sessions() -> None:
    """Drop cached ONNX sessions so only one model stays resident at a time."""
    global _ACTIVE_MODEL

    if not _SESSION_CACHE:
        return

    released = list(_SESSION_CACHE.keys())
    _SESSION_CACHE.clear()
    _ACTIVE_MODEL = None
    gc.collect()
    _LOGGER.info("rembg_sessions_released", released=released)


def get_session(model: RembgModel) -> object:
    global _ACTIVE_MODEL

    cached = _SESSION_CACHE.get(model.value)
    if cached is not None:
        _LOGGER.debug("rembg_session_cache_hit", model=model.value)
        return cached

    if _SESSION_CACHE:
        _LOGGER.info(
            "rembg_session_switch",
            from_model=_ACTIVE_MODEL,
            to_model=model.value,
        )
        release_sessions()

    _LOGGER.info("creating_rembg_session", model=model.value)
    started = time.perf_counter()
    session = new_session(model.value)
    _SESSION_CACHE[model.value] = session
    _ACTIVE_MODEL = model.value
    _LOGGER.info(
        "rembg_session_ready",
        model=model.value,
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return session


def _apply_bbox(image: Image.Image, bbox: Bbox | None) -> tuple[Image.Image, Bbox | None]:
    if bbox is None:
        return image, None

    clamped = bbox.clamp(width=image.width, height=image.height)
    if clamped.width == 0 or clamped.height == 0:
        raise ValueError("Bounding box is empty after clamping to the image.")

    _LOGGER.info(
        "pre_crop_bbox",
        x=clamped.x,
        y=clamped.y,
        width=clamped.width,
        height=clamped.height,
    )
    return image.crop(clamped.as_box()), clamped


def _remove_background(image: Image.Image, *, session: object, options: CutoutOptions) -> Image.Image:
    _LOGGER.info(
        "removing_background",
        matting=options.matting,
        alpha_matting_foreground_threshold=options.foreground_threshold,
        alpha_matting_background_threshold=options.background_threshold,
        alpha_matting_erode_size=options.erode_size,
        post_process_mask=options.post_process_mask,
    )
    started = time.perf_counter()
    result = remove(
        image,
        session=session,
        alpha_matting=options.matting,
        alpha_matting_foreground_threshold=options.foreground_threshold,
        alpha_matting_background_threshold=options.background_threshold,
        alpha_matting_erode_size=options.erode_size,
        post_process_mask=options.post_process_mask,
    ).convert("RGBA")
    _LOGGER.info(
        "background_removed",
        width=result.width,
        height=result.height,
        mode=result.mode,
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return result


def _crop_to_subject(
    image: Image.Image,
    *,
    pad: int,
    crop_alpha_threshold: int,
) -> tuple[Image.Image, dict[str, int]]:
    alpha = np.array(image)[:, :, 3]
    subject_pixels = int(np.count_nonzero(alpha > crop_alpha_threshold))
    _LOGGER.debug(
        "alpha_channel_stats",
        subject_pixels=subject_pixels,
        total_pixels=alpha.size,
        crop_alpha_threshold=crop_alpha_threshold,
    )

    ys, xs = np.where(alpha > crop_alpha_threshold)
    if len(xs) == 0:
        raise ValueError("Model found no subject — try a different model, bbox, or matting settings.")

    height, width = alpha.shape
    bounds = {
        "x0": max(0, int(xs.min()) - pad),
        "y0": max(0, int(ys.min()) - pad),
        "x1": min(width, int(xs.max()) + 1 + pad),
        "y1": min(height, int(ys.max()) + 1 + pad),
    }
    _LOGGER.info(
        "cropping_to_subject",
        pad=pad,
        source_width=width,
        source_height=height,
        **bounds,
        crop_width=bounds["x1"] - bounds["x0"],
        crop_height=bounds["y1"] - bounds["y0"],
    )
    cropped = image.crop((bounds["x0"], bounds["y0"], bounds["x1"], bounds["y1"]))
    return cropped, bounds


def cutout_from_image(
    image: Image.Image,
    options: CutoutOptions,
    *,
    session: object | None = None,
) -> CutoutResult:
    total_started = time.perf_counter()
    _LOGGER.info(
        "cutout_started",
        source_width=image.width,
        source_height=image.height,
        model=options.model.value,
        matting=options.matting,
        pad=options.pad,
        auto_crop=options.auto_crop,
        bbox=None if options.bbox is None else dataclasses.asdict(options.bbox),
    )

    working, pre_crop_bbox = _apply_bbox(image, options.bbox)
    active_session = session or get_session(options.model)
    cutout = _remove_background(working, session=active_session, options=options)

    post_crop_bounds = None
    if options.auto_crop:
        cutout, post_crop_bounds = _crop_to_subject(
            cutout,
            pad=options.pad,
            crop_alpha_threshold=options.crop_alpha_threshold,
        )

    duration_ms = round((time.perf_counter() - total_started) * 1000, 1)
    _LOGGER.info(
        "cutout_complete",
        model=options.model.value,
        matting=options.matting,
        pad=options.pad,
        output_width=cutout.width,
        output_height=cutout.height,
        pre_crop_bbox=None if pre_crop_bbox is None else dataclasses.asdict(pre_crop_bbox),
        post_crop_bounds=post_crop_bounds,
        duration_ms=duration_ms,
    )
    return CutoutResult(
        image=cutout,
        pre_crop_bbox=pre_crop_bbox,
        post_crop_bounds=post_crop_bounds,
        duration_ms=duration_ms,
    )


def cutout_file(
    src: pathlib.Path,
    dst: pathlib.Path,
    options: CutoutOptions,
) -> CutoutResult:
    input_path = resolve_input(src)
    output_path = resolve_output(dst)
    result = cutout_from_image(load_image(input_path), options)
    save_image(result.image, output_path)
    return result


def save_image(image: Image.Image, path: pathlib.Path) -> None:
    _LOGGER.info("saving_output", path=str(path), width=image.width, height=image.height)
    started = time.perf_counter()
    image.save(path)
    _LOGGER.info(
        "output_saved",
        path=str(path),
        width=image.width,
        height=image.height,
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )


def image_to_png_bytes(image: Image.Image) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def parse_bbox(raw: tuple[int, int, int, int] | list[int] | None) -> Bbox | None:
    if raw is None:
        return None
    if len(raw) != 4:
        raise ValueError("Bounding box must have exactly four integers: x, y, width, height.")
    x, y, width, height = (int(value) for value in raw)
    if width <= 0 or height <= 0:
        raise ValueError("Bounding box width and height must be positive.")
    return Bbox(x=x, y=y, width=width, height=height)
