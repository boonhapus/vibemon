from typing import ClassVar, TYPE_CHECKING
import abc

import niquests
import structlog

if TYPE_CHECKING:
   from app import schema

_LOGGER = structlog.get_logger(__name__)


class VibeProvider(abc.ABC):
    """
    Base interface for provider plugins.

    Subclasses only need to:
    - set `name` class attribute
    - implement `synthesize()` to translate raw API data to Affinity components
    - optionally override `teardown()` when managing resources

    ──── Docstring convention for subclasses ───────────────────────────────────────────

    A provider's class docstring should follow this five-part shape so that
    readers can quickly grasp both what it does and the aesthetic it imparts
    to a Vibemon. See `ClimateProvider` for a worked example.

    1. Opening line — one evocative sentence stating the provider's thematic
       premise (e.g. "A Vibemon is born from the sky above its birthplace.").
    2. Preamble — one sentence naming the data source and noting that its
       signals fold into a `schema.Affinity`.
    3. Type list — a bullet list of `TYPE — conditions that drive it`,
       covering every elemental type the provider can score.
    4. Stats line — one sentence mapping the six signals chosen for HP,
       Attack, Defense, Sp. Attack, Sp. Defense, and Speed.
    5. Closer — a short "the result is..." paragraph illustrating how
       different inputs produce visibly different creatures.
    """

    name: ClassVar[str]
    """Stable provider identifier (persisted in `Affinity.provider_id`)."""

    def _log_http_error(self, exception: niquests.HTTPError) -> None:
        """If an HTTP error is encountered, log its context."""
        log_data = {}
        
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
    async def synthesize(self, ctx: schema.BirthContext) -> schema.Affinity:
        """
        Translate raw API data to Affinity components.

        Use ctx.geo_coords, ctx.timestamp, ctx.providers as needed.
        Return a complete Affinity with identity, moves, intensity, and visual_notes.
        """

    async def teardown(self) -> None:
        """Release provider-owned resources. Override only when needed."""
