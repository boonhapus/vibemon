import datetime as dt
import uuid

import pytest

from app.domains.generation.affinity import Affinity
from app.domains.generation.ports import TrainerSecrets
from app.domains.generation.seed import BirthSeed
from app.domains.generation.snapshot import BirthSnapshot
from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, VibemonTypeT
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.identity import BaseStats, Identity
from app.providers.base import VibeProvider
from tests.conftest import TEST_TRAINER_ID
from tests.providers.fake_provider import FakeProviderPayload


def _named_fake(provider_id: str, *, element: VibemonTypeT, attack: int) -> VibeProvider[FakeProviderPayload]:
    class Provider(VibeProvider[FakeProviderPayload]):
        name = provider_id
        payload_type = FakeProviderPayload

        def __init__(self) -> None:
            self._element = element
            self._attack = attack

        async def fetch(self, seed: BirthSeed, *, secrets: TrainerSecrets | None = None) -> FakeProviderPayload:
            return FakeProviderPayload(
                datestamp=seed.datestamp.isoformat(),
                element=self._element.value,
                attack=self._attack,
            )

        async def synthesize(self, seed: BirthSeed, payload: FakeProviderPayload) -> Affinity:
            element = VibemonTypeT(payload.element)
            return Affinity(
                identity=Identity(
                    name=f"{self.name}-{payload.datestamp}",
                    elements=(element,),
                    base=BaseStats(attack=payload.attack),
                ),
                provider_id=self.name,
                intensity=0.5,
                element_rankings={element: 1.0},
                moves=(
                    Move(
                        id=f"{self.name}.tap",
                        name=f"{self.name} Tap",
                        flavor_text="A deterministic test move.",
                        type=element,
                        category=MoveCategoryT.PHYSICAL,
                        power=40,
                    ),
                    Move(
                        id=f"{self.name}.pulse",
                        name=f"{self.name} Pulse",
                        flavor_text="A second deterministic test move.",
                        type=element,
                        category=MoveCategoryT.SPECIAL,
                        power=35,
                    ),
                ),
            )

    return Provider()


def test_birth_seed_rng_changes_with_trainer_id() -> None:
    base_kwargs = {
        "timestamp": dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        "geo_coords": (41.8781, -87.6298),
        "providers": [],
    }
    first = BirthSeed(trainer_id=TEST_TRAINER_ID, **base_kwargs)
    second = BirthSeed(trainer_id=uuid.uuid7(), **base_kwargs)
    assert first.rng_seed != second.rng_seed


def test_birth_seed_normalizes_timestamp_and_derives_stable_rngs() -> None:
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30),
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
        providers=[],
    )
    same_seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
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
        trainer_id=TEST_TRAINER_ID,
        providers=[
            _named_fake("beta", element=VibemonTypeT.WATER, attack=82),
            _named_fake("alpha", element=VibemonTypeT.FIRE, attack=76),
        ],
    )

    snapshot = await seed.fetch_snapshot()
    affinities = list(await snapshot.regenerate(reversed(seed.providers), seed))

    assert set(snapshot.provider_payloads) == {"alpha", "beta"}
    assert [affinity.provider_id for affinity in affinities] == ["alpha", "beta"]
    assert [affinity.identity.elements[0] for affinity in affinities] == [VibemonTypeT.FIRE, VibemonTypeT.WATER]


@pytest.mark.asyncio
async def test_birth_snapshot_requires_all_recorded_provider_implementations() -> None:
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
        providers=[],
    )
    snapshot = BirthSnapshot(provider_payloads={"missing": {}})

    with pytest.raises(ValueError, match="Missing provider implementations"):
        await snapshot.regenerate([], seed)


@pytest.mark.asyncio
async def test_vibemon_birth_is_replayable_from_same_seed_and_snapshot() -> None:
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 9, 30, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
        providers=[
            _named_fake("alpha", element=VibemonTypeT.FIRE, attack=76),
            _named_fake("beta", element=VibemonTypeT.WATER, attack=82),
        ],
    )
    snapshot = await seed.fetch_snapshot()

    first = Vibemon.birth(*await snapshot.regenerate(seed.providers, seed), birth_seed=seed)
    second = Vibemon.birth(*await snapshot.regenerate(seed.providers, seed), birth_seed=seed)

    assert first.identity.model_dump(exclude={"generated_at"}) == second.identity.model_dump(exclude={"generated_at"})
    assert first.growth_rate == second.growth_rate
    assert [move.id for move in first.moves] == [move.id for move in second.moves]


def test_affinity_merge_uses_fused_rankings_not_local_elements() -> None:
    import random

    fire_move = Move(
        id="climate.fire",
        name="Climate Fire",
        flavor_text="A deterministic test move.",
        type=VibemonTypeT.FIRE,
        category=MoveCategoryT.PHYSICAL,
        power=40,
    )
    water_move = Move(
        id="biome.water",
        name="Biome Water",
        flavor_text="A deterministic test move.",
        type=VibemonTypeT.WATER,
        category=MoveCategoryT.PHYSICAL,
        power=40,
    )
    climate = Affinity(
        identity=Identity(name="climate", elements=(VibemonTypeT.FIRE,), base=BaseStats(attack=70)),
        provider_id="climate",
        intensity=0.4,
        element_rankings={VibemonTypeT.FIRE: 0.9, VibemonTypeT.WATER: 0.1},
        moves=(fire_move,),
    )
    biome = Affinity(
        identity=Identity(name="biome", elements=(VibemonTypeT.STEEL,), base=BaseStats(attack=80)),
        provider_id="biome",
        intensity=0.8,
        element_rankings={VibemonTypeT.WATER: 0.95, VibemonTypeT.STEEL: 0.5},
        moves=(water_move,),
    )

    outcome = Affinity.merge(climate, biome, rng=random.Random(0))

    assert VibemonTypeT.WATER in outcome.identity.elements
