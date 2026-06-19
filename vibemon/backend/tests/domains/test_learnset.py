from app.domains.generation.snapshot import BirthSnapshot
from app.domains.vibemon.progression import learnset


def test_birth_provider_names_ignore_legacy_learnset_payload() -> None:
    snapshot = BirthSnapshot(
        provider_payloads={
            "climate": {"datestamp": "2026-01-01"},
            "__learnset__": {"entries": [{"content_id": "climate.old_move", "level_requirement": 1}]},
        }
    )

    assert learnset.birth_provider_names(snapshot) == ("climate",)


def test_moves_for_providers_union_live_provider_catalogs() -> None:
    moves = learnset.moves_for_providers(("climate", "biome"), level=99)

    assert moves
    assert all(move.provider != "universal" for move in moves)
    assert {move.provider for move in moves} <= {"climate", "biome"}


def test_provider_moves_at_level_excludes_universal_moves() -> None:
    snapshot = BirthSnapshot(provider_payloads={"climate": {}})
    moves = learnset.provider_moves_at_level(snapshot, level=99)

    assert moves
    assert all(move.provider != "universal" for move in moves)
