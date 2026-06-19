"""HTTP read models for trainer crew screens."""

import uuid

from app.core.schema import Schema
from app.domains.adoption import hatch_projection
from app.domains.vibemon import assets as vibemon_assets
from app.domains.vibemon import entity as vibemon_entity
from app.domains.vibemon.progression import formulas as progression_formulas
from app.domains.vibemon.schema import PublicVibemon


class CrewMemberRead(Schema):
    id: uuid.UUID
    name: str
    nickname: str | None = None
    level: int
    current_hp: int
    max_hp: int
    xp: int
    xp_to_next: int
    xp_bar_ratio: float
    crew_slot: int
    sprite_url: str | None = None
    reference_detected_facing: str | None = None
    detail: hatch_projection.HatchCandidateRead


class CrewListRead(Schema):
    members: tuple[CrewMemberRead, ...]
    max_size: int = 6


class CrewSlotWrite(Schema):
    id: uuid.UUID
    crew_slot: int


class CrewOrderWrite(Schema):
    members: tuple[CrewSlotWrite, ...]


def crew_member_read(vibemon: PublicVibemon, *, reference_detected_facing: str | None = None) -> CrewMemberRead:
    battle = vibemon_entity.Vibemon(
        id=vibemon.id,
        identity=vibemon.identity,
        moves=vibemon.moves,
        level=vibemon.level,
        xp=vibemon.xp,
        evo_stage=vibemon.evo_stage,
        lifecycle=vibemon.lifecycle,
        nickname=vibemon.nickname,
        trainer_id=vibemon.trainer_id,
        crew_slot=vibemon.crew_slot,
    )
    sprite_url = next(
        (
            asset.url
            for asset in vibemon.assets
            if asset.kind in (vibemon_assets.AssetKind.REFERENCE, vibemon_assets.AssetKind.POSE_BATTLE_HERO)
        ),
        None,
    )
    slot = vibemon.crew_slot if vibemon.crew_slot is not None else 0
    return CrewMemberRead(
        id=vibemon.id,
        name=vibemon.name,
        nickname=vibemon.nickname,
        level=vibemon.level,
        current_hp=battle.hp,
        max_hp=battle.hp,
        xp=vibemon.xp,
        xp_to_next=progression_formulas.xp_to_next_level(
            level=vibemon.level,
            xp=vibemon.xp,
            growth_rate=vibemon.growth_rate,
        ),
        xp_bar_ratio=progression_formulas.xp_bar_ratio(
            level=vibemon.level,
            xp=vibemon.xp,
            growth_rate=vibemon.growth_rate,
        ),
        crew_slot=slot,
        sprite_url=sprite_url,
        reference_detected_facing=reference_detected_facing,
        detail=hatch_projection.assemble_hatch_candidate(
            vibemon,
            reference_facing=(reference_detected_facing or "LEFT").lower(),
        ),
    )
