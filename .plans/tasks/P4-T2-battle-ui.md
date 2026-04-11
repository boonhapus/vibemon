# P4-T2 — Battle UI Components (HP Bar, Move Buttons, Battle Log)

**Phase:** 4 — Battle System
**Dependencies:** P4-T1, P3-T3
**Depends on this:** P4-T3

---

## Objective

Build the interactive battle screen UI: HP bars with animated depletion, move selection buttons, stat/type labels, and a scrolling battle log. All displayed values come from `BattleState` returned by the backend — the frontend computes nothing about game logic.

## Important

- Use **Svelte 5 syntax only**: `$state()`, `$derived()`, `$props()`, `Tween`/`Spring` from `svelte/motion`
- The frontend is a **renderer** of `BattleState`. It never calculates damage, type effectiveness, or turn order
- Move buttons call `POST /api/v1/battle/turn` — they do not invoke any local game logic

---

## Tasks

### 1. Create `frontend/src/lib/stores/battle.ts`

Thin state holder — no game logic:

```typescript
import type { BattleState, TurnEvent } from '$lib/types'

// Last BattleState received from the server
let state = $state<BattleState | null>(null)
// Events from the most recent turn (used for animation sequencing)
let pendingEvents = $state<TurnEvent[]>([])
// True while a /battle/start or /battle/turn request is in-flight
let loading = $state(false)

export async function startBattle(player: VibemonPayload, enemy: VibemonPayload) {
  loading = true
  const res = await fetch('/api/v1/battle/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ player, enemy }),
  })
  state = await res.json()
  loading = false
}

export async function submitMove(moveIndex: number) {
  if (!state || loading) return
  loading = true
  const res = await fetch('/api/v1/battle/turn', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state, move_index: moveIndex }),
  })
  const { state: newState, events } = await res.json()
  pendingEvents = events
  state = newState
  loading = false
}

export { state, pendingEvents, loading }
```

### 2. Add `BattleState`, `BattleMon`, and `TurnEvent` TypeScript types in `$lib/types.ts`

Mirror the Python models exactly (snake_case keys, same field names as JSON):

```typescript
export type Phase = 'player-turn' | 'enemy-turn' | 'victory' | 'defeat'

export type BattleMon = {
  vibemon:       VibemonPayload
  current_hp:    number
  max_hp:        number
  stat_stages:   Record<'attack' | 'defense' | 'sp_attack' | 'sp_defense' | 'speed', number>
  status_effect: 'seed' | 'drain' | 'burrowed' | null
}

export type BattleState = {
  phase:     Phase
  player:    BattleMon
  enemy:     BattleMon
  log:       string[]
  turn:      number
  rng_seed:  number
}

export type TurnEvent = {
  type:          string
  actor:         'player' | 'enemy'
  move_name:     string | null
  damage:        number | null
  effectiveness: 'super-effective' | 'not-very-effective' | 'immune' | null
  stat_key:      string | null
  stat_delta:    number | null
  heal:          number | null
  message:       string
}
```

### 3. Create `frontend/src/lib/components/HpBar.svelte`

- Props: `current: number`, `max: number`, `name: string`, `element: string`, `elementSecondary: string | null`
- Animated width using `Tween` from `svelte/motion` with `cubicOut` easing, 600ms duration
- Colour transitions: green (>50%) → yellow (25–50%) → red (<25%)
- Display `current / max HP` text
- Display Vibemon name and element badge(s) above the bar
- Drives from `BattleMon.current_hp` / `BattleMon.max_hp` from state

### 4. Create `frontend/src/lib/components/MoveButton.svelte`

- Props: `move: Move`, `disabled: boolean`, `onSelect: () => void`
- Show move name, category icon (physical/special/status), power, element type colour
- Signature moves get a ★ prefix
- Press animation using `Spring` from `svelte/motion`: scale 0.95 → 1.0
- Disabled when `loading` is true, when `state.phase !== 'player-turn'`, or during animation
- On click: calls `onSelect()` → parent calls `submitMove(index)`

### 5. Create `frontend/src/lib/components/BattleLog.svelte`

- Props: `entries: string[]`
- Driven by `state.log` from the server (not a local accumulator)
- Scrolling container that auto-scrolls to the latest entry
- Style effectiveness messages: "super effective" in gold, "not very effective" in grey, "no effect" in red
- Fade-in animation for new entries

### 6. Assemble the battle screen in `frontend/src/routes/battle/+page.svelte`

- On mount: call `startBattle(player, enemy)` (payloads come from navigation state set by `/generate`)
- Layout:
  - Top: enemy HP bar + enemy name/element
  - Upper centre: enemy `VibemonRenderer` (flipped)
  - Lower centre: player `VibemonRenderer`
  - Below player: player HP bar + name/element
  - Bottom left: 2×2 grid of `MoveButton` components
  - Bottom right or below: `BattleLog`
- Wire move button clicks to `submitMove(index)` from the battle store
- Show a loading indicator while `loading === true`

### 7. Add turn indicator

- Show "Your turn" / "Enemy's turn" text based on `state.phase`
- Note: `phase` is set by the server — the frontend just reads and renders it

### 8. Responsive layout

- Stack vertically on narrow screens (mobile-first)
- Move buttons min 48px height for touch targets

---

## Acceptance Criteria

- HP bar animates smoothly when `current_hp` in returned state differs from previous state
- Move buttons are interactive only when `state.phase === 'player-turn'` and `loading === false`
- Battle log displays `state.log` in order with styled effectiveness text
- No game logic in the frontend — no damage formula, no type chart, no turn order logic
- Submitting a move calls `POST /api/v1/battle/turn` with the full current state

## Files Created

```
frontend/src/lib/components/HpBar.svelte
frontend/src/lib/components/MoveButton.svelte
frontend/src/lib/components/BattleLog.svelte
```

## Files Modified

```
frontend/src/lib/stores/battle.ts    (new thin state holder)
frontend/src/lib/types.ts            (add BattleState, BattleMon, TurnEvent)
frontend/src/routes/battle/+page.svelte
```
