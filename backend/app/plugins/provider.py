from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, ClassVar
import abc

import niquests
import structlog

from app import types

if TYPE_CHECKING:
    from app import schema

_LOGGER = structlog.get_logger(__name__)


class VibeProvider(abc.ABC):
    """
    Base interface for provider plugins.

    Subclasses only need to:
    - set `name` class attribute
    - declare `exposed_elements` with Annotated metadata mapping types to real-world signals
    - implement `fetch()` to capture provider payloads from external APIs
    - implement `synthesize()` to translate captured payloads to Affinity components
    - optionally override `teardown()` when managing resources

    ──── Docstring convention for subclasses ───────────────────────────────────────────

    A provider's class docstring should follow this shape so that readers can
    quickly grasp both what it does and the aesthetic it imparts to a Vibemon.
    See `ClimateProvider` for a worked example.

    1. Opening line — one evocative sentence stating the provider's thematic
       premise (e.g. "A Vibemon is born from the sky above its birthplace.").
    2. Preamble — one sentence naming the data source and noting that its
       signals fold into a `schema.Affinity`.
    3. Stats line — one sentence mapping the six signals chosen for HP,
       Attack, Defense, Sp. Attack, Sp. Defense, and Speed.
    4. Closer — a short "the result is..." paragraph illustrating how
       different inputs produce visibly different creatures.

    Note: The `exposed_elements` class variable replaces the need for a
    type list in the docstring. Use `Annotated[VibemonTypeT, str]` to
    map each element to its real-world signal (e.g., "solar radiation").
    """

    name: ClassVar[str]
    """Stable provider identifier (persisted in `Affinity.provider_id`)."""

    exposed_elements: ClassVar[list[tuple[types.VibemonTypeT, str]]]
    """Elements this provider can assign with real-world signal descriptions."""

    @classmethod
    def get_exposed_elements(cls) -> dict[types.VibemonTypeT, str]:
        """Return a mapping of elements to their real-world signal descriptions."""
        return dict(cls.exposed_elements)

    def _log_http_error(self, exception: niquests.HTTPError) -> None:
        """If an HTTP error is encountered, log its context."""
        log_data: dict[str, Any] = {}

        if exception.response is not None:
            log_data["status"] = exception.response.status_code
            log_data["text"] = exception.response.text
            log_data["response.headers"] = exception.response.headers

        if exception.request is not None:
            log_data["url"] = exception.request.url
            log_data["request.headers"] = exception.request.headers

        _LOGGER.exception(f"HTTP error from {self.name} provider", **log_data)
        raise exception

    @abc.abstractmethod
    async def fetch(self, seed: schema.BirthSeed) -> dict[str, Any]:
        """
        Fetch and return a provider payload from upstream sources.

        Use seed.geo_coords and seed.timestamp as needed.
        Return provider-owned data (raw and/or deterministic enrichment)
        that can be persisted and replayed.
        """

    @abc.abstractmethod
    async def synthesize(self, seed: schema.BirthSeed, payload: dict[str, Any]) -> schema.Affinity:
        """
        Translate captured provider payload to Affinity components.

        Must be pure with respect to external providers: do not make new API calls here.
        Return a complete Affinity with identity, moves, intensity, and visual_notes.
        """

    @abc.abstractmethod
    def moves(self) -> Iterable[schema.Move]:
        """Return provider-authored moves for catalog seeding/sync."""

    @abc.abstractmethod
    async def teardown(self) -> None:
        """Release provider-owned resources. Override only when needed."""
