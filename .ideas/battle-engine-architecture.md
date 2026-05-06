# Battle Engine Architecture Refactor

This document is the interface design for refactoring `backend/app/battle/game_engine.py`.

The refactor is structural except for Decision 4 and the legacy effect-target migration in Decision 5. Damage calculation deliberately moves to the modern mainline Pokemon formula, including intermediate rounding, integer random rolls, and true immunities. Legacy `MoveEffect.target_self` is consumed and replaced by explicit `EffectTarget` semantics. Outside those cases, current battle outcomes are preserved until a later mechanic PR changes them.

Pokemon battle architecture is the fallback model:

- battle-scoped mutable state lives on the battle, field, side, active slot, or volatile condition
- the engine executes a fixed move pipeline
- mechanics attach at explicit event points such as before move, modify priority, modify damage, on hit, on faint, on switch in, and end of turn
- move data stays serializable, while exceptional move behavior is referenced by stable script ids rather than embedded Python function refs

No tests are required while this interface is still being designed. Once the shape is accepted, implementation should start with characterization coverage that locks the accepted shape, the new canon damage outcomes, the explicit effect-target outcomes, and the remaining current outcomes.

## Goals

1. Make planned mechanics cheap to add without re-litigating engine internals.
2. Keep `GameEngine` stateless. `Battle` owns all persistent combat state.
3. Replace string-typed bags with discriminated unions at action, event, effect, target, and condition boundaries.
4. Preserve direct-call simplicity for the fixed battle pipeline.
5. Add typed registries only where Pokemon-style mechanics naturally have subscribers.
6. Keep content data serializable. First-party executable behavior is referenced by id.

---

## Decision 1 - Engine State Model

**Engine is stateless. `Battle` is the single source of truth. `Turn` is per-submit scratch.**

`GameEngine` carries no hidden battle state across calls. Persistent combat state lives on `Battle` and its child objects:

- `Battle.field`: field-scoped state such as weather, terrain, trick room, gravity, and global counters.
- `BattleTrainer` / future `BattleSide`: side-scoped state such as screens, hazards, tailwind, and side conditions.
- `BattleVibemon`: active combatant state such as HP, status, stat stages, PP, volatile conditions, and future ability/item refs.
- `TurnRecord`: submitted actions and emitted events.

Weather is in-battle state, but "in-battle only" does not mean "not serialized." If a `Battle` snapshot is persisted for replay or reconnect, weather rides with it. It does not leak into trainer progression, Vibemon birth data, or out-of-battle domain models.

Randomness must preserve the current continuous RNG stream. The current engine consumes randomness in one sequence across turns. The refactor must not reseed per turn. During the structural refactor, keep accepting an injected `random.Random`. A later replay feature may add:

```python
class Battle(_Transient):
    rng_seed: int | None = None
    rng_state: object | None = None
```

If `rng_state` exists, the engine restores it at `submit()` start and writes the new state at `submit()` end. Forward replay can then use seed plus actions; random-access replay uses snapshots.

---

## Decision 2 - Pipeline Shape

**Use a linear move pipeline, but preserve the current edge behavior exactly.**

Drop `Phase`, `BattleStateMachine`, `PhaseState`, and `PHASE_STATE_MAP`. Replace them with top-to-bottom methods on `GameEngine`:

```python
def submit(self, actions: Sequence[BattleAction]) -> list[TurnEvent]:
    turn = Turn.from_submit(self.battle, self._rng, actions)
    self._record_turn_start(turn)
    self._build_execution_stack(turn)
    self._execute_stack(turn)
    self._end_of_turn(turn)
    self._finish_turn(turn)
    return turn.events
```

The pipeline is linear, but these current behaviors are load-bearing:

- action sorting happens before pre-action status checks
- sleep/freeze/flinch/paralysis/confusion can block only move actions
- PP is spent immediately before executing a move, as today
- fainting the defender cancels the remaining stack
- end-of-turn status damage still runs after the stack ends
- `turn_number` increments after end-of-turn maintenance
- winner assignment keeps the current double-faint tie rule unless a later design changes it

This is a readability refactor, not permission to normalize battle rules.

---

## Decision 3 - Turn Context

**Rules functions take `Turn` only when they need battle awareness.**

`Turn` is a transient execution context. It is not persisted.

