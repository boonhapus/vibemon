"""Pydantic value objects for asset metadata."""

import uuid

import pydantic

from app.storage import const, types


class AssetRef(pydantic.BaseModel):
    """A handle to a stored asset blob.

    ``key`` is the stable object-store key. ``content_type``, ``byte_size``,
    and ``sha256`` capture the blob as written; persistence layers may
    independently track DB row timestamps.
    """

    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    vibemon_id: uuid.UUID
    kind: types.AssetKind
    key: str
    content_type: str
    byte_size: int
    sha256: str
    version: str = const.ASSET_VERSION
