"""Provider catalog registry and requirement evaluation."""

from typing import Any
import inspect
import uuid

from app.core.errors import ProviderConfigRequired, ProviderNotImplemented
from app.domains.generation.ports import TrainerSecrets
from app.providers import catalog_schema as catalog
from app.providers import types as provider_types
from app.providers.base import VibeProvider
from app.providers.biome.provider import BiomeProvider
from app.providers.books.provider import BooksProvider
from app.providers.celestial.provider import CelestialProvider
from app.providers.climate.provider import ClimateProvider
from app.providers.fitness.provider import FitnessProvider
from app.providers.music.provider import MusicProvider
from app.providers.video.provider import VideoProvider

CATALOG_PROVIDER_TYPES: tuple[type[VibeProvider[Any]], ...] = (
    ClimateProvider,
    BiomeProvider,
    CelestialProvider,
    MusicProvider,
    VideoProvider,
    BooksProvider,
    FitnessProvider,
)

_PROVIDER_BY_NAME: dict[str, type[VibeProvider[Any]]] = {cls.name: cls for cls in CATALOG_PROVIDER_TYPES}


def get_catalog_provider(name: str) -> type[VibeProvider[Any]]:
    try:
        return _PROVIDER_BY_NAME[name]
    except KeyError as exc:
        msg = f"Unknown provider {name!r}."
        raise KeyError(msg) from exc


def list_catalog_entries() -> tuple[catalog.ProviderCatalogEntry, ...]:
    return tuple(cls.catalog_entry() for cls in CATALOG_PROVIDER_TYPES)


def _lore_from_docstring(doc: str | None) -> tuple[str, ...]:
    if doc is None:
        return ()
    paragraphs = [paragraph.strip() for paragraph in doc.split("\n\n") if paragraph.strip()]
    cleaned: list[str] = []
    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if not lines:
            continue
        if lines[0].startswith("────"):
            continue
        cleaned.append(" ".join(lines))
    return tuple(cleaned)


async def _secret_kinds_satisfied(
    secret_kinds: tuple[str, ...],
    *,
    trainer_id: uuid.UUID,
    secrets: TrainerSecrets | None,
) -> bool:
    if secrets is None or not secret_kinds:
        return False
    for kind in secret_kinds:
        if await secrets.get(trainer_id, kind) is None:
            return False
    return True


async def _evaluate_secret_branch(
    branch: catalog.SecretBranchRequirement,
    *,
    trainer_id: uuid.UUID,
    secrets: TrainerSecrets | None,
) -> catalog.RequirementStatus:
    satisfied = await _secret_kinds_satisfied(branch.secret_kinds, trainer_id=trainer_id, secrets=secrets)
    authorize_path = None
    if not satisfied and isinstance(branch, catalog.OAuth2LinkRequirement):
        authorize_path = branch.authorize_path
    return catalog.RequirementStatus(
        status=provider_types.RequirementStatusT.SATISFIED if satisfied else provider_types.RequirementStatusT.MISSING,
        authorize_path=authorize_path,
    )


async def evaluate_requirement(
    requirement: catalog.ProviderRequirement,
    *,
    trainer_id: uuid.UUID,
    secrets: TrainerSecrets | None,
    geolocation: tuple[float, float] | None,
) -> catalog.RequirementStatus:
    match requirement:
        case catalog.GeolocationRequirement():
            satisfied = geolocation is not None
            return catalog.RequirementStatus(
                status=(
                    provider_types.RequirementStatusT.SATISFIED
                    if satisfied
                    else provider_types.RequirementStatusT.MISSING
                )
            )
        case catalog.TrainerSecretsRequirement():
            satisfied = await _secret_kinds_satisfied(
                requirement.secret_kinds,
                trainer_id=trainer_id,
                secrets=secrets,
            )
            return catalog.RequirementStatus(
                status=(
                    provider_types.RequirementStatusT.SATISFIED
                    if satisfied
                    else provider_types.RequirementStatusT.MISSING
                )
            )
        case catalog.OAuth2LinkRequirement():
            return await _evaluate_secret_branch(
                requirement,
                trainer_id=trainer_id,
                secrets=secrets,
            )
        case catalog.SecretGroupRequirement():
            branch_statuses = [
                await _evaluate_secret_branch(
                    branch,
                    trainer_id=trainer_id,
                    secrets=secrets,
                )
                for branch in requirement.branches
            ]
            if any(status.status is provider_types.RequirementStatusT.SATISFIED for status in branch_statuses):
                return catalog.RequirementStatus(status=provider_types.RequirementStatusT.SATISFIED)
            authorize_path = next(
                (status.authorize_path for status in branch_statuses if status.authorize_path is not None),
                None,
            )
            return catalog.RequirementStatus(
                status=provider_types.RequirementStatusT.MISSING,
                authorize_path=authorize_path,
            )


