# P4-T2 — Battle UI Components (HP Bar, Move Buttons, Battle Log)

**Phase:** 4 — Battle System
**Dependencies:** P4-T1, P3-T3
**Depends on this:** P4-T3

---

## Objective

Build the interactive battle screen UI: HP bars with animated depletion, move selection buttons, stat/type labels, and a scrolling battle log.

## Important

Use **Svelte 5 syntax only**: `$state()`, `$derived()`, `$props()`, `Tween`/`Spring` from `svelte/motion`.

## Tasks

1. **Create `frontend/src/lib/components/HpBar.svelte`**
   - Props: `current: number`, `max: number`, `name: string`, `element: string`, `elementSecondary: string | null`
   - Animated width using `Tween` from `svelte/motion` with `cubicOut` easing, 600ms duration
   - Colour transitions: green (>50%) → yellow (25–50%) → red (<25%)
   - Display `current / max HP` text
   - Display Vibemon name and element badge(s) above the bar

2. **Create `frontend/src/lib/components/MoveButton.svelte`**
   - Props: `move: Move`, `disabled: boolean`, `onSelect: () => void`
   - Show move name, category icon (physical/special/status), power, element type colour
   - Signature moves get a ★ prefix
   - Press animation using `Spring` from `svelte/motion`: scale 0.95 → 1.0
   - Disabled state during enemy turn and animation phases

3. **Create `frontend/src/lib/components/BattleLog.svelte`**
   - Props: `entries: string[]`
   - Scrolling container that auto-scrolls to the latest entry
   - Style effectiveness messages: "super effective" in gold, "not very effective" in grey, "no effect" in red
   - Fade-in animation for new entries

4. **Assemble the battle screen layout**
   - Update `frontend/src/routes/battle/+page.svelte`:
     - Top: enemy HP bar + enemy name/element
     - Upper centre: enemy `VibemonRenderer` (flipped)
     - Lower centre: player `VibemonRenderer`
     - Below player: player HP bar + name/element
     - Bottom left: 2×2 grid of `MoveButton` components
     - Bottom right or below: `BattleLog`
   - Wire move button clicks to `executePlayerMove(index)` from the battle store
   - Disable move buttons when `phase !== 'player-turn'`

5. **Add turn indicator**
   - Show "Your turn" / "Enemy's turn" / "Animating..." text based on `phase`
   - Brief delay between player and enemy attacks for readability (e.g. 800ms via `setTimeout` or `$effect`)

6. **Responsive layout**
   - Stack vertically on narrow screens (mobile-first)
   - Move buttons should be large enough for touch targets (min 48px height)

## Acceptance Criteria

- HP bar animates smoothly when damage is dealt
- Move buttons are interactive during player turn and disabled otherwise
- Battle log displays all turn events in order with styled effectiveness text
- Layout is functional on both desktop (side-by-side) and mobile (stacked)

## Files Created

```
frontend/src/lib/components/HpBar.svelte
frontend/src/lib/components/MoveButton.svelte
frontend/src/lib/components/BattleLog.svelte
```

## Files Modified

```
frontend/src/routes/battle/+page.svelte
```
