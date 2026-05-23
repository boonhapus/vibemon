from pathlib import Path

import pytest

from app.content.moves import load_provider_moves

_FIXTURES = Path(__file__).parent / "fixtures" / "moves"


def test_load_provider_moves_valid_dataset() -> None:
    result = load_provider_moves(_FIXTURES / "valid.json")

    assert result.provider == "climate"
    assert not result.has_errors
    assert [move.id for move in result.moves] == ["climate.spark_tap", "climate.ember_snap"]


def test_load_provider_moves_rejects_duplicate_ids_and_keeps_first() -> None:
    result = load_provider_moves(_FIXTURES / "duplicate_ids.json")

    assert [move.id for move in result.moves] == ["climate.spark_tap"]
    assert len(result.issues) == 1
    assert result.issues[0].code == "duplicate_move_id"


def test_load_provider_moves_rejects_canonical_name_collision() -> None:
    result = load_provider_moves(_FIXTURES / "canonical_collision.json")

    assert [move.id for move in result.moves] == ["climate.spark_tap"]
    assert len(result.issues) == 1
    assert result.issues[0].code == "duplicate_canonical_name"


def test_load_provider_moves_mixed_dataset_reports_per_move_errors() -> None:
    result = load_provider_moves(_FIXTURES / "mixed.json")

    assert [move.id for move in result.moves] == ["climate.spark_tap"]
    assert {issue.code for issue in result.issues} == {"invalid_move", "provider_mismatch"}


def test_load_provider_moves_rejects_unknown_root_fields(tmp_path: Path) -> None:
    path = tmp_path / "invalid_root.json"
    path.write_text(
        """
        {
          "version": 1,
          "provider": "climate",
          "moves": [],
          "extra": true
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown top-level fields"):
        load_provider_moves(path)
