"""HTTP request and response bodies for provider catalog routes."""

from typing import Literal
import datetime as dt
import uuid

from app.core.schema import Schema
from app.providers import catalog_schema as provider_catalog
from app.providers import types as provider_types


class RequirementStatusRead(Schema):
    status: provider_types.RequirementStatusT
    authorize_url: str | None = None


class ProviderStatusRead(Schema):
    id: str
    ready: bool
    requirements: dict[str, RequirementStatusRead]
    prefetched_at: dt.datetime | None = None


class ProviderCatalogListRead(Schema):
    providers: tuple[provider_catalog.ProviderCatalogEntry, ...]


class ProviderStatusListRead(Schema):
    providers: tuple[ProviderStatusRead, ...]


class ProviderPrefetchBody(Schema):
    latitude: float | None = None
    longitude: float | None = None
    force_refresh: bool = False


class ProviderPrefetchRead(Schema):
    status: Literal["ready"] = "ready"
    prefetched_at: dt.datetime


def _authorize_url(path: str, trainer_id: uuid.UUID) -> str:
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}trainer_id={trainer_id}"


def requirement_status_to_read(
    status: provider_catalog.RequirementStatus,
    *,
    trainer_id: uuid.UUID,
) -> RequirementStatusRead:
    authorize_url = None
    if status.authorize_path is not None:
        authorize_url = _authorize_url(status.authorize_path, trainer_id)
    return RequirementStatusRead(status=status.status, authorize_url=authorize_url)


def provider_status_to_read(
    status: provider_catalog.ProviderStatus,
    *,
    trainer_id: uuid.UUID,
    prefetched_at: dt.datetime | None = None,
) -> ProviderStatusRead:
    return ProviderStatusRead(
        id=status.id,
        ready=status.ready,
        requirements={
            requirement_id: requirement_status_to_read(requirement_status, trainer_id=trainer_id)
            for requirement_id, requirement_status in status.requirements.items()
        },
        prefetched_at=prefetched_at,
    )
