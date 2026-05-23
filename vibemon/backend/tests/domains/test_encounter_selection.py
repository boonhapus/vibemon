from __future__ import annotations

import datetime as dt
import random
import uuid

import pytest

from app.domains.encounter import wild_encounter


@pytest.mark.asyncio
async def test_pick_encounter_tops_up_supply_and_revalidates_choice() -> None:
    now = dt.datetime(2026, 5, 19, 12, tzinfo=dt.UTC)
    initial_id = uuid.uuid7()
    generated_ids = [uuid.uuid7(), uuid.uuid7()]
    eligible_calls: list[int] = []
    generated: list[tuple[float, float]] = []
    revealed: list[uuid.UUID] = []

    async def list_eligible_wild_ids(latitude: float, longitude: float, limit: int) -> list[uuid.UUID]:
        eligible_calls.append(limit)
        if len(eligible_calls) == 1:
            return [initial_id]
        return [initial_id, *generated_ids]

    async def generate_supply(latitude: float, longitude: float) -> uuid.UUID:
        generated.append((latitude, longitude))
        return generated_ids[len(generated) - 1]

    async def load_candidates(
        trainer_id: uuid.UUID, eligible_ids: list[uuid.UUID], loaded_at: dt.datetime
    ) -> list[wild_encounter.EncounterCandidate]:
        assert loaded_at == now
        return [
            wild_encounter.EncounterCandidate(vibemon_id=eligible_ids[0], member_strength=100, adjustment_multiplier=1),
            wild_encounter.EncounterCandidate(vibemon_id=eligible_ids[1], member_strength=100, adjustment_multiplier=1),
            wild_encounter.EncounterCandidate(vibemon_id=eligible_ids[2], member_strength=100, adjustment_multiplier=1),
        ]

    async def revalidate_eligible(vibemon_id: uuid.UUID) -> bool:
        return vibemon_id != initial_id

    async def reveal_hook(vibemon_id: uuid.UUID) -> None:
        revealed.append(vibemon_id)

    service = wild_encounter.WildEncounterService(
        clock=lambda: now,
        rng=random.Random(1),
        supply_generator=generate_supply,
        reveal_hook=reveal_hook,
    )

    selection = await service.pick_encounter(
        trainer_id=uuid.uuid7(),
        latitude=41.8781,
        longitude=-87.6298,
        party_strength=100,
        list_eligible_wild_ids=list_eligible_wild_ids,
        load_candidates=load_candidates,
        revalidate_eligible=revalidate_eligible,
        desired_supply=3,
    )

    assert selection is not None
    assert selection.vibemon_id in generated_ids
    assert eligible_calls == [3, 3]
    assert generated == [(41.8781, -87.6298), (41.8781, -87.6298)]
    assert revealed == [selection.vibemon_id]


def test_active_adjustment_multiplier_decays_to_neutral() -> None:
    starts_at = dt.datetime(2026, 5, 19, 12, tzinfo=dt.UTC)
    ends_at = starts_at + dt.timedelta(hours=2)

    assert wild_encounter.active_adjustment_multiplier(
        initial_multiplier=0.25,
        starts_at=starts_at,
        ends_at=ends_at,
        now=starts_at + dt.timedelta(hours=1),
    ) == pytest.approx(0.625)
    assert (
        wild_encounter.active_adjustment_multiplier(
            initial_multiplier=0.25,
            starts_at=starts_at,
            ends_at=ends_at,
            now=ends_at,
        )
        == 1.0
    )
