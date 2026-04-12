# P4-T2 — Battle UI (Gen 3 Layout, Neutral Moves, Battle Log)

**Phase:** 4 — Battle System  
**Dependencies:** P4-T1, P3-T3  
**Depends on this:** P4-T3

---

## Objective

Build the interactive battle screen as a **renderer** of `BattleState`: Gen 3–style **battle scene** + **battle panel**, HP/EXP treatment, **neutral** move grid (no elemental or provider-based button chrome), message bar, and battle log. Visual tokens and layout follow [.plans/vibemon-visual-design-system.md](../vibemon-visual-design-system.md).

## Important

- **Svelte 5 only:** `$state()`, `$derived()`, `$props()`, `Tween` / `Spring` from `svelte/motion` where animation is needed.
- Frontend **never** implements damage, effectiveness chart, or turn order — only displays server state and sends `POST /api/v1/battle/turn` with `{ state, move_index }`.
- **Move buttons:** show move name (pixel font stack) + secondary line (`--f-dt`): category, power if applicable, PP when available. **Do not** show elemental `type` on the button.

---

## Tasks

### 1. Create `frontend/src/lib/stores/battle.ts`

Thin holder — no game logic:

- `$state` for last `BattleState`, `pendingEvents: TurnEvent[]`, `loading: boolean`
- `startBattle(player, enemy)` → `POST /api/v1/battle/start`
- `submitMove(moveIndex)` → `POST /api/v1/battle/turn` with full current state
- Export reactive getters / functions as needed for Svelte 5

### 2. Add `BattleState`, `BattleMon`, `TurnEvent` in `$lib/types.ts`

Mirror Python / JSON (`snake_case`), aligned with [design.md](../design.md) battle models.

### 3. `frontend/src/lib/components/HpBar.svelte` (or card-integrated bar)

- Props: `current`, `max`, optional `showNumeric` (player yes, enemy card no per design system §3.3).
- Width animation (`Tween`, ~600ms, easing consistent with design §4.1).
- Fill color from HP% thresholds (`--hp-hi` / `--hp-mid` / `--hp-lo`).
- Uses `--f-ui` for numerals, never pixel font for numbers.

### 4. `frontend/src/lib/components/MoveButton.svelte`

- Props: `move`, `disabled`, `onSelect`.
- Neutral styles: `var(--vb-surface)`, `var(--vb-border)`; hover `var(--vb-raised)` — see design system §4.3.
- Content: `★` prefix for signature; name; secondary line category / power / PP only.
- `Spring` press feedback (scale) optional.
- Disabled when not player turn, `loading`, or animation lockout.

### 5. `frontend/src/lib/components/BattleLog.svelte`

- Props: `entries: string[]` from `state.log`.
- Scroll to latest; effectiveness phrases styled (gold / grey / red) as today’s copy requires.

### 6. Assemble `frontend/src/routes/battle/+page.svelte`

- On mount: `startBattle` with payloads from generation store.
- Layout matches **vibemon-visual-design-system** §3: scene (gradient, grid, stars, platforms, sprites, floating info cards with teal vs magenta borders), panel (`--vb-deep`), message bar + cursor, 2×2 move grid, log placement per implementation sketch.
- Wire moves to `submitMove(index)`.
- Loading indicator while `loading`.

### 7. Turn indicator

- Read-only from `state.phase` (“Your turn” / “Enemy’s turn” / end states).

### 8. Responsive

- Breakpoint and tweaks per design system §9 (2-col grid invariant).

---

## Acceptance Criteria

- UI matches the design system document for structure, tokens, and **neutral** move treatment.
- HP reflects `current_hp` / `max_hp` from server; animations on state change.
- Moves interactive only when phase is player turn and not loading; no local battle math.
- `POST /api/v1/battle/turn` sends full current `BattleState`.

## Files

**New:** `battle.ts` store, `HpBar.svelte`, `MoveButton.svelte`, `BattleLog.svelte` (paths as above).  
**Modified:** `types.ts`, `battle/+page.svelte`, global CSS or imports for design tokens and keyframes per design doc.
