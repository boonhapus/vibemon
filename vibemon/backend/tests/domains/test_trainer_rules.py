from dataclasses import dataclass
import datetime as dt
import uuid

import pytest

from app.core.errors import CrewFull, GenerationAlreadyActive, GenerationCreditUnavailable
from app.domains.trainer import credits, crew


@dataclass
class CreditLedger:
    credits_consumed: int = 0
    active_hold_id: uuid.UUID | None = None
    hold_started_at: dt.datetime | None = None


def test_generation_credit_reservation_consumes_and_clears_hold() -> None:
    ledger = CreditLedger()
    now = dt.datetime(2026, 5, 19, 12, tzinfo=dt.UTC)

    hold_id = credits.reserve_generation_credit(ledger, now=now)
    credits.consume_generation_credit(ledger, hold_id)

    assert ledger.credits_consumed == 1
    assert ledger.active_hold_id is None
    assert ledger.hold_started_at is None


def test_generation_credit_rejects_concurrent_active_hold() -> None:
    now = dt.datetime(2026, 5, 19, 12, tzinfo=dt.UTC)
    ledger = CreditLedger(active_hold_id=uuid.uuid7(), hold_started_at=now)

    with pytest.raises(GenerationAlreadyActive):
        credits.reserve_generation_credit(ledger, now=now)


def test_generation_credit_replaces_stale_hold() -> None:
    now = dt.datetime(2026, 5, 19, 12, tzinfo=dt.UTC)
    stale_hold_id = uuid.uuid7()
    ledger = CreditLedger(
        active_hold_id=stale_hold_id,
        hold_started_at=now - credits.GENERATION_HOLD_TIMEOUT,
    )

    new_hold_id = credits.reserve_generation_credit(ledger, now=now)

    assert new_hold_id != stale_hold_id
    assert ledger.active_hold_id == new_hold_id
    assert ledger.hold_started_at == now


def test_generation_credit_enforces_daily_limit() -> None:
    ledger = CreditLedger(credits_consumed=credits.DAILY_GENERATION_CREDITS)
    now = dt.datetime(2026, 5, 19, 12, tzinfo=dt.UTC)

    with pytest.raises(GenerationCreditUnavailable):
        credits.reserve_generation_credit(ledger, now=now)


def test_crew_selects_first_open_slot() -> None:
    assert crew.select_adoption_slot(owned_count=3, used_slots={0, 2, 3}, release_slot=None) == 1


def test_crew_requires_release_when_full() -> None:
    with pytest.raises(CrewFull):
        crew.select_adoption_slot(owned_count=crew.MAX_CREW_SIZE, used_slots=set(range(6)), release_slot=None)


def test_crew_uses_release_slot_when_full() -> None:
    assert crew.select_adoption_slot(owned_count=crew.MAX_CREW_SIZE, used_slots=set(range(6)), release_slot=4) == 4


def _crew(*slots: int) -> list[crew.CrewMember]:
    return [crew.CrewMember(vibemon_id=uuid.uuid7(), crew_slot=slot) for slot in slots]


def test_plan_adoption_fills_open_slot_and_ignores_release_when_room() -> None:
    owned = _crew(0, 1)
    plan = crew.plan_adoption(owned=owned, release_vibemon_id=owned[0].vibemon_id)

    assert plan.slot == 2
    assert plan.release_vibemon_id is None


def test_plan_adoption_releases_into_freed_slot_when_full() -> None:
    owned = _crew(0, 1, 2, 3, 4, 5)
    released = owned[3]

    plan = crew.plan_adoption(owned=owned, release_vibemon_id=released.vibemon_id)

    assert plan.slot == 3
    assert plan.release_vibemon_id == released.vibemon_id


def test_plan_adoption_full_without_release_raises() -> None:
    with pytest.raises(CrewFull):
        crew.plan_adoption(owned=_crew(0, 1, 2, 3, 4, 5), release_vibemon_id=None)


def test_plan_adoption_full_with_unowned_release_raises() -> None:
    with pytest.raises(CrewFull):
        crew.plan_adoption(owned=_crew(0, 1, 2, 3, 4, 5), release_vibemon_id=uuid.uuid7())
