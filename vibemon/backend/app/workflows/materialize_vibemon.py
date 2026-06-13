"""Lifecycle realization with injected IO adapters."""

from collections.abc import Sequence
from typing import Protocol
import asyncio
import dataclasses
import uuid

import structlog

from app.domains.move.entity import Move
from app.domains.sprite import const as sprite_const
from app.domains.sprite import types as sprite_types
from app.domains.vibemon import lifecycle as policy
from app.domains.vibemon.assets import AssetKind, AssetRef
from app.domains.vibemon.entity import Aesthetic, Vibemon
from app.domains.vibemon.identity import Identity
from app.domains.vibemon.types import PoseT, VibemonLifecycleT
from app.storage.blob import const as ds_const
from app.storage.blob.monstore import get_default_monstore
from app.workflows import sprite_postprocess

_LOGGER = structlog.get_logger(__name__)


def _pose_snap_profile(pose: PoseT) -> sprite_const.SnapProfile:
    """Battle poses snap moderately; emotes follow the showcase treatment."""
    return sprite_const.BATTLE_SNAP if pose.name.startswith("BATTLE_") else sprite_const.EMOTE_SNAP


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceAssets:
    """Raw GenAI reference bytes and the snapped display PNG stored as REFERENCE."""

    raw: bytes
    display: bytes
    detected_facing: sprite_types.SpriteFacing


class VibemonAssetGenerator(Protocol):
    async def generate_name(self, identity: Identity, moves: Sequence[Move], visual_notes: str | None) -> str: ...

    async def generate_reference_image(self, vibemon: Vibemon) -> bytes: ...

    async def detect_vibemon_reference_facing(
        self,
        reference_png: bytes,
        *,
        vibemon_name: str,
    ) -> sprite_types.SpriteFacing: ...

    async def generate_battle_cry_audio(self, vibemon: Vibemon) -> bytes: ...

    async def generate_sprite_sheet_image(self, vibemon: Vibemon, reference_image: bytes) -> bytes: ...


class AssetStore(Protocol):
    async def put(
        self,
        vibemon_id: uuid.UUID,
        kind: AssetKind,
        data: bytes,
        *,
        revision: int,
        content_type: str | None = None,
    ) -> AssetRef: ...

    async def get(self, key: str) -> bytes: ...


