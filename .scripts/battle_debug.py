# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" }
# ///

import uuid
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app import game_engine, schema, types


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
    "gray": "\033[90m",
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
    "dark": "white",
    "steel": "white",
    "fairy": "magenta",
}

WIDTH = 120
CARD_W = 54
GAP = "    "


def c(color: str, text: str) -> str:
    return f"{COLORS.get(color, '')}{text}{RESET}"


def bold(text: str) -> str:
    return f"{BOLD}{text}{RESET}"


def dim(text: str) -> str:
    return f"{DIM}{text}{RESET}"


def _visible_len(s: str) -> int:
    """Length of string without ANSI escape sequences."""
    import re
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def _pad(s: str, width: int) -> str:
    """Pad string to width accounting for ANSI codes."""
    vis = _visible_len(s)
    return s + " " * max(0, width - vis)


def hp_bar(current: int, maximum: int, bar_width: int = 20) -> str:
    pct = current / maximum if maximum > 0 else 0
    filled = int(pct * bar_width)
    if pct > 0.5:
        color = "green"
    elif pct > 0.2:
        color = "yellow"
    else:
        color = "red"
    bar = c(color, "█" * filled) + dim("░" * (bar_width - filled))
    return f"{bar} {c(color, str(current))}{dim('/')}{maximum}"


def type_badge(t: types.VibemonTypeT) -> str:
    color = TYPE_COLORS.get(t.value, "white")
    return c(color, f"[{t.value.upper()}]")


def header(text: str):
    print(c("cyan", "═" * WIDTH))
    padding = (WIDTH - len(text) - 2) // 2
    right = WIDTH - padding - len(text) - 2
    print(c("cyan", "║") + " " * padding + bold(text) + " " * right + c("cyan", "║"))
    print(c("cyan", "═" * WIDTH))


def section(text: str):
    print()
    print(f"  {c('cyan', '──')} {bold(text)} {c('cyan', '─' * (WIDTH - 8 - len(text)))}")


def _build_vibemon_lines(v: schema.BattleVibemon, trainer_name: str, color: str) -> list[str]:
    """Build card lines for a vibemon. Each line is CARD_W visible chars."""
    lines: list[str] = []

    types_str = " ".join(type_badge(t) for t in v.type_list)
    faint = c("red", " ✖ FAINTED") if v.is_fainted else ""
    lines.append(f"{c(color, '▌')} {c(color, trainer_name)}  {bold(v.name)}  Lv.{v.level}  {types_str}{faint}")

    lines.append(f"  HP  {hp_bar(v.current_hp, v.max_hp)}")

    if v.status != types.StatusConditionT.NONE:
        lines.append(f"      {c('red', f'⚠ {v.status.value.upper()}')}")

    stat_line1 = (
        f"  {dim('ATK')} {v.attack:<4}  "
        f"{dim('DEF')} {v.defense:<4}  "
        f"{dim('SPD')} {v.speed:<4}"
    )
    stat_line2 = (
        f"  {dim('SPA')} {v.sp_attack:<4}  "
        f"{dim('SPD')} {v.sp_defense:<4}"
    )

    stages = v.stat_stages
    stage_parts = []
    for label, val in [("atk", stages.attack), ("def", stages.defense),
                       ("spa", stages.sp_attack), ("spd", stages.sp_defense),
                       ("spe", stages.speed)]:
        if val != 0:
            sc = "green" if val > 0 else "red"
            stage_parts.append(c(sc, f"{label}{val:+d}"))
    if stage_parts:
        stat_line2 += f"  {dim('stages:')} {' '.join(stage_parts)}"

    lines.append(stat_line1)
    lines.append(stat_line2)

    lines.append(f"  {dim('Moves:')}")
    for m in v.moves:
        tc = TYPE_COLORS.get(m.type.value, "white")
        pp_pct = m.pp_current / m.pp if m.pp > 0 else 0
        pp_c = "green" if pp_pct > 0.5 else "yellow" if pp_pct > 0 else "red"
        icon = "💥" if m.category == types.MoveCategoryT.PHYSICAL else "✦" if m.category == types.MoveCategoryT.SPECIAL else "◈"
        prio = c("cyan", f" +{m.priority}") if m.priority > 0 else ""
        lines.append(
            f"    {icon} {m.name:<14} {c(tc, m.type.value.upper()):<10} "
            f"PWR {m.power:<3} PP {c(pp_c, str(m.pp_current))}/{m.pp}{prio}"
        )

    volatile = []
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
    if volatile:
        lines.append(f"  {c('red', '⚡ ' + ' | '.join(volatile))}")

    return lines


