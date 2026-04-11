# P4-T1 — Battle State Machine & Turn Logic

**Phase:** 4 — Battle System
**Dependencies:** P3-T3, P2-T3 (full move pools), P1-T7
**Depends on this:** P4-T2, P4-T3

---

## Objective

Implement the core battle state machine as a Svelte 5 `$state`-backed store, including the turn flow, damage formula, type effectiveness, stat stages, and status effects.

## Important

Use `$state`-backed classes/objects — **not** `writable()`/`readable()` stores.

## Tasks

1. **Create `frontend/src/lib/stores/battle.ts`**
   - Define types:
     ```typescript
     type Phase = 'player-turn' | 'enemy-turn' | 'animating' | 'victory' | 'defeat'
     type BattleMon = {
       vibemon: VibemonPayload,
       currentHp: number,
       maxHp: number,
       statStages: Record<'attack'|'defense'|'spAttack'|'spDefense'|'speed', number>,
       statusEffect: 'drain' | 'seed' | 'burrowed' | null
     }
     type BattleState = { phase: Phase, player: BattleMon, enemy: BattleMon, log: string[], turn: number }
     ```
   - Export a `$state`-backed battle state object
   - `initBattle(playerPayload, enemyPayload)` — sets up initial state, HP = stat HP value

2. **Create `frontend/src/lib/utils/damage.ts`**
   - Implement the damage formula:
     ```
     Damage = floor(((2×50/5+2) × Power × A/D) / 50 + 2) × Modifier
     ```
   - `A` = attacker's Attack (physical) or Sp.Attack (special)
   - `D` = defender's Defense (physical) or Sp.Defense (special)
   - Apply stat stage multipliers: stages −6 to +6 → ×0.25 to ×2.50
   - `STAB` = 1.5 if move element matches attacker's element
   - `TypeEffectiveness` from the 9×9 type chart (including immunities)
   - Random factor: `0.85 + Math.random() × 0.15`

3. **Implement the type effectiveness chart**
   - 9×9 matrix as a nested object or Map
   - Include all ×0, ×0.5, ×1, ×2 matchups from the design doc

4. **Implement turn execution**
   - `executePlayerMove(moveIndex)`:
     - Compare effective speed (with stat stages) to determine turn order
     - Faster attacker goes first
     - Accuracy roll: `Math.random() * 100 < move.accuracy`
     - On hit: calculate damage, subtract from target HP
     - Apply move effects (stat stage changes, drain, seed, burrow)
     - Check KO after each attack
     - If no KO, slower attacker executes
   - Add log entries for each action

5. **Implement stat stage effects**
   - Stat stage changes from status moves (e.g. "Own Defense +1", "Enemy Speed −1")
   - Clamp stages to [−6, +6]
   - Apply stage multiplier when computing A and D in damage formula

6. **Implement status effects**
   - `seed` (Grass): drain ⅛ max HP per turn from the target
   - `drain` (Dark): heal 25% of damage dealt
   - `burrowed` (Ground): next hit against self has 50% miss chance

7. **Implement enemy AI**
   - `chooseEnemyMove(state)`: weighted random selection
   - Weights: high-power moves ×3 when player HP < 25%, status moves ×1.5 when enemy HP < 50%
   - Physical moves weighted by enemy attack, special by sp_attack

8. **Write unit tests**
   - Damage formula produces expected values for known inputs
   - Type effectiveness returns correct multipliers (spot-check 10+ matchups)
   - Stat stages clamp correctly
   - Turn order respects speed comparison
   - KO detection triggers correct phase transition

## Acceptance Criteria

- `initBattle` creates a valid state from two payloads
- A full turn executes: player selects move → speed comparison → attacks resolve → HP updates → log entries → phase transitions
- Type effectiveness messages appear ("super effective", "not very effective", "no effect")

## Files Created

```
frontend/src/lib/stores/battle.ts
frontend/src/lib/utils/damage.ts
frontend/src/lib/utils/typeChart.ts
tests/damage.test.ts
```
