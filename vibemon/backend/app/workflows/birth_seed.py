"""Workflow seam turning opted-in Providers into a BirthSeed."""

from collections.abc import Iterable
import datetime as dt
import random

from app.core.ids import TrainerIdT
from app.domains.generation.seed import BirthSeed
from app.providers import registry


def build_birth_seed(
    *,
    trainer_id: TrainerIdT,
    latitude: float,
    longitude: float,
    provider_names: Iterable[registry.ProviderName | str] | None = None,
    timestamp: dt.datetime | None = None,
) -> BirthSeed:
    return BirthSeed(
        timestamp=timestamp or dt.datetime.now(tz=dt.UTC),
        geo_coords=(latitude, longitude),
        trainer_id=trainer_id,
        providers=registry.build_provider_instances(provider_names),
    )


def default_coordinates() -> tuple[float, float]:
    return random.uniform(-90.0, 90.0), random.uniform(-180.0, 180.0)
