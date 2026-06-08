from typing import TYPE_CHECKING, Any, ClassVar, cast
import abc
import json
import pathlib
import sys

import niquests
import structlog

from app.domains.move import universal
from app.domains.move.entity import Move
from app.domains.move.types import VibemonTypeT
from app.providers import catalog_schema as catalog
from app.providers import schema

if TYPE_CHECKING:
    from app.domains.generation.affinity import Affinity
    from app.domains.generation.ports import TrainerSecrets
    from app.domains.generation.seed import BirthSeed

_LOGGER = structlog.get_logger(__name__)


class VibeProvider[PayloadT: schema.ProviderPayload](abc.ABC):
    """
    Base interface for provider plugins.

    Subclasses only need to:
    - set `name` class attribute
    - set `payload_type` to the provider's ``ProviderPayload`` subclass
    - declare `exposed_elements` with Annotated metadata mapping types to real-world signals
    - implement `fetch()` to capture provider payloads from external APIs
    - implement `synthesize()` to translate captured payloads to Affinity components

    ──── Docstring convention for subclasses ───────────────────────────────────────────

    Provider class docstrings are player-facing lore in the configuration modal
    (see ``catalog._lore_from_docstring``). Write them in Vibemon's 1960s-70s
    mid-century register: warm, analog, unhurried, a little Kodachrome-concrete.
    See ``ClimateProvider`` for a worked example.

    Voice
        - Cozy nostalgia, not epic fantasy. Prefer "reads differently", "carries",
          "picked up from" over "soul", "destiny", or "fundamentally different".
        - Ground flavor in period texture when it fits: linoleum-bright noon, pea-soup
          fog, boulevard haze, transistor static, harvest-gold sun, linen overcast.
        - Stay poetic, not mechanical: do not name API clients, data pipelines,
          ``Affinity``, base stats, signals, or typing rules — those belong in code
          and the configuration panel's data-source list.
        - Avoid modern SaaS tone ("leverage", "unlock") and weak openers ("The
          result is that…").

    Shape (two paragraphs only)
        1. Thesis — one sentence stating what real-world context the Vibemon
           carries from birth.
        2. Meaning — one short paragraph expanding the thesis with two or three
           concrete contrasts (place, weather, taste, habit) in the 1960s-70s
           register.

    Note: ``exposed_elements`` and ``data_sources`` carry technical mapping;
    the docstring is flavor only.
    """

    name: ClassVar[str]
    """Stable provider identifier (persisted in `Affinity.provider_id`)."""

    payload_type: ClassVar[type[schema.ProviderPayload]]
    """Typed payload model produced by ``fetch`` and consumed by ``synthesize``."""

    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]]
    """Elements this provider can assign with real-world signal descriptions."""

    display_label: ClassVar[str]
    """Short UI label such as ``SKY`` or ``GROUND``."""

    tagline: ClassVar[str]
    """One-line provider summary for list hover and selection rails."""

    data_sources: ClassVar[tuple[catalog.DataSourceInfo, ...]] = ()
    """Upstream sources surfaced in the provider configuration panel."""

    requirements: ClassVar[tuple[catalog.ProviderRequirement, ...]] = ()
    """Configuration gates that must pass before ``fetch`` can succeed."""

    implemented: ClassVar[bool] = True
    """Whether this provider can fetch and synthesize birth payloads."""

    @classmethod
    def parse_payload(cls, raw: dict[str, Any]) -> PayloadT:
        """Validate a persisted JSON payload for replay."""
        return cast(PayloadT, cls.payload_type.model_validate(raw))

    @classmethod
    def serialize_payload(cls, payload: PayloadT) -> dict[str, Any]:
        """Serialize a typed payload for snapshot persistence."""
        return payload.model_dump(mode="json")

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

    @classmethod
    def get_exposed_elements(cls) -> dict[VibemonTypeT, str]:
        """Return a mapping of elements to their real-world signal descriptions."""
        return dict(cls.exposed_elements)

    @abc.abstractmethod
    async def fetch(
        self,
        seed: BirthSeed,
        *,
        secrets: TrainerSecrets | None = None,
    ) -> PayloadT:
        """
        Fetch and return a provider payload from upstream sources.

        Use seed.geo_coords and seed.timestamp as needed.
        Return provider-owned data (raw and/or deterministic enrichment)
        that can be persisted and replayed.
        """

    @abc.abstractmethod
    async def synthesize(self, seed: BirthSeed, payload: PayloadT) -> Affinity:
        """
        Translate captured provider payload to Affinity components.

        Must be pure with respect to external providers: do not make new API calls here.
        Return a complete Affinity with identity, moves, intensity, and visual_notes.
        """

    def moves(self) -> tuple[Move, ...]:
        """Return provider-authored moves loaded from JSON content."""
        if moves := getattr(self, "_moves", False):
            return cast(tuple[Move], moves)

        module = sys.modules[self.__class__.__module__]

        if module.__file__ is None:
            raise RuntimeError(f"Cannot resolve move data path for provider {self.name!r}")

        path = pathlib.Path(module.__file__).resolve().parent / "data" / "moves.json"
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)

        self._moves = tuple(Move.model_validate(move_data) for move_data in data)

        return self._moves

    def selectable_moves(self, *, level: int = 1) -> tuple[Move, ...]:
        """Return shared universal moves plus provider-authored moves."""
        return tuple(m for m in (*universal.moves(), *self.moves()) if m.level_requirement <= level)
