# ── Status Chance Constants ───────────────────────────────────────────────────────────

FREEZE_THAW_CHANCE = 0.2
"""Chance per turn for a frozen Pokémon to thaw. 20% in Gen VI+."""

PARALYSIS_FULLY_PARALYZED_CHANCE = 0.25
"""Chance per turn for a paralyzed Pokémon to be fully paralyzed and skip its turn."""

CONFUSION_SELF_HIT_CHANCE = 0.33
"""Chance per turn for a confused Pokémon to hurt itself instead of acting."""


# ── Status Damage Constants ───────────────────────────────────────────────────────────

BURN_DAMAGE_DIVISOR = 16
"""Burn deals 1/16 of max HP per turn."""

POISON_DAMAGE_DIVISOR = 8
"""Regular poison deals 1/8 of max HP per turn.

Badly poison scales linearly: damage = (turns * max_hp) / 16
"""

CONFUSION_SELF_HIT_DIVISOR = 4
"""Confusion self-hit deals 1/4 of max HP."""


# ── Critical Hit Constants ────────────────────────────────────────────────────────────

CRIT_THRESHOLDS = [1 / 24, 1 / 8, 1 / 2, 1.0]
"""Critical hit probability thresholds by stage.

Index: effective_stage = min(crit_stage + move_crit_ratio, 3)
- Stage 0: 1/24 (~4.2%)
- Stage 1: 1/8 (12.5%)
- Stage 2: 1/2 (50%)
- Stage 3: Always crit (100%)
"""


# ── Stat Stage Constants ──────────────────────────────────────────────────────────────

STAT_STAGE_MIN = -6
"""Minimum stat stage."""


STAT_STAGE_MAX = 6
"""Maximum stat stage."""


STAT_ACCURACY_DIVISOR = 3
"""Base for accuracy/evasion stat stage formulas. Multiplier = (3 + stage) / 3 when positive."""


# ── Damage Formula Constants ──────────────────────────────────────────────────────────

DAMAGE_RANDOM_MIN = 0.85
"""Minimum random damage multiplier."""

DAMAGE_RANDOM_MAX = 1.0
"""Maximum random damage multiplier."""

STAB_MULTIPLIER = 1.5
"""Same-type attack bonus multiplier when move type matches Pokémon type."""

BURN_PHYSICAL_REDUCTION = 0.5
"""Burn reduces physical move damage by 50%."""

CRITICAL_HIT_MULTIPLIER = 1.5
"""Critical hit multiplies final damage by 1.5x."""

DAMAGE_DIVISOR = 50
"""Divisor in damage formula."""

DAMAGE_BASE_ADDEND = 2
"""Additive constant at end of damage formula."""


# ── Level Scaling Constants ───────────────────────────────────────────────────────────

MAX_LEVEL = 100
"""Maximum level for Vibemon."""


# ── Move Constants ────────────────────────────────────────────────────────────────────

PP_DEFAULT = 10
"""Default PP (Power Points) for a move."""

STARTING_MOVE_COUNT = 2
"""The minimum number of moves a Vibemon will start off with."""


# ── Miscellaneous ─────────────────────────────────────────────────────────────────────

RADIANT_ODDS = 4096
"""A rare, alternative style that differs from its peer identities' appearance."""