class MaterializeVibemon:
    def __init__(
        self,
        *,
        generator: VibemonAssetGenerator | None = None,
        monstore: AssetStore | None = None,
    ) -> None:
        if generator is None:
            from app.genai import vibemon_assets

            generator = vibemon_assets.get_default_asset_generator()

        self._generator = generator
        asset_store = monstore or get_default_monstore()
        self._put_asset_store = asset_store.put
        self._get_asset = asset_store.get

    async def _put_asset(self, vibemon: Vibemon, kind: AssetKind, data: bytes) -> AssetRef:
        return await _put_asset_impl(self._put_asset_store, vibemon, kind, data)

    async def christen(self, vibemon: Vibemon, *, force: bool = False) -> Vibemon:
        vibemon, _, _ = await self._christen_assets(vibemon, force=force)
        return vibemon

    async def christen_and_manifest(self, vibemon: Vibemon) -> Vibemon:
        """Christen then manifest, passing the raw reference in memory instead of re-reading blob storage."""
        if vibemon.lifecycle is VibemonLifecycleT.MANIFESTED and _has_required_assets(
            vibemon, ds_const.REQUIRED_MANIFEST_ASSETS
        ):
            return vibemon

        vibemon, reference, _ = await self._christen_assets(vibemon)
        return await self.manifest(
            vibemon,
            reference_bytes=reference.raw if reference is not None else None,
        )

    async def _christen_assets(
        self,
        vibemon: Vibemon,
        *,
        force: bool = False,
    ) -> tuple[Vibemon, ReferenceAssets | None, bytes | None]:
        if not force and _can_skip_christen(vibemon):
            return vibemon, None, None

        if vibemon.lifecycle is VibemonLifecycleT.BORN:
            name = await self._generator.generate_name(
                vibemon.identity,
                vibemon.moves,
                vibemon.identity.provider_visual_notes,
            )
            vibemon.identity = vibemon.identity.model_copy(update={"name": name})

        _ensure_aesthetic(vibemon)

        async with asyncio.TaskGroup() as g:
            ref_task = g.create_task(self._generate_christen_reference(vibemon))
            cry_task = g.create_task(self._generator.generate_battle_cry_audio(vibemon))

        reference = ref_task.result()
        cry_bytes = cry_task.result()

        vibemon.reference_detected_facing = reference.detected_facing

        await asyncio.gather(
            self._put_asset(vibemon, AssetKind.REFERENCE_RAW, reference.raw),
            self._put_asset(vibemon, AssetKind.REFERENCE, reference.display),
            self._put_asset(vibemon, AssetKind.CRY_BATTLE, cry_bytes),
        )

        if _has_required_assets(vibemon, ds_const.REQUIRED_CHRISTEN_ASSETS):
            vibemon.lifecycle = VibemonLifecycleT.CHRISTENED

        await _LOGGER.ainfo(
            "Christened Vibemon",
            id=str(vibemon.id),
            name=vibemon.name,
            lifecycle=vibemon.lifecycle,
            reference_detected_facing=reference.detected_facing.value,
        )
        return vibemon, reference, cry_bytes

    async def manifest(self, vibemon: Vibemon, *, reference_bytes: bytes | None = None) -> Vibemon:
        policy.require_can_manifest(vibemon)

        aesthetic = _ensure_aesthetic(vibemon)
        matte = aesthetic.background_color
        _require_christen_assets(vibemon)

        if reference_bytes is None:
            reference_ref = _prompt_reference_ref(aesthetic)
            reference_bytes = await self._get_asset(reference_ref.key) if reference_ref else None
        if reference_bytes is None:
            raise RuntimeError(f"Vibemon {vibemon.id} REFERENCE_RAW blob is missing from monstore")

        raw_sheet_bytes = await self._generator.generate_sprite_sheet_image(vibemon, reference_bytes)
        sheet_bytes = sprite_postprocess.normalize_sprite_matte(raw_sheet_bytes, bg_color=matte)
        if issues := sprite_postprocess.validate_sprite_sheet(sheet_bytes, bg_color=matte):
            raise RuntimeError(f"Generated sprite sheet failed validation: {'; '.join(issues)}")
        await self._put_asset(vibemon, AssetKind.SHEET, sheet_bytes)

        poses = sprite_postprocess.extract_sprites(image=sheet_bytes, bg_color=matte)
        pose_uploads = [
            self._put_asset(
                vibemon,
                ds_const.POSE_TO_ASSET[pose],
                sprite_postprocess.snap_pose_display(image, profile=_pose_snap_profile(pose)),
            )
            for pose, image in poses.items()
        ]
        await asyncio.gather(*pose_uploads)

        if _has_required_assets(vibemon, ds_const.REQUIRED_MANIFEST_ASSETS):
            vibemon.lifecycle = VibemonLifecycleT.MANIFESTED

        await _LOGGER.ainfo(
            "Manifested Vibemon",
            id=str(vibemon.id),
            name=vibemon.name,
            lifecycle=vibemon.lifecycle,
        )
        return vibemon

    async def reprocess_display_assets(self, vibemon: Vibemon) -> Vibemon:
        """Re-chroma reference and pose PNGs from stored blobs without calling GenAI."""
        aesthetic = _ensure_aesthetic(vibemon)
        matte = aesthetic.background_color

        reference_source = _reference_source_ref(aesthetic)
        if reference_source is not None:
            source_bytes = await self._get_asset(reference_source.key)
            normalized = sprite_postprocess.normalize_reference_image(
                source_bytes,
                bg_color=aesthetic.background_color,
            )
            facing = await _resolve_reference_facing(
                self._generator,
                vibemon,
                normalized,
            )
            display = sprite_postprocess.finalize_reference_display(normalized, facing=facing)
            vibemon.reference_detected_facing = facing
            await self._put_asset(vibemon, AssetKind.REFERENCE, display)

        sheet_ref = aesthetic.assets.get(AssetKind.SHEET)
        if sheet_ref is not None:
            sheet_bytes = await self._get_asset(sheet_ref.key)
            sheet_bytes = sprite_postprocess.normalize_sprite_matte(sheet_bytes, bg_color=matte)
            await self._put_asset(vibemon, AssetKind.SHEET, sheet_bytes)
            poses = sprite_postprocess.extract_sprites(image=sheet_bytes, bg_color=matte)
            await asyncio.gather(
                *(
                    self._put_asset(
                        vibemon,
                        ds_const.POSE_TO_ASSET[pose],
                        sprite_postprocess.snap_pose_display(image, profile=_pose_snap_profile(pose)),
                    )
                    for pose, image in poses.items()
                )
            )

        await _LOGGER.ainfo(
            "Reprocessed Vibemon display assets",
            id=str(vibemon.id),
            name=vibemon.name,
        )
        return vibemon

    async def regenerate_display_assets(self, vibemon: Vibemon) -> Vibemon:
        """Regenerate reference (and sprite sheet when manifested) via GenAI."""
        aesthetic = _ensure_aesthetic(vibemon)
        had_sheet = aesthetic.assets.get(AssetKind.SHEET) is not None

        reference = await self._generate_christen_reference(vibemon)
        vibemon.reference_detected_facing = reference.detected_facing
        await asyncio.gather(
            self._put_asset(vibemon, AssetKind.REFERENCE_RAW, reference.raw),
            self._put_asset(vibemon, AssetKind.REFERENCE, reference.display),
        )

        if had_sheet or vibemon.lifecycle is VibemonLifecycleT.MANIFESTED:
            vibemon = await self.manifest(vibemon, reference_bytes=reference.raw)

        await _LOGGER.ainfo(
            "Regenerated Vibemon display assets",
            id=str(vibemon.id),
            name=vibemon.name,
            lifecycle=vibemon.lifecycle.value,
        )
        return vibemon

    async def _generate_christen_reference(self, vibemon: Vibemon) -> ReferenceAssets:
        aesthetic = _ensure_aesthetic(vibemon)
        raw_reference = await self._generator.generate_reference_image(vibemon)
        normalized = sprite_postprocess.normalize_reference_image(
            raw_reference,
            bg_color=aesthetic.background_color,
        )
        facing = await _resolve_reference_facing(self._generator, vibemon, normalized)
        display = sprite_postprocess.finalize_reference_display(normalized, facing=facing)
        return ReferenceAssets(raw=raw_reference, display=display, detected_facing=facing)


