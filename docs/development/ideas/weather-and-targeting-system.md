# Weather and Multi-Target Battle Mechanics

| | |
| --- | --- |
| **Status** | Deferred |
| **Priority** | — |
| **Complexity** | Medium |
| **Area** | Battle |
| **Related** | [move-interface-vs-pokemon.md](move-interface-vs-pokemon.md) |

## Summary

Reintroduce field weather and explicit move targeting on the battle schema so climate-born **Vibemon** can project atmosphere onto the field and spread/self-target utility moves become expressible. Enums were prototyped then removed until engine consumers exist.

## Problem

The **climate** provider reads atmospheric data into **Affinity**, but battles cannot reflect that DNA today:

- `Battle` has no weather slot.
- `MoveEffect` cannot set or clear weather.
- Damage calculation has no weather hook.
- Every move is implicitly single-target — fine for 1v1, a hard ceiling on tactical depth.

Spread moves (Earthquake hits all adjacent, Surf hits both opponents in doubles) similarly cannot be declared.

## Concept

Two related systems tracked together:

1. **Field weather** — per-battle weather state interacting with type damage, residual chip, and move properties.
2. **Move targeting** — per-move declaration of who the move can hit (self, single opponent, all opponents, all adjacent).

Both were prototyped as enums (`types.WeatherT`, `types.MoveTargetT`) but removed because no field on `schema.Move`, `schema.MoveEffect`, or `schema.Battle` consumed them. Reintroduce with engine support, not orphan enums.

## Design

### Weather state on the battle

```python
class WeatherT(enum.StrEnum):
    CLEAR = "clear"
    SUN = "sun"
    RAIN = "rain"
    SANDSTORM = "sandstorm"
    HAIL = "hail"
    HEAVY_RAIN = "heavy_rain"
    EXTREME_SUN = "extreme_sun"
    STRONG_WINDS = "strong_winds"


class FieldWeather(_Transient):
    kind: WeatherT = WeatherT.CLEAR
    turns_remaining: int = 0


class Battle(_Transient):
    ...
    weather: FieldWeather = pydantic.Field(default_factory=FieldWeather)
```

### Weather-setting moves on `MoveEffect`

```python
class MoveEffect(_Static):
    status_inflict: types.StatusConditionT | None = None
    stat_changes: dict[types.BaseStatNameT, int] = pydantic.Field(default_factory=dict)
    target_self: bool = False
    chance: float = 1.0
    weather_set: types.WeatherT | None = None  # NEW
    weather_turns: int = 5                      # NEW (ignored when weather_set is None)
    drain: float | None = None                  # NEW; fraction of damage healed back to user
    recoil: float | None = None                 # NEW; fraction of damage dealt back as recoil
```

`drain` and `recoil` cover canon archetypes (Giga Drain, Drain Punch, Flare Blitz, Wood Hammer, Brave Bird) that today have no schema slot.

### Targeting on `Move`

```python
class MoveTargetT(enum.StrEnum):
    SELF = "self"
    SINGLE = "single"
    ALL_OPPONENTS = "all_opponents"
    ALL_ADJACENT = "all_adjacent"


class Move(_Static):
    ...
    target: types.MoveTargetT = types.MoveTargetT.SINGLE  # NEW
```

`target_self` on `MoveEffect` becomes redundant for self-buff status moves once `Move.target` exists, but is kept for secondary self-effects on damaging moves (Overheat self-debuff on a single-target attack). Until doubles/triples land, anything other than `SINGLE` and `SELF` is engine-inert.

### Battle engine hooks

`game_engine.py` needs three integration points:

1. **Damage modifier** — type × weather multipliers (Rain ×1.5 WATER, ×0.5 FIRE; Sun mirrors; Sandstorm boosts ROCK Sp.Def, Hail boosts ICE defense).
2. **End-of-turn residual** — Sandstorm chips non-{ROCK, GROUND, STEEL}; Hail chips non-ICE; Sun/Rain modify burn/freeze rates.
3. **Move execution** — apply `weather_set` from `MoveEffect`, decrement `turns_remaining`, transition back to `CLEAR` at zero.

Spread moves require the engine to iterate targets per `Move.target` rather than the implicit `defender` parameter. Single-target battles still work if `ALL_OPPONENTS` collapses to `SINGLE` while `crew_size == 1`.

### Climate-provider flavor hooks

Once weather lives on `Battle`, the **climate** plugin can ship moves like:

- **Sun Loom** (FIRE, status, summons SUN, +Sp.Atk on user) — birth-weather at trainer geo could pick a signature weather move.
- **Cyclone Vow** (FLYING, status, summons STRONG_WINDS) — ground immunity + flying-type damage interactions.
- **Petrichor** (WATER, status, summons RAIN, restores HP) — ties drain/regen mechanics to weather.
- **Glacial Court** (ICE, status, summons HAIL, +Defense) — natural pair with freeze status.

## Open Questions

1. **Weather persistence across battles**: should birth-weather seed persistent buffs, or is weather strictly in-battle? Default: in-battle only — `Battle` owns `FieldWeather`.
2. **Stacking with move callbacks**: callbacks already need `battle` access; weather on `Battle` lets Solar Beam read rain/sun without extra plumbing.
3. **Doubles UX**: `ALL_OPPONENTS` and `ALL_ADJACENT` only diverge when adjacency matters (triples). For now collapse both to "every living opponent."
4. **Weather-immunity types**: ROCK no chip in sandstorm; ICE no chip in hail; STEEL/GROUND mirror sandstorm. Encode as a small dict in the residual hook, not per **Vibemon**.

## Anti-Goals

- Orphan enums without schema fields or engine call sites (why they were removed).
- Cross-battle weather persistence without an explicit product decision.
- Doubles-only targeting complexity before crew size > 1 ships.
