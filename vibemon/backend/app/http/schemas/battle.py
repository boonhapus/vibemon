"""HTTP schemas for battle routes."""

import uuid

from app.core.schema import Schema
from app.domains.move.types import MoveCategoryT, VibemonTypeT


class BattleStartBody(Schema):
    hero_vibemon_id: uuid.UUID
    wild_vibemon_id: uuid.UUID


class BattleTurnBody(Schema):
    move_name: str


class BattleSwitchBody(Schema):
    bench_index: int


class MoveLearnAcceptBody(Schema):
    vibemon_id: uuid.UUID
    move_content_id: str
    replace_content_id: str | None = None


class MoveLearnDeclineBody(Schema):
    vibemon_id: uuid.UUID


class HeroProgressionRead(Schema):
    """Hero XP/level movement after a battle, tailored for the HUD."""

    vibemon_id: uuid.UUID
    previous_xp: int
    new_xp: int
    previous_level: int
    new_level: int
    xp_to_next: int
    xp_bar_ratio: float
    leveled_up: bool
    stat_deltas: tuple[dict[str, int | str], ...] = ()


class MoveLearnOptionRead(Schema):
    id: str
    name: str
    type: VibemonTypeT
    category: MoveCategoryT
    power: int | None
    accuracy: float | None
    pp: int
    level_requirement: int
    flavor_text: str
    combat_hints: tuple[str, ...] = ()


class MoveLearnOfferRead(Schema):
    vibemon_id: uuid.UUID
    vibemon_name: str
    moves: tuple[MoveLearnOptionRead, ...]
    requires_replace: bool


class BattleFinishResponse(Schema):
    progression: HeroProgressionRead | None
    move_offers: tuple[MoveLearnOfferRead, ...] = ()
