"""Video birth provider catalog stub."""

from typing import ClassVar

from app.domains.move.types import VibemonTypeT
from app.providers import catalog_schema as catalog
from app.providers.base import UnimplementedProvider


class VideoProvider(UnimplementedProvider):
    """
    A Vibemon catches the glow of whatever was playing on the tube when it hatched.

    One shaped by slow prestige drama reads differently from one raised on
    rapid sci-fi marathons - same couch, different evening, different creature.
    """

    name = "video"
    display_label = "VIDEO"
    tagline = "Late-night UHF and whatever stayed on."

    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]] = [
        (VibemonTypeT.NORMAL, "mainstream sitcom and comfort viewing"),
        (VibemonTypeT.FIRE, "action, thriller, and high-tension genres"),
        (VibemonTypeT.WATER, "melodrama, romance, and slow-burn series"),
        (VibemonTypeT.GRASS, "nature docs and gentle ensemble casts"),
        (VibemonTypeT.GHOST, "nostalgic rewatches and classic catalogs"),
        (VibemonTypeT.DARK, "crime, horror, and antihero narratives"),
        (VibemonTypeT.PSYCHIC, "speculative fiction and puzzle-box plots"),
        (VibemonTypeT.ELECTRIC, "animated action and fast-cut editing"),
    ]

    requirements = (
        catalog.OAuth2LinkRequirement(
            id="trakt.link",
            label="Link Trakt",
            description="Connect watch history when this provider launches.",
            service="trakt",
            secret_kinds=("trakt.access_token",),
            authorize_path="/trakt/authorize",
        ),
    )
    data_sources = (
        catalog.DataSourceInfo(name="Trakt", description="Watch history and episode activity."),
        catalog.DataSourceInfo(name="TVDB", description="Optional genre and show enrichment."),
    )
