"""Mapping between ORM rows and Vibemon domain objects."""

import uuid

from app.core.ids import TrainerIdT
from app.domains.move.entity import EffectGroup, Move, MoveBehavior
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.domains.sprite import types as sprite_types
from app.domains.vibemon.assets import AssetKind, AssetRef, SpriteAnchor
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.entity import Aesthetic, Vibemon
from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.progression.types import GrowthGroupT
from app.domains.vibemon.types import EvolutionStageT, VibemonLifecycleT
from app.storage.database import models


def identity_row(vibemon: Vibemon) -> models.Identity:
    identity = vibemon.identity
    base = identity.base
    return models.Identity(
        name=identity.name,
        visual_notes=identity.visual_notes,
        elements=[element.value for element in identity.elements],
        base_hp=base.hp,
        base_attack=base.attack,
        base_defense=base.defense,
        base_sp_attack=base.sp_attack,
        base_sp_defense=base.sp_defense,
        base_speed=base.speed,
        evo_seed=int(identity.evo_seed),
        is_radiant=identity.is_radiant,
        generation=identity.generation,
        generated_at=identity.generated_at,
    )


def apply_vibemon_to_row(row: models.Vibemon, vibemon: Vibemon) -> None:
    row.nickname = vibemon.nickname
    row.xp = vibemon.xp
    row.level = vibemon.level
    row.growth_rate = vibemon.growth_rate.value
    row.evo_stage = int(vibemon.evo_stage)
    row.lifecycle = vibemon.lifecycle.value
    row.identity.name = vibemon.identity.name
    base = vibemon.identity.base
    row.identity.base_hp = base.hp
    row.identity.base_attack = base.attack
    row.identity.base_defense = base.defense
    row.identity.base_sp_attack = base.sp_attack
    row.identity.base_sp_defense = base.sp_defense
    row.identity.base_speed = base.speed
    row.reference_detected_facing = (
        vibemon.reference_detected_facing.value if vibemon.reference_detected_facing is not None else None
    )


def apply_adopted_vibemon_to_row(
    row: models.Vibemon,
    vibemon: Vibemon,
    *,
    trainer_id: TrainerIdT,
    crew_slot: int,
) -> None:
    """Persist an adopted Vibemon: domain fields plus Owned disposition transition."""
    apply_vibemon_to_row(row, vibemon)
    row.trainer_id = trainer_id
    row.crew_slot = crew_slot
    row.disposition = VibemonDispositionT.OWNED.value
    row.wild_entered_at = None
    row.last_encountered_at = None


async def vibemon_from_row(row: models.Vibemon) -> Vibemon:
    identity = Identity(
        name=row.identity.name,
        visual_notes=row.identity.visual_notes,
        elements=tuple(VibemonTypeT(element) for element in row.identity.elements),
        base=BaseStats(
            hp=row.identity.base_hp,
            attack=row.identity.base_attack,
            defense=row.identity.base_defense,
            sp_attack=row.identity.base_sp_attack,
            sp_defense=row.identity.base_sp_defense,
            speed=row.identity.base_speed,
        ),
        evo_seed=EvolutionStageT(row.identity.evo_seed),
        is_radiant=row.identity.is_radiant,
        generation=row.identity.generation,
        generated_at=row.identity.generated_at,
    )
    vibemon = Vibemon(
        id=row.id,
        nickname=row.nickname,
        identity=identity,
        moves=tuple(move_from_row(vibemon_move.move) for vibemon_move in sorted(row.moves, key=move_slot)),
        level=row.level,
        xp=row.xp,
        growth_rate=GrowthGroupT(row.growth_rate or GrowthGroupT.MEDIUM.value),
        evo_stage=EvolutionStageT(row.evo_stage),
        trainer_id=row.trainer_id,
        crew_slot=row.crew_slot,
        lifecycle=VibemonLifecycleT(row.lifecycle),
        reference_detected_facing=(
            sprite_types.SpriteFacing(row.reference_detected_facing)
            if row.reference_detected_facing is not None
            else None
        ),
    )
    vibemon.aesthetic = Aesthetic.from_vibemon(vibemon)
    vibemon.aesthetic.assets = {AssetKind(asset.kind): asset_ref(row.id, asset) for asset in row.assets}
    return vibemon


def move_from_row(row: models.Move) -> Move:
    return Move(
        id=row.content_id,
        name=row.name,
        flavor_text=row.flavor_text,
        type=VibemonTypeT(row.type),
        category=MoveCategoryT(row.category),
        power=row.power,
        accuracy=row.accuracy,
        pp=row.pp,
        priority=row.priority,
        target=MoveTargetT(row.target),
        level_requirement=row.level_requirement,
        effects=tuple(EffectGroup.model_validate(group) for group in row.effects),
        behavior=MoveBehavior.model_validate(row.behavior),
    )


def move_slot(row: models.VibemonMove) -> int:
    return row.active_slot if row.active_slot is not None else 99


def asset_ref(vibemon_id: uuid.UUID, row: models.VibemonAsset) -> AssetRef:
    return AssetRef(
        vibemon_id=vibemon_id,
        kind=AssetKind(row.kind),
        revision=row.selected_revision,
        key=row.object_key,
        content_type=row.content_type,
        byte_size=row.byte_size,
        sha256=row.sha256,
        anchor=SpriteAnchor.model_validate(row.display_anchor) if row.display_anchor else None,
    )
