"""Tests for tag classification rule loading."""

from app.domains.move.types import VibemonTypeT
from app.providers.music import utils


def test_genre_rules_loads_expected_count() -> None:
    assert len(utils.load_rules("classify_genre.json")) == 30


def test_mood_rules_loads_expected_count() -> None:
    assert len(utils.load_rules("classify_mood.json")) == 13


def test_instrument_rules_loads_expected_count() -> None:
    assert len(utils.load_rules("classify_instrument.json")) == 12


def test_genre_rules_match_heavy_metal() -> None:
    matched = [
        type_weights
        for _name, type_weights, pattern in utils.load_rules("classify_genre.json")
        if pattern.search("heavy metal")
    ]
    assert matched
    assert (VibemonTypeT.STEEL, 1.0) in matched[0]


def test_blues_rock_matches_multiple_genre_families() -> None:
    rules = utils.load_rules("classify_genre.json")
    matches = [name for name, _weights, pattern in rules if pattern.search("blues rock")]
    assert matches == ["rock", "blues"]


def test_dance_matches_electronic_genre() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["electronic"].search("dance") is not None


def test_indie_alternative_covers_common_mb_gaps() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    rule = rules["indie_alternative"]
    for tag in ("indie", "alternative", "singer-songwriter", "singer/songwriter", "alternative rock"):
        assert rule.search(tag) is not None, tag


def test_punk_matches_post_hardcore() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["punk"].search("post-hardcore") is not None


def test_punk_matches_hardcore() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["punk"].search("hardcore") is not None


def test_rock_matches_grunge() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["rock"].search("grunge") is not None


def test_dark_matches_darkwave() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["dark"].search("darkwave") is not None
    assert rules["dark"].search("gothic") is not None


def test_flying_matches_shoegaze() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["flying"].search("shoegaze") is not None
    assert rules["flying"].search("dream pop") is not None
    assert rules["rock"].search("shoegaze") is None


def test_microgenre_matches_hyperpop() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["microgenre"].search("hyperpop") is not None
    assert rules["microgenre"].search("glitch hop") is not None


def test_minimal_matches_microhouse() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["minimal"].search("microhouse") is not None
    assert rules["minimal"].search("minimal techno") is not None
    assert rules["minimal"].search("dub techno") is not None


def test_noise_industrial_matches_power_electronics() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["noise_industrial"].search("power electronics") is not None
    assert rules["noise_industrial"].search("aggrotech") is not None
    assert rules["noise_industrial"].search("harsh noise wall") is not None


def test_progressive_matches_power_metal() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["progressive"].search("power metal") is not None
    assert rules["progressive"].search("symphonic metal") is not None
    assert rules["progressive"].search("speed metal") is not None
    assert rules["metal"].search("power metal") is None


def test_spectral_matches_dungeon_synth() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["spectral"].search("dungeon synth") is not None
    assert rules["spectral"].search("dark ambient") is not None
    assert rules["electronic"].search("dungeon synth") is None


def test_sparkle_matches_electropop() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["sparkle"].search("electropop") is not None
    assert rules["sparkle"].search("dance pop") is not None


def test_electronic_matches_edm_and_psytrance() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["electronic"].search("edm") is not None
    assert rules["electronic"].search("psytrance") is not None


def test_electronic_matches_amapiano() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["electronic"].search("amapiano") is not None


def test_normalize_classify_label_strips_hashtag_prefix() -> None:
    assert utils.normalize_classify_label("#chill") == "chill"


def test_calm_matches_hashtag_chill() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_mood.json")}
    assert rules["calm"].search(utils.normalize_classify_label("#chill")) is not None


def test_aggressive_matches_angry() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_mood.json")}
    assert rules["aggressive"].search("angry") is not None


def test_guitar_matches_ukulele() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_instrument.json")}
    assert rules["guitar"].search("ukulele") is not None


def test_synth_matches_keyboard() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_instrument.json")}
    assert rules["synth"].search("keyboard") is not None


def test_country_matches_stomp_and_holler() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["country"].search("stomp & holler") is not None


def test_instrument_electronic_rule_removed() -> None:
    rules = {name for name, _weights, _pattern in utils.load_rules("classify_instrument.json")}
    assert "electronic" not in rules


def test_terms_use_word_boundaries() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_genre.json")}
    assert rules["rock"].search("rocksteady") is None
    assert rules["progressive"].search("post-rock") is not None
    assert rules["metal"].search("power metal") is None


def test_patterns_keep_prefix_matching() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_mood.json")}
    assert rules["sad"].search("melancholy") is not None


def test_aggressive_matches_rough() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_mood.json")}
    assert rules["aggressive"].search("rough") is not None


def test_flute_matches_reed() -> None:
    rules = {name: pattern for name, _weights, pattern in utils.load_rules("classify_instrument.json")}
    assert rules["flute"].search("reed") is not None


def test_load_rules_is_cached() -> None:
    assert utils.load_rules("classify_genre.json") is utils.load_rules("classify_genre.json")
    assert utils.load_rules("classify_mood.json") is utils.load_rules("classify_mood.json")
    assert utils.load_rules("classify_instrument.json") is utils.load_rules("classify_instrument.json")
