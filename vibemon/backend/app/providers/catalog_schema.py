"""Provider catalog metadata declared by plugins and evaluated at runtime."""

from typing import Annotated, Literal

import pydantic

from app.core.schema import Schema
from app.providers import types as provider_types


class DataSourceInfo(Schema):
    name: str
    description: str


class GeolocationRequirement(Schema):
    kind: Literal[provider_types.RequirementKindT.GEOLOCATION] = provider_types.RequirementKindT.GEOLOCATION
    id: str
    label: str
    description: str


class TrainerSecretsRequirement(Schema):
    kind: Literal[provider_types.RequirementKindT.TRAINER_SECRETS] = provider_types.RequirementKindT.TRAINER_SECRETS
    id: str
    label: str
    description: str
    secret_kinds: tuple[str, ...]


class OAuth2LinkRequirement(Schema):
    kind: Literal[provider_types.RequirementKindT.OAUTH2_LINK] = provider_types.RequirementKindT.OAUTH2_LINK
    id: str
    label: str
    description: str
    service: str
    secret_kinds: tuple[str, ...]
    authorize_path: str


class SecretGroupRequirement(Schema):
    kind: Literal[provider_types.RequirementKindT.SECRET_GROUP] = provider_types.RequirementKindT.SECRET_GROUP
    id: str
    label: str
    description: str
    branches: tuple[TrainerSecretsRequirement | OAuth2LinkRequirement, ...]


SecretBranchRequirement = TrainerSecretsRequirement | OAuth2LinkRequirement

ProviderRequirement = Annotated[
    GeolocationRequirement | TrainerSecretsRequirement | OAuth2LinkRequirement | SecretGroupRequirement,
    pydantic.Field(discriminator="kind"),
]


class ProviderElement(Schema):
    type: str
    signal: str


class ProviderCatalogEntry(Schema):
    id: str
    label: str
    tagline: str
    lore: tuple[str, ...]
    data_sources: tuple[DataSourceInfo, ...]
    elements: tuple[ProviderElement, ...]
    requirements: tuple[ProviderRequirement, ...]
    implemented: bool


class RequirementStatus(Schema):
    status: provider_types.RequirementStatusT
    authorize_path: str | None = None


class ProviderStatus(Schema):
    id: str
    ready: bool
    requirements: dict[str, RequirementStatus]