def print_matchup(battle: schema.BattleState):
    ta = battle.trainer_a
    tb = battle.trainer_b
    va = ta.active_vibemon
    vb = tb.active_vibemon

    left_lines = _build_vibemon_lines(va, ta.name, "yellow")
    right_lines = _build_vibemon_lines(vb, tb.name, "magenta")

    max_lines = max(len(left_lines), len(right_lines))
    left_lines += [""] * (max_lines - len(left_lines))
    right_lines += [""] * (max_lines - len(right_lines))

    print()
    for i, (left, right) in enumerate(zip(left_lines, right_lines)):
        sep = f"  {dim('⚔')}  " if i == 0 else GAP + " " + GAP
        print(f"  {_pad(left, CARD_W)}{sep}{right}")
    print()


def print_events(events: list[schema.TurnEvent]):
    for event in events:
        desc = event.description or ""

        parts = []
        if event.hp_delta:
            hp_color = "green" if event.hp_delta > 0 else "red"
            parts.append(c(hp_color, f"{event.hp_delta:+d} HP"))
        if event.missed:
            parts.append(c("yellow", "MISSED"))
        if event.fainted:
            parts.append(c("red", "FAINTED ✖"))
        if event.stat_stage_changes:
            for stat, delta in event.stat_stage_changes.items():
                sc = "green" if delta > 0 else "red"
                parts.append(c(sc, f"{stat} {delta:+d}"))

        suffix = f"  [{', '.join(parts)}]" if parts else ""
        print(f"    {dim('›')} {bold(event.actor)}: {desc}{suffix}")


def create_pikachu():
    return schema.BattleVibemon(
        name="Pikachu",
        type_list=[types.VibemonTypeT.ELECTRIC],
        base_hp=111,
        base_attack=55,
        base_defense=40,
        base_sp_attack=50,
        base_sp_defense=50,
        base_speed=90,
        moves=[
            types.Move(
                name="Thunderbolt",
                type=types.VibemonTypeT.ELECTRIC,
                category=types.MoveCategoryT.SPECIAL,
                power=90,
                accuracy=1.0,
                pp=15,
                pp_current=15,
            ),
            types.Move(
                name="Quick Attack",
                type=types.VibemonTypeT.NORMAL,
                category=types.MoveCategoryT.PHYSICAL,
                power=40,
                accuracy=1.0,
                priority=1,
                pp=30,
                pp_current=30,
            ),
        ],
    )


def create_charizard():
    return schema.BattleVibemon(
        name="Charizard",
        type_list=[types.VibemonTypeT.FIRE, types.VibemonTypeT.FLYING],
        base_hp=148,
        base_attack=84,
        base_defense=78,
        base_sp_attack=109,
        base_sp_defense=85,
        base_speed=100,
        moves=[
            types.Move(
                name="Flamethrower",
                type=types.VibemonTypeT.FIRE,
                category=types.MoveCategoryT.SPECIAL,
                power=90,
                accuracy=1.0,
                pp=15,
                pp_current=15,
            ),
            types.Move(
                name="Ember",
                type=types.VibemonTypeT.FIRE,
                category=types.MoveCategoryT.SPECIAL,
                power=40,
                accuracy=1.0,
                pp=25,
                pp_current=25,
            ),
        ],
    )


def main():
    trainer_a_id = uuid.uuid4()
    trainer_b_id = uuid.uuid4()

    engine = game_engine.GameEngine(
        trainer_a=schema.Trainer(
            id=trainer_a_id,
            name="Red",
            team=[create_pikachu()],
        ),
        trainer_b=schema.Trainer(
            id=trainer_b_id,
            name="Blue",
            team=[create_charizard()],
        ),
    )

    action_a = types.Action(
        trainer_name=trainer_a_id,
        action_type=types.ActionType.MOVE,
        value="Thunderbolt",
    )
    action_b = types.Action(
        trainer_name=trainer_b_id,
        action_type=types.ActionType.MOVE,
        value="Flamethrower",
    )

    header("⚔  BATTLE START  ⚔")
    print_matchup(engine.battle)

    turn_count = 0
    while not engine.battle.is_over and turn_count < 10:
        turn_count += 1
        events = engine.submit(action_a, action_b)

        header(f"TURN {turn_count}")

        section("Actions")
        print(f"    {c('yellow', 'Red')}:  {action_a.value}")
        print(f"    {c('magenta', 'Blue')}: {action_b.value}")

        section("Events")
        print_events(events)

        section("State")
        print_matchup(engine.battle)

    header("🏆  BATTLE RESULT  🏆")
    if engine.battle.winner:
        print(f"\n  {c('green', bold('Winner'))}: {bold(engine.battle.winner.name)}!\n")
    print_matchup(engine.battle)

    section("Turn History")
    for record in engine.battle.turn_history:
        print(f"\n    {bold(f'Turn {record.turn_number}')}")
        print_events(record.events)

    section("Raw JSON")
    print(json.dumps(engine.battle.to_json(), indent=2, default=str))


if __name__ == "__main__":
    main()
