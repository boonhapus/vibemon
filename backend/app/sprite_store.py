"""Sprite blob storage backed by obstore.

The canonical artifact for a Vibemon's visuals is a single sprite-sheet PNG.
Per-cell layouts are derived deterministically from that sheet, so we only
persist the sheet bytes and let consumers slice on demand.

The store URL is configured via ``settings.sprite_store_url`` and may point at
local disk, S3, GCS, Azure, or in-memory backends — anything obstore supports.
"""
from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit
import datetime as dt

import obstore
from obstore.store import ObjectStore, from_url

from app.settings import settings


SHEET_FILENAME = "sprite-sheet.png"

# Schemes where presigning is unsupported / meaningless. Hand back a direct
# locator instead of asking obstore to sign.
_UNSIGNABLE_SCHEMES = frozenset({"file", "memory"})


@lru_cache(maxsize=1)
def _store() -> ObjectStore:
    return from_url(settings.sprite_store_url)


def _scheme() -> str:
    return urlsplit(settings.sprite_store_url).scheme


def sheet_key(vibemon_slug: str) -> str:
    """Canonical storage key for a Vibemon's sprite sheet."""
    return f"{vibemon_slug}/{SHEET_FILENAME}"


async def put_sheet(vibemon_slug: str, data: bytes) -> str:
    """Persist sheet bytes; return the storage key."""
    key = sheet_key(vibemon_slug)
    await obstore.put_async(_store(), key, data)
    return key


async def get_sheet(key: str) -> bytes:
    """Read sheet bytes back from the store."""
    result = await obstore.get_async(_store(), key)
    payload = await result.bytes_async()
    return bytes(payload)


async def sheet_url(key: str, *, expires_in: dt.timedelta = dt.timedelta(hours=1)) -> str:
    """URL a frontend can fetch the sheet from.

    Remote stores yield a presigned URL. ``file://`` returns a direct file URL;
    ``memory://`` returns the opaque store URL with the key appended (callers
    on memory stores are expected to read via :func:`get_sheet`).
    """
    if _scheme() in _UNSIGNABLE_SCHEMES:
        base = settings.sprite_store_url.rstrip("/")
        return f"{base}/{key}"

    return await obstore.sign_async(_store(), "GET", key, expires_in)
