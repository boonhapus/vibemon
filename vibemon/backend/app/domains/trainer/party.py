"""Trainer party domain rules."""

from __future__ import annotations

from app.core.errors import PartyFull

MAX_PARTY_SIZE = 6


def select_adoption_slot(
    *,
    owned_count: int,
    used_slots: set[int],
    release_slot: int | None,
) -> int:
    """Decide adoption slot based on party occupancy and optional release slot."""
    if owned_count < MAX_PARTY_SIZE:
        return next(slot for slot in range(MAX_PARTY_SIZE) if slot not in used_slots)
    if release_slot is None:
        raise PartyFull("Adoption requires releasing one party Vibemon.")
    return release_slot