async def _resolve_reference_facing(
    generator: VibemonAssetGenerator,
    vibemon: Vibemon,
    normalized_reference: bytes,
) -> sprite_types.SpriteFacing:
    if vibemon.reference_detected_facing is not None:
        return vibemon.reference_detected_facing
    try:
        return await generator.detect_vibemon_reference_facing(
            normalized_reference,
            vibemon_name=vibemon.name,
        )
    except Exception as exc:
        await _LOGGER.awarn(
            "vibemon_reference_facing_detection_failed",
            vibemon_id=str(vibemon.id),
            error=str(exc),
        )
        return sprite_types.SpriteFacing.RIGHT


def _next_revision(vibemon: Vibemon, kind: AssetKind) -> int:
    aesthetic = vibemon.aesthetic
    existing = aesthetic.assets.get(kind) if aesthetic is not None else None
    return (existing.revision if existing is not None else 0) + 1


async def _put_asset_impl(
    put_asset,
    vibemon: Vibemon,
    kind: AssetKind,
    data: bytes,
) -> AssetRef:
    revision = _next_revision(vibemon, kind)
    ref = await put_asset(vibemon.id, kind, data, revision=revision)
    if kind is AssetKind.REFERENCE:
        anchor = sprite_postprocess.compute_display_anchor(data)
        if anchor is not None:
            ref = ref.model_copy(update={"anchor": anchor})
    aesthetic = _ensure_aesthetic(vibemon)
    aesthetic.assets[kind] = ref
    return ref


def _reference_source_ref(aesthetic: Aesthetic) -> AssetRef | None:
    """Prefer the GenAI raw reference for reprocessing; fall back to keyed reference."""
    return aesthetic.assets.get(AssetKind.REFERENCE_RAW) or aesthetic.assets.get(AssetKind.REFERENCE)


def _prompt_reference_ref(aesthetic: Aesthetic) -> AssetRef | None:
    """Return the raw GenAI reference used as prompt input for downstream image generation."""
    return aesthetic.assets.get(AssetKind.REFERENCE_RAW)


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
