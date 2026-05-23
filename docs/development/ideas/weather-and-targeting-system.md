# Weather and Multi-Target Battle Mechanics

## Concept

Add two related battle systems that the schema does not currently express:

1. **Field weather** — a per-battle weather state that interacts with type damage, residual chip, and move properties.
2. **Move targeting** — a per-move declaration of who the move can hit (self, single opponent, all opponents, all adjacent), enabling spread moves and self-targeted utility.

Both were prototyped as enums (`types.WeatherT`, `types.MoveTargetT`) but removed because no field on `schema.Move`, `schema.MoveEffect`, or `schema.Battle` consumed them. They are tracked here so the design space is preserved.

## Motivation

The `climate` provider literally reads atmospheric data and folds it into Vibemon affinity. Battles born of that DNA should be able to *project* weather back onto the field — a Sandstorm-summoning rock-type, a Rain Dance ice/water duo, a Sunny Day fire mythic. None of this is possible today because:

- `Battle` has no weather slot.
- `MoveEffect` cannot set/clear weather.
- Damage calculation in `app.balance.formulas` has no weather hook.

Spread moves (Earthquake hits all adjacent, Surf hits both opponents in doubles) similarly cannot be expressed. Every move today is implicitly single-target — fine for 1v1 but a hard ceiling on tactical depth.

## Proposed Schema Changes

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

`drain` and `recoil` cover the canon Vibemon archetypes (Giga Drain, Drain Punch, Flare Blitz, Wood Hammer, Brave Bird) that today have no schema slot.

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

`target_self` on `MoveEffect` becomes redundant for self-buff status moves once `Move.target` exists, but is kept for *secondary* self-effects on damaging moves (Overheat self-debuff is a rider on a single-target attack). Until doubles/triples land, anything other than `SINGLE` and `SELF` is engine-inert.

## Battle Engine Hooks

`game_engine.py` needs three integration points:

1. **Damage modifier** — type x weather multipliers (Rain x1.5 WATER, x0.5 FIRE; Sun mirrors; Sandstorm boosts ROCK Sp.Def, Hail boosts ICE defense).
2. **End-of-turn residual** — Sandstorm chips non-{ROCK, GROUND, STEEL}; Hail chips non-ICE; Sun/Rain modify burn/freeze rates.
3. **Move execution** — apply `weather_set` from `MoveEffect`, decrement `turns_remaining`, transition back to `CLEAR` at zero.

Spread moves require the engine to iterate targets per `Move.target` rather than the implicit `defender` parameter. Single-target battles (the current shape) still work if `ALL_OPPONENTS` collapses to `SINGLE` while `team_size == 1`.

## Climate-Provider Flavor Hooks

Once weather lives on `Battle`, the `climate` plugin can ship moves like:

- **Sun Loom** (FIRE, status, summons SUN, +Sp.Atk on user) — current real weather of the trainer's geo at birth could deterministically pick a "signature" weather move.
- **Cyclone Vow** (FLYING, status, summons STRONG_WINDS) — ground immunity + flying-type damage interactions.
- **Petrichor** (WATER, status, summons RAIN, restores HP) — ties drain/regen mechanics from `move-callbacks.md` to weather.
- **Glacial Court** (ICE, status, summons HAIL, +Defense) — natural pair with the freeze status.

## Open Questions

1. **Weather persistence across battles**: should the trainer's birth-weather seed any persistent buffs, or is weather strictly an in-battle effect? Default: in-battle only — keep `Battle` the only owner of `FieldWeather`.
2. **Stacking with `move-callbacks.md`**: callbacks already need `battle` access. Once weather lives on `Battle`, callbacks naturally read it (Solar Beam = 0 power in rain, 150 in sun) without extra plumbing.
3. **Doubles UX**: `ALL_OPPONENTS` and `ALL_ADJACENT` only diverge when adjacency matters (triples). For now they are spec sugar; the engine can collapse both to "every living opponent."
4. **Weather-immunity types**: ROCK no chip in sandstorm; ICE no chip in hail; STEEL/GROUND mirror sandstorm. Encoded as a small dict in the residual hook, not on each Vibemon.

## Why Removed For Now

`types.WeatherT` and `types.MoveTargetT` were defined but had zero call sites in schema, engine, or plugins. Dead enums rot — they accumulate `from app import types` references with no behavior, then get retro-fitted later in incompatible ways. Cleaner to delete them, write this design down, and re-introduce with engine support behind it.
