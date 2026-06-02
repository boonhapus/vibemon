"""Generation affinity concepts and merge behavior."""

from typing import Any
import math
import random

import pydantic
import structlog

from app.core.math import clamp, weighted_sample
from app.core.schema import FrozenSchema
from app.domains.move.entity import Move
from app.domains.vibemon import types
from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.strength_formulas import apply_evo_seed_bst_bias
from app.providers import schema as providers_schema
from app.providers.helpers import filter_element_types, fuse_element_rankings

_LOGGER = structlog.get_logger(__name__)

_PROVIDER_MERGE_WEIGHT = 1.0


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
    element_rankings: dict[types.VibemonTypeT, float] = pydantic.Field(default_factory=dict)
    provider_notes: tuple[providers_schema.ProviderNote, ...] = ()

    @classmethod
    def collect_notes(cls, *affinities: Affinity) -> tuple[providers_schema.ProviderNote, ...]:
        seen: set[str] = set()
        notes: list[providers_schema.ProviderNote] = []
        for affinity in affinities:
            for note in affinity.provider_notes:
                if note.code in seen:
                    continue
                seen.add(note.code)
                notes.append(note)
        return tuple(notes)

    @pydantic.field_validator("element_rankings", mode="before")
    @classmethod
    def _coerce_element_rankings(cls, value: Any) -> Any:
        if value is None:
            return dict[types.VibemonTypeT, float]()
        return value

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
        stat_keys = ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed")
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
        pop_m: list[tuple[Move, int]] = []
        ranking_pairs: list[tuple[dict[types.VibemonTypeT, float], float]] = []

        for idx, affinity in enumerate(sorted(affinities, key=lambda a: (-a.intensity, a.provider_id))):
            weight = int(affinity.intensity * 100)
            total += weight

            for k in stat_keys:
                stats[k] += weight * math.floor(getattr(affinity.identity.base, k))

            pop_m.extend((m, weight) for m in affinity.moves)
            ranking_pairs.append((cls._rankings_for_merge(affinity), _PROVIDER_MERGE_WEIGHT))

            if idx == 0:
                name = affinity.identity.name

            if affinity.visual_notes:
                notes.append(f"{affinity.visual_notes} ({weight}%)")

        try:
            stats_merged = {k: math.floor(stats[k] / total) for k in stat_keys}
            elements = filter_element_types(fuse_element_rankings(*ranking_pairs))
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
            base=BaseStats(**stats_scaled),
        )

        return BirthOutcome(identity=identity, moves=tuple(moves), evo_stage=evo_stage)

    @staticmethod
    def _rankings_for_merge(affinity: Affinity) -> dict[types.VibemonTypeT, float]:
        if affinity.element_rankings:
            return affinity.element_rankings
        return {element: 1.0 - index * 0.01 for index, element in enumerate(affinity.identity.elements)}
