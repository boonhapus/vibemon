# Plan 01 — Fake buttons and hint controls

**Findings:** A11Y-001  
**Severity:** High  
**Effort:** S (half day)  
**Primary files:**

- `vibemon/frontend/src/lib/domains/crew/CrewShowcasePanel.svelte`

**Reference (good pattern in same file):** EVO/STR ledger hits use real `<button type="button">` with `aria-label`, `onfocus`/`onblur`, and `:focus-visible` styles.

---

## Goal

Every interactive hint control must be a **real button** (or equivalent) with:

1. An accessible **name** (`aria-label` or visible text).
2. **Keyboard activation** (Enter/Space — native for `<button>`).
3. **Focus handlers** mirroring hover (`onfocus` / `onblur`) so keyboard users get the same cabinet guide / detail hint as mouse users.

---

## Problem detail

### Broken: HP and XP runtime rows

```213:231:vibemon/frontend/src/lib/domains/crew/CrewShowcasePanel.svelte
<div
  class="crew-showcase-panel__runtime-row"
  role="button"
  tabindex="0"
  onmouseenter={() => showHint(runtimeHpHint())}
  onmouseleave={() => clearHint(runtimeHpHint())}
>
```

| Issue | Impact |
| :--- | :--- |
| `role="button"` on `<div>` | Screen reader announces "button" with **no name** |
| No `onkeydown` | Enter/Space do nothing |
| No `onfocus` / `onblur` | Keyboard focus does not show hints in guide readout |
| `tabindex="0"` | Focusable but inert — worst-case a11y anti-pattern |

The XP row (`crew-showcase-panel__runtime-row--xp`) has the same defects.

### OK: Story items

Story list items use `role="button"` but **do** include `onfocus`/`onblur`. They still lack keyboard activation unless Enter/Space is wired — converting to `<button>` fixes both.

### OK elsewhere: `HatchCandidatePanel.svelte`

Stat hits, move hits, source rows, chart — all native `<button>` with focus handlers. **Do not regress** when aligning showcase panel.

---

## Implementation

### Step 1 — Replace HP row with `<button>`

**Before:** `<div role="button" tabindex="0" …>`

**After:**

```svelte
<button
  type="button"
  class="crew-showcase-panel__runtime-row"
  aria-label={runtimeHpHint()}
  onmouseenter={() => showHint(runtimeHpHint())}
  onmouseleave={() => clearHint(runtimeHpHint())}
  onfocus={() => showHint(runtimeHpHint())}
  onblur={() => clearHint(runtimeHpHint())}
>
  <span class="crew-showcase-panel__runtime-level">Lv{level}</span>
  <SegmentedHpBar current={currentHp} max={maxHp} />
</button>
```

**CSS adjustments** in the same file's `<style>` block:

- Reset button chrome on `.crew-showcase-panel__runtime-row`:
  - `margin: 0; padding: 0; border: 0; background: transparent; width: 100%; text-align: inherit; font: inherit; color: inherit; cursor: help;`
- Add `:focus-visible` rule matching story items (mustard outline, 2px, offset 2px).
- Ensure `SegmentedHpBar` inside button does not double-announce: the bar already has `aria-label`; the button's `aria-label` should be the **hint sentence** (human-readable), not duplicate the bar's numeric label. Option: pass `label=""` or a prop to suppress inner label when embedded in hint button — **prefer** wrapping bar in `aria-hidden="true"` container and let button label carry HP info:

```svelte
aria-label={runtimeHpHint()}
<!-- visual bar only -->
<span aria-hidden="true">
  <SegmentedHpBar current={currentHp} max={maxHp} label="HP" />
</span>
```

### Step 2 — Replace XP row similarly

```svelte
<button
  type="button"
  class="crew-showcase-panel__runtime-row crew-showcase-panel__runtime-row--xp"
  aria-label={runtimeXpHint()}
  onmouseenter={() => showHint(runtimeXpHint())}
  onmouseleave={() => clearHint(runtimeXpHint())}
  onfocus={() => showHint(runtimeXpHint())}
  onblur={() => clearHint(runtimeXpHint())}
>
  <span aria-hidden="true">
    <XpProgressBar ratio={xpBarRatio} />
  </span>
</button>
```

### Step 3 — Convert story items to `<button>`

**Before:** `<div role="button" tabindex="0" …>`

**After:**

```svelte
<button
  type="button"
  class="crew-showcase-panel__story-item"
  aria-label={hint}
  onmouseenter={() => showHint(hint)}
  onmouseleave={() => clearHint(hint)}
  onfocus={() => showHint(hint)}
  onblur={() => clearHint(hint)}
>
  <span class="crew-showcase-panel__story-title">{entry.title}</span>
  <p class="crew-showcase-panel__story-body">{entry.body}</p>
</button>
```

- Reset button styles (same pattern as runtime row).
- Keep `cursor: help` — hints are supplementary, not primary actions.
- Story body remains readable; `aria-label` gives concise hint for activation context.

### Step 4 — Grep for regressions

```bash
rg 'role="button"' vibemon/frontend/src
```

Any remaining `role="button"` on non-button elements should be ticketed or fixed in this PR.

---

## Tests

### Manual

1. Open `/deck/crew`, select a member, Stats tab.
2. Tab to HP row → guide readout shows HP hint; Enter does not navigate away.
3. Tab to XP row → XP hint appears.
4. Story tab → Tab through story cards → hints update; Enter does not submit forms.

### Automated (optional, small)

If `onDetailHintChange` is testable via component test:

```typescript
// crewShowcasePanel.test.ts — minimal
it('shows HP hint on focus', async () => { ... });
```

Not required for merge if manual checklist passes; Plan 11 adds axe coverage on `/deck/crew`.

---

## Acceptance criteria

- [ ] No `role="button"` + `tabindex="0"` on `<div>` in `CrewShowcasePanel.svelte`.
- [ ] HP/XP/story hint controls are `<button type="button">` with descriptive `aria-label`.
- [ ] Focus and hover both drive `showHint` / `clearHint`.
- [ ] `:focus-visible` visible on all new buttons.
- [ ] `pnpm check` passes.
- [ ] VoiceOver/NVDA: Tab to HP control → announces hint text (via label or live guide region).

---

## Non-goals

- Changing hint copy or guide panel layout.
- Refactoring `HatchCandidatePanel` (already correct).
