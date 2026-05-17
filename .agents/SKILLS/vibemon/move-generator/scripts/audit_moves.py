# /// script
# requires-python = ">=3.12"
# dependencies = ["vibemon-backend"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../../../../../backend", editable = true }
# ///

"""Audit Vibemon moves data against the move-generator balance gates.

Emits the Step A7 batch summary block, runs every Step B2.5 HARD gate, and
exits non-zero if any HARD gate fails. Intended as deterministic feedback for
move-generator agents.

Usage:
    uv run .agents/SKILLS/vibemon/move-generator/scripts/audit_moves.py [provider]

Example:
    uv run .agents/SKILLS/vibemon/move-generator/scripts/audit_moves.py climate
"""

import argparse
import sys
from collections import Counter
from importlib import import_module
from statistics import mean, median, stdev

from app import types
from app import schema
from app.schema import Move


# ── Tier definitions (§3.5) ────────────────────────────────────────────────────
# Lower-bound-dominant boundaries to eliminate overlap from the reference table.
# Reference: spam 10-30, early-stab 35-55, mid 65-80, workhorse 80-100,
# high 100-120, signature 120+. Boundaries assigned to the higher tier.
TIERS: tuple[tuple[str, int, int, float], ...] = (
    # (label, lo, hi_inclusive, target_share_of_D)
    ("spam", 0, 34, 0.075),  # 5-10%, midpoint 7.5%
    ("early-stab", 35, 64, 0.175),  # 15-20%, midpoint 17.5%
    ("mid", 65, 79, 0.275),  # 25-30%, midpoint 27.5%
    ("workhorse", 80, 99, 0.275),  # 25-30%, midpoint 27.5%
    ("high", 100, 119, 0.125),  # 10-15%, midpoint 12.5%
    ("signature", 120, 999, 0.050),  # 3-7%, midpoint 5%
)

STRONG_STATUS = {
    types.StatusConditionT.BURN,
    types.StatusConditionT.PARALYSIS,
    types.StatusConditionT.FREEZE,
    types.StatusConditionT.SLEEP,
    types.StatusConditionT.POISON,
    types.StatusConditionT.BAD_POISON,
}


def load_moves(provider: str) -> tuple[Move, ...]:
    moves_mod = import_module(f"app.plugins.{provider}.moves")
    return moves_mod.MOVES


def tier_of(power: int) -> str:
    for label, lo, hi, _ in TIERS:
        if lo <= power <= hi:
            return label
    return "spam"


def move_effect_groups(m: Move) -> tuple[schema.EffectGroup, ...]:
    return tuple(m.effects)


def flat_effects(m: Move) -> list[tuple[schema.EffectGroup, schema.Effect]]:
    return [(group, effect) for group in move_effect_groups(m) for effect in group.effects]


def is_self_drawback(effect: schema.Effect) -> bool:
    return (
        isinstance(effect, schema.StatChange)
        and effect.target == "self"
        and any(delta < 0 for delta in effect.changes.values())
    )


def has_visible_drawback(m: Move) -> bool:
    if m.accuracy is not None and m.accuracy < 0.9:
        return True
    if m.pp <= 5:
        return True
    return any(isinstance(effect, schema.Recoil) or is_self_drawback(effect) for _group, effect in flat_effects(m))


def has_damaging_rider(m: Move) -> bool:
    if m.category == types.MoveCategoryT.STATUS:
        return False
    for _group, effect in flat_effects(m):
        if isinstance(effect, schema.Recoil) or is_self_drawback(effect):
            continue
        return True
    return False


def level_power_cap(level: int) -> tuple[int, int]:
    if level == 1:
        return (45, 55)
    if 2 <= level <= 15:
        return (55, 60)
    if 16 <= level <= 35:
        return (75, 80)
    if 36 <= level <= 55:
        return (95, 100)
    if 56 <= level <= 80:
        return (110, 120)
    return (120, 150)


def fmt_check(passed: bool, hard: bool = True) -> str:
    if passed:
        return "PASS"
    return "FAIL" if hard else "WARN"


