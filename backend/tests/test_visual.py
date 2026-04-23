"""Focused tests for the VisualDNA pipeline."""

import pytest

from app import schema, types, visual


def _make_vibemon(
    *,
    name: str = "Testmon",
    description: str = "",
    base_hp: int = 80,
    base_attack: int = 80,
    base_defense: int = 80,
    base_sp_attack: int = 80,
    base_sp_defense: int = 80,
    base_speed: int = 80,
    elements: list[types.VibemonTypeT] | None = None,
    affinity_narrative: str = "",
    birth_affinities: tuple[schema.Identity, ...] = (),
) -> schema.Vibemon:
    return schema.Vibemon(
        name=name,
        description=description,
        base_hp=base_hp,
        base_attack=base_attack,
        base_defense=base_defense,
        base_sp_attack=base_sp_attack,
        base_sp_defense=base_sp_defense,
        base_speed=base_speed,
        elements=elements or [types.VibemonTypeT.NORMAL],
        affinity_narrative=affinity_narrative,
        birth_affinities=birth_affinities,
    )


# ── stat_signature ──────────────────────────────────────────────────────────────────


def test_stat_signature_physical_lean():
    mon = _make_vibemon(base_attack=130, base_sp_attack=60)
    assert "physical offence" in visual.stat_signature(mon)


def test_stat_signature_special_lean():
    mon = _make_vibemon(base_attack=60, base_sp_attack=130)
    assert "special offence" in visual.stat_signature(mon)


def test_stat_signature_mixed_lean():
    mon = _make_vibemon(base_attack=80, base_sp_attack=80)
    assert "mixed offence" in visual.stat_signature(mon)


def test_stat_signature_speed_tempo():
    mon = _make_vibemon(base_hp=60, base_defense=60, base_sp_defense=60, base_speed=130)
    assert "swift" in visual.stat_signature(mon)


def test_stat_signature_bulky_tempo():
    mon = _make_vibemon(base_hp=140, base_defense=140, base_sp_defense=140, base_speed=40)
    assert "bulky" in visual.stat_signature(mon)


def test_stat_signature_tier_monotonic():
    low = _make_vibemon(
        base_hp=40,
        base_attack=40,
        base_defense=40,
        base_sp_attack=40,
        base_sp_defense=40,
        base_speed=40,
    )
    mid = _make_vibemon(
        base_hp=90,
        base_attack=90,
        base_defense=90,
        base_sp_attack=90,
        base_sp_defense=90,
        base_speed=90,
    )
    high = _make_vibemon(
        base_hp=120,
        base_attack=120,
        base_defense=120,
        base_sp_attack=120,
        base_sp_defense=120,
        base_speed=120,
    )
    tiers = [visual.stat_signature(m).split(";")[0] for m in (low, mid, high)]
    assert tiers[0] != tiers[1] != tiers[2]


# ── element lexicon ─────────────────────────────────────────────────────────────────


def test_element_lexicon_covers_all_types():
    missing = [t for t in types.VibemonTypeT if t not in visual.ELEMENT_LEXICON]
    assert not missing, f"Missing lexicon entries for: {missing}"


def test_element_visuals_dual_type_emits_both_lines():
    output = visual.element_visuals([types.VibemonTypeT.FIRE, types.VibemonTypeT.WATER])
    assert "fire" in output
    assert "water" in output
    assert output.count("\n") >= 1


def test_element_visuals_fallback_to_normal_when_empty():
    output = visual.element_visuals([])
    assert "normal" in output


# ── trainer_steering ────────────────────────────────────────────────────────────────


def test_trainer_steering_normalizes_whitespace():
    assert visual.trainer_steering("  lots   of\n  spaces  ") == "lots of spaces"


def test_trainer_steering_caps_length():
    long = "x" * 600
    out = visual.trainer_steering(long, max_chars=100)
    assert len(out) == 100
    assert out.endswith("…")


# ── provider_echo ───────────────────────────────────────────────────────────────────


def test_provider_echo_sorted_by_intensity():
    sig_a = schema.Identity(provider_id="a", intensity=0.3, description="low")
    sig_b = schema.Identity(provider_id="b", intensity=0.7, description="high")
    output = visual.provider_echo([sig_a, sig_b])
    assert output.index("high") < output.index("low")


def test_provider_echo_handles_empty():
    output = visual.provider_echo([])
    assert "no provider contributions" in output


# ── from_affinities regression ──────────────────────────────────────────────────────


def _make_affinity(
    *,
    provider_id: str,
    intensity: float = 1.0,
    description: str = "",
    elements: tuple[types.VibemonTypeT, ...] = (),
) -> schema.Affinity:
    return schema.Affinity(
        signature=schema.Identity(
            provider_id=provider_id,
            intensity=intensity,
            description=description,
            elements=elements,
        ),
    )


def test_from_affinities_preserves_user_description():
    affinity = _make_affinity(provider_id="test", description="Sunny")
    mon = schema.Vibemon.from_affinities(affinity, name="TestMon", description="a brave little one")
    assert mon.description == "a brave little one"
    assert "Sunny" not in mon.description
    assert "Sunny" in mon.affinity_narrative


def test_from_affinities_populates_birth_identities():
    affinity = _make_affinity(provider_id="climate", description="Rain", intensity=0.8)
    mon = schema.Vibemon.from_affinities(affinity, name="Drip", description="")
    assert len(mon.birth_affinities) == 1
    assert mon.birth_affinities[0].provider_id == "climate"
    assert mon.birth_affinities[0].intensity == 0.8


def test_from_affinities_rejects_empty():
    with pytest.raises(ValueError):
        schema.Vibemon.from_affinities(name="Empty", description="")


# ── VisualDNA render ────────────────────────────────────────────────────────────────


def test_visual_dna_render_keeps_style_and_panels_verbatim():
    sig = schema.Identity(provider_id="climate", description="Light rain", intensity=1.0)
    mon = _make_vibemon(
        name="Drizzlemite",
        description="trainer said: keep it small",
        affinity_narrative="Light rain (1.00)",
        birth_affinities=(sig,),
    )
    output = mon.render_sprite()

    # Frozen anchors.
    assert "STYLE: Pokémon Sugimori" in output
    assert "21:9 ultrawide" in output
    assert "Over-shoulder back / alert" in output
    assert "Three-quarter front / combat" in output

    # Steerable middle reflects inputs.
    assert "Drizzlemite" in output
    assert "keep it small" in output
    assert "climate" in output
    assert "Light rain" in output
