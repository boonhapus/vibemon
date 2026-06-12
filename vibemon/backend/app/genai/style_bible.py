"""Bundled style-bible reference images for GenAI sprite generation."""

import functools as ft
import pathlib

from app.core import asset_paths

_STYLE_BIBLE_DIR = pathlib.Path(__file__).parent / "style_bible"
_HATCHLING_PNG = "hatchling-silhouette.png"


def load_trainer_style_bible_png() -> bytes:
    """Return canonical ``trainer.png`` bytes (single on-disk copy under frontend static)."""
    return asset_paths.load_canonical_trainer_raw_png()


@ft.cache
def load_hatchling_style_bible_png() -> bytes:
    """Return bundled ``hatchling-silhouette.png`` bytes."""
    return (_STYLE_BIBLE_DIR / _HATCHLING_PNG).read_bytes()
