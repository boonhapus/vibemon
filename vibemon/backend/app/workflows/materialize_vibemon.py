"""Lifecycle realization with injected IO adapters."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
import asyncio
import io
import uuid

from PIL import Image
import structlog

from app.domains.move.entity import Move
from app.domains.vibemon import lifecycle as policy
from app.domains.vibemon.assets import AssetKind, AssetRef
from app.domains.vibemon.entity import Aesthetic, Vibemon
from app.domains.vibemon.identity import Identity
from app.domains.vibemon.types import VibemonLifecycleT
from app.genai import sprites as app_utils
from app.storage.blob import const as ds_const
from app.storage.blob.monstore import MonStore, get_default_monstore

type NameGenerator = Callable[[Identity, list[Move], str | None], Coroutine[object, object, str]]
type SpriteReferenceGenerator = Callable[[Vibemon], Coroutine[object, object, bytes]]
type BattleCryGenerator = Callable[[Vibemon], Coroutine[object, object, bytes]]
type SpriteSheetGenerator = Callable[[Vibemon, bytes], Coroutine[object, object, bytes]]
type AssetPut = Callable[[uuid.UUID, AssetKind, bytes], Coroutine[object, object, AssetRef]]

_LOGGER = structlog.get_logger(__name__)


class MaterializeVibemon:
    def __init__(
        self,
        *,
        generate_name: NameGenerator | None = None,
        generate_sprite_reference: SpriteReferenceGenerator | None = None,
        generate_battle_cry: BattleCryGenerator | None = None,
        generate_sprite_sheet: SpriteSheetGenerator | None = None,
        monstore: MonStore | None = None,
    ) -> None:
        from app.genai import client as genai

        client = genai.get_default_client()
        asset_store = monstore or get_default_monstore()
        self._generate_name = generate_name or client.generate_vibemon_name
        self._generate_sprite_reference = generate_sprite_reference or client.generate_sprite_reference
        self._generate_battle_cry = generate_battle_cry or client.generate_battle_cry
        self._generate_sprite_sheet = generate_sprite_sheet or client.generate_sprite_sheet
        self._put_asset = asset_store.put
        self._get_asset = asset_store.get

    async def christen(self, vibemon: Vibemon) -> Vibemon:
        if _can_skip_christen(vibemon):
            return vibemon

        if vibemon.lifecycle is VibemonLifecycleT.BORN:
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
            self._put_asset(vibemon.id, AssetKind.REFERENCE, ref_bytes),
            self._put_asset(vibemon.id, AssetKind.CRY_BATTLE, cry_bytes),
        )

        aesthetic.assets[AssetKind.REFERENCE] = ref_ref
        aesthetic.assets[AssetKind.CRY_BATTLE] = cry_ref

        if _has_required_assets(vibemon, ds_const.REQUIRED_CHRISTEN_ASSETS):
            vibemon.lifecycle = VibemonLifecycleT.CHRISTENED

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
        _require_christen_assets(vibemon)

        reference_ref = aesthetic.assets.get(AssetKind.REFERENCE)
        reference_bytes = await self._get_asset(reference_ref.key) if reference_ref else None
        if reference_bytes is None:
            raise RuntimeError(f"Vibemon {vibemon.id} REFERENCE blob is missing from monstore")

        sheet_bytes = await self._generate_sprite_sheet(vibemon, reference_bytes)
        sheet_ref = await self._put_asset(vibemon.id, AssetKind.SHEET, sheet_bytes)
        aesthetic.assets[AssetKind.SHEET] = sheet_ref

        poses = app_utils.extract_sprites(image=sheet_bytes)
        pose_uploads = []
        for pose, image in poses.items():
            kind = ds_const.POSE_TO_ASSET[pose]
            pose_uploads.append(self._put_asset(vibemon.id, kind, _encode_png(image)))

        pose_refs = await asyncio.gather(*pose_uploads)
        for ref in pose_refs:
            aesthetic.assets[ref.kind] = ref

        if _has_required_assets(vibemon, ds_const.REQUIRED_MANIFEST_ASSETS):
            vibemon.lifecycle = VibemonLifecycleT.MANIFESTED

        await _LOGGER.ainfo(
            "Manifested Vibemon",
            id=str(vibemon.id),
            name=vibemon.name,
            lifecycle=vibemon.lifecycle,
        )
        return vibemon


def _ensure_aesthetic(vibemon: Vibemon) -> Aesthetic:
    if vibemon.aesthetic is None:
        vibemon.aesthetic = Aesthetic.from_vibemon(vibemon)
    return vibemon.aesthetic


def _has_required_assets(vibemon: Vibemon, required: frozenset[AssetKind]) -> bool:
    return vibemon.aesthetic is not None and required.issubset(vibemon.aesthetic.assets.keys())


def _can_skip_christen(vibemon: Vibemon) -> bool:
    return vibemon.lifecycle in (
        VibemonLifecycleT.CHRISTENED,
        VibemonLifecycleT.MANIFESTED,
    ) and _has_required_assets(vibemon, ds_const.REQUIRED_CHRISTEN_ASSETS)


def _require_christen_assets(vibemon: Vibemon) -> None:
    aesthetic = vibemon.aesthetic
    if aesthetic is None:
        raise ValueError(f"Vibemon {vibemon.id} missing christen refs: {sorted(ds_const.REQUIRED_CHRISTEN_ASSETS)}")
    keys = aesthetic.assets.keys()
    if not ds_const.REQUIRED_CHRISTEN_ASSETS.issubset(keys):
        missing = sorted(ds_const.REQUIRED_CHRISTEN_ASSETS - keys)
        raise ValueError(f"Vibemon {vibemon.id} missing christen refs: {missing}")


def _encode_png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
