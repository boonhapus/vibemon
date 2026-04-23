# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend", "rich"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///

import uuid

from app import game_engine, schema, types
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


def hp_bar(current: int, maximum: int, bar_width: int = 20) -> text.Text:
    pct = current / maximum if maximum > 0 else 0
    filled = int(pct * bar_width)
    if pct > 0.5:
        color = "green"
    elif pct > 0.2:
        color = "yellow"
    else:
        color = "red"
    text = text.Text()
    text.append("█" * filled, STYLE_COLORS[color])
    text.append("░" * (bar_width - filled), "dim")
    text.append(" ")
    text.append(str(current), STYLE_COLORS[color])
    text.append("/", "dim")
    text.append(str(maximum))
    return text


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


def _build_stage_line(v: schema.BattleVibemon) -> text.Text | None:
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


def _build_move_line(move: types.Move) -> text.Text:
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


def _volatile_effects(v: schema.BattleVibemon) -> list[str]:
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


def _event_parts(event: schema.TurnEvent) -> list[text.Text]:
    parts: list[text.Text] = []
    if event.hp_delta:
        hp_color = "green" if event.hp_delta > 0 else "red"
        parts.append(text.Text(f"{event.hp_delta:+d} HP", style=hp_color))
    if event.missed:
        parts.append(text.Text("MISSED", style="yellow"))
    if event.fainted:
        parts.append(text.Text("FAINTED ✖", style="red"))
    if event.stat_stage_changes:
        for stat, delta in event.stat_stage_changes.items():
            stat_color = "green" if delta > 0 else "red"
            parts.append(text.Text(f"{stat} {delta:+d}", style=stat_color))
    return parts


def _build_vibemon_panel(
    v: schema.BattleVibemon, trainer_name: str, color: str
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
    return panel.Panel(body, border_style=STYLE_COLORS[color], box=box.ROUNDED, expand=True)


def print_matchup(battle: schema.Battle) -> None:
    ta = battle.trainer_a
    tb = battle.trainer_b
    va = ta.active_vibemon
    vb = tb.active_vibemon

    rich_console.print()
    rich_console.print(
        columns.Columns(
            [
                _build_vibemon_panel(va, ta.name, "yellow"),
                _build_vibemon_panel(vb, tb.name, "magenta"),
            ],
            equal=True,
            expand=True,
        )
    )
    rich_console.print()


def print_events(events: list[schema.TurnEvent]) -> None:
    for event in events:
        line = text.Text.assemble(
            ("› ", "dim"), (event.actor, "bold"), (": "), (event.description or "")
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


def create_shocktail() -> schema.BattleVibemon:
    """Fake a new Vibemon."""
    affinity = schema.Affinity(
        elements=[types.VibemonTypeT.ELECTRIC],
        base_hp=111,
        base_attack=55,
        base_defense=40,
        base_sp_attack=50,
        base_sp_defense=50,
        base_speed=90,
        moves=[
            types.Move(
                name="Arc Burst",
                type=types.VibemonTypeT.ELECTRIC,
                category=types.MoveCategoryT.SPECIAL,
                power=32,
                accuracy=1.0,
                pp=20,
                pp_current=20,
            ),
            types.Move(
                name="Dash Claw",
                type=types.VibemonTypeT.NORMAL,
                category=types.MoveCategoryT.PHYSICAL,
                power=24,
                accuracy=1.0,
                priority=1,
                pp=30,
                pp_current=30,
            ),
        ]
    )

    vibemon = schema.BattleVibemon.from_affinities(
        affinity,
        name="Shocktail",
        description="A storm-chasing quadruped with a whip-tail that stores static arcs.",
    )

    return vibemon


def create_embermoth() -> schema.BattleVibemon:
    """Fake a new Vibemon."""
    affinity = schema.Affinity(
        elements=[types.VibemonTypeT.FIRE],
        base_hp=150,
        base_attack=64,
        base_defense=92,
        base_sp_attack=78,
        base_sp_defense=94,
        base_speed=88,
        moves=[
            types.Move(
                name="Cinder Lance",
                type=types.VibemonTypeT.FIRE,
                category=types.MoveCategoryT.SPECIAL,
                power=30,
                accuracy=1.0,
                pp=20,
                pp_current=20,
            ),
            types.Move(
                name="Ash Flare",
                type=types.VibemonTypeT.FIRE,
                category=types.MoveCategoryT.SPECIAL,
                power=22,
                accuracy=1.0,
                pp=25,
                pp_current=25,
            ),
        ]
    )

    vibemon = schema.BattleVibemon.from_affinities(
        affinity,
        name="Embermoth",
        description="A volcanic moth with heat-diffusing wing scales and ember veins.",
    )

    return vibemon


def main() -> None:
    trainer_a_id = uuid.uuid4()
    trainer_b_id = uuid.uuid4()

    engine = game_engine.GameEngine(
        trainer_a=schema.Trainer(
            id=trainer_a_id,
            name="Red",
            team=[create_shocktail()],
        ),
        trainer_b=schema.Trainer(
            id=trainer_b_id,
            name="Blue",
            team=[create_embermoth()],
        ),
    )

    action_a = types.Action(
        trainer_name=trainer_a_id,
        action_type=types.ActionType.MOVE,
        value="Arc Burst",
    )
    action_b = types.Action(
        trainer_name=trainer_b_id,
        action_type=types.ActionType.MOVE,
        value="Cinder Lance",
    )

    header("⚔  BATTLE START  ⚔")
    print_matchup(engine.battle)

    turn_count = 0
    while not engine.battle.concluded and turn_count < 10:
        turn_count += 1
        events = engine.submit(action_a, action_b)

        header(f"TURN {turn_count}")

        section("Actions")
        rich_console.print(text.Text.assemble(("Red", "yellow"), (f":  {action_a.value}")))
        rich_console.print(text.Text.assemble(("Blue", "magenta"), (f": {action_b.value}")))

        section("Events")
        print_events(events)

        section("State")
        print_matchup(engine.battle)

    header("🏆  BATTLE RESULT  🏆")
    if engine.battle.winner:
        rich_console.print()
        rich_console.print(
            text.Text.assemble(
                ("Winner", "bold green"),
                (": "),
                (engine.battle.winner.name, "bold"),
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


if __name__ == "__main__":
    main()
