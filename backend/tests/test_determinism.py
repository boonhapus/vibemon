import datetime as dt
import json
import os
import subprocess
import sys

from app import schema, types


def test_birth_seed_rng_seed_uses_canonical_material() -> None:
    seed = schema.BirthSeed(
        timestamp=dt.datetime(2026, 5, 9, 12, 34, 56, 789, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        providers=[],
    )
    same_in_central_time = schema.BirthSeed(
        timestamp=dt.datetime(
            2026,
            5,
            9,
            7,
            34,
            56,
            789,
            tzinfo=dt.timezone(dt.timedelta(hours=-5)),
        ),
        geo_coords=(41.8781, -87.6298),
        providers=[],
    )

    assert seed.rng_seed == same_in_central_time.rng_seed
    assert seed.rng_seed == 69934579946597931810092047351875716077475658457934627553706683873854401783345


def test_birth_seed_rng_namespaces_are_stable_and_isolated() -> None:
    seed = schema.BirthSeed(
        timestamp=dt.datetime(2026, 5, 9, 12, 34, 56, 789, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        providers=[],
    )

    assert seed.rng_seed_for("affinity.merge") == seed.rng_seed_for("affinity.merge")
    assert seed.rng_seed_for("affinity.merge") != seed.rng_seed_for("identity.radiant")
    assert seed.rng("affinity.merge").random() == seed.rng("affinity.merge").random()


def test_identity_defaults_are_deterministic() -> None:
    identity = schema.Identity(name="test", elements=(types.VibemonTypeT.FIRE,))

    assert identity.evo_seed == types.EvolutionStageT.BASE
    assert identity.is_radiant is False


def test_affinity_merge_element_order_is_hash_seed_independent() -> None:
    script = r"""
import json
import random

from app import schema, types

m1 = schema.Move(
    id="test.a",
    name="A", flavor_text="a", type=types.VibemonTypeT.FIRE, category=types.MoveCategoryT.PHYSICAL, power=40
)
m2 = schema.Move(
    id="test.b",
    name="B", flavor_text="b", type=types.VibemonTypeT.WATER, category=types.MoveCategoryT.SPECIAL, power=40
)

a1 = schema.Affinity(
    identity=schema.Identity(
        name="x",
        elements=(types.VibemonTypeT.FIRE, types.VibemonTypeT.WATER),
        base_hp=70,
        base_attack=70,
        base_defense=70,
        base_sp_attack=70,
        base_sp_defense=70,
        base_speed=70,
    ),
    provider_id="a",
    intensity=1,
    moves=[m1, m2],
)
a2 = schema.Affinity(
    identity=schema.Identity(
        name="y",
        elements=(types.VibemonTypeT.FIRE, types.VibemonTypeT.WATER),
        base_hp=70,
        base_attack=70,
        base_defense=70,
        base_sp_attack=70,
        base_sp_defense=70,
        base_speed=70,
    ),
    provider_id="b",
    intensity=1,
    moves=[m1, m2],
)
merged = schema.Affinity.merge(a1, a2, rng=random.Random(5))
print(json.dumps(list(merged.identity.elements)))
"""
    outputs: list[list[str]] = []

    for hash_seed in ("1", "2"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = hash_seed
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            encoding="utf-8",
            env=env,
        )
        outputs.append(json.loads(result.stdout))

    assert outputs == [["fire", "water"], ["fire", "water"]]