async def evaluate_provider_status(
    provider_cls: type[VibeProvider[Any]],
    *,
    trainer_id: uuid.UUID,
    secrets: TrainerSecrets | None,
    geolocation: tuple[float, float] | None,
) -> catalog.ProviderStatus:
    if not provider_cls.implemented:
        requirements = {
            requirement.id: catalog.RequirementStatus(status=provider_types.RequirementStatusT.UNAVAILABLE)
            for requirement in provider_cls.requirements
        }
        return catalog.ProviderStatus(id=provider_cls.name, ready=False, requirements=requirements)

    requirement_status: dict[str, catalog.RequirementStatus] = {}
    for requirement in provider_cls.requirements:
        requirement_status[requirement.id] = await evaluate_requirement(
            requirement,
            trainer_id=trainer_id,
            secrets=secrets,
            geolocation=geolocation,
        )

    ready = all(status.status is provider_types.RequirementStatusT.SATISFIED for status in requirement_status.values())
    return catalog.ProviderStatus(id=provider_cls.name, ready=ready, requirements=requirement_status)


async def list_provider_statuses(
    *,
    trainer_id: uuid.UUID,
    secrets: TrainerSecrets | None,
    geolocation: tuple[float, float] | None,
) -> tuple[catalog.ProviderStatus, ...]:
    statuses: list[catalog.ProviderStatus] = []
    for provider_cls in CATALOG_PROVIDER_TYPES:
        statuses.append(
            await evaluate_provider_status(
                provider_cls,
                trainer_id=trainer_id,
                secrets=secrets,
                geolocation=geolocation,
            )
        )
    return tuple(statuses)


async def ensure_requirements_met(
    provider_cls: type[VibeProvider[Any]],
    *,
    trainer_id: uuid.UUID,
    secrets: TrainerSecrets | None,
    geolocation: tuple[float, float] | None,
) -> None:
    if not provider_cls.implemented:
        raise ProviderNotImplemented(f"Provider {provider_cls.name!r} is not implemented yet.")

    status = await evaluate_provider_status(
        provider_cls,
        trainer_id=trainer_id,
        secrets=secrets,
        geolocation=geolocation,
    )
    if not status.ready:
        raise ProviderConfigRequired(f"Provider {provider_cls.name!r} is missing required configuration.")


def bind_catalog_methods() -> None:
    """Attach catalog helpers to ``VibeProvider`` without import cycles at class body time."""

    @classmethod
    def catalog_entry(cls: type[VibeProvider[Any]]) -> catalog.ProviderCatalogEntry:
        elements = tuple(
            catalog.ProviderElement(type=element.value, signal=signal) for element, signal in cls.exposed_elements
        )
        return catalog.ProviderCatalogEntry(
            id=cls.name,
            label=cls.display_label,
            tagline=cls.tagline,
            lore=_lore_from_docstring(inspect.getdoc(cls)),
            data_sources=cls.data_sources,
            elements=elements,
            requirements=cls.requirements,
            implemented=cls.implemented,
        )

    VibeProvider.catalog_entry = catalog_entry  # type: ignore[attr-defined]


bind_catalog_methods()
