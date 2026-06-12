"""Public Vibemon read-model assembly with signed asset URLs."""

import datetime as dt

from app.core.ids import TrainerIdT
from app.domains.vibemon.schema import PublicVibemon
from app.storage.blob.monstore import get_default_monstore
from app.storage.database import mapper, models, read_model


async def public_vibemon(
    row: models.Vibemon,
    *,
    reviewing_trainer_id: TrainerIdT | None = None,
) -> PublicVibemon:
    assembler = read_model.ReadModelAssembler(
        schema_loader=mapper.vibemon_from_row,
        asset_urler=default_asset_urler,
    )
    return await assembler.assemble(row, reviewing_trainer_id=reviewing_trainer_id)


async def default_asset_urler(key: str, expires_in: dt.timedelta) -> str:
    return await get_default_monstore().url(key, expires_in)
