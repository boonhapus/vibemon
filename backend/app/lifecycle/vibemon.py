"""Vibemon lifecycle: christen, manifest, adopt.

Schema-level methods cannot perform async I/O cleanly, so the lifecycle
verbs live here. Each function mutates the passed ``schema.Vibemon`` and
returns it for chaining.
"""

import asyncio
import io

from PIL import Image
import structlog

from app import schema, types
from app import utils as app_utils
from app.data_store import const as ds_const
from app.data_store import monstore
from app.data_store import types as ds_types
from app.genai import client as genai

_LOGGER = structlog.get_logger(__name__)


def _ensure_aesthetic(vibemon: schema.Vibemon) -> schema.Aesthetic:
    if vibemon.aesthetic is None:
        vibemon.aesthetic = schema.Aesthetic.from_vibemon(vibemon)
    return vibemon.aesthetic


def _has_required(vibemon: schema.Vibemon, required: frozenset[ds_types.AssetKind]) -> bool:
    return vibemon.aesthetic is not None and required.issubset(vibemon.aesthetic.assets.keys())


async def christen(vibemon: schema.Vibemon) -> schema.Vibemon:
    """Finalize the Vibemon's name and generate preview assets.

    Required preview assets: ``REFERENCE`` and ``CRY_BATTLE``. Lifecycle
    advances to ``CHRISTENED`` only after both refs are populated.
    """
    if vibemon.lifecycle in (types.VibemonLifecycleT.CHRISTENED, types.VibemonLifecycleT.MANIFESTED) and _has_required(
        vibemon, ds_const.REQUIRED_CHRISTEN_ASSETS
    ):
        return vibemon

    if vibemon.lifecycle is types.VibemonLifecycleT.BORN:
        name = await genai.generate_vibemon_name(
            identity=vibemon.identity,
            moves=list(vibemon.moves),
            visual_notes=vibemon.identity.provider_visual_notes,
        )
        vibemon.identity = vibemon.identity.model_copy(update={"name": name})

    aesthetic = _ensure_aesthetic(vibemon)

    async with asyncio.TaskGroup() as g:
        ref_task = g.create_task(genai.generate_sprite_reference(vibemon=vibemon))
        cry_task = g.create_task(genai.generate_battle_cry(vibemon=vibemon))

    ref_bytes = ref_task.result()
    cry_bytes = cry_task.result()

    ref_ref, cry_ref = await asyncio.gather(
        monstore.put(vibemon.id, ds_types.AssetKind.REFERENCE, ref_bytes),
        monstore.put(vibemon.id, ds_types.AssetKind.CRY_BATTLE, cry_bytes),
    )

    aesthetic.assets[ds_types.AssetKind.REFERENCE] = ref_ref
    aesthetic.assets[ds_types.AssetKind.CRY_BATTLE] = cry_ref

    if _has_required(vibemon, ds_const.REQUIRED_CHRISTEN_ASSETS):
        vibemon.lifecycle = types.VibemonLifecycleT.CHRISTENED

    await _LOGGER.ainfo(
        "Christened Vibemon",
        id=str(vibemon.id),
        name=vibemon.name,
        lifecycle=vibemon.lifecycle,
    )

    return vibemon


async def manifest(vibemon: schema.Vibemon) -> schema.Vibemon:
    """Realize full sprite sheet and pose assets from the preview reference.

    Internal asset-realization primitive; does not assign ownership. Caller
    must already have a ``CHRISTENED`` (or ``MANIFESTED``) Vibemon.
    """
    if vibemon.lifecycle not in (types.VibemonLifecycleT.CHRISTENED, types.VibemonLifecycleT.MANIFESTED):
        raise ValueError(f"Cannot manifest Vibemon {vibemon.id} from {vibemon.lifecycle}; must be CHRISTENED first.")

    aesthetic = _ensure_aesthetic(vibemon)

    if not ds_const.REQUIRED_CHRISTEN_ASSETS.issubset(aesthetic.assets.keys()):
        missing = sorted(ds_const.REQUIRED_CHRISTEN_ASSETS - aesthetic.assets.keys())
        raise ValueError(f"Vibemon {vibemon.id} missing christen refs: {missing}")

    reference_bytes = await aesthetic.bytes_for(ds_types.AssetKind.REFERENCE)
    if reference_bytes is None:
        raise RuntimeError(f"Vibemon {vibemon.id} REFERENCE blob is missing from monstore")

    sheet_bytes = await genai.generate_sprite_sheet(vibemon=vibemon, reference=reference_bytes)
    sheet_ref = await monstore.put(vibemon.id, ds_types.AssetKind.SHEET, sheet_bytes)
    aesthetic.assets[ds_types.AssetKind.SHEET] = sheet_ref

    poses = app_utils.extract_sprites(image=sheet_bytes)

    pose_uploads = []
    for pose, image in poses.items():
        kind = ds_const.POSE_TO_ASSET[pose]
        png_bytes = _encode_png(image)
        pose_uploads.append(monstore.put(vibemon.id, kind, png_bytes))

    pose_refs = await asyncio.gather(*pose_uploads)
    for ref in pose_refs:
        aesthetic.assets[ref.kind] = ref

    if _has_required(vibemon, ds_const.REQUIRED_MANIFEST_ASSETS):
        vibemon.lifecycle = types.VibemonLifecycleT.MANIFESTED

    await _LOGGER.ainfo(
        "Manifested Vibemon",
        id=str(vibemon.id),
        name=vibemon.name,
        lifecycle=vibemon.lifecycle,
    )

    return vibemon


async def adopt(vibemon: schema.Vibemon, trainer_id: types.TrainerIdT) -> schema.Vibemon:
    """Assign trainer ownership and realize full assets.

    Future ownership/workflow logic (party placement, wilderness removal,
    async manifestation) belongs here without changing the call site.
    """
    vibemon.trainer_id = trainer_id
    await manifest(vibemon)
    return vibemon


def _encode_png(image: Image.Image) -> bytes:
    """Encode a PIL image to PNG bytes."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
