"""Minimal VibeProvider fake for workflow and generation tests."""

from app.domains.generation.affinity import Affinity
from app.domains.generation.ports import TrainerSecrets
from app.domains.generation.seed import BirthSeed
from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.domains.vibemon.identity import BaseStats, Identity
from app.providers import schema as providers_schema
from app.providers.base import VibeProvider


class FakeProviderPayload(providers_schema.ProviderPayload):
    datestamp: str
    element: str
    attack: int


class FakeProvider(VibeProvider[FakeProviderPayload]):
    name = "fake"
    payload_type = FakeProviderPayload

    def __init__(self, *, element: VibemonTypeT = VibemonTypeT.NORMAL, attack: int = 50) -> None:
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
            ),
        )


class WorkflowProviderPayload(providers_schema.ProviderPayload):
    weather: str = "clear"


class WorkflowFakeProvider(VibeProvider[WorkflowProviderPayload]):
    name = "test-provider"
    payload_type = WorkflowProviderPayload

    async def fetch(self, seed: BirthSeed, *, secrets: TrainerSecrets | None = None) -> WorkflowProviderPayload:
        return WorkflowProviderPayload()

    async def synthesize(self, seed: BirthSeed, payload: WorkflowProviderPayload) -> Affinity:
        return Affinity(
            identity=Identity(
                name="Testling",
                elements=(VibemonTypeT.FIRE,),
                base=BaseStats(hp=70, attack=75, defense=70, sp_attack=80, sp_defense=70, speed=90),
            ),
            intensity=1.0,
            provider_id=self.name,
            element_rankings={VibemonTypeT.FIRE: 1.0},
            moves=(
                Move(
                    id="test.ember",
                    name="Ember",
                    flavor_text="A tiny controlled flame.",
                    type=VibemonTypeT.FIRE,
                    category=MoveCategoryT.SPECIAL,
                    power=40,
                    accuracy=1.0,
                    pp=25,
                    target=MoveTargetT.SINGLE,
                ),
                Move(
                    id="test.flare",
                    name="Flare",
                    flavor_text="A quick flash of heat.",
                    type=VibemonTypeT.FIRE,
                    category=MoveCategoryT.SPECIAL,
                    power=50,
                    accuracy=0.95,
                    pp=20,
                    target=MoveTargetT.SINGLE,
                ),
            ),
        )
