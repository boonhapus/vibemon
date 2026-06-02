"""Shared Pydantic schema base classes."""

import pydantic


class Schema(pydantic.BaseModel):
    """Mutable domain data object base. Use for runtime/lifecycle-shaped data."""

    model_config = pydantic.ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )


class FrozenSchema(pydantic.BaseModel):
    """Immutable value object base. Use for definitions and event/log records."""

    model_config = pydantic.ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        frozen=True,
    )
