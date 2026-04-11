from __future__ import annotations

from app.engine.names import generate_name
from app.engine.stats import make_seed


def test_name_deterministic() -> None:
    assert generate_name("Fire", make_seed("u", "vibemon")) == generate_name(
        "Fire", make_seed("u", "vibemon")
    )


def test_name_length() -> None:
    n = generate_name("Water", 12345)
    assert 4 <= len(n) <= 10
