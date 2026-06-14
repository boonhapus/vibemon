"""Trainer crew domain rules."""

from collections.abc import Sequence
import dataclasses
import uuid

from app.core.errors import CrewFull

MAX_CREW_SIZE = 6


@dataclasses.dataclass(frozen=True, slots=True)
class CrewMember:
    """An owned Vibemon's identity and its occupied crew slot, if any."""

    vibemon_id: uuid.UUID
    crew_slot: int | None


@dataclasses.dataclass(frozen=True, slots=True)
class AdoptionPlan:
    """The crew decision for an adoption: which slot to fill, which Vibemon to release."""

    slot: int
    release_vibemon_id: uuid.UUID | None


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


def plan_adoption(
    *,
    owned: Sequence[CrewMember],
    release_vibemon_id: uuid.UUID | None,
) -> AdoptionPlan:
    """Decide the slot and release action for adopting a candidate into a crew.

    A release only takes effect when the crew is full; below capacity the
    candidate fills an open slot and any requested release is ignored.
    """
    used = {member.crew_slot for member in owned if member.crew_slot is not None}
    release = next((m for m in owned if m.vibemon_id == release_vibemon_id), None) if release_vibemon_id else None
    slot = select_adoption_slot(
        owned_count=len(owned),
        used_slots=used,
        release_slot=release.crew_slot if release is not None else None,
    )
    full = len(owned) >= MAX_CREW_SIZE
    if full and release is None:
        raise CrewFull("Release Vibemon is not owned by this trainer.")
    return AdoptionPlan(slot=slot, release_vibemon_id=release.vibemon_id if full and release is not None else None)
