---
name: balance
description: >
  Governs every numeric dial in Vibemon — type effectiveness, stat boundaries,
  damage formula, status mechanics, move assignment weighting, tier classification,
  and role distribution. Load this skill when making decisions about type matchups,
  stat generation, move balance, or any numeric aspect of the battle system.
metadata:
  version: 1.0.0
---

# Vibemon Balance Reference

## 1. Type System

18 elemental types defined in `backend/app/types.py:VibemonTypeT`:

```
NORMAL  FIRE    WATER   ELECTRIC  GRASS  ICE
FIGHTING POISON GROUND  FLYING    PSYCHIC BUG
ROCK    GHOST   DRAGON  DARK      STEEL  FAIRY
```

- Each Vibemon has 1–2 elements (`Identity.elements: tuple[VibemonTypeT, ...]`)
- Each Move has exactly 1 type (`Move.type: VibemonTypeT`)
- See `backend/app/balance/element_chart.py` for the full chart

---

## 2. Type Effectiveness Matrix

`ELEMENT_CHART` maps `(attacker_type, defender_type) -> multiplier`:

| Multiplier | Meaning |
|---|---|
| `0.0` | Immune — no damage |
| `0.5` | Resist — half damage |
| `1.0` | Neutral — normal damage (default if not in chart) |
| `2.0` | Weak — double damage |

**Combined effectiveness** (dual-element defender):

| Product | Meaning |
|---|---|
| `4.00x` | Double weakness |
| `1.00x` | Neutralised (one weak, one resist) |
| `0.25x` | Double resist |
| `0.00x` | Immunity on either element trumps all |

**Key function** — `get_element_effectiveness(attack_type, defender_elements)` in `element_chart.py`.

---

## 3. Move Assignment Bonus

`get_move_assignment_bonus(move_type, vibemon_elements)` controls which moves a Vibemon can learn:

| Condition | Bonus |
|---|---|
| Move type matches any Vibemon element | `2.0x` (STAB fit) |
| Move type is NORMAL | `1.0x` (utility, no penalty) |
| Any other type | `0.5x` (antagonistic) |

**Planned** (Phase 2): `TYPE_AFFINITIES` will add `1.5x` coverage bonus for moves that hit a Vibemon's defensive weaknesses.

---

## 4. Base Stats

`Identity` fields, each with type-specific ranges:

| Stat | Min | Median | Max |
|---|---|---|---|
| `base_hp` | 1 | 70 | 255 |
| `base_attack` | 5 | 75 | 190 |
| `base_defense` | 5 | 70 | 230 |
| `base_sp_attack` | 10 | 70 | 194 |
| `base_sp_defense` | 20 | 70 | 230 |
| `base_speed` | 5 | 70 | 200 |

**Level scaling** (`base_stat_level_scaling` in `formulas.py`):
```
stat = floor((2 * base * level) / MAX_LEVEL) + 5
```

**Asymmetric stat generation** (`base_stat_asymmetric_scaling`):
- Maps a 0–1 ratio onto `[min, med]` for lower half, `[med, max]` for upper half
- Keeps median anchored at `ratio = 0.5`

### 4.1. Stat-Element Rating Matrix

Grades each element's affinity with every stat (S/A/B/C/D). Used to guide stat distribution during Identity generation — an element's `S` and `A` stats should trend high, `D` stats should trend low.

| Element | HP | Attack | Defense | Sp. Atk | Sp. Def | Speed | Stat Identity |
|---|---|---|---|---|---|---|---|
| Dragon | S | S | A | S | S | A | All-Around Elite |
| Steel | B | A | S | B | A | D | Physical Fortress |
| Fighting | A | S | B | D | C | B | Physical Powerhouse |
| Psychic | C | D | C | S | S | B | Special Specialist |
| Electric | D | C | D | A | B | S | Speed / Sp. Atk |
| Flying | B | B | D | B | C | S | Speed / Utility |
| Rock | B | A | S | D | B | D | Sturdy Attacker |
| Ice | A | B | B | B | B | C | Balanced Glass |
| Normal | S | C | D | D | D | B | HP / Neutrality |
| Ghost | D | B | B | B | B | C | Tactical Utility |
| Ground | A | A | A | D | D | D | Physical Bruiser |
| Fire | C | B | C | A | B | B | Special Sweeper |
| Fairy | C | D | C | B | A | C | Special Wall |
| Water | B | C | B | C | B | C | The Balanced Middle |
| Dark | B | A | C | B | D | A | Fast Offense |
| Poison | C | C | C | C | C | C | Mid-Tier Attrition |
| Grass | C | B | B | B | B | D | Balanced Support |
| Bug | D | D | C | D | C | C | Early Game / Utility |

---

## 5. Base Stat Total (BST) & Tier

`Identity.tier` classifies by BST:

| Tier | BST Range |
|---|---|
| `RUNT` | < 400 |
| `MID` | 400–499 |
| `SOLID` | 500–569 |
| `APEX` | 570–669 |
| `MYTHIC` | ≥ 670 |

