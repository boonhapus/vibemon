"""Shared command-line plumbing for Vibemon rehearsal scripts."""

import app._compat.httpx  # noqa: F401 — patch httpx annotations for google-genai on Python 3.14+

from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from typing import Literal
import dataclasses
import datetime as dt
import enum
import json
import os
import pathlib
import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import cyclopts
import sqlalchemy as sa

from app.core.ids import TrainerIdT
from app.domains.battle import actions as battle_actions
from app.domains.battle import engine as battle_engine
from app.domains.battle import entity as battle_entity
from app.domains.generation.seed import BirthSeed
from app.domains.move import catalog as move_catalog
from app.domains.move import entity as move_entity
from app.domains.move import types as move_types
from app.domains.vibemon.schema import PublicVibemon
from app.domains.vibemon.types import VibemonLifecycleT
from app.providers.biome.provider import BiomeProvider
from app.providers.climate.provider import ClimateProvider
from app.providers.music.provider import MusicProvider
from app.settings import Settings
from app.storage.database import engine as db_engine
from app.storage.database import mapper, models, repositories
from app.workflows import _workflow_support as workflow_support
from app.workflows.materialize_vibemon import MaterializeVibemon

type BattleMovePolicyT = Literal["first_available", "best_damage", "stab_first", "status_aware", "random"]
type ScriptProviderT = ClimateProvider | BiomeProvider | MusicProvider

SCRIPT_ANONYMOUS_TRAINER_ID = uuid.UUID("01900000-0000-7000-8000-000000000002")
_BUST_CACHE_ENV = "VIBEMON_BUST_CACHE"


class ProviderName(enum.StrEnum):
    CLIMATE = "climate"
    BIOME = "biome"
    MUSIC = "music"


DEFAULT_PROVIDERS: tuple[ProviderName, ...] = (ProviderName.CLIMATE, ProviderName.BIOME)

_PROVIDER_TYPES: dict[ProviderName, type[ScriptProviderT]] = {
    ProviderName.CLIMATE: ClimateProvider,
    ProviderName.BIOME: BiomeProvider,
    ProviderName.MUSIC: MusicProvider,
}


def bust_cache_parameter(group: cyclopts.Group) -> cyclopts.Parameter:
    return cyclopts.Parameter(
        group=group,
        negative="",
        help="Force fresh provider HTTP responses and refresh cache entries.",
    )


def apply_cache_bust_flag(bust_cache: bool) -> None:
    if bust_cache:
        os.environ[_BUST_CACHE_ENV] = "1"


def load_script_settings(
    *,
    database_url: str | None = None,
    asset_store_url: str | None = None,
    bust_cache: bool = False,
) -> Settings:
    """Load settings from env, applying optional CLI storage overrides."""
    apply_cache_bust_flag(bust_cache)
    Settings.load(refresh=True)
    patch: dict[str, str] = {}
    if database_url is not None:
        patch["database"] = database_url
    if asset_store_url is not None:
        patch["assets"] = asset_store_url
    if patch:
        return Settings.load(storage=patch)
    return Settings.load()


