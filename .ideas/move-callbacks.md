# Move Callbacks

## Status

Superseded direction.

The current backend should prefer declarative move behavior first:

- `EffectGroup` and typed effects for common move outcomes;
- `MoveBehavior.conditions` for conditional validity, priority, accuracy, power, and flavor keys;
- `MoveBehavior.script_id` only as a future escape hatch for exceptional first-party mechanics.

Do not add provider-authored Python callbacks to move content. If executable custom move logic becomes necessary, use a backend-owned `MoveBehaviorRegistry` or `MoveBehaviorService` that maps stable `script_id` values to first-party battle code.

This note is kept for historical design context, not as the active implementation plan.

## Concept

Add a `callback` field to `Move` that allows moves to inspect battle state at resolution time to determine their own validity, accuracy, priority, and power dynamically.

## Motivation

Currently, move attributes (`power`, `accuracy`, `priority`) are static dataclass fields set at definition time. Some moves need to behave conditionally based on:
- What the opponent is doing this turn (e.g., Sucker Punch)
- The current weather or terrain
- The user's or opponent's current state (HP %, status, etc.)

### Pokémon Analogue: Sucker Punch

Sucker Punch has:
- **Priority +1** (elevated) **only if** the opponent is using a damaging move
- **100% accuracy** if the condition is met
- **Fails** (or loses priority) if the opponent is not using an attacking move

This cannot be expressed with static fields alone — it requires inspecting the opponent's chosen action during action sorting.

## Proposed `callback` Field

```python
class MoveCallback(Protocol):
    """Signature for move callback functions."""

    def __call__(
        self,
        move: BattleMove,
        user: BattleVibemon,
        target: BattleVibemon,
        battle: Battle,
        opponent_action: BattleAction | None,
    ) -> MoveCallbackResult:
        ...


class MoveCallbackResult(pydantic.BaseModel):
    """The resolved state of a move after callback evaluation."""

    valid: bool = True
    """Whether the move can be executed at all. If False, the move fails."""

    priority: int | None = None
    """Override the move's priority. If None, use the move's static priority."""

    accuracy: float | None = None
    """Override the move's accuracy. If None, use the move's static accuracy."""

    power: int | None = None
    """Override the move's power. If None, use the move's static power."""

    description: str | None = None
    """Optional flavor text to append to the move's event description."""
```

## Schema Changes

```python
class Move(_Static):
    name: str
    flavor_text: str
    type: types.VibemonTypeT
    category: types.MoveCategoryT
    power: int | None = None
    accuracy: float | None = 1.0
    pp: int = 10
    priority: Annotated[int, validators.ensure_between_abs_7] = 0
    effect: MoveEffect | None = None
    level_requirement: int = 1
    callback: MoveCallback | None = None  # NEW
```

The `callback` is **not serialized** — it's a runtime-only reference to a Python function (similar to how Django stores function references). It is attached to `Move` instances at definition time in each plugin's `moves.py`, not stored in JSON/database.

## Example: Sucker Punch (Vibemon Flavor: "Shadow Jab")

```python
# In moves.py or a callbacks module:

def shadow_jab_callback(move, user, target, battle, opponent_action):
    # Check if opponent is using an attacking move
    if opponent_action and opponent_action.action_type == ActionTypeT.MOVE:
        opp_move = find_move(target, opponent_action.value)
        if opp_move and opp_move.power is not None:
            # Opponent is attacking — priority +1, 100% accuracy
            return MoveCallbackResult(
                valid=True,
                priority=move.priority + 1,
                accuracy=1.0,
            )

    # Opponent is not attacking — move fails
    return MoveCallbackResult(
        valid=False,
        description=f"{user.name}'s {move.name} missed because the opponent wasn't attacking!",
    )


MOVES = (
    schema.Move(
        name='Shadow Jab',
        flavor_text='A quick strike that surprises unprepared foes.',
        type=types.VibemonTypeT.DARK,
        category=types.MoveCategoryT.PHYSICAL,
        power=70,
        accuracy=1.0,
        pp=10,
        priority=0,
        callback=shadow_jab_callback,
    ),
)
```

## Engine Integration Points

The callback needs to be invoked at two points in `game_engine.py`:

1. **`resolve_turn_order`** (Phase I): To adjust `priority` for action sorting
2. **`execute_attack`** (Phase II.2): To adjust `accuracy`, `power`, and check `valid` before executing

### Changes to `resolve_turn_order`

```python
def resolve_turn_order(a, b, action_a, action_b, rng):
    # ... existing code ...

    prio_a = move_a.priority if move_a else 0
    prio_b = move_b.priority if move_b else 0

    # NEW: Apply callbacks for priority adjustment
    if move_a and move_a.callback:
        result_a = move_a.callback(move_a, a, b, battle, action_b)
        prio_a = result_a.priority if result_a.priority is not None else prio_a

    if move_b and move_b.callback:
        result_b = move_b.callback(move_b, b, a, battle, action_a)
        prio_b = result_b.priority if result_b.priority is not None else prio_b

    # ... rest of existing code ...
```

### Changes to `execute_attack`

```python
def execute_attack(attacker, defender, move, rng, opponent_action=None):
    # NEW: Run callback for validity/accuracy/power overrides
    if move.callback:
        result = move.callback(move, attacker, defender, battle, opponent_action)
        if not result.valid:
            return [TurnEvent(
                actor=attacker.name,
                move_used=move.name,
                missed=True,
                description=result.description or f"{attacker.name}'s {move.name} failed!"
            )]
        if result.accuracy is not None:
            move = move.model_copy(update={"accuracy": result.accuracy})
        if result.power is not None:
            move = move.model_copy(update={"power": result.power})

    # ... existing accuracy roll and damage calculation ...
```

## Battle State Access

The callback receives `battle` (the full `Battle` object), giving it access to:
- Both trainers and their teams
- Turn history
- Current turn number
- Any weather/terrain fields (when added later)

This makes callbacks extensible for future mechanics like:
- Weather-dependent power (Solar Beam = 0 power in rain, 150 in sun)
- Revenge boosts (moves that hit harder if user fainted last turn)
- Conditional priority (Sucker Punch, Grassy Glide)
- Stance-change moves (Move X becomes Move Y under certain conditions)

## Open Questions

1. **Serialization**: Callbacks are Python functions and can't be serialized. They should be excluded from `model_dump()` via Pydantic's `Field(exclude=True)` or by storing them outside the schema (e.g., a registry mapping move names to callback functions).

2. **Callback purity**: Should callbacks be pure functions (no side effects), or can they modify battle state? Recommendation: callbacks should only *read* battle state and return a `MoveCallbackResult` — side effects should happen in the normal move execution flow.

3. **Finding opponent action**: The callback needs to know the opponent's chosen action for the turn. This means either passing it into the callback (as shown above) or having the callback inspect `battle.turn_history[-1].actions`.
