# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../../../../../vibemon/backend", editable = true }
# ///

"""Audit a provider move catalog against move-generator Step B2.5 balance gates."""

import argparse
import sys
from collections import Counter
from statistics import mean, median, stdev

from app.domains.move.entity import Move, Recoil, StatChange, StatusInflict
from app.domains.move.types import MoveCategoryT, StatusConditionT, VibemonTypeT

from discover import discover_provider_names, load_provider_moves

TIERS: tuple[tuple[str, int, int, float], ...] = (
    ("spam", 0, 34, 0.075),
    ("early-stab", 35, 64, 0.175),
    ("mid", 65, 79, 0.275),
    ("workhorse", 80, 99, 0.275),
    ("high", 100, 119, 0.125),
    ("signature", 120, 999, 0.050),
)

STRONG_STATUS = {
    StatusConditionT.BURN,
    StatusConditionT.PARALYSIS,
    StatusConditionT.FREEZE,
    StatusConditionT.SLEEP,
    StatusConditionT.POISON,
    StatusConditionT.BAD_POISON,
}

DEFAULT_CAP_BY_SIZE: tuple[tuple[int, int], ...] = (
    (120, 100),
    (999, 300),
)


def default_cap(move_count: int) -> int:
    for threshold, cap in DEFAULT_CAP_BY_SIZE:
        if move_count <= threshold:
            return cap
    return 300


def tier_of(power: int) -> str:
    for label, lo, hi, _ in TIERS:
        if lo <= power <= hi:
            return label
    return "spam"


def flat_effects(move: Move) -> list[tuple[object, object]]:
    return [(group, effect) for group in move.effects for effect in group.effects]


def is_self_drawback(effect: object) -> bool:
    return (
        isinstance(effect, StatChange)
        and effect.target == "self"
        and any(delta < 0 for delta in effect.changes.values())
    )


def has_visible_drawback(move: Move) -> bool:
    if move.accuracy is not None and move.accuracy < 0.9:
        return True
    if move.pp <= 5:
        return True
    return any(isinstance(effect, Recoil) or is_self_drawback(effect) for _group, effect in flat_effects(move))


def has_damaging_rider(move: Move) -> bool:
    if move.category == MoveCategoryT.STATUS:
        return False
    for _group, effect in flat_effects(move):
        if isinstance(effect, Recoil) or is_self_drawback(effect):
            continue
        return True
    return False


def anti_pattern_flags(move: Move) -> list[str]:
    flags: list[str] = []
    power = move.power
    accuracy = move.accuracy
    pp = move.pp
    is_status = move.category == MoveCategoryT.STATUS

    if power is not None:
        if power >= 100 and accuracy == 1.0 and pp >= 15:
            flags.append("power>=100 with acc=1.0 and pp>=15")
        if power >= 120 and accuracy == 1.0 and pp > 5 and not has_visible_drawback(move):
            flags.append("power>=120 with no visible drawback")
        if power < 60 and accuracy is not None and accuracy < 1.0:
            flags.append("sub-60 power with acc<1.0")
        if pp == 5 and power < 90 and not move.effects:
            flags.append("5 PP on sub-90 power with no effect")
        for group, effect in flat_effects(move):
            if (
                isinstance(effect, StatusInflict)
                and effect.target != "self"
                and group.chance >= 0.30
                and effect.status in STRONG_STATUS
                and power >= 100
            ):
                flags.append("power>=100 with >=30% strong-status proc")

    for _group, effect in flat_effects(move):
        if (
            is_status
            and accuracy == 1.0
            and isinstance(effect, StatusInflict)
            and effect.status in {StatusConditionT.SLEEP, StatusConditionT.FREEZE}
        ):
            flags.append("STATUS sleep/freeze with acc=1.0")

    if move.priority >= 1 and power is not None and power >= 80 and not has_visible_drawback(move):
        flags.append("priority>=1 on power>=80 without drawback")
    if move.priority >= 3 and not is_status:
        flags.append("priority>=3 on damaging move")
    return flags


