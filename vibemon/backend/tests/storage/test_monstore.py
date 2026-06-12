import uuid

from app.domains.trainer import assets as trainer_assets
from app.domains.vibemon.assets import ASSET_VERSION, AssetKind
from app.storage.blob.monstore import MonStore


def test_vibemon_asset_key_includes_layout_version_and_revision() -> None:
    vibemon_id = uuid.UUID("019e8ddf-a63b-7340-8afd-d2e0289ffef9")
    store = MonStore("memory://")

    key = store.vibemon_asset_key(vibemon_id, AssetKind.REFERENCE, revision=3)

    assert key == f"mons/{vibemon_id}/{ASSET_VERSION}/r3/sprite/reference.png"

    raw_key = store.vibemon_asset_key(vibemon_id, AssetKind.REFERENCE_RAW, revision=1)
    assert raw_key == f"mons/{vibemon_id}/{ASSET_VERSION}/r1/sprite/reference-raw.png"


def test_trainer_asset_key_includes_layout_version_and_revision() -> None:
    trainer_id = uuid.UUID("019e8ddf-a63b-7340-8afd-d2e0289ffef9")
    store = MonStore("memory://")

    key = store.trainer_asset_key(trainer_id, trainer_assets.TrainerAssetKind.REFERENCE, revision=2)

    assert key == f"trainers/{trainer_id}/{ASSET_VERSION}/r2/sprite/reference.png"
