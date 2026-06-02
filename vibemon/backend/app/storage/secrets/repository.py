"""Encrypted trainer secret persistence and access adapters."""

import base64
import hashlib
import uuid

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.trainer import types as trainer_types
from app.settings import Settings
from app.storage.database import models


class SecretCipher:
    """Encrypt and decrypt trainer secret payloads at rest."""

    def __init__(self, *, key_material: str) -> None:
        digest = hashlib.sha256(key_material.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt trainer secret.") from exc


def get_secret_cipher() -> SecretCipher:
    """Build a cipher from ``Settings.load().secrets.trainer_encryption``."""
    settings = Settings.load()
    return SecretCipher(key_material=settings.secrets.trainer_encryption.get_secret_value())


class DbTrainerSecrets:
    """Load trainer secrets from the database, keyed by trainer_id + kind."""

    def __init__(self, sess: AsyncSession) -> None:
        self._sess = sess

    async def get(self, trainer_id: uuid.UUID, kind: str) -> str | None:
        return await get_trainer_secret(
            self._sess,
            trainer_id,
            kind,  # pyrefly: ignore[bad-argument-type]
        )


async def get_trainer_secret(
    sess: AsyncSession,
    trainer_id: uuid.UUID,
    kind: trainer_types.TrainerSecretKindT,
) -> str | None:
    """Read and decrypt one trainer secret, or ``None`` when absent."""
    row = (
        await sess.execute(
            sa.select(models.TrainerSecret).where(
                models.TrainerSecret.trainer_id == trainer_id,
                models.TrainerSecret.kind == kind,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return get_secret_cipher().decrypt(row.ciphertext)


async def set_trainer_secret(
    sess: AsyncSession,
    trainer_id: uuid.UUID,
    kind: trainer_types.TrainerSecretKindT,
    plaintext: str | None,
) -> None:
    """Insert, update, or delete one trainer secret row. Caller commits."""
    row = (
        await sess.execute(
            sa.select(models.TrainerSecret).where(
                models.TrainerSecret.trainer_id == trainer_id,
                models.TrainerSecret.kind == kind,
            )
        )
    ).scalar_one_or_none()

    if plaintext is None:
        if row is not None:
            await sess.delete(row)
        return

    ciphertext = get_secret_cipher().encrypt(plaintext)
    if row is None:
        sess.add(
            models.TrainerSecret(
                trainer_id=trainer_id,
                kind=kind,
                ciphertext=ciphertext,
            )
        )
        return

    row.ciphertext = ciphertext
