"""Trainer crew domain rules."""

from app.core.errors import CrewFull

MAX_CREW_SIZE = 6


def select_adoption_slot(
    *,
    owned_count: int,
    used_slots: set[int],
    release_slot: int | None,
) -> int:
    """Decide adoption slot based on crew occupancy and optional release slot."""
    if owned_count < MAX_CREW_SIZE:
        return next(slot for slot in range(MAX_CREW_SIZE) if slot not in used_slots)
    if release_slot is None:
        raise CrewFull("Adoption requires releasing one crew Vibemon.")
    return release_slot
