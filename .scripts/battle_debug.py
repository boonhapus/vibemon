# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend", "rich", "sqlalchemy[asyncio]", "aiosqlite"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///

import argparse
import asyncio
import pathlib
import random
import sys
import uuid

from contextlib import redirect_stdout
from io import StringIO

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from app import models
from app import schema, types
from app.battle import actions, events
from app.battle import schema as battle_schema
from app.battle.engine import GameEngine
from rich import box, columns, console, panel, rule, text

STYLE_COLORS = {
    "red": "red",
    "green": "green",
    "yellow": "yellow",
    "blue": "blue",
    "magenta": "magenta",
    "cyan": "cyan",
    "white": "white",
    "gray": "dim",
}

TYPE_COLORS = {
    "fire": "red",
    "water": "blue",
    "electric": "yellow",
    "grass": "green",
    "normal": "white",
    "flying": "cyan",
    "fighting": "red",
    "poison": "magenta",
    "ground": "yellow",
    "rock": "yellow",
    "bug": "green",
    "ghost": "magenta",
    "psychic": "magenta",
    "ice": "cyan",
    "dragon": "magenta",
    "dark": "gray",
    "steel": "white",
    "fairy": "magenta",
}

WIDTH = 120
rich_console = console.Console(width=WIDTH)

MOVE_CATEGORY_ICONS = {
    types.MoveCategoryT.PHYSICAL: "💥",
    types.MoveCategoryT.SPECIAL: "✦",
    types.MoveCategoryT.STATUS: "◈",
}

STAGE_FIELDS = (
    ("atk", "attack"),
    ("def", "defense"),
    ("spa", "sp_attack"),
    ("spd", "sp_defense"),
    ("spe", "speed"),
)

DB_PATH = pathlib.Path(__file__).parent / "vibemon.db"


async def ensure_move_effects_column(conn) -> None:
    """Add the modern effects JSON column to older local SQLite databases."""
    columns = await conn.run_sync(
        lambda sync_conn: {
            row[1] for row in sync_conn.exec_driver_sql("PRAGMA table_info(move)")
        }
    )
    if "effects" not in columns:
        await conn.exec_driver_sql("ALTER TABLE move ADD COLUMN effects JSON")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", choices=("rich", "chat"), default="rich")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save battle files")
    parser.add_argument("--battle-id", type=int, default=None, help="Battle number for filename")
    return parser.parse_args()


def hp_bar(current: int, maximum: int, bar_width: int = 20) -> text.Text:
    pct = current / maximum if maximum > 0 else 0
    filled = int(pct * bar_width)
    if pct > 0.5:
        color = "green"
    elif pct > 0.2:
        color = "yellow"
    else:
        color = "red"
    bar = text.Text()
    bar.append("█" * filled, STYLE_COLORS[color])
    bar.append("░" * (bar_width - filled), "dim")
    bar.append(" ")
    bar.append(str(current), STYLE_COLORS[color])
    bar.append("/", "dim")
    bar.append(str(maximum))
    return bar


def type_badge(t: types.VibemonTypeT) -> text.Text:
    color = TYPE_COLORS.get(t.value, "white")
    return text.Text(f"[{t.value.upper()}]", style=STYLE_COLORS.get(color, "white"))


def header(string: str) -> None:
    rich_console.print(
        panel.Panel(
            text.Text(string, style="bold"),
            border_style="cyan",
            box=box.DOUBLE,
            width=WIDTH,
            expand=False,
        )
    )


def section(string: str) -> None:
    rich_console.print()
    rich_console.print(rule.Rule(text.Text(string, style="bold"), style="cyan"))


def _build_stage_line(v: battle_schema.BattleVibemon) -> text.Text | None:
    stage_parts: list[text.Text] = []
    for label, attr_name in STAGE_FIELDS:
        value = getattr(v.stat_stages, attr_name)
        if value != 0:
            stage_parts.append(
                text.Text(f"{label}{value:+d}", style="green" if value > 0 else "red")
            )

    if not stage_parts:
        return None

    stage_line = text.Text("stages: ", style="dim")
    for idx, part in enumerate(stage_parts):
        if idx:
            stage_line.append(" ")
        stage_line.append_text(part)
    return stage_line


