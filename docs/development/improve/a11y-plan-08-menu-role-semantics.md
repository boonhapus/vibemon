# Plan 08 — Menu role semantics

**Findings:** A11Y-008  
**Severity:** Medium  
**Effort:** S (half day)  
**Depends on:** Plan 04 (battle grid behavior stable)  
**Primary files:**

- `vibemon/frontend/src/lib/domains/battle/CommandMenu.svelte`
- `vibemon/frontend/src/lib/domains/battle/MoveMenu.svelte`
- `vibemon/frontend/src/lib/domains/battle/MoveLearnMenu.svelte` (inherits MoveMenu)
- `vibemon/frontend/src/lib/domains/title/TitleScene.svelte`
- `vibemon/frontend/src/lib/domains/trainer/SettingsModal.svelte`
- `vibemon/frontend/src/lib/domains/crew/CrewFormationMenu.svelte`

---

## Goal

Fix incorrect `role="menu"` usage. ARIA **menu** widgets expect:

- Arrow keys between items (not Tab between every item in all browsers)
- Often **one** tab stop with roving focus
- `menuitem` children, not mixed patterns

Vibemon grids are **button toolbars** or **navigation lists**, not application menus.

---

## Recommended mapping

| Component | Current | Target | Rationale |
| :--- | :--- | :--- | :--- |
| `CommandMenu` | `role="menu"` | `role="toolbar"` + `aria-label="Battle commands"` | 2×2 action grid |
| `MoveMenu` | `role="menu"` | `role="toolbar"` + `aria-label="Moves"` | Same |
| `TitleScene` list | `role="menu"` on `<ul>` | Remove role; keep `<nav aria-label="Title menu">` | Links/buttons in nav |
| `SettingsModal` | `role="menu"` on `<ul>` | Remove role; list of buttons in dialog | Native dialog navigation |
| `CrewFormationMenu` | two `role="menu"` grids | `role="toolbar"` each with labels | Position + command grids |

**Do not use** `role="menubar"` — not applicable.

---

## Implementation

### CommandMenu / MoveMenu

```svelte
<div
  bind:this={gridEl}
  class="command-menu__grid"
  role="toolbar"
  aria-label="Battle commands"
>
  <button type="button" …>
```

Remove any `role="menuitem"` if present (currently none — buttons are direct children, which is valid for toolbar in practice; strict APG uses `role="group"` per cluster — optional).

**Note:** WAI-ARIA toolbar pattern expects arrow keys between controls. Plan 04 implements roving tabindex + window arrows — document that **toolbar** + custom key handling is intentional for JRPG UX.

### TitleScene

```svelte
<ul class="title-scene__menu-list">
```

Remove `role="menu"`. `GameButton` children remain `<button>`.

### SettingsModal

```svelte
<ul class="settings-modal__options">
  <li …>
    <FreeFormButton …>
```

Remove `role="menu"` and `role="none"` on li (plain list semantics OK inside dialog).

### CrewFormationMenu

Both grids → `role="toolbar"` with existing `aria-label` values.

---

## `aria-current` vs `aria-pressed`

Battle cells use `aria-current="true"` for selection. For toolbar toggle pattern, **`aria-pressed`** on the active command (like `GameButton selected`) may be clearer.

Optional alignment:

```svelte
aria-pressed={selected === index ? true : undefined}
```

Pick one convention across CommandMenu and MoveMenu — prefer **`aria-current="true"`** already in use (grid location, not toggle).

---

## Keyboard behavior documentation

Add comment above toolbar divs:

```svelte
<!-- Toolbar: arrow keys handled by BattleScene window listener; roving tabindex on cells (Plan 04) -->
```

---

## Tests

### Manual screen reader

1. NVDA on command grid → should **not** announce "menu"; announces "Battle commands toolbar" (exact wording varies by AT).
2. Title nav → "Title menu navigation region".
3. Settings → list of buttons, not menu.

### axe

Rule `aria-allowed-role` — should pass after change.

---

## Acceptance criteria

- [ ] No `role="menu"` in listed files (grep clean).
- [ ] Toolbars have `aria-label`.
- [ ] Title and settings use semantic nav/list without menu roles.
- [ ] Battle keyboard navigation unchanged (Plan 04).
- [ ] `pnpm check` passes.

---

## Alternative (not recommended)

Implement full ARIA menu pattern with `role="menuitem"`, roving tabindex, and arrow keys **only** on menu container — duplicates BattleScene window handler; reject unless dropping window-level keys.