def anti_pattern_flags(m: Move) -> list[str]:
    """Per-move §12 anti-pattern flags (auto-detectable subset)."""
    flags: list[str] = []
    p = m.power
    a = m.accuracy
    pp = m.pp
    effects = flat_effects(m)

    is_status_cat = m.category == types.MoveCategoryT.STATUS

    if p is not None:
        if p >= 100 and a == 1.0 and pp >= 15:
            flags.append("§12: power≥100 ∧ acc=1.0 ∧ pp≥15 (too strong on every dial)")
        if p >= 120 and a == 1.0 and pp > 5 and not has_visible_drawback(m):
            flags.append("§12: power≥120 with no visible drawback (acc/pp/self-debuff)")
        if p < 60 and a is not None and a < 1.0:
            flags.append("§12: sub-60 power with acc<1.0 (no flavor reason to miss)")
        if pp == 5 and p < 90 and not effects:
            flags.append("§12: 5 PP on sub-90 power with no heavy effect")
        for group, effect in effects:
            if (
                isinstance(effect, schema.StatusInflict)
                and effect.target != "self"
                and group.chance >= 0.30
                and effect.status in STRONG_STATUS
                and p >= 100
            ):
                flags.append("§12: power≥100 with ≥30% strong-status proc")

    for _group, effect in effects:
        if (
            is_status_cat
            and a == 1.0
            and isinstance(effect, schema.StatusInflict)
            and effect.status in {types.StatusConditionT.SLEEP, types.StatusConditionT.FREEZE}
        ):
            flags.append("§12: STATUS sleep/freeze with acc=1.0 (must trade accuracy)")

        if isinstance(effect, schema.StatChange) and effect.target != "self" and not is_status_cat:
            for stat, delta in effect.changes.items():
                if abs(delta) >= 2:
                    flags.append(f"§12: +{delta} {stat} on damaging move with no self-cost")
                    break

    if p is not None:
        normal_cap, rare_cap = level_power_cap(m.level_requirement)
        if p > rare_cap:
            flags.append(f"§12: level {m.level_requirement} power {p} exceeds rare cap {rare_cap}")
        elif p > normal_cap and not has_visible_drawback(m):
            flags.append(f"§12: level {m.level_requirement} power {p} exceeds normal cap {normal_cap} without drawback")

    if m.priority >= 1 and p is not None and p >= 80:
        flags.append("§12: priority≥1 on power≥80 without obvious drawback")
    if m.priority >= 3 and not is_status_cat:
        flags.append("§12: priority≥3 on damaging move")

    return flags