def _build_move_line(move: battle_schema.BattleMove) -> text.Text:
    type_color = TYPE_COLORS.get(move.type.value, "white")
    pp_ratio = move.pp_current / move.pp if move.pp > 0 else 0
    pp_color = "green" if pp_ratio > 0.5 else "yellow" if pp_ratio > 0 else "red"
    icon = MOVE_CATEGORY_ICONS.get(move.category, "◈")

    move_line = text.Text()
    move_line.append(f"{icon} {move.name:<14} ")
    move_line.append(
        f"{move.type.value.upper():<10}", style=STYLE_COLORS.get(type_color, "white")
    )
    move_line.append(f" PWR {move.power:<3} PP ")
    move_line.append(str(move.pp_current), style=pp_color)
    move_line.append(f"/{move.pp}")
    if move.priority > 0:
        move_line.append(f" +{move.priority}", style="cyan")
    return move_line


def _volatile_effects(v: battle_schema.BattleVibemon) -> list[str]:
    volatile: list[str] = []
    if v.is_confused:
        volatile.append(f"Confused({v.confusion_turns}t)")
    if v.taunt_turns > 0:
        volatile.append(f"Taunt({v.taunt_turns}t)")
    if v.bound_turns > 0:
        volatile.append(f"Bound({v.bound_turns}t)")
    if v.is_flinched:
        volatile.append("Flinched")
    if v.is_seeded:
        volatile.append("Seeded")
    return volatile


def _lines_to_text(lines: list[text.Text]) -> text.Text:
    body = text.Text()
    for idx, line in enumerate(lines):
        if idx:
            body.append("\n")
        body.append_text(line)
    return body


def _event_parts(event: events.TurnEvent) -> list[text.Text]:
    parts: list[text.Text] = []
    if isinstance(event, events.DamageEvent):
        parts.append(text.Text(f"-{event.amount} HP", style="red"))
        if event.is_crit:
            parts.append(text.Text("CRIT", style="yellow"))
        if event.effectiveness > 1:
            parts.append(text.Text(f"{event.effectiveness:g}x", style="green"))
        elif event.effectiveness < 1:
            parts.append(text.Text(f"{event.effectiveness:g}x", style="yellow"))
    if isinstance(event, events.HealEvent):
        parts.append(text.Text(f"+{event.amount} HP", style="green"))
    if isinstance(event, events.StatusDamageEvent):
        parts.append(text.Text(f"-{event.amount} HP", style="red"))
    if isinstance(event, events.MoveMissedEvent):
        parts.append(text.Text("MISSED", style="yellow"))
    if isinstance(event, events.FaintEvent):
        parts.append(text.Text("FAINTED ✖", style="red"))
    if isinstance(event, events.StatChangeEvent):
        for stat, delta in event.changes.items():
            stat_color = "green" if delta > 0 else "red"
            parts.append(text.Text(f"{stat} {delta:+d}", style=stat_color))
    return parts


def _build_vibemon_panel(
    v: battle_schema.BattleVibemon, trainer_name: str, color: str
) -> panel.Panel:
    lines: list[text.Text] = []

    title = text.Text()
    title.append(trainer_name, style=STYLE_COLORS[color])
    title.append("  ")
    title.append(v.name, style="bold")
    title.append(f"  Lv.{v.level}")
    if v.is_fainted:
        title.append("  ✖ FAINTED", style="red")
    lines.append(title)

    type_line = text.Text()
    for idx, t in enumerate(v.elements):
        if idx:
            type_line.append(" ")
        type_line.append_text(type_badge(t))
    lines.append(type_line)

    hp_line = text.Text("HP ", style="dim")
    hp_line.append_text(hp_bar(v.current_hp, v.max_hp))
    lines.append(hp_line)

    if v.status != types.StatusConditionT.NONE:
        lines.append(text.Text(f"⚠ {v.status.value.upper()}", style="red"))

    lines.append(
        text.Text.assemble(
            ("ATK ", "dim"),
            (f"{v.attack:<4}"),
            (" DEF ", "dim"),
            (f"{v.defense:<4}"),
            (" SPD ", "dim"),
            (f"{v.speed:<4}"),
        )
    )
    lines.append(
        text.Text.assemble(
            ("SPA ", "dim"),
            (f"{v.sp_attack:<4}"),
            (" SPD ", "dim"),
            (f"{v.sp_defense:<4}"),
        )
    )

    if stage_line := _build_stage_line(v):
        lines.append(stage_line)

    lines.append(text.Text("Moves:", style="dim"))
    for move in v.moves:
        lines.append(_build_move_line(move))

    volatile = _volatile_effects(v)
    if volatile:
        lines.append(text.Text("⚡ " + " | ".join(volatile), style="red"))

    body = _lines_to_text(lines)
    return panel.Panel(
        body, border_style=STYLE_COLORS[color], box=box.ROUNDED, expand=True
    )


