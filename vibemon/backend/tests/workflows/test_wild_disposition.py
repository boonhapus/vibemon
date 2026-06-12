"""Unit tests for wild disposition transitions and encounter adjustments."""

import datetime as dt
import uuid

import pytest

from app.domains.vibemon.disposition import VibemonDispositionT
from app.storage.database import models
from app.workflows.encounter_adjustment import upsert_encounter_adjustment
from app.workflows.wild_disposition import mark_wild


def test_mark_wild_clears_ownership_and_stamps_wild_fields() -> None:
    now = dt.datetime(2026, 6, 11, 12, 0, tzinfo=dt.UTC)
    row = models.Vibemon(
        id=uuid.uuid7(),
        trainer_id=uuid.uuid7(),
        crew_slot=2,
        disposition=VibemonDispositionT.OWNED.value,
    )

    mark_wild(row, now)

    assert row.trainer_id is None
    assert row.crew_slot is None
    assert row.disposition == VibemonDispositionT.WILD.value
    assert row.wild_entered_at == now
    assert row.last_encountered_at == now


async def test_upsert_encounter_adjustment_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="Unknown encounter adjustment source"):
        await upsert_encounter_adjustment(
            None,  # session unused before source validation
            uuid.uuid7(),
            uuid.uuid7(),
            "polka",
            dt.datetime.now(tz=dt.UTC),
        )
