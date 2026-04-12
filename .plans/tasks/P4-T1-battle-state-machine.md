# P4-T1 — Battle Engine (Backend)

**Phase:** 4 — Battle System
**Dependencies:** P3-T3, P2-T3 (full move pools), P1-T6
**Depends on this:** P4-T2, P4-T3

---

## Objective

Implement the battle engine as a pure Python module (`engine/battle.py`) with no HTTP dependency, plus thin Litestar route handlers in `routes/battle.py`. All game logic — damage formula, type effectiveness, turn order, stat stages, status effects, enemy AI — lives here. The frontend is a renderer only.

## Architecture

The engine is importable directly (headless mode):

```python
from app.engine.battle import start_battle, execute_turn

state = start_battle(player_payload, enemy_payload)
state, events = execute_turn(state, move_index=0)
```

The HTTP routes are thin wrappers:

```python
# routes/battle.py
@post("/battle/start")
async def battle_start(data: BattleStartRequest) -> BattleState: ...

@post("/battle/turn")
async def battle_turn(data: BattleTurnRequest) -> BattleTurnResponse: ...
```

Battle state is **not** stored server-side. The full `BattleState` travels with every `/battle/turn` request (stateless echo).

## Tasks

### 1. Define battle data models in `engine/battle.py`

```python
@define
class BattleMon:
    vibemon:       VibemonPayload
    current_hp:    int
    max_hp:        int
    stat_stages:   dict[str, int] = field(factory=lambda: {
                       "attack": 0, "defense": 0,
                       "sp_attack": 0, "sp_defense": 0, "speed": 0
                   })
    status_effect: Optional[str] = None  # "seed" | "drain" | "burrowed" | None

@define
class BattleState:
    phase:     str        # "player-turn" | "enemy-turn" | "victory" | "defeat"
    player:    BattleMon
    enemy:     BattleMon
    log:       list[str]
    turn:      int
    rng_seed:  int        # advances each turn; keeps battles deterministic/replayable

@define
class TurnEvent:
    type:          str            # "attack" | "miss" | "damage" | "stat_change"
                                  # | "status_applied" | "ko" | "phase_change"
                                  # | "seed_drain" | "heal"
    actor:         str            # "player" | "enemy"
    move_name:     Optional[str]  = None
    damage:        Optional[int]  = None
    effectiveness: Optional[str]  = None  # "super-effective" | "not-very-effective" | "immune"
    stat_key:      Optional[str]  = None
    stat_delta:    Optional[int]  = None
    heal:          Optional[int]  = None
    message:       str            = ""
```

### 2. Implement `start_battle`

```python
def start_battle(player: VibemonPayload, enemy: VibemonPayload) -> BattleState:
    seed = make_seed(player.uid, "battle")
    return BattleState(
        phase="player-turn",
        player=BattleMon(vibemon=player, current_hp=player.stats.hp, max_hp=player.stats.hp),
        enemy=BattleMon(vibemon=enemy,   current_hp=enemy.stats.hp,  max_hp=enemy.stats.hp),
        log=[],
        turn=1,
        rng_seed=seed,
    )
```

### 3. Implement the type effectiveness chart

9×9 nested dict `TYPE_CHART[attacking][defending] -> float`:

| Attacking ↓ / Defending → | Fire | Water | Ice | Elec | Grass | Ground | Dark | Psychic | Normal |
|---|---|---|---|---|---|---|---|---|---|
| **Fire**     | ×0.5 | ×0.5 | ×2 | ×1 | ×2 | ×1 | ×1 | ×1 | ×1 |
| **Water**    | ×2 | ×0.5 | ×1 | ×1 | ×0.5 | ×2 | ×1 | ×1 | ×1 |
| **Ice**      | ×0.5 | ×0.5 | ×0.5 | ×1 | ×2 | ×2 | ×1 | ×1 | ×1 |
| **Electric** | ×1 | ×2 | ×1 | ×0.5 | ×0.5 | ×0 | ×1 | ×1 | ×1 |
| **Grass**    | ×0.5 | ×2 | ×1 | ×1 | ×0.5 | ×2 | ×1 | ×1 | ×1 |
| **Ground**   | ×2 | ×1 | ×1 | ×0 | ×0.5 | ×1 | ×1 | ×1 | ×1 |
| **Dark**     | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 | ×0.5 | ×2 | ×1 |
| **Psychic**  | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 | ×2 | ×0.5 | ×1 |
| **Normal**   | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 |

### 4. Implement damage calculation