def early_accuracy_evasion_violations(moves: tuple[Move, ...]) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for move in moves:
        if move.level_requirement >= 15:
            continue
        for _group, effect in flat_effects(move):
            if not isinstance(effect, StatChange):
                continue
            for stat, delta in effect.changes.items():
                if stat == "evasion" and delta > 0:
                    violations.append((move.name, f"raises evasion ({delta:+}) below level 15"))
                if effect.target != "self" and stat == "accuracy" and delta < 0:
                    violations.append((move.name, f"lowers target accuracy ({delta:+}) below level 15"))
    return violations


def audit_moves(moves: tuple[Move, ...], *, provider: str, cap: int) -> int:
    failures: list[str] = []

    n = len(moves)
    damaging = [move for move in moves if move.category != MoveCategoryT.STATUS]
    d = len(damaging)
    powers = [move.power for move in damaging if move.power is not None]
    levels = [move.level_requirement for move in moves]

    l1 = sum(1 for level in levels if level == 1)
    l1_target = round(0.7 * n)
    l1_drift = abs(l1 / n - 0.7) if n else 0.0

    riders = sum(1 for move in damaging if has_damaging_rider(move))
    rider_target = round(0.3 * d) if d else 0

    pri_elevated = sum(1 for move in moves if move.priority >= 1)
    pri_cap = round(0.07 * n)

    sure_hit = sum(1 for move in moves if move.accuracy is None)
    sure_hit_cap = round(0.05 * n)

    batch_l1_ratio = l1 / n if n else 0.0
    type_l1_rows: list[tuple[str, int, int, float, float]] = []
    for element in VibemonTypeT:
        type_moves = [move for move in moves if move.type == element]
        if not type_moves:
            continue
        type_l1 = sum(1 for move in type_moves if move.level_requirement == 1)
        ratio = type_l1 / len(type_moves)
        type_l1_rows.append((element.value, type_l1, len(type_moves), ratio, ratio - batch_l1_ratio))

    type_l1_violations = [row for row in type_l1_rows if abs(row[4]) > 0.15]
    type_l1_lo = min((row[3] for row in type_l1_rows), default=0.0)
    type_l1_hi = max((row[3] for row in type_l1_rows), default=0.0)

    tier_counts = Counter(tier_of(power) for power in powers)
    capstone = any(power >= 120 for power in powers)

    print(f"=== {provider.upper()} MOVE BALANCE AUDIT ===")
    print("Batch summary")
    print(f"  N: {n}      L1 count: {l1} / {n}      target: {l1_target}, tolerance +/-5pp")
    print(f"  Damaging: {d}   riders: {riders} / {d}        target: {rider_target}")
    print(
        f"  Power tiers: spam={tier_counts.get('spam', 0)}  "
        f"early={tier_counts.get('early-stab', 0)}  "
        f"mid={tier_counts.get('mid', 0)}  "
        f"workhorse={tier_counts.get('workhorse', 0)}  "
        f"high={tier_counts.get('high', 0)}  "
        f"signature={tier_counts.get('signature', 0)}"
    )
    print(f"  Priority elevated (>=1): {pri_elevated} / {n}        cap: {pri_cap}")
    print(f"  Per-type L1 share min/max: {type_l1_lo * 100:.1f}% / {type_l1_hi * 100:.1f}%")
    print()
    print("HARD GATES (Step B2.5)")

    ok = n <= cap
    if not ok:
        failures.append("batch-size")
    print(f"  [{'PASS' if ok else 'FAIL'}] Batch size: N={n} (cap {cap})")

    ok = l1_drift <= 0.05
    if not ok:
        failures.append("l1-ratio")
    print(f"  [{'PASS' if ok else 'FAIL'}] L1 ratio: |{l1}/{n} - 0.7| = {l1_drift:.3f} (<= 0.05)")

    ok = not type_l1_violations
    if not ok:
        failures.append("per-type-l1")
    print(f"  [{'PASS' if ok else 'FAIL'}] Per-type L1 +/-15pp: {len(type_l1_violations)} violation(s)")
    for tname, type_l1, total, ratio, diff in type_l1_violations:
        print(f"        {tname:<10} {type_l1}/{total} = {ratio * 100:.1f}% (diff {diff:+.3f})")

    if d:
        tier_floor_fail: list[str] = []
        tier_ceiling_fail: list[str] = []
        for label, _lo, _hi, share in TIERS:
            count = tier_counts.get(label, 0)
            target = share * d
            floor = 0.5 * target
            if count < floor:
                tier_floor_fail.append(f"{label} ({count} < floor {floor:.1f})")
            if count / d > 0.40:
                tier_ceiling_fail.append(f"{label} ({count}/{d} = {count / d * 100:.1f}% > 40%)")
        ok = not tier_floor_fail and not tier_ceiling_fail
        if not ok:
            failures.append("power-band")
        print(f"  [{'PASS' if ok else 'FAIL'}] Power-band floors/ceiling")
        for detail in tier_floor_fail + tier_ceiling_fail:
            print(f"        {detail}")

        capstone_required = n >= 20 and d >= 10
        ok = capstone or not capstone_required
        if not ok:
            failures.append("capstone")
        print(f"  [{'PASS' if ok else 'FAIL'}] Capstone (>=1 move at power >=120)")

        ok = abs(riders - rider_target) <= 1
        if not ok:
            failures.append("rider-budget")
        print(f"  [{'PASS' if ok else 'FAIL'}] Damaging rider ratio: {riders}/{d} (target {rider_target} +/-1)")

        l1_damaging = [move for move in damaging if move.level_requirement == 1 and move.power is not None]
        l1_high = [move for move in l1_damaging if move.power is not None and move.power > 55]
        l1_strong = [move for move in l1_damaging if move.power is not None and 50 <= move.power <= 55]
        l1_strong_ratio = len(l1_strong) / len(l1_damaging) if l1_damaging else 0.0
        ok = not l1_high and l1_strong_ratio <= 0.20
        if not ok:
            failures.append("l1-power")
        print(
            f"  [{'PASS' if ok else 'FAIL'}] L1 damaging power: >55={len(l1_high)}, "
            f"50-55={len(l1_strong)}/{len(l1_damaging)} ({l1_strong_ratio * 100:.1f}%, cap 20%)"
        )

    ok = pri_elevated <= pri_cap
    if not ok:
        failures.append("priority-budget")
    print(f"  [{'PASS' if ok else 'FAIL'}] Priority budget: {pri_elevated} elevated (cap {pri_cap})")

    pri_counts = Counter(move.priority for move in moves)
    p1 = pri_counts.get(1, 0)
    p2 = pri_counts.get(2, 0)
    p3plus_dmg = sum(1 for move in moves if move.priority >= 3 and move.category != MoveCategoryT.STATUS)
    sparsity_violations: list[str] = []
    if p1 > round(0.05 * n):
        sparsity_violations.append(f"+1 count {p1} > 5% cap ({round(0.05 * n)})")
    if p2 > max(round(0.015 * n), 0):
        sparsity_violations.append(f"+2 count {p2} > 1.5% cap ({round(0.015 * n)})")
    if p3plus_dmg > 0:
        sparsity_violations.append(f"{p3plus_dmg} damaging move(s) at priority >=3")
    ok = not sparsity_violations
    if not ok:
        failures.append("priority-sparsity")
    print(f"  [{'PASS' if ok else 'FAIL'}] Priority sparsity ladder")
    for detail in sparsity_violations:
        print(f"        {detail}")

    ok = sure_hit <= sure_hit_cap
    if not ok:
        failures.append("sure-hit")
    print(f"  [{'PASS' if ok else 'FAIL'}] Sure-hit budget: {sure_hit}/{n} (cap {sure_hit_cap})")

    early_acc_evasion = early_accuracy_evasion_violations(moves)
    ok = not early_acc_evasion
    if not ok:
        failures.append("early-accuracy-evasion")
    print(f"  [{'PASS' if ok else 'FAIL'}] Early accuracy/evasion guard: {len(early_acc_evasion)} violation(s)")

    flagged = [(move.name, anti_pattern_flags(move)) for move in moves]
    flagged = [(name, flags) for name, flags in flagged if flags]
    ok = not flagged
    if not ok:
        failures.append("anti-patterns")
    print(f"  [{'PASS' if ok else 'FAIL'}] S12 anti-patterns: {len(flagged)} move(s) flagged")
    for name, flags in flagged:
        for flag in flags:
            print(f"        {name}: {flag}")

    print()
    print("DETAIL - TYPE DISTRIBUTION")
    type_counts = Counter(move.type for move in moves)
    for element in VibemonTypeT:
        count = type_counts.get(element, 0)
        if count:
            print(f"  {element.value:<12} {count:>3}  {count / n * 100:.1f}%")

    print()
    print("DETAIL - LEVEL BANDS")
    for lo, hi in [(1, 1), (2, 20), (21, 40), (41, 55), (56, 80), (81, 100)]:
        count = sum(1 for level in levels if lo <= level <= hi)
        label = "L1 only" if lo == hi == 1 else f"{lo:>3}-{hi:<3}"
        print(f"  {label:<10} {count:>3}  {count / n * 100:.1f}%")

    print()
    print("DETAIL - CATEGORY MIX (damaging)")
    category_counts = Counter(move.category.value for move in damaging)
    for category, count in sorted(category_counts.items()):
        print(f"  {category:<10} {count:>3}  {count / d * 100:.1f}%")

    if powers:
        print()
        print("DETAIL - POWER")
        print(f"  Min / Mean / Median / Max: {min(powers)} / {mean(powers):.1f} / {median(powers)} / {max(powers)}")
        if len(powers) > 1:
            print(f"  Stdev: {stdev(powers):.1f}")
        for label, lo, hi, share in TIERS:
            count = tier_counts.get(label, 0)
            target = share * d
            print(
                f"  {label:<11} ({lo:>3}-{hi:<3}) {count:>3} {count / d * 100:>5.1f}%  "
                f"target~{target:.1f}  floor>={0.5 * target:.1f}"
            )

    print()
    print("DETAIL - PER-TYPE RIDERS (damaging)")
    for element in VibemonTypeT:
        type_moves = [move for move in damaging if move.type == element]
        if not type_moves:
            continue
        type_riders = sum(1 for move in type_moves if has_damaging_rider(move))
        print(f"  {element.value:<12} {type_riders:>2}/{len(type_moves):>2}  ({type_riders / len(type_moves) * 100:.0f}%)")

    chances = [group.chance for move in moves for group in move.effects]
    if chances:
        print()
        print("DETAIL - EFFECT TEXTURE")
        print(f"  Moves with effects: {sum(1 for move in moves if move.effects)} / {n}")
        print(f"  Effect chance min/mean/max: {min(chances):.2f} / {mean(chances):.2f} / {max(chances):.2f}")
        print(f"  Unique chance values: {len(set(chances))}")

    print()
    if failures:
        print(f"VERDICT: FAIL ({len(failures)} hard gate(s)): {', '.join(failures)}")
        return 1
    print("VERDICT: PASS (all hard gates green)")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit provider move catalog balance gates.")
    parser.add_argument(
        "--provider",
        default="climate",
        choices=discover_provider_names(),
        help="Provider whose data/moves.json to audit.",
    )
    parser.add_argument(
        "--cap",
        type=int,
        default=None,
        help="Batch size cap (default: 100 for N<=120 else 300 for accumulated catalogs).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    moves = load_provider_moves(args.provider)
    cap = args.cap if args.cap is not None else default_cap(len(moves))
    return audit_moves(moves, provider=args.provider, cap=cap)


if __name__ == "__main__":
    sys.exit(main())
