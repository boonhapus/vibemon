"""Deterministic Vibemon birth orchestration."""

from app.domains.generation.affinity import Affinity, BirthOutcome
from app.domains.generation.seed import BirthSeed


def birth_outcome_from_affinities(
    *affinities: Affinity,
    birth_seed: BirthSeed,
    core_identity: str | None = None,
) -> BirthOutcome:
    if not affinities:
        raise ValueError("Vibemon must be born from at least one Affinity!")
    return Affinity.merge(
        *affinities,
        core_identity_description=core_identity,
        rng=birth_seed.rng("affinity.merge"),
        evo_rng=birth_seed.rng("identity.evo_seed"),
        radiant_rng=birth_seed.rng("identity.radiant"),
    )
