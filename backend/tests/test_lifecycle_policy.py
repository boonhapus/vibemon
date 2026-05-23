from __future__ import annotations

import pytest

from app import types
from app.domain.vibemon import Aesthetic, Identity, Vibemon
from app.lifecycle import policy
from app.storage import const as ds_const
from app.storage import schema as ds_schema
from app.storage import types as ds_types


def _vibemon() -> Vibemon:
    return Vibemon(
        identity=Identity(
            name="testmon",
            elements=(types.VibemonTypeT.FIRE,),
        ),
    )


def _asset_ref(vibemon: Vibemon, kind: ds_types.AssetKind) -> ds_schema.AssetRef:
    return ds_schema.AssetRef(
        vibemon_id=vibemon.id,
        kind=kind,
        key=f"{vibemon.id}/{kind.value}",
        content_type="image/png",
        byte_size=1,
        sha256="hash",
    )


def test_can_skip_christen_requires_lifecycle_and_assets() -> None:
    vibemon = _vibemon()
    vibemon.lifecycle = types.VibemonLifecycleT.CHRISTENED
    vibemon.aesthetic = Aesthetic.from_vibemon(vibemon)
    assert not policy.can_skip_christen(vibemon)

    for kind in ds_const.REQUIRED_CHRISTEN_ASSETS:
        vibemon.aesthetic.assets[kind] = _asset_ref(vibemon, kind)

    assert policy.can_skip_christen(vibemon)


def test_require_can_manifest_rejects_born() -> None:
    vibemon = _vibemon()
    vibemon.lifecycle = types.VibemonLifecycleT.BORN
    with pytest.raises(ValueError, match="must be CHRISTENED first"):
        policy.require_can_manifest(vibemon)


def test_require_christen_assets_reports_missing() -> None:
    vibemon = _vibemon()
    vibemon.aesthetic = Aesthetic.from_vibemon(vibemon)
    with pytest.raises(ValueError, match="missing christen refs"):
        policy.require_christen_assets(vibemon)
