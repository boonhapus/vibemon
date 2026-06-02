"""Object-store API for Vibemon binary assets.

Storage is configured via ``Settings.load().storage.assets`` and may point at local
disk, S3, GCS, Azure, or in-memory backends — anything obstore supports.

Object keys: ``<vibemon_uuid>/<version>/<kind.value>``.
"""

from functools import lru_cache
from urllib.parse import urlsplit
import datetime as dt
import hashlib
import uuid

from obstore.store import from_url
import obstore

from app.domains.vibemon import assets
from app.domains.vibemon.assets import AssetKind, AssetRef
from app.settings import Settings
from app.storage.blob import const


class MonStore:
    """Read and write Vibemon asset blobs through obstore."""

    def __init__(self, asset_store_url: str) -> None:
        self._asset_store_url = asset_store_url
        self._store = from_url(asset_store_url)
        self._scheme = urlsplit(asset_store_url).scheme

    def asset_key(self, vibemon_id: uuid.UUID, kind: AssetKind) -> str:
        """Canonical storage key for one asset slot."""
        return f"{vibemon_id}/{assets.ASSET_VERSION}/{kind.value}"

    async def put(
        self,
        vibemon_id: uuid.UUID,
        kind: AssetKind,
        data: bytes,
        *,
        content_type: str | None = None,
    ) -> AssetRef:
        """Persist asset bytes for one Vibemon slot; return the resulting ref."""
        key = self.asset_key(vibemon_id, kind)
        await obstore.put_async(self._store, key, data)

        return AssetRef(
            vibemon_id=vibemon_id,
            kind=kind,
            key=key,
            content_type=content_type or const.ASSET_CONTENT_TYPES[kind],
            byte_size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            version=assets.ASSET_VERSION,
        )

    async def get(self, key: str) -> bytes:
        """Read asset bytes back from the store."""
        result = await obstore.get_async(self._store, key)
        payload = await result.bytes_async()
        return bytes(payload)

    async def url(self, key: str, expires_in: dt.timedelta = dt.timedelta(hours=1)) -> str:
        """URL a frontend can fetch the asset from.

        Remote stores yield a presigned URL. ``file://`` returns a direct file URL;
        ``memory://`` returns the opaque store URL with the key appended (callers
        on memory stores are expected to read via :meth:`get`).
        """
        if self._scheme in const.UNSIGNABLE_SCHEMES:
            base = self._asset_store_url.rstrip("/")
            return f"{base}/{key}"

        return await obstore.sign_async(self._store, "GET", key, expires_in)

    async def delete(self, key: str) -> None:
        """Delete a stored blob."""
        await obstore.delete_async(self._store, key)


@lru_cache(maxsize=1)
def get_default_monstore() -> MonStore:
    """Process-wide MonStore built from ``Settings.load().storage.assets``."""
    return MonStore(Settings.load().storage.assets)