```python
class Turn:
    battle: Battle
    rng: random.Random
    actions: tuple[BattleAction, ...]
    actions_by_actor: dict[ActorRef, BattleAction]
    events: list[TurnEvent]
    stack: list[StackEntry]
    current_entry: StackEntry | None
    phase: PipelinePhaseName
```

Function tiers:

| Tier | Takes | Examples |
|---|---|---|
| Pure math | nothing | `clamp_stage`, `_stage_multiplier`, `stat_stage_multiplier`, `_accuracy_modifier`, `effective_speed` |
| Stochastic stateless | `rng` only | `_is_crit`, `resolve_speed_tie` |
| Battle-aware | `Turn` | `calc_damage`, `execute_move_use`, `check_pre_action`, `resolve_turn_order`, `apply_status_damage`, `end_of_turn_maintenance`, `apply_effect_group` |

A helper that takes `Turn` but ignores it is still wrong. A helper that needs submitted actions, field state, hook registry, events, or battle mutation takes `Turn`.

---

## Decision 4 - Damage Modifier Pipeline

**Use a modern mainline Pokemon damage pipeline with explicit integer rounding.**

This is the one intentional mechanics change in the architecture refactor. Current `calc_damage` is not Pokemon-canon: it uses float stat multipliers, draws `rng.uniform(0.85, 1.0)`, multiplies everything together, floors once at the end, and then forces at least 1 damage even through type immunity. Replace that with the Generation VI+ mainline formula family:

- base damage is integer math with floor points
- effective Attack/Defense stats are integer stage-adjusted values
- critical hits ignore negative attacker offensive stages and positive defender defensive stages
- critical multiplier is 1.5, matching modern Pokemon and the current Vibemon constant
- random damage is an integer roll from 85 through 100, inclusive
- type effectiveness of 0 short-circuits to 0 damage, not 1
- STAB, type, burn, and final modifiers apply with canon rounding, not a float product

Target the modern mainline games, not Pokemon Legends: Arceus and not Generation V's 2x crit multiplier.

Core arithmetic:

```python
def round_half_down(value: float) -> int:
    """Nearest integer; exact .5 rounds down."""

def round_half_up(value: float) -> int:
    """Nearest integer; exact .5 rounds up."""

def pokemon_base_damage(level: int, power: int, attack: int, defense: int) -> int:
    damage = floor((2 * level) / 5 + 2)
    damage = floor(damage * power * attack / defense)
    damage = floor(damage / 50)
    return damage + 2

def chain_mods(mods: Iterable[int], *, minimum: int = 1, maximum: int = 131072) -> int:
    chained = 4096
    for mod in mods:
        if mod != 4096:
            chained = round_half_up(chained * mod / 4096)
    return clamp(chained, minimum, maximum)

def apply_mod(value: int, mod: int) -> int:
    return round_half_down(value * mod / 4096)
```

Use fixed-point modifier values where `4096 == 1.0`, `6144 == 1.5`, `2048 == 0.5`, `3072 == 0.75`, and `8192 == 2.0`. This avoids float drift and makes modifier audit data line up with Pokemon references and Pokemon Showdown-style calculators.

Calculation order:

1. Resolve effective move type, category, base power, Attack, and Defense.
2. If type effectiveness is 0 or an immunity hook blocks the hit, return `DamageResult(damage=0, blocked_reason=...)`.
3. Compute integer base damage with `pokemon_base_damage`.
4. Apply spread/target modifier, if any.
5. Apply weather modifier, if any.
6. Apply critical modifier, if any.
7. Apply random modifier from an integer `rng.randint(85, 100)` roll.
8. Apply STAB.
9. Apply type effectiveness.
10. Apply burn modifier.
11. Apply chained "other" modifiers from screens, abilities, held items, move scripts, protection leakage, and future mechanics.
12. Clamp to at least 1 only after confirming type effectiveness was not 0.

Represent the pipeline as ordered steps, not a dict:

```python
class DamageModifier(_Static):
    key: str
    numerator: int          # fixed-point over 4096, except random/type special cases
    display: float
    source: str | None = None

class DamageStep(_Static):
    key: str
    modifiers: tuple[DamageModifier, ...]
    rounding: Literal["floor", "round_half_down", "round_half_up"]
    damage_after: int

class DamageResult(_Static):
    damage: int
    is_crit: bool
    random_roll: int | None
    effectiveness: float
    base_damage: int
    steps: tuple[DamageStep, ...]
    blocked_reason: Literal["type_immune", "ability_immune", "move_failed"] | None = None
```

