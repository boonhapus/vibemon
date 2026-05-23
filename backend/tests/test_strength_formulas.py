import datetime as dt
import uuid

from app import models
from app.balance import strength

NOW = dt.datetime(2026, 5, 17, 12, 0, tzinfo=dt.UTC)


def _vibemon(*, level: int, base: int) -> models.Vibemon:
    return models.Vibemon(
        id=uuid.uuid7(),
        nickname="test",
        level=level,
        evo_stage=1,
        lifecycle="christened",
        disposition="wild",
        team_slot=None,
        trainer_id=None,
        birth_snapshot_id=uuid.uuid7(),
        wild_entered_at=NOW,
        last_encountered_at=NOW,
        expired_at=None,
        identity=models.Identity(
            name="test",
            visual_notes=None,
            provider_visual_notes=None,
            elements=["normal"],
            base_hp=base,
            base_attack=base,
            base_defense=base,
            base_sp_attack=base,
            base_sp_defense=base,
            base_speed=base,
            evo_seed=1,
            is_radiant=False,
            generation=0,
            generated_at=NOW,
        ),
    )


def test_party_strength_uses_avg_plus_max_plus_total_bonus() -> None:
    values = [100.0, 200.0, 300.0]
    result = strength.party_strength(values)
    assert result == 200.0 + 75.0 + 60.0


def test_member_strength_increases_with_level() -> None:
    low = strength.member_strength(_vibemon(level=5, base=70))
    high = strength.member_strength(_vibemon(level=20, base=70))
    assert high > low
