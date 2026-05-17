# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "vibemon-backend",
#   "sqlalchemy[asyncio]",
#   "aiosqlite",
# ]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///
"""Local monstore cleanup.

Compares ``settings.asset_store_url`` (only ``file://`` is supported) against
the ``vibemon`` and ``vibemon_asset`` tables, and reports — or with
``--apply``, removes — orphan UUID folders and stale blobs.

Integrity errors (DB asset rows whose blobs are missing) are reported but
never auto-deleted.
"""

from __future__ import annotations

from urllib.parse import urlsplit
import argparse
import asyncio
import datetime as dt
import logging
import pathlib
import sys
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa
import structlog

from app import models
from app.settings import settings

_LOGGER = structlog.get_logger(__name__)


def _resolve_local_store_root() -> pathlib.Path:
    parts = urlsplit(settings.asset_store_url)
    if parts.scheme != "file":
        raise SystemExit(
            f"cleanup_monstore.py supports file:// stores only; got scheme={parts.scheme!r}"
        )

    raw = parts.path.lstrip("/")
    return pathlib.Path(raw).resolve()


def _try_parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _walk_blob_keys(root: pathlib.Path, vibemon_dir: pathlib.Path) -> list[str]:
    """Return store-relative keys for every file under one Vibemon UUID folder."""
    keys: list[str] = []
    for path in vibemon_dir.rglob("*"):
        if path.is_file():
            keys.append(path.relative_to(root).as_posix())
    return keys


async def audit(
    sess: AsyncSession, root: pathlib.Path, *, older_than: dt.timedelta
) -> tuple[list[pathlib.Path], list[pathlib.Path], list[tuple[uuid.UUID, str]]]:
    """Return (orphan_dirs, stale_blobs, missing_blob_rows)."""
    if not root.exists():
        await _LOGGER.ainfo(
            "monstore root missing; nothing to scan", root=root.as_posix()
        )
        return [], [], []

    db_vibemon_ids = {
        row[0] for row in (await sess.execute(sa.select(models.Vibemon.id))).all()
    }
    db_object_keys = {
        row[0]
        for row in (await sess.execute(sa.select(models.VibemonAsset.object_key))).all()
    }
    db_assets_by_vibemon: dict[uuid.UUID, list[str]] = {}
    rows = (
        await sess.execute(
            sa.select(models.VibemonAsset.vibemon_id, models.VibemonAsset.object_key)
        )
    ).all()
    for vibemon_id, object_key in rows:
        db_assets_by_vibemon.setdefault(vibemon_id, []).append(object_key)

    now = dt.datetime.now()
    cutoff = now - older_than

    orphan_dirs: list[pathlib.Path] = []
    stale_blobs: list[pathlib.Path] = []

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue

        parsed = _try_parse_uuid(child.name)
        if parsed is None:
            continue

        if parsed not in db_vibemon_ids:
            mtime = dt.datetime.fromtimestamp(child.stat().st_mtime)
            if mtime <= cutoff:
                orphan_dirs.append(child)
            continue

        keys_in_dir = _walk_blob_keys(root, child)
        for key in keys_in_dir:
            if key in db_object_keys:
                continue
            full = root / key
            mtime = dt.datetime.fromtimestamp(full.stat().st_mtime)
            if mtime <= cutoff:
                stale_blobs.append(full)

    missing_blob_rows: list[tuple[uuid.UUID, str]] = []
    for vibemon_id, keys in db_assets_by_vibemon.items():
        for key in keys:
            if not (root / key).exists():
                missing_blob_rows.append((vibemon_id, key))

    return orphan_dirs, stale_blobs, missing_blob_rows


async def run(*, db_path: str, older_than_hours: float, apply: bool) -> int:
    root = _resolve_local_store_root()
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    try:
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as sess:
            orphan_dirs, stale_blobs, missing_rows = await audit(
                sess, root, older_than=dt.timedelta(hours=older_than_hours)
            )
    finally:
        await engine.dispose()

    await _LOGGER.ainfo(
        "Audit complete",
        store_root=root.as_posix(),
        orphan_dirs=len(orphan_dirs),
        stale_blobs=len(stale_blobs),
        missing_blob_rows=len(missing_rows),
        mode="apply" if apply else "dry-run",
    )

    for d in orphan_dirs:
        await _LOGGER.ainfo("Orphan UUID folder", path=d.as_posix())
    for f in stale_blobs:
        await _LOGGER.ainfo("Stale blob", path=f.as_posix())
    for vibemon_id, key in missing_rows:
        await _LOGGER.awarning(
            "DB asset row missing blob", vibemon_id=str(vibemon_id), key=key
        )

    if not apply:
        return 0

    deleted_blobs = 0
    for f in stale_blobs:
        f.unlink()
        deleted_blobs += 1

    deleted_dirs = 0
    for d in orphan_dirs:
        for p in sorted(d.rglob("*"), key=lambda x: -len(x.as_posix())):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
        d.rmdir()
        deleted_dirs += 1

    await _LOGGER.ainfo(
        "Cleanup applied", deleted_blobs=deleted_blobs, deleted_dirs=deleted_dirs
    )
    return deleted_blobs + deleted_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db-path",
        type=str,
        default=pathlib.Path(__file__)
        .parent.parent.joinpath(".generated", "database", "vibemon.db")
        .as_posix(),
    )
    parser.add_argument("--older-than-hours", type=float, default=24.0)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete orphan/stale items. Default is dry-run.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO)
    )
    sys.exit(
        await run(
            db_path=args.db_path,
            older_than_hours=args.older_than_hours,
            apply=args.apply,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