---

## 6. Battle Role

Enum defined in `types.py:BattleRole` (10 roles). Classified at runtime by `Identity.battle_role` in `schema.py:151` using competitive-tier stat thresholds — not persisted, computed from base stats.

### Intermediate calculations

| Measure | Formula | Threshold(s) |
|---|---|---|
| `phys_ehp` | `hp * defense` | >= 8000 for wall |
| `spec_ehp` | `hp * sp_def` | >= 8000 for wall |
| `avg_ehp` | `(phys_ehp + spec_ehp) / 2` | < 5000 = frail, >= 5000 = bulky |
| `best_offense` | `max(atk, sp_atk)` | 120/100/95 tiers |
| `is_very_fast` | `speed >= 110` | — |
| `is_fast` | `speed >= 95` | — |
| `is_slow` | `speed < 65` | — |
| `is_elite_off` | `best_offense >= 120` | — |
| `is_strong_off` | `best_offense >= 100` | — |
| `is_decent_off` | `best_offense >= 95` | — |
| `is_phys_wall` | `phys_ehp >= 8000` | — |
| `is_spec_wall` | `spec_ehp >= 8000` | — |
| `is_any_wall` | `is_phys_wall or is_spec_wall` | — |
| `is_mixed_bulk` | `phys_ehp >= 6000 and spec_ehp >= 6000` | — |
| `is_frail` | `avg_ehp < 5000` | — |

### Decision tree (priority order via `match/case`)

| Priority | Condition | Role |
|---|---|---|
| 1 | `is_fast and is_strong_off and is_frail` | `OFFENSIVE_GLASS_CANNON` |
| 2 | `is_slow and is_elite_off` | `OFFENSIVE_WALLBREAKER` |
| 3 | `is_fast and is_strong_off` | `OFFENSIVE_SWEEPER` |
| 4 | `is_very_fast and is_decent_off` | `OFFENSIVE_REVENGE_KILLER` |
| 5 | `is_mixed_bulk and is_decent_off` | `DEFENSIVE_TANK` |
| 6 | `is_any_wall and not is_decent_off` | `DEFENSIVE_WALL` |
| 7 | `is_mixed_bulk and is_slow` | `DEFENSIVE_STALLER` |
| 8 | `is_fast and avg_ehp >= 5000` | `UTILITY_PIVOT` |
| 9 | `best_offense < 80 and avg_ehp >= 5000` | `UTILITY_CLERIC` |
| 10 | fallback | `UTILITY` |

---

## 7. Damage Formula

Modern mainline Pokemon-style integer formula (`backend/app/battle/rules/damage.py`):

### Base damage
```
base = floor((2 * level / 5) + 2)
base = floor(base * power * attack / defense)
base = floor(base / 50) + 2
```

### Modifier pipeline (ordered, fixed-point 4096)

| Step | Modifier | Rounding |
|---|---|---|
| Spread | ×0.75 (if multi-target) | round_half_down |
| Critical | ×1.5 (if crit) | round_half_down |
| Random | ×`rand(85..100)/100` | floor |
| STAB | ×1.5 (if move.type in attacker.elements) | round_half_down |
| Type | ×effectiveness (0.0, 0.25, 0.5, 1.0, 2.0, 4.0) | round_half_down |
| Burn | ×0.5 (if burned using physical move) | round_half_down |

Final damage: `max(1, result)`.

### Fixed-point constants
```
MOD_ONE = 4096
MOD_HALF = 2048
MOD_THREE_QUARTERS = 3072
MOD_ONE_AND_HALF = 6144
MOD_DOUBLE = 8192
```

### Other constants
| Constant | Value | Meaning |
|---|---|---|
| `STAB_MULTIPLIER` | 1.5 | Same-type attack bonus |
| `CRITICAL_HIT_MULTIPLIER` | 1.5 | Crit modifier |
| `BURN_PHYSICAL_REDUCTION` | 0.5 | Burn halves physical damage |
| `DAMAGE_RANDOM_MIN` | 0.85 | Low end of random roll |
| `DAMAGE_RANDOM_MAX` | 1.0 | High end of random roll |
| `MAX_LEVEL` | 100 | Level cap |

### Critical hit thresholds
| Effective stage | Probability |
|---|---|
| 0 | 1/24 (~4.2%) |
| 1 | 1/8 (12.5%) |
| 2 | 1/2 (50%) |
| 3 | Always |

On crit: attacker's negative stat stages treated as 0; defender's positive stages treated as 0.

---

## 8. Stat Stages

Range: `−6` to `+6`.

| Stage | Multiplier |
|---|---|
| 0 | ×1.0 (baseline) |
| +1 | ×1.5 |
| +2 | ×2.0 |
| +6 | ×4.0 |
| −1 | ×2/3 (~0.667) |
| −2 | ×0.5 |
| −6 | ×0.25 |

