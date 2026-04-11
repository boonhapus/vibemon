# P4-T3 — Battle Animations & End Screens

**Phase:** 4 — Battle System
**Dependencies:** P4-T1, P4-T2
**Depends on this:** P5-T3

---

## Objective

Add hit/critical/faint animations to the Vibemon SVG wrappers and build the victory and defeat screens that conclude a battle. Animations are driven by the `TurnEvent[]` returned by `POST /api/v1/battle/turn` — the frontend never decides what happened, only how to show it.

---

## Animation Architecture

`execute_turn` on the backend returns `{ state: BattleState, events: TurnEvent[] }`. The frontend processes the event list sequentially to produce animations:

```typescript
async function playEvents(events: TurnEvent[]) {
  for (const event of events) {
    switch (event.type) {
      case 'attack':         await showAttackLabel(event); break
      case 'miss':           await showMissLabel(event); break
      case 'damage':         await playHitAnimation(event); break
      case 'stat_change':    await showStatChangeLabel(event); break
      case 'status_applied': await showStatusLabel(event); break
      case 'seed_drain':     await playDrainAnimation(event); break
      case 'ko':             await playFaintAnimation(event); break
    }
  }
}
```

Move buttons remain disabled while `playEvents` is running. Set a `$state animating = false` flag; set it true before `playEvents`, false after.

---

## Tasks

### 1. Hit shake animation

- When a `TurnEvent` with `type === "damage"` is processed, apply CSS `@keyframes shake` to the target Vibemon's SVG wrapper
- Duration: 300ms, horizontal displacement ±5px
- `actor` field identifies the target: `"player"` → enemy attacked player, so shake player SVG; vice versa
- Use a `$state isHit = false` prop on `VibemonRenderer.svelte`; set it true, await 300ms, set false

### 2. Critical hit / super effective flash

- When `event.type === "damage"` and `event.effectiveness === "super-effective"`:
  - Apply a semi-transparent white flash overlay on the target SVG
  - 150ms fade-in then fade-out

### 3. Faint animation

- Triggered by `TurnEvent` with `type === "ko"`
- `translateY(30px)` + `opacity: 0` over 800ms with `ease-in` on the target Vibemon's SVG
- After the animation resolves, the `state.phase` in the returned state will be `"victory"` or `"defeat"` — show the appropriate end screen

### 4. Move button press feedback

- Brief colour pulse on button background matching the move's element type
- Happens on click, before the API response arrives (optimistic feedback)
- The `Spring` scale animation from P4-T2 already covers the press — add the colour pulse on top

### 5. Victory screen (`phase === "victory"`)

- Player Vibemon scales up via `Spring` (1.0 → 1.2 → 1.0 bounce)
- CSS particle burst effect (small coloured dots expanding outward)
- Show "Victory!" text, player Vibemon name, and a summary pulled from `state`:
  - `state.turn` — turns taken
  - `state.player.current_hp` / `state.player.max_hp` — remaining HP
- "Play Again" button → navigate back to `/`

### 6. Defeat screen (`phase === "defeat"`)

- Subdued styling, enemy Vibemon remains visible
- Show "Defeat" text and battle summary from `state`
- "Try Again" button → navigate back to `/`

### 7. Animation sequencing

- Maintain a local `$state animating = false` flag
- Set `animating = true` before calling `playEvents(events)`, false after
- While `animating` is true: disable move buttons, suppress further `submitMove` calls
- Sequence: attack label → hit animation → HP bar drains to new `current_hp` → KO check → faint animation → end screen
- HP bar `Tween` target is always `state.player.current_hp` / `state.enemy.current_hp` from the server — the tween just animates toward that value

---

## Acceptance Criteria

- Hit shake targets the correct Vibemon (determined by `TurnEvent.actor`)
- Super-effective hits produce a white flash overlay
- Fainting Vibemon slides down and fades out before the end screen appears
- Victory screen shows with spring-bounce on player Vibemon
- "Play Again" / "Try Again" buttons return to `/`
- No input is accepted while `animating === true`
- All displayed state (HP numbers, phase label, log) comes from `BattleState` — none is computed locally

## Files Modified

```
frontend/src/lib/components/VibemonRenderer.svelte  (add isHit, isFainted props)
frontend/src/routes/battle/+page.svelte              (event playback, animating flag, end screens)
```

## Files Created

```
frontend/src/lib/components/VictoryScreen.svelte
frontend/src/lib/components/DefeatScreen.svelte
```
