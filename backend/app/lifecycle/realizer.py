"""Lifecycle realization with injected IO adapters."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
import asyncio
import io
import uuid

from PIL import Image
import structlog

from app import types
from app import utils as app_utils
from app.domain.move import Move
from app.domain.vibemon import Aesthetic, Identity, Vibemon
from app.genai import client as genai
from app.lifecycle import policy
from app.storage import const as ds_const
from app.storage import monstore
from app.storage import schema as ds_schema
from app.storage import types as ds_types

type NameGenerator = Callable[[Identity, list[Move], str | None], Coroutine[object, object, str]]
type SpriteReferenceGenerator = Callable[[Vibemon], Coroutine[object, object, bytes]]
type BattleCryGenerator = Callable[[Vibemon], Coroutine[object, object, bytes]]
type SpriteSheetGenerator = Callable[[Vibemon, bytes], Coroutine[object, object, bytes]]
type AssetPut = Callable[[uuid.UUID, ds_types.AssetKind, bytes], Coroutine[object, object, ds_schema.AssetRef]]

_LOGGER = structlog.get_logger(__name__)


class LifecycleRealizer:
    def __init__(
        self,
        *,
        generate_name: NameGenerator | None = None,
        generate_sprite_reference: SpriteReferenceGenerator | None = None,
        generate_battle_cry: BattleCryGenerator | None = None,
        generate_sprite_sheet: SpriteSheetGenerator | None = None,
        put_asset: AssetPut = monstore.put,
    ) -> None:
        client = genai.get_default_client()
        self._generate_name = generate_name or client.generate_vibemon_name
        self._generate_sprite_reference = generate_sprite_reference or client.generate_sprite_reference
        self._generate_battle_cry = generate_battle_cry or client.generate_battle_cry
        self._generate_sprite_sheet = generate_sprite_sheet or client.generate_sprite_sheet
        self._put_asset = put_asset

    async def christen(self, vibemon: Vibemon) -> Vibemon:
        if policy.can_skip_christen(vibemon):
            return vibemon

        if vibemon.lifecycle is types.VibemonLifecycleT.BORN:
            name = await self._generate_name(
                vibemon.identity,
                list(vibemon.moves),
                vibemon.identity.provider_visual_notes,
            )
            vibemon.identity = vibemon.identity.model_copy(update={"name": name})

        aesthetic = _ensure_aesthetic(vibemon)

        async with asyncio.TaskGroup() as g:
            ref_task = g.create_task(self._generate_sprite_reference(vibemon))
            cry_task = g.create_task(self._generate_battle_cry(vibemon))

        ref_bytes = ref_task.result()
        cry_bytes = cry_task.result()

        ref_ref, cry_ref = await asyncio.gather(
            self._put_asset(vibemon.id, ds_types.AssetKind.REFERENCE, ref_bytes),
            self._put_asset(vibemon.id, ds_types.AssetKind.CRY_BATTLE, cry_bytes),
        )

        aesthetic.assets[ds_types.AssetKind.REFERENCE] = ref_ref
        aesthetic.assets[ds_types.AssetKind.CRY_BATTLE] = cry_ref

        if policy.has_required_assets(vibemon, ds_const.REQUIRED_CHRISTEN_ASSETS):
            vibemon.lifecycle = types.VibemonLifecycleT.CHRISTENED

        await _LOGGER.ainfo(
            "Christened Vibemon",
            id=str(vibemon.id),
            name=vibemon.name,
            lifecycle=vibemon.lifecycle,
        )
        return vibemon

    async def manifest(self, vibemon: Vibemon) -> Vibemon:
        policy.require_can_manifest(vibemon)

        aesthetic = _ensure_aesthetic(vibemon)
        policy.require_christen_assets(vibemon)

        reference_bytes = await aesthetic.bytes_for(ds_types.AssetKind.REFERENCE)
        if reference_bytes is None:
            raise RuntimeError(f"Vibemon {vibemon.id} REFERENCE blob is missing from monstore")

        sheet_bytes = await self._generate_sprite_sheet(vibemon, reference_bytes)
        sheet_ref = await self._put_asset(vibemon.id, ds_types.AssetKind.SHEET, sheet_bytes)
        aesthetic.assets[ds_types.AssetKind.SHEET] = sheet_ref

        poses = app_utils.extract_sprites(image=sheet_bytes)
        pose_uploads = []
        for pose, image in poses.items():
            kind = ds_const.POSE_TO_ASSET[pose]
            pose_uploads.append(self._put_asset(vibemon.id, kind, _encode_png(image)))

        pose_refs = await asyncio.gather(*pose_uploads)
        for ref in pose_refs:
            aesthetic.assets[ref.kind] = ref

        if policy.has_required_assets(vibemon, ds_const.REQUIRED_MANIFEST_ASSETS):
            vibemon.lifecycle = types.VibemonLifecycleT.MANIFESTED

        await _LOGGER.ainfo(
            "Manifested Vibemon",
            id=str(vibemon.id),
            name=vibemon.name,
            lifecycle=vibemon.lifecycle,
        )
        return vibemon

    async def adopt(self, vibemon: Vibemon, trainer_id: types.TrainerIdT) -> Vibemon:
        vibemon.trainer_id = trainer_id
        await self.manifest(vibemon)
        return vibemon


def _ensure_aesthetic(vibemon: Vibemon) -> Aesthetic:
    if vibemon.aesthetic is None:
        vibemon.aesthetic = Aesthetic.from_vibemon(vibemon)
    return vibemon.aesthetic


def _encode_png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