Damage contributors register by phase, not by one global list:

| Phase | Examples |
|---|---|
| `base_power` | Technician, power-doubling scripts, weather-ball-style scripts |
| `attack` | Choice Band, Huge Power, Guts |
| `defense` | Eviolite, sand Rock Sp.Def, Marvel Scale |
| `spread` | multi-target 0.75x |
| `weather` | rain/sun Fire/Water modifiers |
| `critical` | crit multiplier, Sniper-style later support |
| `stab` | STAB, Adaptability-style later support |
| `type` | element chart and type overrides |
| `burn` | physical burn reduction |
| `other` | screens, Filter/Solid Rock, Expert Belt, Life Orb, protection leakage |

This keeps extension surfaces Pokemon-shaped without leaking every mechanic into `calc_damage`. Hooks produce typed modifiers for a specific phase; `calc_damage` owns the arithmetic and ordering.

---

## Decision 5 - Move Effects

**Use typed effects, but chance belongs to effect groups, not every leaf effect.**

Current `MoveEffect.chance` is one roll for the entire effect bag. A move with status plus stat changes rolls once; if the roll succeeds, every applicable effect in the bag is attempted. Splitting that into independent per-effect rolls changes mechanics.

Final shape:

```python
class EffectGroup(_Static):
    chance: float = 1.0
    trigger: Literal["on_hit", "on_use", "after_damage"] = "on_hit"
    effects: tuple[Effect, ...] = ()

class StatusInflict(_Static):
    kind: Literal["status"]
    target: EffectTarget = "target"
    status: StatusConditionT

class StatChange(_Static):
    kind: Literal["stat"]
    target: EffectTarget = "target"
    changes: dict[StatStageNameT, int]

class Drain(_Static):
    kind: Literal["drain"]
    ratio: float

class Recoil(_Static):
    kind: Literal["recoil"]
    ratio: float

class WeatherSet(_Static):
    kind: Literal["weather"]
    weather: WeatherT
    turns: int

class Heal(_Static):
    kind: Literal["heal"]
    target: EffectTarget = "self"
    ratio: float

type Effect = Annotated[
    StatusInflict | StatChange | Drain | Recoil | WeatherSet | Heal,
    pydantic.Discriminator("kind"),
]

class Move(_Static):
    ...
    effects: tuple[EffectGroup, ...] = ()
```

`EffectTarget` is relative to the move use: `self`, `target`, `all_targets`, `side`, or `opposing_side` as needed. This covers self-buffs, Overheat-style self drops, status riders, weather-setting status moves, drain, recoil, and future item-like effects.

Migration rule: existing `MoveEffect` becomes one `EffectGroup`, and `target_self` is consumed at that boundary:

- `target_self=True` maps each relative effect to `target="self"`.
- `target_self=False` maps each relative effect to `target="target"`.
- effects that are inherently self-referential, such as `Drain` and `Recoil`, keep their own effect-specific target rules.

The new engine never reads `target_self`. Effect dispatch resolves `EffectTarget` against the current `MoveUse` and applies the effect to the resolved recipient. This intentionally fixes the old leaked abstraction where the schema exposed `target_self` but the engine ignored it.

---

## Decision 6 - Events

**Engine emits typed data events. Rendering is outside the engine. Avoid overloaded `actor`.**

The final event model is a discriminated union. Event fields name their role directly:

```python
class MoveUsedEvent(_Static):
    kind: Literal["move_used"]
    user: str
    move: str
    targets: tuple[str, ...]

class DamageEvent(_Static):
    kind: Literal["damage"]
    source: str
    target: str
    amount: int
    hp_after: int
    is_crit: bool
    effectiveness: float
    modifiers: tuple[DamageModifier, ...]

class FaintEvent(_Static):
    kind: Literal["faint"]
    target: str

class StatusInflictedEvent(_Static):
    kind: Literal["status_inflicted"]
    source: str | None
    target: str
    status: StatusConditionT

class StatChangeEvent(_Static):
    kind: Literal["stat_change"]
    source: str | None
    target: str
    changes: dict[StatStageNameT, int]
```

No event should require the frontend to infer whether `actor` means user, target, source, or subject.

During implementation, a compatibility renderer can produce the current English `description` strings from typed events. The final engine does not format prose.

---

## Decision 7 - Move Behavior: Declarative Conditions Plus First-Party Scripts

