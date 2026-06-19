"""Tests for battle event dialog copy."""

from app.domains.battle import events
from app.http import battle_read


def test_stat_change_message_for_opponent_drop() -> None:
    messages = battle_read.events_to_messages(
        [events.StatChangeEvent(source="Hero", target="Fodder", changes={"attack": -1})],
        hero_name="Hero",
        wild_name="Fodder",
    )
    assert messages == ["Their Attack has dropped!"]


def test_stat_change_message_for_hero_rise_sharply() -> None:
    messages = battle_read.events_to_messages(
        [events.StatChangeEvent(source="Fodder", target="Hero", changes={"sp_attack": 2})],
        hero_name="Hero",
        wild_name="Fodder",
    )
    assert messages == ["Your Sp. Atk has risen sharply!"]