def print_matchup(battle: battle_schema.Battle) -> None:
    ta = battle.trainer_a
    tb = battle.trainer_b
    va = ta.active_vibemon
    vb = tb.active_vibemon

    rich_console.print()
    rich_console.print(
        columns.Columns(
            [
                _build_vibemon_panel(va, ta.username, "yellow"),
                _build_vibemon_panel(vb, tb.username, "magenta"),
            ],
            equal=True,
            expand=True,
        )
    )
    rich_console.print()


def _event_actor(event: events.TurnEvent) -> str:
    match event:
        case events.MoveUsedEvent():
            return event.user
        case events.MoveMissedEvent():
            return event.user
        case events.MoveFailedEvent():
            return event.user
        case events.DamageEvent():
            return event.source
        case events.FaintEvent():
            return event.target
        case events.StatusInflictedEvent():
            return event.source or event.target
        case events.StatusDamageEvent():
            return event.target
        case events.StatusMessageEvent():
            return event.target
        case events.StatChangeEvent():
            return event.source or event.target
        case events.HealEvent():
            return event.source or event.target
        case events.WeatherSetEvent():
            return event.source or "Field"


def _status_message(target: str, message_key: str) -> str:
    messages = {
        "woke_up": f"{target} woke up!",
        "asleep": f"{target} is asleep!",
        "thawed": f"{target} thawed out!",
        "frozen": f"{target} is frozen!",
        "flinched": f"{target} flinched!",
        "fully_paralyzed": f"{target} is paralyzed and can't move!",
        "confusion_self_hit": f"{target} hurt itself in confusion!",
        "confusion_ended": f"{target} snapped out of confusion!",
        "taunt_ended": f"{target}'s taunt wore off!",
        "bind_ended": f"{target} is freed from bind!",
    }
    return messages.get(message_key, message_key.replace("_", " "))


def _event_description(event: events.TurnEvent) -> str:
    match event:
        case events.MoveUsedEvent():
            targets = ", ".join(event.targets)
            return f"used {event.move}" + (f" on {targets}" if targets else "")
        case events.MoveMissedEvent():
            return f"{event.move} missed {event.target}"
        case events.MoveFailedEvent():
            move = f"{event.move} " if event.move else ""
            reason = f" ({event.reason})" if event.reason else ""
            return f"{move}failed{reason}"
        case events.DamageEvent():
            return f"{event.move or 'damage'} hit {event.target} for {event.amount}"
        case events.FaintEvent():
            return "fainted"
        case events.StatusInflictedEvent():
            return f"{event.target} got {event.status.value}"
        case events.StatusDamageEvent():
            return f"takes status damage: {event.amount}"
        case events.StatusMessageEvent():
            return _status_message(event.target, event.message_key)
        case events.StatChangeEvent():
            return f"{event.target} stat stages changed"
        case events.HealEvent():
            return f"{event.target} recovered {event.amount} HP"
        case events.WeatherSetEvent():
            return f"weather became {event.weather.value} for {event.turns} turns"


def print_events(turn_events: list[events.TurnEvent]) -> None:
    for event in turn_events:
        line = text.Text.assemble(
            ("› ", "dim"),
            (_event_actor(event), "bold"),
            (": "),
            (_event_description(event)),
        )
        parts = _event_parts(event)

        if parts:
            line.append("  [")
            for idx, part in enumerate(parts):
                if idx:
                    line.append(", ")
                line.append_text(part)
            line.append("]")
        rich_console.print(line)


def _event_parts_plain(event: events.TurnEvent) -> str:
    parts: list[str] = []
    if isinstance(event, events.DamageEvent):
        parts.append(f"-{event.amount} HP")
        if event.is_crit:
            parts.append("crit")
        if event.effectiveness != 1:
            parts.append(f"{event.effectiveness:g}x")
    elif isinstance(event, events.HealEvent):
        parts.append(f"+{event.amount} HP")
    elif isinstance(event, events.StatusDamageEvent):
        parts.append(f"-{event.amount} HP")
    elif isinstance(event, events.MoveMissedEvent):
        parts.append("missed")
    elif isinstance(event, events.FaintEvent):
        parts.append("fainted")
    elif isinstance(event, events.StatChangeEvent):
        parts.extend(f"{stat} {delta:+d}" for stat, delta in event.changes.items())
    return f" ({', '.join(parts)})" if parts else ""


def _event_plain(event: events.TurnEvent) -> str:
    return (
        f"{_event_actor(event)}: {_event_description(event)}{_event_parts_plain(event)}"
    )


