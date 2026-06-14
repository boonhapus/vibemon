"""Deterministic offline adapter for the asset-generation seam.

A real second adapter for the ``VibemonAssetGenerator`` interface — not a
test-local mock. It draws solid-matte placeholder images at the dimensions and
grid the ``sprite_postprocess`` pipeline expects, so the whole Lifecycle
realization path (christen → manifest) runs offline with no GenAI keys or
network. Selected by ``get_default_asset_generator()`` when
``VIBEMON_GENAI__FAKE_ASSETS=1`` (the ``--fake-assets`` script mode).

Two adapters satisfying one interface make the seam real: callers that design
against this protocol — instead of the Google client's behaviour — stay honest.
"""

from collections.abc import Sequence
import hashlib
import io

from PIL import Image, ImageDraw

from app.domains.move import entity as move_entity
from app.domains.sprite import types as sprite_types
from app.domains.vibemon import brand, entity as vibemon_entity, identity as vibemon_identity

# Grid the sprite sheet is keyed and sliced on (sprite_postprocess defaults).
_SHEET_ROWS = 3
_SHEET_COLS = 3
_CELL = 100
_REFERENCE_DIM = 96

# Canned species names, indexed deterministically by Vibemon id so the same
# Vibemon always christens to the same name across runs.
_NAMES = (
    "Fauxmon", "Mockling", "Stubbeast", "Placeholdra", "Nullkin",
    "Driftfen", "Emberlite", "Gloamtail", "Pixelle", "Vaporhusk",
    "Cindermoth", "Brackish", "Tindersnap", "Murklet", "Quartzeon", "Sablefin",
)


class FakeVibemonAssetGenerator:
    """Offline stand-in for ``genai.vibemon_assets.VibemonAssetGenerator``."""

    async def generate_name(
        self,
        identity: vibemon_identity.Identity,
        moves: Sequence[move_entity.Move],
    ) -> str:
        del moves
        seed = hashlib.sha256(identity.name.encode("utf-8")).digest()
        return _NAMES[seed[0] % len(_NAMES)]

    async def generate_reference_image(self, vibemon: vibemon_entity.Vibemon) -> bytes:
        aesthetic = _require_aesthetic(vibemon)
        image = Image.new("RGB", (_REFERENCE_DIM, _REFERENCE_DIM), aesthetic.background_color.hex)
        draw = ImageDraw.Draw(image)
        draw.ellipse((28, 24, 68, 72), fill=aesthetic.primary_color.hex)
        return _png_bytes(image)

    async def detect_vibemon_reference_facing(
        self,
        reference_png: bytes,
        *,
        vibemon_name: str,
    ) -> sprite_types.SpriteFacing:
        del reference_png, vibemon_name
        return sprite_types.SpriteFacing.RIGHT

    async def generate_battle_cry_audio(self, vibemon: vibemon_entity.Vibemon) -> bytes:
        del vibemon
        # Non-empty silent placeholder; stored as CRY_BATTLE, never decoded here.
        return b"\x00" * 64

    async def generate_sprite_sheet_image(
        self,
        vibemon: vibemon_entity.Vibemon,
        reference_image: bytes,
    ) -> bytes:
        del reference_image
        aesthetic = _require_aesthetic(vibemon)
        width = _SHEET_COLS * _CELL
        height = _SHEET_ROWS * _CELL
        image = Image.new("RGB", (width, height), aesthetic.background_color.hex)
        draw = ImageDraw.Draw(image)
        for row in range(_SHEET_ROWS):
            for col in range(_SHEET_COLS):
                cx = col * _CELL + _CELL // 2
                cy = row * _CELL + _CELL // 2
                draw.ellipse((cx - 20, cy - 24, cx + 20, cy + 24), fill=aesthetic.primary_color.hex)
        return _png_bytes(image)

    async def generate_trainer_reference(
        self,
        likeness_bytes: bytes,
        *,
        username: str,
        likeness_media_type: str,
    ) -> tuple[bytes, brand.Color]:
        del likeness_bytes, username, likeness_media_type
        background = brand.CREAM
        image = Image.new("RGB", (_REFERENCE_DIM, _REFERENCE_DIM), background.hex)
        draw = ImageDraw.Draw(image)
        draw.ellipse((24, 20, 72, 76), fill=brand.TOBACCO_BROWN.hex)
        return _png_bytes(image), background

    async def detect_trainer_reference_facing(self, reference_png: bytes) -> sprite_types.SpriteFacing:
        del reference_png
        return sprite_types.SpriteFacing.RIGHT


def _require_aesthetic(vibemon: vibemon_entity.Vibemon) -> vibemon_entity.Aesthetic:
    if vibemon.aesthetic is None:
        raise ValueError("Vibemon aesthetic is required to generate sprite assets")
    return vibemon.aesthetic


def _png_bytes(image: Image.Image) -> bytes:
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    return payload.getvalue()