**Declarative conditions are the common path. Special move scripts are the escape hatch.**

Reject raw function refs on `Move`. They are not serializable and make content data impossible to inspect. Also reject "no escape hatch." Canon Pokemon has moves that cannot fit a small declarative condition vocabulary without making that vocabulary unbounded: Transform, Metronome, Mirror Move, Mimic, Sketch, Copycat, Counter, Mirror Coat, Bide, Destiny Bond, Substitute, Baton Pass, Pursuit, Protect, Rollout, Stockpile, Curse, Fling, Natural Gift, Weather Ball, Acupressure, and similar exceptions.

Final shape:

```python
class ConditionalOverride(_Static):
    valid: bool | None = None
    priority_delta: int = 0
    accuracy_override: float | None = None
    power_multiplier: float | None = None
    flavor_key: str | None = None

class IfOpponentAttacking(_Static):
    kind: Literal["opponent_attacking"]
    on_match: ConditionalOverride
    on_miss: ConditionalOverride | None = None

class IfWeather(_Static):
    kind: Literal["weather"]
    weather: WeatherT
    on_match: ConditionalOverride

class IfHpBelow(_Static):
    kind: Literal["hp_below"]
    threshold: float
    on_match: ConditionalOverride

class RandomPower(_Static):
    kind: Literal["random_power"]
    buckets: tuple[tuple[float, int], ...]

type Condition = Annotated[
    IfOpponentAttacking | IfWeather | IfHpBelow | RandomPower | ...,
    pydantic.Discriminator("kind"),
]

class MoveBehavior(_Static):
    conditions: tuple[Condition, ...] = ()
    script_id: str | None = None

class Move(_Static):
    ...
    behavior: MoveBehavior = pydantic.Field(default_factory=MoveBehavior)
```

`script_id` is a stable id into a first-party registry:

```python
class MoveScript(Protocol):
    def modify_priority(self, ctx: Turn, use: MoveUse) -> int: ...
    def before_move(self, ctx: Turn, use: MoveUse) -> MoveUseResult: ...
    def modify_power(self, ctx: Turn, use: MoveUse, target: BattleVibemon) -> int | None: ...
    def on_hit(self, ctx: Turn, hit: HitResult) -> None: ...
    def after_move(self, ctx: Turn, use: MoveUse) -> None: ...
```

Implement only the methods a script needs. Scripts are first-party mechanics, not third-party plugin callbacks. Serialized move data stores only `script_id`; the registry supplies executable behavior at runtime.

Rule of thumb:

- scalar, inspectable conditions use `Condition`
- move identity changes, move copying, history-dependent counterattacks, substitute-like state, and arbitrary target/state mutation use `script_id`

---

## Decision 8 - Actions

**Final actions are tagged unions and self-identifying. Keep positional submit only as an adapter during migration.**

Current `submit(action_a, action_b)` is positional and ignores `BattleAction.trainer_name`. The final API should not depend on argument position.

```python
class MoveAction(_Static):
    kind: Literal["move"]
    trainer: TrainerIdT
    slot: int = 0
    move_name: str
    targets: tuple[TargetRef, ...] = ()

class SwitchAction(_Static):
    kind: Literal["switch"]
    trainer: TrainerIdT
    slot: int = 0
    bench_index: int

class ItemAction(_Static):
    kind: Literal["item"]
    trainer: TrainerIdT
    item_id: str
    target: TargetRef | None = None

class RunAction(_Static):
    kind: Literal["run"]
    trainer: TrainerIdT

type BattleAction = Annotated[
    MoveAction | SwitchAction | ItemAction | RunAction,
    pydantic.Discriminator("kind"),
]
```

Final `submit()` takes a sequence and validates ownership:

- every required trainer/active slot has exactly one action unless forced replacement or another special state says otherwise
- no duplicate trainer/slot submissions
- action trainer ids must match battle participants
- target refs must resolve in the current battle topology

Migration should provide:

```python
def submit(self, action_a: LegacyBattleAction, action_b: LegacyBattleAction) -> list[TurnEvent]:
    return self.submit_actions([_legacy_to_action(self.battle.trainer_a, action_a), _legacy_to_action(...)])
```

That keeps current positional behavior while the new interface settles.

---

## Decision 9 - Targeting

**Separate move use from hit resolution. Target topology lives on the move; chosen targets live on the action.**