def _vibemon_plain(label: str, vibemon: battle_schema.BattleVibemon) -> str:
    types_text = "/".join(t.value for t in vibemon.elements)
    moves = ", ".join(
        f"{move.name} [{move.type.value}, {move.category.value}, {move.power or '-'}]"
        for move in vibemon.moves
    )
    fainted = " fainted" if vibemon.is_fainted else ""
    bst = vibemon.affinity.identity.bst
    return (
        f"{label}: {vibemon.name} Lv.{vibemon.level} ({types_text}) BST {bst}"
        f" HP {vibemon.current_hp}/{vibemon.max_hp}{fainted}\n"
        f"  Stats: Atk {vibemon.attack}, Def {vibemon.defense}, SpA {vibemon.sp_attack}, "
        f"SpD {vibemon.sp_defense}, Spe {vibemon.speed}\n"
        f"  Moves: {moves}"
    )


def print_chat_turn(
    turn_number: int,
    battle: battle_schema.Battle,
    action_a: actions.MoveAction,
    action_b: actions.MoveAction,
    turn_events: list[events.TurnEvent],
) -> None:
    print(f"\n### Turn {turn_number}")
    print(f"- Red chose {action_a.move_name}")
    print(f"- Blue chose {action_b.move_name}")
    print("\nEvents:")
    for event in turn_events:
        print(f"- {_event_plain(event)}")
    print("\nState:")
    print(
        f"- Red: {battle.trainer_a.active_vibemon.name} HP {battle.trainer_a.active_vibemon.current_hp}/{battle.trainer_a.active_vibemon.max_hp}"
    )
    print(
        f"- Blue: {battle.trainer_b.active_vibemon.name} HP {battle.trainer_b.active_vibemon.current_hp}/{battle.trainer_b.active_vibemon.max_hp}"
    )


def choose_random_usable_move(
    vibemon: battle_schema.BattleVibemon,
) -> battle_schema.BattleMove:
    usable_moves = [move for move in vibemon.moves if move.pp_current > 0]
    if not usable_moves:
        raise RuntimeError(f"{vibemon.name} has no moves with remaining PP")
    return random.choice(usable_moves)


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
        effect=schema.MoveEffect(**move.effect) if move.effect is not None else None,
        effects=tuple(
            schema.EffectGroup.model_validate(group) for group in (move.effects or ())
        ),
        level_requirement=move.level_requirement,
    )


