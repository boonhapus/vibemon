"""Trainer generation-credit domain rules."""

from typing import Protocol
import datetime as dt
import uuid

from app.core.errors import GenerationAlreadyActive, GenerationCreditUnavailable

DAILY_GENERATION_CREDITS = 3
GENERATION_HOLD_TIMEOUT = dt.timedelta(minutes=10)


class GenerationCreditLedger(Protocol):
    @property
    def credits_consumed(self) -> int: ...

    @credits_consumed.setter
    def credits_consumed(self, value: int) -> None: ...

    @property
    def active_hold_id(self) -> uuid.UUID | None: ...

    @active_hold_id.setter
    def active_hold_id(self, value: uuid.UUID | None) -> None: ...

    @property
    def hold_started_at(self) -> dt.datetime | None: ...

    @hold_started_at.setter
    def hold_started_at(self, value: dt.datetime | None) -> None: ...


def reserve_generation_credit(row: GenerationCreditLedger, *, now: dt.datetime) -> uuid.UUID:
    """Reserve one daily generation credit and return the active hold id."""
    if row.active_hold_id is not None:
        if row.hold_started_at is not None and row.hold_started_at <= now - GENERATION_HOLD_TIMEOUT:
            row.active_hold_id = None
            row.hold_started_at = None
        else:
            raise GenerationAlreadyActive("Trainer already has an active generation hold.")
    if row.credits_consumed >= DAILY_GENERATION_CREDITS:
        raise GenerationCreditUnavailable("Trainer has no generation credits remaining today.")
    hold_id = uuid.uuid7()
    row.active_hold_id = hold_id
    row.hold_started_at = now
    return hold_id


def consume_generation_credit(row: GenerationCreditLedger, hold_id: uuid.UUID) -> None:
    """Consume a reserved generation credit."""
    if row.active_hold_id != hold_id:
        raise GenerationAlreadyActive("Generation hold changed before credit consumption.")
    row.credits_consumed += 1
    row.active_hold_id = None
    row.hold_started_at = None


def release_generation_credit(row: GenerationCreditLedger, hold_id: uuid.UUID) -> None:
    """Release a generation-credit hold without consuming it."""
    if row.active_hold_id == hold_id:
        row.active_hold_id = None
        row.hold_started_at = None
