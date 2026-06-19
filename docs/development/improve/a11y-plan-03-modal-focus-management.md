# Plan 03 — Modal focus management

**Findings:** A11Y-003, A11Y-015  
**Severity:** High  
**Effort:** M (1–2 days)  
**Primary files:**

- `vibemon/frontend/src/lib/ui/GameModal.svelte`
- **Consumers (smoke after change):**
  - `SettingsModal.svelte`
  - `ProviderConfigModal.svelte`
  - `AdoptCrewModal.svelte` (uses custom backdrop — audit separately)
  - `MobileViewportGuideModal.svelte`

---

## Goal

When `GameModal` opens:

1. **Focus moves** to the dialog (already partially done).
2. **Tab cycles** within the modal only (focus trap).
3. **Shift+Tab** from first focusable wraps to last.
4. On close, **focus returns** to the element that opened the modal.
5. **Escape** closes (already on `svelte:window`).
6. Background content is **inert** while open (`inert` attribute on backdrop sibling or `aria-hidden` on main app — prefer `inert` where supported).

---

## Current behavior (`GameModal.svelte`)

```58:62:vibemon/frontend/src/lib/ui/GameModal.svelte
$effect(() => {
  if (open && dialogEl) {
    dialogEl.focus();
  }
});
```

| Gap | Detail |
| :--- | :--- |
| No trap | Tab reaches page behind scrim |
| No restore | Closing settings knob doesn't return focus to gear button |
| Scrim | `role="presentation"` + `onclick` only — OK for mouse |
| `tabindex="-1"` on dialog | Correct for programmatic focus; inner buttons remain tabbable |
| `outline: none` on panel | OK if inner controls have `:focus-visible` |

---

## Implementation

### Step 1 — Track trigger element

Add optional prop:

```typescript
/** Element to restore focus on close. If omitted, capture `document.activeElement` at open time. */
restoreFocusTo?: HTMLElement | null;
```

Internal state:

```typescript
let previouslyFocused = $state<HTMLElement | null>(null);

$effect(() => {
  if (open) {
    previouslyFocused =
      restoreFocusTo ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    queueMicrotask(() => dialogEl?.focus());
  } else if (previouslyFocused) {
    previouslyFocused.focus({ preventScroll: true });
    previouslyFocused = null;
  }
});
```

Callers can pass explicit trigger, e.g. Settings knob — optional enhancement.

### Step 2 — Focus trap handler

On dialog panel `onkeydown`:

```typescript
function handleDialogKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    close();
    return;
  }
  if (event.key !== 'Tab' || !dialogEl) return;

  const focusables = dialogEl.querySelectorAll<HTMLElement>(
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  );
  const list = [...focusables].filter((el) => el.offsetParent !== null);
  if (list.length === 0) {
    event.preventDefault();
    dialogEl.focus();
    return;
  }
  const first = list[0]!;
  const last = list[list.length - 1]!;
  const active = document.activeElement;

  if (event.shiftKey && active === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}
```

Attach to the `role="dialog"` div (merge with existing Escape handler).

**ponytail ceiling:** querySelector focusable list is naive (no shadow DOM); sufficient for flat GamePanel modals. Upgrade path: `focus-trap` if modals gain complex portals.

### Step 3 — Inert background

When modal mounts via `portalToBody`:

```typescript
$effect(() => {
  if (!open) return;
  const root = document.querySelector('[data-sveltekit-body]') ?? document.body.firstElementChild;
  if (root instanceof HTMLElement) {
    root.inert = true;
    return () => {
      root.inert = false;
    };
  }
});
```

Verify SvelteKit body wrapper selector in dev — adjust to `document.getElementById('svelte')` or wrap app in `+layout.svelte` with `data-app-root`.

**Fallback for older browsers:** `aria-hidden="true"` on app root while open (ensure modal portal is **outside** hidden subtree — it is on `body`, so OK).

### Step 4 — Initial focus target

Prefer **first focusable** inside dialog over dialog container:

```typescript
function focusInitial() {
  if (!dialogEl) return;
  const first = dialogEl.querySelector<HTMLElement>(
    'button:not([disabled]), input:not([disabled])'
  );
  (first ?? dialogEl).focus({ preventScroll: true });
}
```

Settings modal: first option button receives focus — better than focusing dialog shell.

### Step 5 — Keep `svelte-ignore a11y_no_noninteractive_tabindex`

Document in comment:

```svelte
<!-- svelte-ignore a11y_no_noninteractive_tabindex — dialog shell receives focus when no inner controls; trap in handleDialogKeydown -->
```

### Step 6 — Audit `AdoptCrewModal.svelte`

Uses **custom** modal markup (`role="presentation"`, backdrop button) — not `GameModal`. Either migrate to `GameModal` or duplicate trap/restore in a follow-up ticket **A11Y-003b**.

---

## Consumer updates (optional)

`SettingsNavButton.svelte`:

```svelte
<!-- when opening settings, no change needed if capture activeElement works -->
```

If focus lands on knob before modal opens, capture works. If open is triggered programmatically, pass `restoreFocusTo`.

---

## Tests

### Manual

1. Tab to Settings gear → Enter → focus inside modal (first settings option).
2. Tab through options → from last option Tab wraps to first.
3. Shift+Tab from first wraps to last.
4. Escape closes → focus back on gear.
5. Click scrim closes → focus restored.
6. Open Provider config from hatch — same behavior.

### Unit (light)

Extract `getFocusableElements(container: HTMLElement): HTMLElement[]` to `focusTrap.ts` + test wrap logic with jsdom if vitest setup allows.

---

## Acceptance criteria

- [ ] Tab cannot reach page content behind open `GameModal`.
- [ ] Focus restored to trigger on close (Escape, scrim click, programmatic `open = false`).
- [ ] First focusable focused on open when present.
- [ ] `inert` or `aria-hidden` on app root while modal open.
- [ ] All `GameModal` consumers smoke-tested.
- [ ] `pnpm check` passes.
- [ ] Adopt crew modal tracked (migrate or fix separately).

---

## Non-goals

- Adding a close button to every modal (Escape + scrim sufficient for now).
- Focus trap for non-modal overlays (toasts are `pointer-events: none`).
