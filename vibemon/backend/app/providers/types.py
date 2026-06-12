"""Provider catalog vocabulary."""

import enum


class RequirementKindT(enum.StrEnum):
    """Kinds of configuration a provider may require before fetch."""

    GEOLOCATION = "geolocation"
    TRAINER_SECRETS = "trainer_secrets"
    OAUTH2_LINK = "oauth2_link"
    SECRET_GROUP = "secret_group"


class RequirementStatusT(enum.StrEnum):
    """Whether a requirement is satisfied for the current trainer/context."""

    SATISFIED = "satisfied"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"
