"""Pure lifecycle transition policy for Vibemon asset realization."""

from __future__ import annotations

from app import schema, types
from app.data_store import const as ds_const
from app.data_store import types as ds_types

ALLOWED_CHRISTEN_LIFECYCLES: frozenset[types.VibemonLifecycleT] = frozenset(
    {
        types.VibemonLifecycleT.BORN,
        types.VibemonLifecycleT.CHRISTENED,
        types.VibemonLifecycleT.MANIFESTED,
    }
)

ALLOWED_MANIFEST_LIFECYCLES: frozenset[types.VibemonLifecycleT] = frozenset(
    {
        types.VibemonLifecycleT.CHRISTENED,
        types.VibemonLifecycleT.MANIFESTED,
    }
)


def has_required_assets(vibemon: schema.Vibemon, required: frozenset[ds_types.AssetKind]) -> bool:
    return vibemon.aesthetic is not None and required.issubset(vibemon.aesthetic.assets.keys())


def can_skip_christen(vibemon: schema.Vibemon) -> bool:
    return vibemon.lifecycle in (
        types.VibemonLifecycleT.CHRISTENED,
        types.VibemonLifecycleT.MANIFESTED,
    ) and has_required_assets(vibemon, ds_const.REQUIRED_CHRISTEN_ASSETS)


def require_can_manifest(vibemon: schema.Vibemon) -> None:
    if vibemon.lifecycle not in ALLOWED_MANIFEST_LIFECYCLES:
        raise ValueError(f"Cannot manifest Vibemon {vibemon.id} from {vibemon.lifecycle}; must be CHRISTENED first.")


def require_christen_assets(vibemon: schema.Vibemon) -> None:
    aesthetic = vibemon.aesthetic
    if aesthetic is None:
        raise ValueError(f"Vibemon {vibemon.id} missing christen refs: {sorted(ds_const.REQUIRED_CHRISTEN_ASSETS)}")
    keys = aesthetic.assets.keys()
    if not ds_const.REQUIRED_CHRISTEN_ASSETS.issubset(keys):
        missing = sorted(ds_const.REQUIRED_CHRISTEN_ASSETS - keys)
        raise ValueError(f"Vibemon {vibemon.id} missing christen refs: {missing}")
