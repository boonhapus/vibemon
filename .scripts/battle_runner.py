# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend", "sqlalchemy[asyncio]", "aiosqlite"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///
import argparse
import asyncio
import pathlib
import random
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload, sessionmaker

from app import models, schema, types
from app.battle import actions, events
from app.battle import schema as battle_schema
from app.battle.engine import GameEngine

DB_PATH = pathlib.Path(__file__).parent / "vibemon.db"


def _model_move_to_schema(move: models.Move) -> schema.Move:
    return schema.Move(
        name=move.name,
        flavor_text=move.flavor_text,
        type=types.VibemonTypeT(move.type),
        category=types.MoveCategoryT(move.category),
        power=move.power,
        accuracy=move.accuracy,
        pp=move.pp,
        priority=move.priority,
        effects=tuple(
            schema.EffectGroup.model_validate(group) for group in (move.effects or ())
        ),
        level_requirement=move.level_requirement,
    )


def _ensure_4_moves(moves: list[schema.Move]) -> list[schema.Move]:
    while len(moves) < 4:
        moves.append(schema.Move(
            name="Struggle",
            flavor_text="A last-resort attack.",
            type=types.VibemonTypeT.NORMAL,
            category=types.MoveCategoryT.PHYSICAL,
            power=50,
            accuracy=1.0,
            pp=999,
            priority=0,
            level_requirement=1,
        ))
    return moves[:4]


def _model_affinity_to_schema(affinity: models.Affinity) -> schema.Affinity:
    identity = affinity.identity
    return schema.Affinity(
        identity=schema.Identity(
            name=identity.name,
            visual_notes=identity.visual_notes,
            elements=tuple(types.VibemonTypeT(element) for element in identity.elements),
            base_hp=identity.base_hp,
            base_attack=identity.base_attack,
            base_defense=identity.base_defense,
            base_sp_attack=identity.base_sp_attack,
            base_sp_defense=identity.base_sp_defense,
            base_speed=identity.base_speed,
            evo_seed=types.EvolutionStageT(identity.evo_seed),
            evo_stage=types.EvolutionStageT[identity.evo_stage],
            is_radiant=identity.is_radiant,
        ),
        visual_notes=affinity.visual_notes,
        intensity=affinity.intensity,
        provider_id=affinity.provider_id,
        moves=_ensure_4_moves([_model_move_to_schema(move) for move in affinity.moves]),
    )


def _model_vibemon_to_battle(vibemon: models.Vibemon) -> battle_schema.BattleVibemon:
    return battle_schema.BattleVibemon(
        nickname=vibemon.nickname,
        affinity=_model_affinity_to_schema(vibemon.affinity),
        level=vibemon.level,
        birth_affinities=tuple(
            _model_affinity_to_schema(affinity) for affinity in vibemon.birth_affinities
        ),
    )


def choose_random_usable_move(vibemon: battle_schema.BattleVibemon) -> battle_schema.BattleMove:
    usable = [m for m in vibemon.battle_moves if m.pp_current > 0]
    return random.choice(usable)


async def load_all_vibemon(db_path: str) -> list[models.Vibemon]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as sess:
            result = await sess.execute(
                sa.select(models.Vibemon)
                .options(
                    selectinload(models.Vibemon.affinity).selectinload(models.Affinity.identity),
                    selectinload(models.Vibemon.affinity).selectinload(models.Affinity.moves),
                    selectinload(models.Vibemon.birth_affinities).selectinload(models.Affinity.identity),
                    selectinload(models.Vibemon.birth_affinities).selectinload(models.Affinity.moves),
                )
            )
            return list(result.scalars())
    finally:
        await engine.dispose()


def run_single_battle(va: models.Vibemon, vb: models.Vibemon, battle_id: int) -> str:
    bva = _model_vibemon_to_battle(va)
    bvb = _model_vibemon_to_battle(vb)

    ta_id = uuid.uuid4()
    tb_id = uuid.uuid4()

    engine = GameEngine(
        trainer_a=battle_schema.BattleTrainer(id=ta_id, username="Red", team=[bva]),
        trainer_b=battle_schema.BattleTrainer(id=tb_id, username="Blue", team=[bvb]),
    )

    turn_count = 0
    while not engine.battle.concluded:
        turn_count += 1
        ma = choose_random_usable_move(engine.battle.trainer_a.active_vibemon)
        mb = choose_random_usable_move(engine.battle.trainer_b.active_vibemon)
        _ = engine.submit_actions([
            actions.MoveAction(trainer=ta_id, move_name=ma.name),
            actions.MoveAction(trainer=tb_id, move_name=mb.name),
        ])

    winner = engine.battle.winner
    va_final = engine.battle.trainer_a.active_vibemon
    vb_final = engine.battle.trainer_b.active_vibemon

    if winner:
        if winner.username == "Red":
            wv, lv = va_final, vb_final
        else:
            wv, lv = vb_final, va_final
        return (
            f"Battle {battle_id:04d}: "
            f"WINNER={winner.username} "
            f"Winner={wv.name}(BST={wv.affinity.identity.bst}) "
            f"Loser={lv.name}(BST={lv.affinity.identity.bst}) "
            f"Turns={turn_count} "
            f"WinnerTypes={'/'.join(t.value for t in wv.elements)} "
            f"LoserTypes={'/'.join(t.value for t in lv.elements)} "
            f"WinnerRole={wv.affinity.identity.battle_role.name} "
            f"LoserRole={lv.affinity.identity.battle_role.name}"
        )
    else:
        return (
            f"Battle {battle_id:04d}: "
            f"WINNER=draw "
            f"Red={va_final.name}(BST={va_final.affinity.identity.bst}) "
            f"Blue={vb_final.name}(BST={vb_final.affinity.identity.bst}) "
            f"Turns={turn_count}"
        )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5000)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--db-path", type=str, default=str(DB_PATH))
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    output_dir = pathlib.Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading vibemon from {args.db_path}...")
    all_vibemon = await load_all_vibemon(args.db_path)
    print(f"Loaded {len(all_vibemon)} vibemon")

    output_lines: list[str] = []
    total_battles = args.count
    batch_size = args.batch_size

    for i in range(total_battles):
        va, vb = random.sample(all_vibemon, 2)
        result = run_single_battle(va, vb, i)
        output_lines.append(result)

        if output_dir and i % batch_size == 0 and i > 0:
            batch_file = output_dir / f"battles_{i-batch_size:04d}-{i-1:04d}.txt"
            batch_file.write_text("\n".join(output_lines[-batch_size:]) + "\n")
            print(f"Batch {i-batch_size:04d}-{i-1:04d} saved", flush=True)

    if output_dir:
        final_batch_start = (total_battles // batch_size) * batch_size
        remaining = output_lines[final_batch_start:]
        if remaining:
            batch_file = output_dir / f"battles_{final_batch_start:04d}-{total_battles-1:04d}.txt"
            batch_file.write_text("\n".join(remaining) + "\n")

        summary_file = output_dir / "all_battles.txt"
        summary_file.write_text("\n".join(output_lines) + "\n")
        print(f"All {total_battles} battle results written to {summary_file}")

    # Print summary
    wins = sum(1 for l in output_lines if "WINNER=Red" in l)
    losses = sum(1 for l in output_lines if "WINNER=Blue" in l)
    draws = sum(1 for l in output_lines if "WINNER=draw" in l)
    print(f"\nResults: Red={wins}, Blue={losses}, Draws={draws}")


if __name__ == "__main__":
    asyncio.run(main())