```python
def calculate_damage(
    attacker: BattleMon,
    defender: BattleMon,
    move: Move,
    rng: random.Random,
) -> tuple[int, str | None]:
    """Returns (damage, effectiveness_label). damage=0 means immune."""
    a = _staged(attacker, "attack" if move.category == "physical" else "sp_attack")
    d = _staged(defender, "defense" if move.category == "physical" else "sp_defense")
    eff = TYPE_CHART[move.type][defender.vibemon.stats.element]
    if eff == 0:
        return (0, "immune")
    base   = ((2 * 50 / 5 + 2) * move.power * a / d) / 50 + 2
    stab   = 1.5 if move.type == attacker.vibemon.stats.element else 1.0
    rand   = rng.uniform(0.85, 1.00)
    damage = max(1, math.floor(base * stab * eff * rand))
    label  = (
        "super-effective"    if eff >= 2.0 else
        "not-very-effective" if eff < 1.0  else
        None
    )
    return (damage, label)

def _staged(mon: BattleMon, stat: str) -> int:
    STAGE_MULT = {
        -6: 0.25, -5: 0.29, -4: 0.33, -3: 0.40, -2: 0.50, -1: 0.67,
         0: 1.00,  1: 1.50,  2: 2.00,  3: 2.50,  4: 3.00,  5: 3.50,  6: 4.00
    }
    base  = getattr(mon.vibemon.stats, stat)
    stage = mon.stat_stages.get(stat, 0)
    return max(1, round(base * STAGE_MULT[stage]))
```

### 5. Implement stat stage application and status effects

- Stat stage changes: clamp to [−6, +6]
- `seed`: drain ⅛ max HP per turn end
- `drain`: heal 25% of damage dealt this turn
- `burrowed`: 50% miss chance on incoming attacks this turn, then clear

### 6. Implement enemy AI

```python
def choose_enemy_move(state: BattleState, rng: random.Random) -> int:
    """Returns a move index 0–3."""
    enemy, player = state.enemy, state.player
    player_hp_ratio = player.current_hp / player.max_hp
    enemy_hp_ratio  = enemy.current_hp  / enemy.max_hp
    weights = []
    for m in enemy.vibemon.moves:
        w = 1.0
        if player_hp_ratio < 0.25 and m.power > 80:         w *= 3.0
        if enemy_hp_ratio  < 0.50 and m.category == "status": w *= 1.5
        if m.category == "physical": w *= enemy.vibemon.stats.attack    / 128
        if m.category == "special":  w *= enemy.vibemon.stats.sp_attack / 128
        weights.append(max(w, 0.1))
    return rng.choices(range(len(enemy.vibemon.moves)), weights=weights, k=1)[0]
```

### 7. Implement `execute_turn`

Signature: `execute_turn(state: BattleState, move_index: int) -> tuple[BattleState, list[TurnEvent]]`

- Does **not** mutate the input state — return a new `BattleState`
- Advance `rng_seed` deterministically at the end of each turn
- Turn flow:
  1. Select enemy move via `choose_enemy_move`
  2. Compare effective speed (staged); RNG breaks ties
  3. Faster attacker resolves move → produce `TurnEvent`s
  4. Check KO; if KO, set `phase = "victory"/"defeat"`, return
  5. Apply end-of-turn status effects (seed drain)
  6. Slower attacker resolves move
  7. Check KO again
  8. Advance turn counter; update `rng_seed`
- Append human-readable message to `state.log` for each meaningful action

### 8. Create HTTP route handlers in `routes/battle.py`

```python
@define
class BattleStartRequest:
    player: VibemonPayload
    enemy:  VibemonPayload

@define
class BattleTurnRequest:
    state:      BattleState
    move_index: int

@define
class BattleTurnResponse:
    state:  BattleState
    events: list[TurnEvent]

@post("/battle/start")
async def battle_start(data: BattleStartRequest) -> BattleState:
    return start_battle(data.player, data.enemy)

@post("/battle/turn")
async def battle_turn(data: BattleTurnRequest) -> BattleTurnResponse:
    if data.state.phase in ("victory", "defeat"):
        raise HTTPException(status_code=422, detail="battle already finished")
    if not (0 <= data.move_index <= 3):
        raise HTTPException(status_code=422, detail="move_index must be 0–3")
    new_state, events = execute_turn(data.state, data.move_index)
    return BattleTurnResponse(state=new_state, events=events)
```

Register both handlers in `app/main.py`.

### 9. Write unit tests in `backend/tests/test_battle.py`

- `start_battle` produces correct initial HP and phase
- Damage formula produces expected values for known inputs (no RNG variance: seed fixed)
- Type effectiveness: spot-check ≥10 matchups including ×0 (immune), ×0.5, ×2
- Stat stages clamp to [−6, +6]
- Turn order respects staged speed comparison
- KO detection sets correct phase (`victory` vs `defeat`)
- `execute_turn` returns a new state, not a mutated copy of the input
- A full two-turn exchange produces a coherent log

## Acceptance Criteria

- `start_battle` creates a valid `BattleState` from two payloads
- `execute_turn` processes a full turn: player move + enemy move, HP updates, events, phase transitions
- `POST /battle/start` and `POST /battle/turn` return correct JSON-serialised models
- No game logic exists in the frontend — `damage.ts` and `typeChart.ts` are absent
- Engine importable and callable without starting the HTTP server

## Files Created

```
backend/app/engine/battle.py
backend/app/routes/battle.py
backend/tests/test_battle.py
```

## Files Modified

```
backend/app/main.py   (register battle routes)
```
