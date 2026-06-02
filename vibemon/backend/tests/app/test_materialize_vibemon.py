from typing import TYPE_CHECKING
import io
import uuid

from PIL import Image, ImageDraw
import pytest

from app.domains.move.entity import Move
from app.domains.vibemon.assets import AssetKind, AssetRef
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.types import VibemonLifecycleT, VibemonTypeT
from app.storage.blob import const as blob_const
from app.workflows.materialize_vibemon import MaterializeVibemon

if TYPE_CHECKING:
    from app.domains.vibemon.entity import Aesthetic


class FakeVibemonAssetGenerator:
    def __init__(self) -> None:
        self.sheet_reference_image: bytes | None = None

    async def generate_name(self, identity: Identity, moves: list[Move], visual_notes: str | None) -> str:
        return "Testling"

    async def generate_reference_image(self, vibemon: Vibemon) -> bytes:
        return _reference_png(vibemon.aesthetic)

    async def generate_battle_cry_audio(self, vibemon: Vibemon) -> bytes:
        return b"fake-mp3"

    async def generate_sprite_sheet_image(self, vibemon: Vibemon, reference_image: bytes) -> bytes:
        self.sheet_reference_image = reference_image
        return _sheet_png(vibemon.aesthetic)


class FakeMonStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(
        self,
        vibemon_id: uuid.UUID,
        kind: AssetKind,
        data: bytes,
        *,
        content_type: str | None = None,
    ) -> AssetRef:
        key = f"{vibemon_id}/test/{kind.value}"
        self.objects[key] = data
        return AssetRef(
            vibemon_id=vibemon_id,
            kind=kind,
            key=key,
            content_type=content_type or blob_const.ASSET_CONTENT_TYPES[kind],
            byte_size=len(data),
            sha256="test",
        )

    async def get(self, key: str) -> bytes:
        return self.objects[key]


@pytest.mark.asyncio
async def test_materialize_vibemon_uses_asset_generator_seam() -> None:
    generator = FakeVibemonAssetGenerator()
    monstore = FakeMonStore()
    vibemon = _vibemon()
    realizer = MaterializeVibemon(generator=generator, monstore=monstore)

    christened = await realizer.christen(vibemon)
    manifested = await realizer.manifest(christened)

    assert manifested.aesthetic is not None
    assert manifested.identity.name == "Testling"
    assert manifested.lifecycle is VibemonLifecycleT.MANIFESTED
    assert generator.sheet_reference_image == monstore.objects[manifested.aesthetic.assets[AssetKind.REFERENCE].key]
    assert AssetKind.CRY_BATTLE in manifested.aesthetic.assets
    assert AssetKind.SHEET in manifested.aesthetic.assets
    for kind in blob_const.POSE_TO_ASSET.values():
        assert kind in manifested.aesthetic.assets


def _vibemon() -> Vibemon:
    return Vibemon(
        identity=Identity(
            name="__",
            elements=(VibemonTypeT.FIRE,),
            visual_notes="small ember shell",
            provider_visual_notes="clear heat",
            base=BaseStats(),
        )
    )


def _reference_png(aesthetic: Aesthetic | None) -> bytes:
    if aesthetic is None:
        raise ValueError("expected aesthetic")
    image = Image.new("RGB", (96, 96), str(aesthetic.background_color))
    draw = ImageDraw.Draw(image)
    draw.ellipse((28, 24, 68, 72), fill=str(aesthetic.primary_color))
    return _png_bytes(image)


def _sheet_png(aesthetic: Aesthetic | None) -> bytes:
    if aesthetic is None:
        raise ValueError("expected aesthetic")
    image = Image.new("RGB", (300, 300), str(aesthetic.background_color))
    draw = ImageDraw.Draw(image)
    for row in range(3):
        for col in range(3):
            cx = col * 100 + 50
            cy = row * 100 + 50
            draw.ellipse((cx - 20, cy - 24, cx + 20, cy + 24), fill=str(aesthetic.primary_color))
    return _png_bytes(image)


def _png_bytes(image: Image.Image) -> bytes:
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    return payload.getvalue()