Pokemon distinguishes "using a move" from "a hit against a target." That distinction is required for PP, accuracy, spread damage, multi-hit moves, drain/recoil, effects, and faint ordering.

```python
class MoveTargetT(enum.StrEnum):
    SELF = "self"
    SINGLE = "single"
    ALL_OPPONENTS = "all_opponents"
    ALL_ADJACENT = "all_adjacent"
    USER_SIDE = "user_side"
    OPPONENT_SIDE = "opponent_side"
    FIELD = "field"

class TargetRef(_Static):
    trainer: TrainerIdT
    slot: int

class Move(_Static):
    ...
    target: MoveTargetT = MoveTargetT.SINGLE
```

Execution shape:

```python
def execute_move_use(ctx: Turn, use: MoveUse) -> None:
    spend_pp(use)
    targets = resolve_targets(ctx, use)
    if not targets:
        emit_failed(...)
        return
    for target in targets:
        hit = execute_hit(ctx, use, target, spread=len(targets) > 1)
        apply_on_hit_effects(ctx, use, hit)
    apply_after_move_effects(ctx, use)
```

`execute_move_use` owns per-use concerns: PP, selected move, primary target selection, move scripts, and after-move cleanup.

`execute_hit` owns per-target concerns: immunity, accuracy if modeled per-target, damage, target fainting, hit-triggered effects, and on-hit hooks.

For current 1v1, `SINGLE` and `ALL_OPPONENTS` resolve to the opposing active slot. The abstraction is still useful because it prevents doubles from forcing a rewrite of every move function later.

---

## Decision 10 - Hook Registration

**Use a mixed model: fixed pipeline, typed first-party hook points, explicit ordering.**

Direct calls stay for the core pipeline. Hook registries exist where Pokemon-style mechanics have unbounded contributors.

| Surface | Shape | Reason |
|---|---|---|
| Action validation | direct pipeline plus optional action hooks | switch, item, forced replacement, PP-zero Struggle |
| Pre-action blocks | direct fixed order | current sleep/freeze/flinch/paralysis/confusion order must stay stable |
| Priority modifiers | ordered hook list plus move conditions/scripts | abilities, items, terrain, move-specific priority |
| Damage modifiers | ordered hook list | STAB, type, crit, burn, weather, items, abilities, spread |
| Accuracy / immunity | ordered hook list | future No Guard, Levitate, Soundproof, weather, protect |
| On hit | ordered hook list | Static, Rough Skin, Rocky Helmet, contact effects |
| On faint | ordered hook list | Aftermath, Destiny Bond, XP, forced switch |
| On switch in/out | ordered hook list | hazards, Intimidate, weather abilities |
| End of turn | ordered hook list | weather, status, items, abilities, volatile cleanup |

Use typed protocols and explicit priority. Do not rely on insertion order once interactions matter.

```python
class HookPriority(enum.IntEnum):
    EARLY = -100
    NORMAL = 0
    LATE = 100

@dataclasses.dataclass(frozen=True)
class RegisteredHook:
    priority: int = HookPriority.NORMAL
    source: str
    hook: Callable

class HookRegistry:
    def register[T](self, protocol: type[T], hook: T, *, source: str, priority: int = 0) -> None: ...
    def get[T](self, protocol: type[T]) -> tuple[T, ...]: ...
```

Provider plugins are content plugins. They can define `Move` data. They do not register executable battle mechanics. First-party battle mechanics live in `battle/mechanics/` and register hooks/scripts at engine construction.

This keeps the engine extensible without turning provider plugins into an unrestricted combat scripting API.

---

## Decision 11 - Module Structure

**Split battle state out of `app/schema.py`, but keep move content schemas cycle-free.**

Do not put `Effect`, `Condition`, or `MoveTargetT` under `battle/` if `Move` imports them. That creates a cycle because battle modules also import `Move`.

Final import direction:

- domain/content schemas import no battle engine modules
- battle state imports domain/content schemas
- rules import battle state and content schemas
- mechanics import hooks/events/rules, not the other way around

Proposed layout:

```text
backend/app/
  schema.py                         # domain/content aggregate: Trainer, Vibemon, Move, EffectGroup, Condition
  types.py                          # enums and shared type aliases
  battle/
    __init__.py
    engine.py                       # GameEngine class + submit pipeline
    turn.py                         # Turn context
    schema.py                       # Battle, BattleTrainer, BattleVibemon, BattleMove, StatStages, FieldState
    actions.py                      # MoveAction | SwitchAction | ItemAction | RunAction
    events.py                       # TurnEvent discriminated union
    hooks.py                        # HookRegistry + Protocol definitions
    scripts.py                      # MoveScript registry
    rules/
      __init__.py
      damage.py
      accuracy.py
      status.py
      targeting.py
      turn_order.py
      effects.py
      conditions.py
    mechanics/
      __init__.py
      weather.py
      items.py
      abilities.py
      status.py
    render/
      en.py
```

`app/schema.py` remains the public import home for domain and move content. `battle/schema.py` is transient combat state. If `schema.py` grows too large later, move content can move to `app/moves/schema.py` and be re-exported from `app/schema.py`, but battle modules must remain downstream.

---

## Expansion Surfaces Not Implemented Yet

These mechanics are not part of the structural refactor, but the design must leave a clean place for each.

**Switching.** `SwitchAction`, switch priority, on-switch-out hooks, on-switch-in hooks, hazards, and forced replacement after faint belong in the action and switch pipelines. Forced replacement is not a normal turn action.

**Items.** `ItemAction` is a trainer action. Held items are future `BattleVibemon.item` or side state and use hooks such as damage modifiers, on-hit, on-faint, and end-of-turn. Bag items are validated separately from held items.

**Weather and terrain.** `Battle.field` owns weather/terrain. Weather setting is an effect or script. Damage changes are damage modifiers. Residual chip and duration decrement are end-of-turn hooks.

**Multi-hit moves.** Add a hit-count policy to move data or a move script. `execute_move_use` loops hits; `execute_hit` remains per target. This prevents Bullet Seed and Double Kick from corrupting single-hit damage code.

**Recharge, charge, and locked-in moves.** These are volatile conditions on `BattleVibemon`, usually installed by a move script and consumed by action validation or pre-action checks.

**Move-blocking abilities.** Soundproof, Levitate, immunities, and similar blockers belong in accuracy/immunity or on-try-hit hooks, not in target resolution.

**PP-zero Struggle.** Action validation owns this. If no selected move has PP or the requested move cannot be used, the validator either canonicalizes to a first-party Struggle move or emits a failure according to the chosen rules.

**Copying and transformation moves.** These use `script_id`, not declarative conditions. They need access to battle history, selected actions, move pools, and temporary move identity.

---

## Migration Order

This is implementation sequencing, not a design-phase test requirement.

1. Accept the final interface shape.
2. Add characterization coverage for accepted wire shapes, canon damage outcomes, explicit effect-target outcomes, and remaining current outcomes.
3. Split transient battle state into `battle/schema.py` and action/event modules with compatibility exports.
4. Collapse the phase machine into linear engine methods while preserving current behavior.
5. Introduce `Turn` and thread it only through battle-aware functions.
6. Add hook and script registries without registering new behavior.
7. Replace damage with the canon integer pipeline from Decision 4, including fixed-point modifiers and integer random rolls.
8. Add typed action unions and keep positional `submit()` as an adapter.
9. Add typed events and compatibility rendering for current English descriptions.
10. Add `EffectGroup` and typed effects, migrating existing `MoveEffect` as one shared-chance group and consuming `target_self` into explicit `EffectTarget`.
11. Add conditions and `MoveBehavior.script_id`, with no script mechanics enabled by default.
12. Add target topology and split `execute_move_use` from `execute_hit`, still collapsing to 1v1 behavior.

Each step should make the new interface more real. Decision 4 and the Decision 5 legacy target migration are the only intended rule changes in this refactor.

---

## What This Enables

- `move-callbacks.md`: replaced by declarative conditions plus first-party move scripts.
- `weather-and-targeting-system.md`: field state, weather effects, damage modifiers, end-of-turn hooks, and target topology.
- `type-system-architecture.md`: type chart stays a pure balance concern and feeds damage modifiers plus content tooling.
- `trainer-progression-and-economy.md`: items and XP use action hooks, held-item hooks, on-faint hooks, and post-battle systems without bloating the core move pipeline.
- Doubles: action slots, target refs, side state, spread modifiers, and per-use/per-hit execution are already represented.

---

## Out of Scope For This Refactor

- Implementing weather, items, abilities, switching, doubles, multi-hit, recharge, charge, locked-in moves, or Struggle.
- Public third-party battle scripting.
- Persisting trainer progression or economy state in `Battle`.
