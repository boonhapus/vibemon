"""Provider catalog and prefetch routes."""

from contextlib import nullcontext
from typing import Annotated
import datetime as dt

from litestar import Router, get, post
from litestar.connection import Request
from litestar.datastructures import State
from litestar.exceptions import HTTPException, NotFoundException
from litestar.params import Parameter
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.errors import ProviderConfigRequired, ProviderNotImplemented
from app.domains.generation.seed import BirthSeed
from app.http import deps
from app.http.schemas import providers as provider_schemas
from app.providers import catalog, registry
from app.providers import types as provider_types
from app.storage.cache.provider_prefetch import list_prefetched_at, record_prefetch
from app.storage.cache.redis import bypass_http_cache
from app.storage.secrets.repository import DbTrainerSecrets

_LOGGER = structlog.get_logger(__name__)


def _geolocation(
    latitude: float | None,
    longitude: float | None,
) -> tuple[float, float] | None:
    if latitude is None or longitude is None:
        return None
    return latitude, longitude


@get("/")
async def list_providers() -> provider_schemas.ProviderCatalogListRead:
    """Return provider catalog metadata for the configuration UI."""
    return provider_schemas.ProviderCatalogListRead(providers=registry.list_catalog_entries())


@get("/status")
async def provider_status(
    request: Request[object, object, State],
    db: AsyncSession,
    latitude: Annotated[float | None, Parameter(query="latitude")] = None,
    longitude: Annotated[float | None, Parameter(query="longitude")] = None,
) -> provider_schemas.ProviderStatusListRead:
    """Return per-trainer requirement satisfaction for provider configuration."""
    trainer = await deps.load_authenticated_trainer(request, db)
    secrets = DbTrainerSecrets(db)
    statuses = await catalog.list_provider_statuses(
        trainer_id=trainer.id,
        secrets=secrets,
        geolocation=_geolocation(latitude, longitude),
    )
    prefetched_at = await list_prefetched_at(
        trainer.id,
        tuple(status.id for status in statuses),
    )
    return provider_schemas.ProviderStatusListRead(
        providers=tuple(
            provider_schemas.provider_status_to_read(
                status,
                trainer_id=trainer.id,
                prefetched_at=prefetched_at.get(status.id),
            )
            for status in statuses
        )
    )


@post("/{provider_id:str}/prefetch")
async def prefetch_provider(
    provider_id: str,
    request: Request[object, object, State],
    data: provider_schemas.ProviderPrefetchBody,
    db: AsyncSession,
) -> provider_schemas.ProviderPrefetchRead:
    """Warm provider upstream caches without running full generation."""
    trainer = await deps.load_authenticated_trainer(request, db)
    try:
        provider_cls = registry.get_catalog_provider(provider_id)
    except KeyError as exc:
        raise NotFoundException(detail=f"Unknown provider {provider_id!r}.") from exc

    geolocation = _geolocation(data.latitude, data.longitude)
    secrets = DbTrainerSecrets(db)

    try:
        await catalog.ensure_requirements_met(
            provider_cls,
            trainer_id=trainer.id,
            secrets=secrets,
            geolocation=geolocation,
        )
    except ProviderNotImplemented as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ProviderConfigRequired:
        raise

    needs_geolocation = any(
        requirement.kind is provider_types.RequirementKindT.GEOLOCATION for requirement in provider_cls.requirements
    )
    if needs_geolocation and geolocation is None:
        raise ProviderConfigRequired("Location is required for this provider.")

    coords = geolocation or (0.0, 0.0)
    seed = BirthSeed(
        timestamp=dt.datetime.now(tz=dt.UTC),
        geo_coords=coords,
        trainer_id=trainer.id,
        providers=[],
    )

    cache_context = bypass_http_cache() if data.force_refresh else nullcontext()
    with cache_context:
        provider = provider_cls()
        await provider.fetch(seed, secrets=secrets)

    prefetched_at = dt.datetime.now(tz=dt.UTC)
    await record_prefetch(trainer.id, provider_id, prefetched_at)

    _LOGGER.info(
        "provider_prefetch",
        provider=provider_id,
        trainer_id=str(trainer.id),
        force_refresh=data.force_refresh,
    )
    return provider_schemas.ProviderPrefetchRead(prefetched_at=prefetched_at)


provider_router = Router(
    path="/api/providers",
    route_handlers=[
        list_providers,
        provider_status,
        prefetch_provider,
    ],
)
