import functools as ft
import json
import pathlib

from app.domains.move.entity import Move


@ft.cache
def moves() -> tuple[Move, ...]:
    """Return globally shared moves available to every provider."""
    path = pathlib.Path(__file__).resolve().parent / "data" / "universal_moves.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return tuple(Move.model_validate(move_data) for move_data in data)
