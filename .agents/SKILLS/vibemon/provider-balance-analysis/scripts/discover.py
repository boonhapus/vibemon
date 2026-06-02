"""Discover provider move catalogs from the backend package layout."""

import json
from functools import cache
from pathlib import Path

from app.domains.move.entity import Move


def providers_root() -> Path:
    import app.providers as providers_pkg

    if providers_pkg.__file__ is None:
        raise RuntimeError("app.providers must be installed as a package")
    return Path(providers_pkg.__file__).resolve().parent


@cache
def discover_provider_names() -> tuple[str, ...]:
    """Providers with an authored move catalog on disk."""
    names: list[str] = []
    for entry in sorted(providers_root().iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        if (entry / "data" / "moves.json").is_file():
            names.append(entry.name)
    return tuple(names)


def provider_moves_path(name: str) -> Path:
    key = name.strip().lower()
    if key not in discover_provider_names():
        available = ", ".join(discover_provider_names())
        raise SystemExit(f"Unknown provider {name!r}. Choose one of: {available}") from None
    return providers_root() / key / "data" / "moves.json"


def load_provider_moves(name: str) -> tuple[Move, ...]:
    data = json.loads(provider_moves_path(name).read_text(encoding="utf-8"))
    return tuple(Move.model_validate(item) for item in data)
