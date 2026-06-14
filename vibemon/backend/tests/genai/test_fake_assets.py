import uuid

import pytest

from app.domains.vibemon.assets import AssetKind, AssetRef
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.types import VibemonLifecycleT, VibemonTypeT
from app.genai.fake_assets import FakeVibemonAssetGenerator
from app.storage.blob import const as blob_const
from app.workflows.materialize_vibemon import MaterializeVibemon


class _FakeMonStore:
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


def _vibemon() -> Vibemon:
    return Vibemon(
        identity=Identity(
            name="__",
            elements=(VibemonTypeT.FIRE,),
            visual_notes="clear heat",
            base=BaseStats(),
        )
    )


@pytest.mark.asyncio
async def test_fake_adapter_drives_full_realization_offline() -> None:
    realizer = MaterializeVibemon(generator=FakeVibemonAssetGenerator(), monstore=_FakeMonStore())

    manifested = await realizer.christen_and_manifest(_vibemon())

    assert manifested.lifecycle is VibemonLifecycleT.MANIFESTED
    assert manifested.aesthetic is not None
    assert AssetKind.CRY_BATTLE in manifested.aesthetic.assets
    assert AssetKind.SHEET in manifested.aesthetic.assets
    for kind in blob_const.POSE_TO_ASSET.values():
        assert kind in manifested.aesthetic.assets


@pytest.mark.asyncio
async def test_fake_name_is_deterministic_per_identity() -> None:
    generator = FakeVibemonAssetGenerator()
    vibemon = _vibemon()

    first = await generator.generate_name(vibemon.identity, vibemon.moves)
    second = await generator.generate_name(vibemon.identity, vibemon.moves)

    assert first == second
