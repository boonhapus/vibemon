from __future__ import annotations

from typing import Any
import datetime as dt

import pytest

from app.domains.generation.affinity import Affinity
from app.domains.generation.seed import BirthSeed
from app.domains.generation.snapshot import BirthSnapshot
from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, VibemonTypeT
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.identity import Identity


class FakeProvider:
    def __init__(self, name: str, element: VibemonTypeT, attack: int) -> None:
        self.name = name
        self._element = element
        self._attack = attack

    async def fetch(self, seed: BirthSeed) -> dict[str, Any]:
        return {
            "datestamp": seed.datestamp.isoformat(),
            "element": self._element.value,
            "attack": self._attack,
        }

    async def synthesize(self, seed: BirthSeed, payload: dict[str, Any]) -> Affinity:
        return Affinity(
            identity=Identity(
                name=f"{self.name}-{payload['datestamp']}",
                elements=(self._element,),
                base_attack=self._attack,
            ),
            provider_id=self.name,
            intensity=0.5,
            moves=(
                Move(
                    id=f"{self.name}.tap",
                    name=f"{self.name} Tap",
                    flavor_text="A deterministic test move.",
                    type=self._element,
                    category=MoveCategoryT.PHYSICAL,
                    power=40,
                ),
            ),
        )


def test_birth_seed_normalizes_timestamp_and_derives_stable_rngs() -> None:
    seed = BirthSeed(timestamp=dt.datetime(2026, 5, 19, 9, 30), geo_coords=(41.8781, -87.6298), providers=[])
    same_seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        providers=[],
    )

    assert seed.timestamp.tzinfo is dt.UTC
    assert seed.rng_seed == same_seed.rng_seed
    assert seed.rng_seed_for("identity.evo_seed") == same_seed.rng_seed_for("identity.evo_seed")
    assert seed.rng_seed_for("identity.evo_seed") != seed.rng_seed_for("identity.radiant")


@pytest.mark.asyncio
async def test_birth_snapshot_replays_provider_payloads_by_provider_name() -> None:
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        providers=[
            FakeProvider("beta", VibemonTypeT.WATER, 82),
            FakeProvider("alpha", VibemonTypeT.FIRE, 76),
        ],
    )

    snapshot = await seed.fetch_snapshot()
    affinities = list(await snapshot.regenerate(reversed(seed.providers), seed))

    assert set(snapshot.provider_payloads) == {"alpha", "beta"}
    assert [affinity.provider_id for affinity in affinities] == ["alpha", "beta"]
    assert [affinity.identity.elements[0] for affinity in affinities] == [VibemonTypeT.FIRE, VibemonTypeT.WATER]


@pytest.mark.asyncio
async def test_birth_snapshot_requires_all_recorded_provider_implementations() -> None:
    seed = BirthSeed(timestamp=dt.datetime(2026, 5, 19, tzinfo=dt.UTC), geo_coords=(41.8781, -87.6298), providers=[])
    snapshot = BirthSnapshot(provider_payloads={"missing": {}})

    with pytest.raises(ValueError, match="Missing provider implementations"):
        await snapshot.regenerate([], seed)


@pytest.mark.asyncio
async def test_vibemon_birth_is_replayable_from_same_seed_and_snapshot() -> None:
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        providers=[
            FakeProvider("alpha", VibemonTypeT.FIRE, 76),
            FakeProvider("beta", VibemonTypeT.WATER, 82),
        ],
    )
    snapshot = await seed.fetch_snapshot()

    first = Vibemon.birth(*await snapshot.regenerate(seed.providers, seed), birth_seed=seed)
    second = Vibemon.birth(*await snapshot.regenerate(seed.providers, seed), birth_seed=seed)

    assert first.identity.model_dump(exclude={"generated_at"}) == second.identity.model_dump(exclude={"generated_at"})
    assert [move.id for move in first.moves] == [move.id for move in second.moves]
