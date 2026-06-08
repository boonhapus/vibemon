"""Birth provider selection for generation workflows."""

from collections.abc import Iterable
import datetime as dt
import enum
import random

from app.core.ids import TrainerIdT
from app.domains.generation.seed import BirthSeed
from app.providers.biome.provider import BiomeProvider
from app.providers.climate.provider import ClimateProvider
from app.providers.music.provider import MusicProvider

type GenerationProviderT = ClimateProvider | BiomeProvider | MusicProvider


class ProviderName(enum.StrEnum):
    CLIMATE = "climate"
    BIOME = "biome"
    MUSIC = "music"


DEFAULT_PROVIDERS: tuple[ProviderName, ...] = (ProviderName.CLIMATE, ProviderName.BIOME)

_PROVIDER_TYPES: dict[ProviderName, type[GenerationProviderT]] = {
    ProviderName.CLIMATE: ClimateProvider,
    ProviderName.BIOME: BiomeProvider,
    ProviderName.MUSIC: MusicProvider,
}


def resolve_provider_names(provider_names: Iterable[str] | None) -> tuple[ProviderName, ...]:
    if provider_names is None or not list(provider_names):
        return DEFAULT_PROVIDERS
    return tuple(ProviderName(name) for name in provider_names)


def build_provider_instances(provider_names: Iterable[str] | None = None) -> list[GenerationProviderT]:
    return [_PROVIDER_TYPES[name]() for name in resolve_provider_names(provider_names)]



def build_birth_seed(
    *,
    trainer_id: TrainerIdT,
    latitude: float,
    longitude: float,
    provider_names: Iterable[str] | None = None,
    timestamp: dt.datetime | None = None,
) -> BirthSeed:
    return BirthSeed(
        timestamp=timestamp or dt.datetime.now(tz=dt.UTC),
        geo_coords=(latitude, longitude),
        trainer_id=trainer_id,
        providers=build_provider_instances(provider_names),
    )


def default_coordinates() -> tuple[float, float]:
    return random.uniform(-90.0, 90.0), random.uniform(-180.0, 180.0)
