"""Canonical on-disk asset locations shared by genai, workflows, and storage.

There is exactly one trainer reference PNG on disk: the shipped
``frontend/static/game/sprites/trainer.png``. GenAI style-bible prompts,
database bootstrap seeding, and static asset generation all read it from here.
"""

import functools as ft
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
GENERATED_DIR = REPO_ROOT / ".generated"

FRONTEND_DIR = REPO_ROOT / "vibemon" / "frontend"
ASSET_PROMPTS_DIR = FRONTEND_DIR / "asset-prompts" / "game"
STYLE_ANCHORS_DIR = FRONTEND_DIR / "asset-prompts"
STATIC_GAME_DIR = FRONTEND_DIR / "static" / "game"
STATIC_GAME_SPRITES_DIR = STATIC_GAME_DIR / "sprites"

CANONICAL_TRAINER_REFERENCE = STATIC_GAME_SPRITES_DIR / "trainer.png"
CANONICAL_TRAINER_DISPLAY = STATIC_GAME_SPRITES_DIR / "trainer@128.png"


@ft.cache
def load_canonical_trainer_raw_png() -> bytes:
    """Read bytes for the default trainer GenAI/style-bible source."""
    if not CANONICAL_TRAINER_REFERENCE.is_file():
        raise FileNotFoundError(f"Canonical trainer sprite is missing at {CANONICAL_TRAINER_REFERENCE}")
    return CANONICAL_TRAINER_REFERENCE.read_bytes()


@ft.cache
def load_canonical_trainer_display_png() -> bytes:
    """Read bytes for the default trainer snapped display sprite."""
    if not CANONICAL_TRAINER_DISPLAY.is_file():
        raise FileNotFoundError(f"Canonical snapped trainer sprite is missing at {CANONICAL_TRAINER_DISPLAY}")
    return CANONICAL_TRAINER_DISPLAY.read_bytes()