def parse_datetime(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def resolve_provider_names(
    provider_names: Iterable[ProviderName | str] | None,
) -> tuple[ProviderName, ...]:
    if provider_names is None:
        return DEFAULT_PROVIDERS
    resolved = tuple(ProviderName(name) for name in provider_names)
    if not resolved:
        raise SystemExit("At least one --provider is required.")
    return resolved


def build_providers(provider_names: Iterable[ProviderName | str] | None = None) -> list[ScriptProviderT]:
    return [_PROVIDER_TYPES[name]() for name in resolve_provider_names(provider_names)]


def require_trainer_for_music(
    provider_names: Iterable[ProviderName | str] | None,
    *,
    trainer_id: uuid.UUID | None,
) -> None:
    names = resolve_provider_names(provider_names)
    if ProviderName.MUSIC in names and trainer_id is None:
        raise SystemExit("--trainer with a linked Last.fm account is required when the music provider is selected.")


def birth_seed(
    *,
    latitude: float,
    longitude: float,
    timestamp: str | None = None,
    trainer_id: uuid.UUID | None = None,
    provider_names: Iterable[ProviderName | str] | None = None,
) -> BirthSeed:
    require_trainer_for_music(provider_names, trainer_id=trainer_id)
    resolved_trainer_id = trainer_id or SCRIPT_ANONYMOUS_TRAINER_ID
    return BirthSeed(
        timestamp=parse_datetime(timestamp) if timestamp is not None else dt.datetime.now(tz=dt.UTC),
        geo_coords=(latitude, longitude),
        trainer_id=resolved_trainer_id,
        providers=build_providers(provider_names),
    )


def random_latitude() -> float:
    return random.uniform(-90.0, 90.0)


def random_longitude() -> float:
    return random.uniform(-180.0, 180.0)


@asynccontextmanager
async def session_scope(*, database_url: str) -> AsyncGenerator[AsyncSession]:
    db_engine.ensure_sqlite_parent_dir(database_url)
    engine = db_engine.create_async_database_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as sess:
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise
    finally:
        await engine.dispose()


def dump(value: object) -> None:
    print(json.dumps(_jsonable(value), default=str, indent=2, sort_keys=True))


def _jsonable(value: object) -> object:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _jsonable(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


def trainer_id(value: uuid.UUID) -> TrainerIdT:
    return value


async def ensure_trainer(
    sess: AsyncSession,
    trainer_id: uuid.UUID,
    *,
    username: str | None = None,
) -> models.Trainer:
    row = await sess.get(models.Trainer, trainer_id)
    if row is not None:
        return row
    row = models.Trainer(id=trainer_id, username=username or f"trainer-{str(trainer_id)[:8]}")
    sess.add(row)
    await sess.flush()
    return row


async def load_public_vibemon(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
) -> PublicVibemon:
    row = await repositories.load_vibemon(sess, vibemon_id)
    return await workflow_support.public_vibemon(row)


async def materialize_vibemon(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
    *,
    lifecycle: VibemonLifecycleT,
) -> PublicVibemon:
    row = await repositories.load_vibemon(sess, vibemon_id)
    vibemon = await mapper.vibemon_from_row(row)
    realizer = MaterializeVibemon()
    if lifecycle is VibemonLifecycleT.CHRISTENED:
        vibemon = await realizer.christen(vibemon)
    elif lifecycle is VibemonLifecycleT.MANIFESTED:
        vibemon = await realizer.manifest(await realizer.christen(vibemon))
    mapper.apply_vibemon_to_row(row, vibemon)
    await repositories.persist_assets(sess, vibemon)
    await sess.flush()
    return await workflow_support.public_vibemon(row)


async def load_battle_vibemon(sess: AsyncSession, vibemon_id: uuid.UUID) -> battle_entity.BattleVibemon:
    row = await repositories.load_vibemon(sess, vibemon_id)
    vibemon = await mapper.vibemon_from_row(row)
    return battle_entity.BattleVibemon(**vibemon.model_dump())


async def load_random_battle_vibemon(
    sess: AsyncSession,
    *,
    exclude_ids: set[uuid.UUID] | None = None,
) -> tuple[uuid.UUID, battle_entity.BattleVibemon]:
    vibemon_id = await _random_battle_vibemon_id(sess, exclude_ids=exclude_ids)
    if vibemon_id is None and exclude_ids:
        vibemon_id = await _random_battle_vibemon_id(sess)
    if vibemon_id is None:
        raise ValueError("No Vibemon with moves exists in the database for random battle selection.")
    return vibemon_id, await load_battle_vibemon(sess, vibemon_id)


async def _random_battle_vibemon_id(
    sess: AsyncSession,
    *,
    exclude_ids: set[uuid.UUID] | None = None,
) -> uuid.UUID | None:
    has_move = sa.exists(
        sa.select(1).where(
            models.VibemonMove.vibemon_id == models.Vibemon.id,
            models.VibemonMove.active_slot.is_not(None),
        )
    )
    stmt = sa.select(models.Vibemon.id).where(has_move).order_by(sa.func.random()).limit(1)
    if exclude_ids:
        stmt = stmt.where(models.Vibemon.id.not_in(exclude_ids))
    return (await sess.execute(stmt)).scalar_one_or_none()


def simulate_battle(
    vibemon_a: battle_entity.BattleVibemon,
    vibemon_b: battle_entity.BattleVibemon,
    *,
    trainer_a_id: uuid.UUID,
    trainer_b_id: uuid.UUID,
    trainer_a_name: str = "trainer-a",
    trainer_b_name: str = "trainer-b",
    rng_seed: int | None = None,
    move_policy: BattleMovePolicyT = "first_available",
) -> dict[str, object]:
    rng = random.Random(rng_seed)
    policy_rng = (
        random.Random()
        if rng_seed is None
        else random.Random(f"move-policy:{move_policy}:{rng_seed}:{trainer_a_id}:{trainer_b_id}")
    )
    engine = battle_engine.GameEngine(
        battle_entity.BattleTrainer(
            id=trainer_id(trainer_a_id),
            username=trainer_a_name,
            crew=[vibemon_a],
        ),
        battle_entity.BattleTrainer(
            id=trainer_id(trainer_b_id),
            username=trainer_b_name,
            crew=[vibemon_b],
        ),
        rng=rng,
    )
    turns: list[dict[str, object]] = []
    while not engine.battle.concluded:
        submitted = [
            _policy_move(engine.battle.trainer_a, engine.battle.trainer_b, policy=move_policy, rng=policy_rng),
            _policy_move(engine.battle.trainer_b, engine.battle.trainer_a, policy=move_policy, rng=policy_rng),
        ]
        events = engine.submit_actions(submitted)
        turns.append(
            {
                "turn": engine.battle.turn_number - 1,
                "actions": [action.model_dump(mode="json") for action in submitted],
                "events": [event.model_dump(mode="json") for event in events],
            }
        )
    winner = engine.battle.winner
    return {
        "winner_trainer_id": None if winner is None else str(winner.id),
        "winner": None if winner is None else winner.username,
        "concluded": engine.battle.concluded,
        "move_policy": move_policy,
        "turns": turns,
        "battle": engine.battle.to_json(),
    }


def _policy_move(
    trainer: battle_entity.BattleTrainer,
    opponent: battle_entity.BattleTrainer,
    *,
    policy: BattleMovePolicyT,
    rng: random.Random,
) -> battle_actions.MoveAction:
    user = trainer.active_vibemon
    target = opponent.active_vibemon
    move = _choose_move(user, target, policy=policy, rng=rng)
    return battle_actions.MoveAction(trainer=trainer.id, move_name=move.name)


def _choose_move(
    user: battle_entity.BattleVibemon,
    target: battle_entity.BattleVibemon,
    *,
    policy: BattleMovePolicyT,
    rng: random.Random,
) -> battle_entity.BattleMove:
    usable = [move for move in user.battle_moves if move.pp_current > 0]
    if not usable:
        return user.battle_moves[0]

    if policy == "first_available":
        return usable[0]
    if policy == "random":
        return rng.choice(usable)

    damaging = [move for move in usable if move.power is not None and move.category != move_types.MoveCategoryT.STATUS]
    if policy == "stab_first":
        stab = [move for move in damaging if move.type in user.elements]
        if stab:
            return max(stab, key=lambda move: (_estimated_damage_score(user, target, move), move.power or 0))
        if damaging:
            return max(damaging, key=lambda move: (_estimated_damage_score(user, target, move), move.power or 0))
        return usable[0]

    best_damage = max(damaging, key=lambda move: _estimated_damage_score(user, target, move), default=None)
    if policy == "status_aware":
        best_status = max(usable, key=lambda move: _status_effect_score(user, target, move), default=None)
        best_status_score = _status_effect_score(user, target, best_status) if best_status is not None else 0.0
        best_damage_score = _estimated_damage_score(user, target, best_damage) if best_damage is not None else 0.0
        if best_status is not None and best_status_score >= max(10.0, best_damage_score * 0.6):
            return best_status

    if best_damage is not None:
        return best_damage
    return usable[0]


def _estimated_damage_score(
    user: battle_entity.BattleVibemon,
    target: battle_entity.BattleVibemon,
    move: battle_entity.BattleMove | None,
) -> float:
    if move is None or move.power is None or move.category == move_types.MoveCategoryT.STATUS:
        return 0.0

    if move.category == move_types.MoveCategoryT.PHYSICAL:
        attack = user.attack
        defense = target.defense
    else:
        attack = user.sp_attack
        defense = target.sp_defense

    stab = 1.5 if move.type in user.elements else 1.0
    type_effect = move_catalog.get_element_effectiveness(move.type, list(target.elements))
    accuracy = 1.0 if move.accuracy is None else move.accuracy
    priority_bonus = 1.05 if move.priority > 0 else 1.0
    return move.power * (attack / max(1, defense)) * stab * type_effect * accuracy * priority_bonus


def _status_effect_score(
    user: battle_entity.BattleVibemon,
    target: battle_entity.BattleVibemon,
    move: battle_entity.BattleMove | None,
) -> float:
    if move is None:
        return 0.0

    score = 0.0
    for group in move.effects:
        chance = group.chance
        for effect in group.effects:
            if isinstance(effect, move_entity.StatusInflict) and target.status == move_types.StatusConditionT.NONE:
                weights = {
                    move_types.StatusConditionT.BURN: 18.0,
                    move_types.StatusConditionT.PARALYSIS: 16.0,
                    move_types.StatusConditionT.FREEZE: 20.0,
                    move_types.StatusConditionT.SLEEP: 10.0,
                    move_types.StatusConditionT.POISON: 12.0,
                    move_types.StatusConditionT.BAD_POISON: 18.0,
                }
                score += weights.get(effect.status, 0.0) * chance
            elif isinstance(effect, move_entity.StatChange):
                magnitude = sum(abs(delta) for delta in effect.changes.values())
                if effect.target == "self":
                    score += 8.0 * magnitude * chance
                elif effect.target == "target":
                    score += 7.0 * magnitude * chance
            elif isinstance(effect, move_entity.Heal) and user.current_hp < user.max_hp * 0.66:
                score += 20.0 * effect.ratio * chance
            elif isinstance(effect, move_entity.WeatherSet):
                score += 4.0 * chance

    if move.category == move_types.MoveCategoryT.STATUS and move.accuracy is not None:
        score *= move.accuracy
    return score


def ensure_local_blob_dir(url: str) -> None:
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    if parts.scheme != "file":
        return
    raw = (parts.netloc + parts.path) if parts.netloc not in ("", "localhost") else parts.path
    stripped = raw.lstrip("/\\")
    path = pathlib.Path(stripped) if len(stripped) >= 2 and stripped[1] == ":" else pathlib.Path(raw)
    path.mkdir(parents=True, exist_ok=True)
