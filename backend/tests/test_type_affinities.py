from app import types
from app.balance.element_chart import ELEMENT_CHART, TYPE_AFFINITIES


def test_type_affinities_cover_all_types() -> None:
    assert set(TYPE_AFFINITIES.keys()) == set(types.VibemonTypeT)


def test_type_affinity_reversal_consistency() -> None:
    for attack_type in types.VibemonTypeT:
        for defender_type in types.VibemonTypeT:
            attack_covers_defender = defender_type in TYPE_AFFINITIES[attack_type].covers
            defender_weak_to_attacker = attack_type in TYPE_AFFINITIES[defender_type].weak_to
            assert attack_covers_defender is defender_weak_to_attacker


def test_type_affinity_matches_element_chart_modifiers() -> None:
    for attack_type in types.VibemonTypeT:
        for defender_type in types.VibemonTypeT:
            modifier = ELEMENT_CHART.get((attack_type, defender_type), 1.0)
            affinity = TYPE_AFFINITIES[defender_type]
            assert (attack_type in affinity.weak_to) is (modifier > 1.0)
            assert (attack_type in affinity.resists) is (0.0 < modifier < 1.0)