def _model_affinity_to_schema(affinity: models.Affinity) -> schema.Affinity:
    identity = affinity.identity
    return schema.Affinity(
        identity=schema.Identity(
            name=identity.name,
            visual_notes=identity.visual_notes,
            elements=tuple(
                types.VibemonTypeT(element) for element in identity.elements
            ),
            base_hp=identity.base_hp,
            base_attack=identity.base_attack,
            base_defense=identity.base_defense,
            base_sp_attack=identity.base_sp_attack,
            base_sp_defense=identity.base_sp_defense,
            base_speed=identity.base_speed,
            evo_seed=identity.evo_seed,
            evo_stage=types.EvolutionStageT[identity.evo_stage],
            is_mythic=identity.is_mythic,
        ),
        visual_notes=affinity.visual_notes,
        intensity=affinity.intensity,
        provider_id=affinity.provider_id,
        moves=[_model_move_to_schema(move) for move in affinity.moves],
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


async def load_random_battle_vibemon(
    count: int = 2,
) -> list[battle_schema.BattleVibemon]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")
    try:
        async with engine.begin() as conn:
            await ensure_move_effects_column(conn)

        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as sess:
            result = await sess.execute(
                sa.select(models.Vibemon)
                .options(
                    selectinload(models.Vibemon.affinity).selectinload(
                        models.Affinity.identity
                    ),
                    selectinload(models.Vibemon.affinity).selectinload(
                        models.Affinity.moves
                    ),
                    selectinload(models.Vibemon.birth_affinities).selectinload(
                        models.Affinity.identity
                    ),
                    selectinload(models.Vibemon.birth_affinities).selectinload(
                        models.Affinity.moves
                    ),
                )
                .order_by(sa.func.random())
                .limit(count)
            )
            vibemon = list(result.scalars())
    finally:
        await engine.dispose()

    if len(vibemon) < count:
        raise RuntimeError(
            f"Need at least {count} Vibemon in {DB_PATH}; run .scripts/vibemon_generator.py first."
        )
    return [_model_vibemon_to_battle(v) for v in vibemon]


async def main() -> None:
    args = parse_args()

    need_file_output = args.render == "chat" and args.output_dir and args.battle_id is not None
    output_buffer = StringIO() if need_file_output else None

    if need_file_output:
        cm = redirect_stdout(output_buffer)
        cm.__enter__()

    try:
        trainer_a_id = uuid.uuid4()
        trainer_b_id = uuid.uuid4()
        vibemon_a, vibemon_b = await load_random_battle_vibemon()

        engine = GameEngine(
            trainer_a=battle_schema.BattleTrainer(
                id=trainer_a_id,
                username="Red",
                team=[vibemon_a],
            ),
            trainer_b=battle_schema.BattleTrainer(
                id=trainer_b_id,
                username="Blue",
                team=[vibemon_b],
            ),
        )

        if args.render == "chat":
            print("# Battle Debug Transcript")
            print()
            print(_vibemon_plain("Red", engine.battle.trainer_a.active_vibemon))
            print()
            print(_vibemon_plain("Blue", engine.battle.trainer_b.active_vibemon))
        else:
            header("⚔  BATTLE START  ⚔")
            print_matchup(engine.battle)

        turn_count = 0
        while not engine.battle.concluded:
            turn_count += 1
            move_a = choose_random_usable_move(engine.battle.trainer_a.active_vibemon)
            move_b = choose_random_usable_move(engine.battle.trainer_b.active_vibemon)
            action_a = actions.MoveAction(
                trainer=trainer_a_id,
                move_name=move_a.name,
            )
            action_b = actions.MoveAction(
                trainer=trainer_b_id,
                move_name=move_b.name,
            )
            turn_events = engine.submit_actions([action_a, action_b])

            if args.render == "chat":
                print_chat_turn(turn_count, engine.battle, action_a, action_b, turn_events)
                continue

            header(f"TURN {turn_count}")

            section("Actions")
            rich_console.print(
                text.Text.assemble(("Red", "yellow"), (f":  {action_a.move_name}"))
            )
            rich_console.print(
                text.Text.assemble(("Blue", "magenta"), (f": {action_b.move_name}"))
            )

            section("Events")
            print_events(turn_events)

            section("State")
            print_matchup(engine.battle)

        if args.render == "chat":
            print("\n## Result")
            if engine.battle.winner:
                print(f"Winner: {engine.battle.winner.username}")
            else:
                print("No winner within the turn limit.")
            print()
            print(_vibemon_plain("Red", engine.battle.trainer_a.active_vibemon))
            print()
            print(_vibemon_plain("Blue", engine.battle.trainer_b.active_vibemon))
        else:
            header("🏆  BATTLE RESULT  🏆")
            if engine.battle.winner:
                rich_console.print()
                rich_console.print(
                    text.Text.assemble(
                        ("Winner", "bold green"),
                        (": "),
                        (engine.battle.winner.username, "bold"),
                        ("!"),
                    )
                )
                rich_console.print()
            print_matchup(engine.battle)

            section("Turn History")
            for record in engine.battle.turn_history:
                rich_console.print()
                rich_console.print(text.Text(f"Turn {record.turn_number}", style="bold"))
                print_events(record.events)

        # Store result for file output
        battle_winner = engine.battle.winner
        battle_turns = turn_count
        va = engine.battle.trainer_a.active_vibemon
        vb = engine.battle.trainer_b.active_vibemon

    finally:
        if need_file_output:
            cm.__exit__(None, None, None)
            captured = output_buffer.getvalue()

            if battle_winner:
                if battle_winner.username == "Red":
                    winner_v, loser_v = va, vb
                else:
                    winner_v, loser_v = vb, va
                one_liner = (
                    f"Battle {args.battle_id:03d}: "
                    f"✅ {winner_v.name} (BST {winner_v.affinity.identity.bst}) "
                    f"vs {loser_v.name} (BST {loser_v.affinity.identity.bst}) "
                    f"- {battle_turns} turns"
                )
            else:
                one_liner = (
                    f"Battle {args.battle_id:03d}: "
                    f"No winner (Red: {va.name} BST {va.affinity.identity.bst} "
                    f"vs Blue: {vb.name} BST {vb.affinity.identity.bst}) "
                    f"- {battle_turns} turns"
                )

            output_path = pathlib.Path(args.output_dir) / f"battle_{args.battle_id:03d}.txt"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(captured)
                if not captured.endswith("\n"):
                    f.write("\n")
                f.write(one_liner + "\n")

            print(one_liner)


if __name__ == "__main__":
    asyncio.run(main())
