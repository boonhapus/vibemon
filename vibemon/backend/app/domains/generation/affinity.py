"""Generation affinity concepts and merge behavior."""

from __future__ import annotations

from typing import Any
import math
import random

import pydantic
import structlog

from app.core.math import clamp, weighted_sample
from app.core.schema import FrozenSchema
from app.domains.move.entity import Move
from app.domains.vibemon import types
from app.domains.vibemon.identity import Identity
from app.domains.vibemon.strength_formulas import apply_evo_seed_bst_bias

_LOGGER = structlog.get_logger(__name__)


class BirthOutcome(FrozenSchema):
    identity: Identity
    moves: tuple[Move, ...]
    evo_stage: types.EvolutionStageT = types.EvolutionStageT.BASE


class Affinity(FrozenSchema):
    identity: Identity
    visual_notes: str | None = None
    intensity: float = 0.5
    provider_id: str
    moves: tuple[Move, ...]

    @pydantic.field_validator("moves", mode="before")
    @classmethod
    def _coerce_moves_tuple(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        return value

    @pydantic.field_validator("intensity")
    @classmethod
    def _clamp_intensity(cls, v: float) -> float:
        if 0.0 <= v <= 1.0:
            return v
        clamped = clamp(v, minimum=0.0, maximum=1.0)
        _LOGGER.warning("Affinity.intensity out of bounds", original=v, clamp_to=clamped)
        return clamped

    @classmethod
    def merge(
        cls,
        *affinities: Affinity,
        core_identity_description: str | None = None,
        rng: random.Random | None = None,
        evo_rng: random.Random | None = None,
        radiant_rng: random.Random | None = None,
    ) -> BirthOutcome:
        stat_keys = ("base_hp", "base_attack", "base_defense", "base_sp_attack", "base_sp_defense", "base_speed")
        if rng is None:
            rng = random.Random()
        if evo_rng is None:
            evo_rng = rng
        if radiant_rng is None:
            radiant_rng = rng

        name = ""
        total = 0
        stats = {k: 0 for k in stat_keys}
        notes: list[str] = []
        pop_e: list[tuple[types.VibemonTypeT, int]] = []
        pop_m: list[tuple[Move, int]] = []

        for idx, affinity in enumerate(sorted(affinities, key=lambda a: (-a.intensity, a.provider_id))):
            weight = int(affinity.intensity * 100)
            total += weight
            for k in stat_keys:
                stats[k] += weight * math.floor(getattr(affinity.identity, k))
            pop_e.extend((e, weight) for e in affinity.identity.elements)
            pop_m.extend((m, weight) for m in affinity.moves)
            if idx == 0:
                name = affinity.identity.name
            if affinity.visual_notes:
                notes.append(f"{affinity.visual_notes} ({weight}%)")

        try:
            stats_merged = {k: math.floor(stats[k] / total) for k in stat_keys}
            elements = weighted_sample(*zip(*pop_e, strict=True), k=rng.randint(1, min(2, len(pop_e))), rng=rng)
            moves = weighted_sample(*zip(*pop_m, strict=True), k=rng.randint(2, min(3, len(pop_m))), rng=rng)
        except ZeroDivisionError:
            _LOGGER.exception("Total is zero.", affinities=affinities)
            raise

        evo_seed = types.EvolutionStageT.random_seed(rng=evo_rng)
        evo_stage = types.EvolutionStageT.BASE
        stats_scaled = apply_evo_seed_bst_bias(stats_merged, evo_seed=evo_seed, evo_stage=evo_stage)

        identity = Identity(
            name=name,
            visual_notes=core_identity_description,
            provider_visual_notes=" ".join(notes) or None,
            elements=tuple(dict.fromkeys(elements)),
            evo_seed=evo_seed,
            is_radiant=radiant_rng.randint(1, 4096) == 4096,
            **stats_scaled,
        )

        return BirthOutcome(identity=identity, moves=tuple(moves), evo_stage=evo_stage)
