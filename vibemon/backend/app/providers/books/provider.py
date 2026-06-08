"""Books birth provider catalog stub."""

from typing import ClassVar

from app.domains.move.types import VibemonTypeT
from app.providers import catalog_schema as catalog
from app.providers.catalog_support import UnimplementedProvider


class BooksProvider(UnimplementedProvider):
    """
    A Vibemon is born from the stories you carry with you.

    One raised on dense nonfiction reads differently from one shaped by mythic
    fantasy re-reads - same armchair, different stack on the nightstand.
    """

    name = "books"
    display_label = "BOOKS"
    tagline = "Paperbacks, armchair stacks, and re-reads."
    data_sources = (
        catalog.DataSourceInfo(name="Reading platforms", description="Shelf and history integrations at launch."),
    )
    requirements = (
        catalog.OAuth2LinkRequirement(
            id="books.link",
            label="Link a reading account",
            description="Connect reading history when this provider launches.",
            service="books",
            secret_kinds=("books.access_token",),
            authorize_path="/books/authorize",
        ),
    )
    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]] = [
        (VibemonTypeT.NORMAL, "contemporary fiction and generalist shelves"),
        (VibemonTypeT.GRASS, "nature writing and pastoral fiction"),
        (VibemonTypeT.WATER, "memoir, travelogue, and reflective prose"),
        (VibemonTypeT.FIRE, "adventure, thriller, and propulsive plots"),
        (VibemonTypeT.GHOST, "historical fiction and archival mood"),
        (VibemonTypeT.PSYCHIC, "philosophy, myth, and metaphysical texts"),
        (VibemonTypeT.DARK, "noir, gothic, and tragic narratives"),
        (VibemonTypeT.DRAGON, "epic fantasy and long-form sagas"),
    ]
