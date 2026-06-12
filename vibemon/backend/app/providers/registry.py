"""Canonical Provider registry: which Providers exist and what they can do."""

from collections.abc import Iterable
from typing import Any
import dataclasses
import enum

from app.providers import catalog_schema as catalog
from app.providers.base import VibeProvider
from app.providers.biome.provider import BiomeProvider
from app.providers.books.provider import BooksProvider
from app.providers.celestial.provider import CelestialProvider
from app.providers.climate.provider import ClimateProvider
from app.providers.fitness.provider import FitnessProvider
from app.providers.music.provider import MusicProvider
from app.providers.video.provider import VideoProvider


class ProviderName(enum.StrEnum):
    CLIMATE = "climate"
    BIOME = "biome"
    CELESTIAL = "celestial"
    MUSIC = "music"
    VIDEO = "video"
    BOOKS = "books"
    FITNESS = "fitness"


@dataclasses.dataclass(frozen=True)
class ProviderRegistration:
    """One catalog Provider and its birth participation flags."""

    name: ProviderName
    provider_type: type[VibeProvider[Any]]
    birth_capable: bool = False
    default_for_birth: bool = False

    def catalog_entry(self) -> catalog.ProviderCatalogEntry:
        return self.provider_type.catalog_entry()


REGISTRATIONS: tuple[ProviderRegistration, ...] = (
    ProviderRegistration(ProviderName.CLIMATE, ClimateProvider, birth_capable=True, default_for_birth=True),
    ProviderRegistration(ProviderName.BIOME, BiomeProvider, birth_capable=True, default_for_birth=True),
    ProviderRegistration(ProviderName.CELESTIAL, CelestialProvider, birth_capable=True, default_for_birth=True),
    ProviderRegistration(ProviderName.MUSIC, MusicProvider, birth_capable=True),
    ProviderRegistration(ProviderName.VIDEO, VideoProvider),
    ProviderRegistration(ProviderName.BOOKS, BooksProvider),
    ProviderRegistration(ProviderName.FITNESS, FitnessProvider),
)

_BY_NAME: dict[ProviderName, ProviderRegistration] = {registration.name: registration for registration in REGISTRATIONS}

DEFAULT_BIRTH_PROVIDERS: tuple[ProviderName, ...] = tuple(
    registration.name for registration in REGISTRATIONS if registration.default_for_birth
)


def get_registration(name: ProviderName | str) -> ProviderRegistration:
    try:
        return _BY_NAME[ProviderName(name)]
    except ValueError as exc:
        msg = f"Unknown provider {name!r}."
        raise KeyError(msg) from exc


def get_catalog_provider(name: str) -> type[VibeProvider[Any]]:
    return get_registration(name).provider_type


def list_catalog_entries() -> tuple[catalog.ProviderCatalogEntry, ...]:
    return tuple(registration.catalog_entry() for registration in REGISTRATIONS)


def resolve_provider_names(provider_names: Iterable[ProviderName | str] | None) -> tuple[ProviderName, ...]:
    """Resolve birth provider names, falling back to the default birth set."""
    if provider_names is None:
        return DEFAULT_BIRTH_PROVIDERS
    resolved = tuple(ProviderName(name) for name in provider_names)
    if not resolved:
        return DEFAULT_BIRTH_PROVIDERS
    for name in resolved:
        if not _BY_NAME[name].birth_capable:
            msg = f"Provider {name!r} cannot participate in birth generation."
            raise ValueError(msg)
    return resolved


def build_provider_instances(provider_names: Iterable[ProviderName | str] | None = None) -> list[VibeProvider[Any]]:
    return [_BY_NAME[name].provider_type() for name in resolve_provider_names(provider_names)]