def early_accuracy_evasion_violations(moves: tuple[Move, ...]) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for m in moves:
        if m.level_requirement >= 15:
            continue
        for _group, effect in flat_effects(m):
            if not isinstance(effect, schema.StatChange):
                continue
            for stat, delta in effect.changes.items():
                if stat == "evasion" and delta > 0:
                    violations.append((m.name, f"raises evasion ({delta:+}) below level 15"))
                if effect.target != "self" and stat == "accuracy" and delta < 0:
                    violations.append((m.name, f"lowers target accuracy ({delta:+}) below level 15"))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile and gate Vibemon moves data")
    parser.add_argument("provider", nargs="?", default="climate")
    parser.add_argument(
        "--cap",
        type=int,
        default=100,
        help=(
            "Per-batch size cap (Step B2.5). Raise when auditing an accumulated "
            "multi-batch provider whose MOVES tuple aggregates several generation "
            "runs. Quota gates (L1, rider, power-band) remain proportional and "
            "stay accurate at higher N."
        ),
    )
    args = parser.parse_args()

    moves = load_moves(args.provider)
    failures: list[str] = []

    N = len(moves)
    damaging = [m for m in moves if m.category != types.MoveCategoryT.STATUS]
    D = len(damaging)
    powers = [m.power for m in damaging if m.power is not None]
    levels = [m.level_requirement for m in moves]

    l1 = sum(1 for l in levels if l == 1)
    l1_target = round(0.7 * N)
    l1_drift = abs(l1 / N - 0.7) if N else 0.0

    riders = sum(1 for m in damaging if has_damaging_rider(m))
    rider_target = round(0.3 * D) if D else 0

    pri_elevated = sum(1 for m in moves if m.priority >= 1)
    pri_cap = round(0.07 * N)

    sure_hit = sum(1 for m in moves if m.accuracy is None)
    sure_hit_cap = round(0.05 * N)

    # ── Per-type L1 share ────────────────────────────────────────────────
    batch_l1_ratio = l1 / N if N else 0.0
    type_l1_rows: list[tuple[str, int, int, float, float]] = []
    for t in types.VibemonTypeT:
        type_moves = [m for m in moves if m.type == t]
        if not type_moves:
            continue
        t_l1 = sum(1 for m in type_moves if m.level_requirement == 1)
        ratio = t_l1 / len(type_moves)
        type_l1_rows.append((t.value, t_l1, len(type_moves), ratio, ratio - batch_l1_ratio))

    type_l1_violations = [r for r in type_l1_rows if abs(r[4]) > 0.15]
    type_l1_lo = min((r[3] for r in type_l1_rows), default=0.0)
    type_l1_hi = max((r[3] for r in type_l1_rows), default=0.0)

    # ── Power-tier counts (§3.5) ─────────────────────────────────────────
    tier_counts = Counter(tier_of(p) for p in powers)
    capstone = any(p >= 120 for p in powers)

    # ── A7 batch summary block ───────────────────────────────────────────
    print("Batch summary")
    print(f"  N: {N}      L1 count: {l1} / {N}      target: {l1_target}, tolerance ±5pp")
    print(f"  Damaging: {D}   riders: {riders} / {D}        target: {rider_target}")
    print(
        f"  Power tiers: spam={tier_counts.get('spam', 0)}  "
        f"early={tier_counts.get('early-stab', 0)}  "
        f"mid={tier_counts.get('mid', 0)}  "
        f"workhorse={tier_counts.get('workhorse', 0)}  "
        f"high={tier_counts.get('high', 0)}  "
        f"signature={tier_counts.get('signature', 0)}"
    )
    print(f"  Priority elevated (≥1): {pri_elevated} / {N}        cap: {pri_cap}")
    if type_l1_rows:
        print(
            f"  Per-type L1 share min/max: {type_l1_lo * 100:.1f}% / {type_l1_hi * 100:.1f}% (must be within ±15pp of batch ratio)"
        )
    print()

    # ── HARD gates (Step B2.5) ───────────────────────────────────────────
    print("HARD GATES (Step B2.5)")

    ok = N <= args.cap
    if not ok:
        failures.append("batch-size")
    print(f"  [{fmt_check(ok)}] Batch size: N={N} (cap {args.cap})")

    ok = l1_drift <= 0.05
    if not ok:
        failures.append("l1-ratio")
    print(f"  [{fmt_check(ok)}] L1 ratio: |{l1}/{N} - 0.7| = {l1_drift:.3f} (≤ 0.05)")

    ok = not type_l1_violations
    if not ok:
        failures.append("per-type-l1")
    print(f"  [{fmt_check(ok)}] Per-type L1 ±15pp: {len(type_l1_violations)} violation(s)")
    for tname, t_l1, t_total, ratio, diff in type_l1_violations:
        print(f"        {tname:<10} {t_l1}/{t_total} = {ratio * 100:.1f}% (diff {diff:+.3f})")

    if D:
        tier_floor_fail: list[str] = []
        tier_ceiling_fail: list[str] = []
        for label, _lo, _hi, share in TIERS:
            cnt = tier_counts.get(label, 0)
            target = share * D
            floor = 0.5 * target
            if cnt < floor:
                tier_floor_fail.append(f"{label} ({cnt} < floor {floor:.1f})")
            if cnt / D > 0.40:
                tier_ceiling_fail.append(f"{label} ({cnt}/{D} = {cnt / D * 100:.1f}% > 40%)")
        ok = not tier_floor_fail and not tier_ceiling_fail
        if not ok:
            failures.append("power-band")
        print(f"  [{fmt_check(ok)}] Power-band §3.5 floors/ceiling")
        for f in tier_floor_fail:
            print(f"        floor: {f}")
        for f in tier_ceiling_fail:
            print(f"        ceiling: {f}")

        capstone_required = N >= 20 and D >= 10
        ok = capstone or not capstone_required
        if not ok:
            failures.append("capstone")
        print(f"  [{fmt_check(ok)}] Capstone (≥1 move at power ≥120 when N≥20 and D≥10)")

        ok = abs(riders - rider_target) <= 1
        if not ok:
            failures.append("rider-budget")
        print(f"  [{fmt_check(ok)}] Damaging rider ratio: {riders}/{D} (target {rider_target} ±1)")

        l1_damaging = [m for m in damaging if m.level_requirement == 1 and m.power is not None]
        l1_high = [m for m in l1_damaging if m.power is not None and m.power > 55]
        l1_strong = [m for m in l1_damaging if m.power is not None and 50 <= m.power <= 55]
        l1_strong_ratio = len(l1_strong) / len(l1_damaging) if l1_damaging else 0.0
        ok = not l1_high and l1_strong_ratio <= 0.20
        if not ok:
            failures.append("l1-power")
        print(
            f"  [{fmt_check(ok)}] L1 damaging power: >55={len(l1_high)}, "
            f"50-55={len(l1_strong)}/{len(l1_damaging)} ({l1_strong_ratio * 100:.1f}%, cap 20%)"
        )
        for m in l1_high:
            print(f"        {m.name}: L1 power {m.power} > 55")

    ok = pri_elevated <= pri_cap
    if not ok:
        failures.append("priority-budget")
    print(f"  [{fmt_check(ok)}] Priority budget: {pri_elevated} elevated (cap {pri_cap})")

    pri_counts = Counter(m.priority for m in moves)
    p1 = pri_counts.get(1, 0)
    p2 = pri_counts.get(2, 0)
    p3plus_dmg = sum(1 for m in moves if m.priority >= 3 and m.category != types.MoveCategoryT.STATUS)
    sparsity_violations: list[str] = []
    if p1 > round(0.05 * N):
        sparsity_violations.append(f"+1 count {p1} > 5% cap ({round(0.05 * N)})")
    if p2 > max(round(0.015 * N), 0):
        sparsity_violations.append(f"+2 count {p2} > 1.5% cap ({round(0.015 * N)})")
    if p3plus_dmg > 0:
        sparsity_violations.append(f"{p3plus_dmg} damaging move(s) at priority ≥3")
    ok = not sparsity_violations
    if not ok:
        failures.append("priority-sparsity")
    print(f"  [{fmt_check(ok)}] Priority §3.6 sparsity ladder")
    for v in sparsity_violations:
        print(f"        {v}")

    ok = sure_hit <= sure_hit_cap
    if not ok:
        failures.append("sure-hit")
    print(f"  [{fmt_check(ok)}] Sure-hit budget: {sure_hit}/{N} (cap {sure_hit_cap})")

    early_acc_evasion = early_accuracy_evasion_violations(moves)
    ok = not early_acc_evasion
    if not ok:
        failures.append("early-accuracy-evasion")
    print(f"  [{fmt_check(ok)}] Early accuracy/evasion guard: {len(early_acc_evasion)} violation(s)")
    for name, reason in early_acc_evasion:
        print(f"        {name}: {reason}")

    flagged = [(m.name, anti_pattern_flags(m)) for m in moves]
    flagged = [(n, fl) for n, fl in flagged if fl]
    ok = not flagged
    if not ok:
        failures.append("anti-patterns")
    print(f"  [{fmt_check(ok)}] §12 anti-patterns: {len(flagged)} move(s) flagged")
    for name, fl in flagged:
        for f in fl:
            print(f"        {name}: {f}")

    print()

    # ── Detail tables (informational) ────────────────────────────────────
    print("DETAIL — TYPE DISTRIBUTION")
    type_counts = Counter(m.type for m in moves)
    for t in types.VibemonTypeT:
        c = type_counts.get(t, 0)
        if c:
            print(f"  {t.value:<12} {c:>3}  {c / N * 100:.1f}%")
    print()

    print("DETAIL — LEVEL BANDS")
    for lo, hi in [(1, 1), (2, 20), (21, 40), (41, 55), (56, 80), (81, 100)]:
        cnt = sum(1 for l in levels if lo <= l <= hi)
        label = "L1 only" if lo == hi == 1 else f"{lo:>3}-{hi:<3}"
        print(f"  {label:<10}  {cnt:>3}  {cnt / N * 100:.1f}%")
    print()

    if powers:
        print("DETAIL — POWER")
        print(f"  Min / Mean / Median / Max:  {min(powers)} / {mean(powers):.1f} / {median(powers)} / {max(powers)}")
        if len(powers) > 1:
            print(f"  Stdev: {stdev(powers):.1f}")
        for label, lo, hi, share in TIERS:
            cnt = tier_counts.get(label, 0)
            target = share * D
            print(
                f"  {label:<11} ({lo:>3}-{hi:<3})  {cnt:>3}  {cnt / D * 100:.1f}%  target≈{target:.1f}  floor≥{0.5 * target:.1f}"
            )
        print()

    chances = [group.chance for m in moves for group in move_effect_groups(m)]
    if chances:
        print("DETAIL — EFFECT TEXTURE")
        print(f"  Moves with effect: {len(chances)} / {N}")
        print(f"  Effect chance — Min / Mean / Max: {min(chances):.2f} / {mean(chances):.2f} / {max(chances):.2f}")
        if len(set(chances)) == 1:
            print("  WARN: all effects share a single chance value (no texture variance)")
        print()

    # ── Verdict ──────────────────────────────────────────────────────────
    if failures:
        print(f"VERDICT: FAIL ({len(failures)} hard gate(s)): {', '.join(failures)}")
        return 1
    print("VERDICT: PASS (all hard gates green)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
