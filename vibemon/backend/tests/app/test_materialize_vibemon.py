from collections.abc import Sequence
from typing import TYPE_CHECKING
import io
import uuid

from PIL import Image, ImageDraw
import numpy as np
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

    async def generate_name(self, identity: Identity, moves: Sequence[Move]) -> str:
        return "Testling"

    async def generate_reference_image(self, vibemon: Vibemon) -> bytes:
        return _reference_png(vibemon.aesthetic)

    async def detect_vibemon_reference_facing(self, reference_png: bytes, *, vibemon_name: str):
        from app.domains.sprite import types as sprite_types

        assert reference_png
        return sprite_types.SpriteFacing.LEFT

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
        revision: int,
        content_type: str | None = None,
    ) -> AssetRef:
        key = f"{vibemon_id}/test/r{revision}/{kind.value}"
        self.objects[key] = data
        return AssetRef(
            vibemon_id=vibemon_id,
            kind=kind,
            revision=revision,
            key=key,
            content_type=content_type or blob_const.ASSET_CONTENT_TYPES[kind],
            byte_size=len(data),
            sha256="test",
        )

    async def get(self, key: str) -> bytes:
        return self.objects[key]


class GroundReferenceGenerator(FakeVibemonAssetGenerator):
    async def generate_reference_image(self, vibemon: Vibemon) -> bytes:
        return _reference_with_ground_png(vibemon.aesthetic)


@pytest.mark.asyncio
async def test_christen_keys_reference_and_preserves_raw() -> None:
    generator = GroundReferenceGenerator()
    monstore = FakeMonStore()
    vibemon = _vibemon()
    realizer = MaterializeVibemon(generator=generator, monstore=monstore)

    christened = await realizer.christen(vibemon)

    assert christened.aesthetic is not None
    assert AssetKind.REFERENCE_RAW in christened.aesthetic.assets
    reference = Image.open(io.BytesIO(monstore.objects[christened.aesthetic.assets[AssetKind.REFERENCE].key]))
    raw_reference = Image.open(io.BytesIO(monstore.objects[christened.aesthetic.assets[AssetKind.REFERENCE_RAW].key]))
    alpha = np.asarray(reference)[..., 3]
    assert (alpha >= 128).any()
    assert (alpha < 32).any()
    assert (
        monstore.objects[christened.aesthetic.assets[AssetKind.REFERENCE_RAW].key]
        != monstore.objects[christened.aesthetic.assets[AssetKind.REFERENCE].key]
    )
    assert raw_reference.size != reference.size


@pytest.mark.asyncio
async def test_reprocess_prefers_raw_reference_source() -> None:
    generator = FakeVibemonAssetGenerator()
    monstore = FakeMonStore()
    vibemon = _vibemon()
    realizer = MaterializeVibemon(generator=generator, monstore=monstore)
    christened = await realizer.christen(vibemon)
    assert christened.aesthetic is not None

    raw_key = christened.aesthetic.assets[AssetKind.REFERENCE_RAW].key
    raw_bytes = monstore.objects[raw_key]
    monstore.objects[raw_key] = _reference_with_ground_png(christened.aesthetic)

    await realizer.reprocess_display_assets(christened)

    reprocessed = Image.open(io.BytesIO(monstore.objects[christened.aesthetic.assets[AssetKind.REFERENCE].key]))
    alpha = np.asarray(reprocessed)[..., 3]
    assert (alpha >= 128).any()
    assert (alpha < 32).any()
    assert monstore.objects[raw_key] != raw_bytes


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
    assert generator.sheet_reference_image == monstore.objects[manifested.aesthetic.assets[AssetKind.REFERENCE_RAW].key]
    assert AssetKind.CRY_BATTLE in manifested.aesthetic.assets
    assert AssetKind.SHEET in manifested.aesthetic.assets
    for kind in blob_const.POSE_TO_ASSET.values():
        assert kind in manifested.aesthetic.assets


def _vibemon() -> Vibemon:
    return Vibemon(
        identity=Identity(
            name="__",
            elements=(VibemonTypeT.FIRE,),
            visual_notes="clear heat",
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


def _reference_with_ground_png(aesthetic: Aesthetic | None) -> bytes:
    if aesthetic is None:
        raise ValueError("expected aesthetic")
    image = Image.new("RGB", (96, 96), str(aesthetic.background_color))
    draw = ImageDraw.Draw(image)
    draw.ellipse((28, 20, 68, 58), fill=str(aesthetic.primary_color))
    draw.ellipse((30, 72, 66, 82), fill="#3D2B1F")
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
