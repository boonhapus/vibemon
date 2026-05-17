"""Object-store API for Vibemon assets.

Storage is configured via ``settings.asset_store_url`` and may point at local
disk, S3, GCS, Azure, or in-memory backends — anything obstore supports.

Object keys: ``<vibemon_uuid>/<version>/<kind.value>``.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit
import datetime as dt
import hashlib
import uuid

from obstore.store import ObjectStore, from_url
import obstore

from app.data_store import const, schema, types
from app.settings import settings


@lru_cache(maxsize=1)
def _store() -> ObjectStore:
    return from_url(settings.asset_store_url)


def _scheme() -> str:
    return urlsplit(settings.asset_store_url).scheme


def asset_key(vibemon_id: uuid.UUID, kind: types.AssetKind) -> str:
    """Canonical storage key for one asset slot."""
    return f"{vibemon_id}/{const.ASSET_VERSION}/{kind.value}"


async def put(
    vibemon_id: uuid.UUID,
    kind: types.AssetKind,
    data: bytes,
    *,
    content_type: str | None = None,
) -> schema.AssetRef:
    """Persist asset bytes for one Vibemon slot; return the resulting ref."""
    key = asset_key(vibemon_id, kind)
    await obstore.put_async(_store(), key, data)

    return schema.AssetRef(
        vibemon_id=vibemon_id,
        kind=kind,
        key=key,
        content_type=content_type or const.ASSET_CONTENT_TYPES[kind],
        byte_size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        version=const.ASSET_VERSION,
    )


async def get(key: str) -> bytes:
    """Read asset bytes back from the store."""
    result = await obstore.get_async(_store(), key)
    payload = await result.bytes_async()
    return bytes(payload)


async def url(key: str, *, expires_in: dt.timedelta = dt.timedelta(hours=1)) -> str:
    """URL a frontend can fetch the asset from.

    Remote stores yield a presigned URL. ``file://`` returns a direct file URL;
    ``memory://`` returns the opaque store URL with the key appended (callers
    on memory stores are expected to read via :func:`get`).
    """
    if _scheme() in const.UNSIGNABLE_SCHEMES:
        base = settings.asset_store_url.rstrip("/")
        return f"{base}/{key}"

    return await obstore.sign_async(_store(), "GET", key, expires_in)


async def delete(key: str) -> None:
    """Delete a stored blob. No-op friendly for missing keys is not guaranteed."""
    await obstore.delete_async(_store(), key)
