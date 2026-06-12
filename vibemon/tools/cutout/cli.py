"""CLI for rembg background removal and sprite cutout."""

import pathlib
from typing import Annotated

import cyclopts
import structlog

from core import CutoutOptions, RembgModel, configure_logging, cutout_file, parse_bbox

_LOGGER = structlog.get_logger(__name__)

IO_OPTIONS = cyclopts.Group("Input / output", sort_key=0)
MATTING_OPTIONS = cyclopts.Group("Matting", sort_key=1)
LOG_OPTIONS = cyclopts.Group("Logging", sort_key=2)

app = cyclopts.App(
    help=(
        "Remove an image background with rembg and crop to the subject.\n\n"
        "Use --bbox to pre-crop a screenshot region before matting (excludes UI chrome).\n"
        "For interactive bbox selection, run: uv run app\n\n"
        "Examples:\n"
        "  uv run cli input.png output.png\n"
        "  uv run cli input.png output.png --bbox 700,20,400,500\n"
        "  uv run cli input.png output.png --model isnet-anime --no-matting --erode-size 0"
    )
)


@app.default
def main(
    input: Annotated[
        pathlib.Path,
        cyclopts.Parameter(help="Source image path (PNG, JPEG, WebP, etc.)."),
    ],
    output: Annotated[
        pathlib.Path,
        cyclopts.Parameter(help="Destination PNG path (parent directories are created)."),
    ],
    *,
    bbox: Annotated[
        str | None,
        cyclopts.Parameter(
            group=IO_OPTIONS,
            help="Pre-crop region as x,y,width,height before rembg (excludes surrounding UI).",
        ),
    ] = None,
    no_auto_crop: Annotated[
        bool,
        cyclopts.Parameter(
            group=IO_OPTIONS,
            name="--no-auto-crop",
            help="Keep the pre-crop frame instead of tightening to alpha bounds.",
        ),
    ] = False,
    model: Annotated[
        RembgModel,
        cyclopts.Parameter(
            group=MATTING_OPTIONS,
            help="rembg model name (default: isnet-anime).",
        ),
    ] = RembgModel.ISNET_ANIME,
    matting: Annotated[
        bool,
        cyclopts.Parameter(
            group=MATTING_OPTIONS,
            name="--matting",
            negative="--no-matting",
            help="Enable alpha matting for crisper edges (slower).",
        ),
    ] = True,
    pad: Annotated[
        int,
        cyclopts.Parameter(
            group=IO_OPTIONS,
            help="Transparent padding in pixels around the auto-cropped subject.",
        ),
    ] = 4,
    erode_size: Annotated[
        int,
        cyclopts.Parameter(
            group=MATTING_OPTIONS,
            help="Alpha-matting erosion radius; lower preserves thin limbs (default: 2).",
        ),
    ] = 2,
    foreground_threshold: Annotated[
        int,
        cyclopts.Parameter(group=MATTING_OPTIONS, help="Alpha-matting foreground threshold."),
    ] = 240,
    background_threshold: Annotated[
        int,
        cyclopts.Parameter(group=MATTING_OPTIONS, help="Alpha-matting background threshold."),
    ] = 15,
    crop_alpha_threshold: Annotated[
        int,
        cyclopts.Parameter(group=IO_OPTIONS, help="Alpha value treated as subject during auto-crop."),
    ] = 8,
    verbose: Annotated[
        bool,
        cyclopts.Parameter(
            group=LOG_OPTIONS,
            help="Emit debug-level structlog output (alpha stats, timings, bounds).",
        ),
    ] = False,
) -> None:
    """Remove the background and write a transparent PNG cutout."""
    configure_logging(verbose=verbose)
    if pad < 0:
        raise SystemExit("--pad must be zero or positive.")
    if erode_size < 0:
        raise SystemExit("--erode-size must be zero or positive.")

    parsed_bbox = None
    if bbox is not None:
        try:
            parts = [int(part.strip()) for part in bbox.split(",")]
            parsed_bbox = parse_bbox(parts)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    options = CutoutOptions(
        model=model,
        matting=matting,
        pad=pad,
        bbox=parsed_bbox,
        auto_crop=not no_auto_crop,
        foreground_threshold=foreground_threshold,
        background_threshold=background_threshold,
        erode_size=erode_size,
        crop_alpha_threshold=crop_alpha_threshold,
    )
    _LOGGER.debug(
        "cli_options",
        input=str(input),
        output=str(output),
        options=options,
        verbose=verbose,
    )
    try:
        cutout_file(input, output, options)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


def main() -> None:
    app()


if __name__ == "__main__":
    main()