Formula: `(2 + stage) / 2` for positive; `2 / (2 + abs(stage))` for negative.

Accuracy/evasion uses divisor 3 instead of 2:
`(3 + stage) / 3` for positive; `3 / (3 + abs(stage))` for negative.

---

## 9. Accuracy System

`accuracy.py`:
- `accuracy=None` → Sure-Hit (bypasses all checks)
- `accuracy=1.0` → normal reliability
- `accuracy < 1.0` → chance to miss
- Final accuracy: `move.accuracy * accuracy_modifier(acc_stage, eva_stage)`

---

## 10. Status Conditions

| Condition | Effect |
|---|---|
| `BURN` | 1/16 max HP per turn; physical damage ×0.5 |
| `POISON` | 1/8 max HP per turn |
| `BAD_POISON` | `(turns * max_hp) / 16` per turn (escalating) |
| `PARALYSIS` | 25% chance to skip turn; speed ×0.5 |
| `SLEEP` | 1–3 turns inactive; wakes on thaw/recovery |
| `FREEZE` | 20% thaw chance per turn; fully immobile |
| `FAINTED` | Cannot act |

---

## 11. Move Balance Dials

Every move trades off four dials (see `move-generator/references/move_balance_reference.md` for full detail):

| Dial | Range | Tradeoff |
|---|---|---|
| **Power** | 10–250 (damaging); `None` (status) | ↑ pulls every other dial down |
| **Accuracy** | 0.0–1.0 or `None` (sure-hit) | Drops as power rises |
| **PP** | 5–40 | Drops as power rises |
| **Level Requirement** | 1–100 | Rises with power & utility |

### Power bands for damaging moves

| Band | Power | Typical PP | Typical Acc |
|---|---|---|---|
| Spam | 10–30 | 25–40 | 1.0 |
| Early STAB | 35–55 | 20–30 | 1.0 |
| Mid | 65–80 | 15–20 | 0.95–1.0 |
| Workhorse | 80–100 | 10–15 | 0.9–1.0 |
| High | 100–110 | 5–10 | 0.8–1.0 |
| Signature | 120–150 | 5 | 0.7–0.9 |
| Mega | 150+ | 5 | 0.9 |

### Secondary effects (~30% of damaging moves carry a rider)

| Move Power | Typical Effect Chance |
|---|---|
| ≤ 40 | up to 30% |
| 65–80 | ~20% |
| 90+ | 10% or less |

See `move_balance_reference.md` §8–§10 for status, stat change, and theme conventions.

---

## 12. Priority Budget

`Move.priority` range: `−7` to `+7` (default `0`).

| Priority | Power Cap | Ceiling |
|---|---|---|
| `+1` | ≤ 40 BP | ~5% of batch |
| `+2` | ≤ 80 BP | ≤ 1.5% of batch |
| `+3` | status only | trace |
| `+4..+7` | status only | ≤ 1 per batch |
| `0` | any | rest of batch |
| `−1..−7` | high power OK | trace |

**Batch rule**: `≤ 7%` of moves with `priority ≥ 1`.

---

## 13. Level-1 Move Sizing

~70% of moves in a batch sit at level 1. L1 damaging power distribution:

| Power | Share |
|---|---|
| 10–30 | 20–30% |
| 35–45 | 45–60% |
| 50–55 | 10–20% |
| 56–60 | 0–5% |
| >60 | 0% |

---

## 14. Key Code Locations

| Aspect | File |
|---|---|
| Type enum | `backend/app/types.py:VibemonTypeT` |
| Element chart | `backend/app/balance/element_chart.py` |
| Move assignment bonus | `backend/app/balance/element_chart.py:get_move_assignment_bonus` |
| Stat formulas | `backend/app/balance/formulas.py` |
| Balance constants | `backend/app/const.py` |
| Damage formula | `backend/app/battle/rules/damage.py` |
| Stat stages | `backend/app/battle/rules/stats.py` |
| Accuracy | `backend/app/battle/rules/accuracy.py` |
| Move schema | `backend/app/schema.py:Move` |
| Identity (base stats) | `backend/app/schema.py:Identity` |
| Battle role enum | `backend/app/types.py:BattleRole` |
| Role classification | `backend/app/schema.py:Identity.battle_role` |
| Status mechanics | `backend/app/battle/rules/status.py` |
| Weather mechanics | `backend/app/battle/mechanics/weather.py` |
| Move balance detail | `.agents/SKILLS/vibemon/move-generator/references/move_balance_reference.md` |
| Type system vision | `.ideas/type-system-architecture.md` |

---

## 15. Future Phases

- **Phase 2**: `TYPE_AFFINITIES` derived from `ELEMENT_CHART` — coverage bonuses, synergy pairs, UI tooltips
- **Phase 3**: Type-aware progression and evolution branching
- **Phase 4**: Type affinities guide affinity generation for new Vibemon
