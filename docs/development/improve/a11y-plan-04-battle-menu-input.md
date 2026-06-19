# Plan 04 — Battle menu input unification

**Findings:** A11Y-004  
**Severity:** High  
**Effort:** M (1–2 days)  
**Depends on:** Plan 03 optional (modal trap unrelated to battle)  
**Primary files:**

- `vibemon/frontend/src/lib/domains/battle/BattleScene.svelte`
- `vibemon/frontend/src/lib/domains/battle/CommandMenu.svelte`
- `vibemon/frontend/src/lib/domains/battle/MoveMenu.svelte`
- `vibemon/frontend/src/lib/domains/battle/MoveLearnMenu.svelte`
- `vibemon/frontend/src/lib/domains/battle/battleGridMenu.ts` (unchanged logic)

---

## Goal

Battle command and move selection should behave as **one coherent input system** for:

- Arrow-key / Enter players (window handlers — primary game mode).
- Mouse click players.
- **Keyboard Tab users** and screen reader users focusing individual cells.

Today `CommandMenu` syncs focus to selection; `MoveMenu` does not and lacks visible focus styles. Window-level indices (`commandIndex`, `moveIndex`) can desync from focused DOM node.

---

## Architecture choice (pick one)

### Option A — **Gamepad mode** (recommended for Vibemon)

Treat battle grids as **single tab stops**; arrow keys handled at window; menu buttons **`tabindex="-1"`** except during explicit "mouse mode".

| Pros | Cons |
| :--- | :--- |
| Matches JRPG convention | Tab users need on-screen instructions |
| No focus/selection desync | Menus not individually tabbable |
| Minimal diff | |

**Implementation:**

1. Add `tabindex={selected === index ? 0 : -1}` on menu cells (roving tabindex inside grid).
2. `$effect` in `MoveMenu` mirroring `CommandMenu.focusSelectedCell`.
3. Window key handler remains source of truth for arrow navigation.
4. When phase enters `command` / `moveSelect`, focus first selected cell once.

### Option B — **Full roving tabindex on buttons**

Remove window arrow handlers for menus; implement arrow keys on `role="menu"` container.

| Pros | Cons |
| :--- | :--- |
| Standard widget behavior | Fights dialog Enter/Space for continue |
| Better for Tab users | Larger refactor of `BattleScene` |

**Decision:** Ship **Option A** first; document Option B in Plan 08 if `role="menu"` is removed.

---

## Implementation — Option A

### 1. Extract shared focus helper

**New file:** `vibemon/frontend/src/lib/domains/battle/focusMenuCell.ts`

```typescript
import { tick } from 'svelte';

export async function focusMenuCell(
  gridEl: HTMLElement | undefined,
  cellSelector: string,
  index: number
): Promise<void> {
  await tick();
  const cells = gridEl?.querySelectorAll<HTMLElement>(cellSelector);
  cells?.[index]?.focus({ preventScroll: true });
}
```

Refactor `CommandMenu.svelte` to use it.

### 2. Update `MoveMenu.svelte`

Add props parity with CommandMenu:

```typescript
let gridEl = $state<HTMLDivElement | undefined>();
// bind:this={gridEl} on move-menu__grid
```

```typescript
$effect(() => {
  void focusMenuCell(gridEl, '.move-menu__cell:not(.move-menu__cell--empty)', selected);
});
```

Cell button attributes:

```svelte
tabindex={selected === index ? 0 : -1}
aria-current={selected === index ? 'true' : undefined}
```

### 3. Add `:focus-visible` styles to `MoveMenu.svelte`

Copy from `CommandMenu.svelte`:

```css
.move-menu__cell:focus-visible {
  outline: 2px solid var(--vm-mustard);
  outline-offset: -2px;
}
```

### 4. `MoveLearnMenu.svelte` — Decline button

Add:

```css
.move-learn-menu__decline-btn:focus-visible {
  outline: 2px solid var(--vm-mustard);
  outline-offset: 2px;
}
```

Wire Decline to `Escape` alternative in `BattleScene` when `moveLearnMode === 'pick'` (already partially on move learn grid — verify Decline is reachable via Tab from trapped focus order).

### 5. Phase entry focus

In `BattleScene.svelte`, when `session.phase` transitions:

```typescript
$effect(() => {
  const phase = session.phase;
  if (phase === 'command' || phase === 'moveSelect') {
    // roving focus handled by child $effect on selected index
  }
});
```

Ensure `commandIndex` / `moveIndex` reset on phase entry (audit existing reset logic in `battleSession.svelte.ts`).

### 6. Click vs keyboard selection

`onSelect` on menus already updates index. Clicking a cell should:

```typescript
onclick={() => {
  onSelect?.(index);
  onConfirm?.(move); // or separate click-to-confirm — match CommandMenu: click activates
}}
```

**Current `MoveMenu`:** click calls `activate` which selects + confirms — OK.

**CommandMenu:** click activates — OK.

When user Tabs to non-selected cell and presses Enter, native button activation fires — OK.

When user Tabs to cell but uses **window arrows**, `$effect` moves focus — OK after step 2.

### 7. Disabled commands (Deck / Crew)

`CommandMenu` sets `aria-disabled` but `disabled={false}`. Keep — allows focus with toast feedback. Ensure screen reader hears disabled:

Optional: `aria-label="{command.label} (unavailable)"` when disabled.

---

## `battleGridMenu.ts`

No logic change. Existing tests in `battleGridMenu` / session tests cover navigation.

Add test that empty move slot skip behavior still works when `validCount < 4`.

---

## Battle scene loading (`A11Y-009 overlap)

While here, add `aria-live="polite"` on loading copy (see Plan 09) — optional same PR.

---

## Tests

### Manual matrix

| Phase | Arrow keys | Tab | Click | SR |
| :--- | :--- | :--- | :--- | :--- |
| command | moves selection + focus ring | one stop per grid roving | activates | announces current cell |
| moveSelect | same | same | confirms move | move name |
| moveLearn pick | same | Decline reachable | confirm/decline | |
| moveLearn replace | Esc back | | | |

### Automated

Extend `battleSession.test.ts` if focus helpers imported indirectly — not required.

`MoveMenu` component test with `@testing-library/svelte` optional.

---

## Acceptance criteria

- [ ] `MoveMenu` syncs DOM focus to `selected` index (like `CommandMenu`).
- [ ] `MoveMenu` cells have `:focus-visible` ring.
- [ ] Roving `tabindex` on command and move cells (0 on selected, -1 on others).
- [ ] Tab into battle menu → arrow keys move selection without desync.
- [ ] Decline button has visible focus.
- [ ] `pnpm check` passes.

---

## Related

- Plan 08 — may remove `role="menu"` after this lands.
- Plan 05 — Deck Read toggle separate from grid focus.
