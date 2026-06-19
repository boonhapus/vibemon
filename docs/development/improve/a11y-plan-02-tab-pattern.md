# Plan 02 — Tab pattern (tablist / tab / tabpanel)

**Findings:** A11Y-002  
**Severity:** High  
**Effort:** M (1–2 days)  
**Primary files:**

- `vibemon/frontend/src/lib/domains/crew/CrewShowcasePanel.svelte`
- `vibemon/frontend/src/lib/domains/trainer/HatchCandidatePanel.svelte`
- **New (recommended):** `vibemon/frontend/src/lib/ui/tabStrip.ts` — shared keyboard + id helpers

---

## Goal

Tab strips for crew showcase and hatch candidate details must follow the [WAI-ARIA tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/):

- Tabs linked to panels via `aria-controls` / `id`.
- Active tab: `aria-selected="true"`, `tabindex="0"`.
- Inactive tabs: `aria-selected="false"`, `tabindex="-1"`.
- Arrow Left/Right (and optionally Home/End) move focus and selection.
- Panel: `role="tabpanel"`, `aria-labelledby` pointing at tab id.

---

## Current state

Both components render:

```svelte
<div role="tablist" aria-label="…">
  <button role="tab" aria-selected={activeTab === 'stats'} onclick={() => selectTab('stats')}>Stats</button>
  …
</div>
…
<div role="tabpanel">…</div>
```

Missing:

| Requirement | Present? |
| :--- | :--- |
| Stable tab `id`s | No |
| Panel `id`s | No |
| `aria-controls` on tab | No |
| `aria-labelledby` on panel | No |
| Roving `tabindex` | No (all tabs default 0) |
| Arrow key navigation | No |

**Extra complexity:** `CrewShowcasePanel` adds a fourth **Story** tab not present on `HatchCandidatePanel`. Embedded `HatchCandidatePanel` inside showcase reuses `hatchTab` for stats/moves/sources only.

---

## Design decision: shared helper vs inline

**Recommended:** `tabStrip.ts` with zero DOM — pure functions:

```typescript
export type TabKey = string;

export function tabId(prefix: string, key: TabKey): string {
  return `${prefix}-tab-${key}`;
}

export function panelId(prefix: string, key: TabKey): string {
  return `${prefix}-panel-${key}`;
}

export function rovingTabIndex(isSelected: boolean): 0 | -1 {
  return isSelected ? 0 : -1;
}

/** ArrowLeft/Right/Home/End among horizontal tablist */
export function navigateTabList(
  keys: readonly TabKey[],
  current: TabKey,
  key: string
): TabKey {
  const index = keys.indexOf(current);
  if (index === -1) return keys[0] ?? current;
  switch (key) {
    case 'ArrowLeft':
      return keys[(index + keys.length - 1) % keys.length] ?? current;
    case 'ArrowRight':
      return keys[(index + 1) % keys.length] ?? current;
    case 'Home':
      return keys[0] ?? current;
    case 'End':
      return keys[keys.length - 1] ?? current;
    default:
      return current;
  }
}
```

Optional unit test: `tabStrip.test.ts` beside the module.

**Not recommended:** A `TabStrip.svelte` wrapper yet — only two call sites; YAGNI until a third appears.

---

## Implementation — `HatchCandidatePanel.svelte`

### Constants

```typescript
const TAB_KEYS = ['stats', 'moves', 'sources'] as const;
const TAB_PREFIX = 'hatch-candidate'; // or pass via prop when embedded
```

### Tablist markup

```svelte
<div
  class="hatch-candidate-panel__tabs"
  role="tablist"
  aria-label="Candidate details"
  onkeydown={handleTabListKeydown}
>
  {#each TAB_KEYS as key (key)}
    <button
      type="button"
      id={tabId(TAB_PREFIX, key)}
      class="hatch-candidate-panel__tab"
      class:hatch-candidate-panel__tab--active={activeTab === key}
      role="tab"
      aria-selected={activeTab === key}
      aria-controls={panelId(TAB_PREFIX, key)}
      tabindex={rovingTabIndex(activeTab === key)}
      onclick={() => selectTab(key)}
    >
      {key === 'stats' ? 'Stats' : key === 'moves' ? 'Moves' : 'Sources'}
    </button>
  {/each}
</div>
```

### Tabpanel markup

Each panel branch:

```svelte
<div
  id={panelId(TAB_PREFIX, 'stats')}
  role="tabpanel"
  aria-labelledby={tabId(TAB_PREFIX, 'stats')}
  tabindex="0"
  hidden={activeTab !== 'stats'}
>
```

**Note:** Use `hidden` attribute (or `hidden={}`) instead of `{#if}` for inactive panels **if** you want DOM preserved for screen readers — **or** keep `{#if}` and omit inactive panels from accessibility tree entirely (simpler, current behavior). Recommended: keep `{#if}` but when mounted set `aria-labelledby` on visible panel only.

### Keyboard handler

```typescript
function handleTabListKeydown(event: KeyboardEvent) {
  const next = navigateTabList(TAB_KEYS, activeTab, event.key);
  if (next === activeTab) return;
  event.preventDefault();
  selectTab(next);
  // Move focus to new tab button
  document.getElementById(tabId(TAB_PREFIX, next))?.focus();
}
```

Attach to `tablist` container, not window — avoids fighting battle keys.

### Embedded mode

When `embedded={true}` inside `CrewShowcasePanel`, pass `tabPrefix="crew-showcase-hatch"` prop so ids don't collide with outer Story tab ids.

---

## Implementation — `CrewShowcasePanel.svelte`

### Tab keys

```typescript
const SHOWCASE_TABS = ['stats', 'moves', 'sources', 'story'] as const;
const TAB_PREFIX = 'crew-showcase';
```

Apply same pattern as hatch panel for the outer tablist (lines ~160–200).

### Panel wiring

- **Story tab:** panel contains story list (Plan 01 buttons).
- **Other tabs:** embed `HatchCandidatePanel` with `embedded` + shared `activeTab` binding for stats/moves/sources only.

Ensure outer tab `aria-controls` for stats/moves/sources points at panels **inside** embedded hatch panel OR hoist panels to showcase level. **Simplest fix:** give embedded hatch panel a single tabpanel id per tab at the hatch component boundary; outer tabs' `aria-controls` targets those ids — requires `tabPrefix` prop on embedded instance.

### Focus on tab switch

In `selectTab()`:

```typescript
function selectTab(tab: ShowcaseTab) {
  cancelHintClear();
  activeTab = tab;
  panelHint = null;
  onDetailHintChange?.(null);
  // optional: focus first focusable in panel for keyboard users
}
```

---

## CSS

- `[hidden] { display: none !important; }` — if using `hidden` attr with tabpanels.
- Existing `.crew-showcase-panel__tab:focus-visible` / hatch equivalents — keep.

---

## Tests

### Unit

`tabStrip.test.ts`:

- `navigateTabList(['a','b','c'], 'b', 'ArrowRight')` → `'c'`
- `navigateTabList(..., 'a', 'End')` → last key
- Wrap-around Left from first tab

### Manual

1. `/deck/crew` → Tab to tablist → Right arrow cycles Stats→Moves→Sources→Story.
2. Screen reader: selected tab announces "selected"; panel name matches tab.
3. Hatch flow `/hatch` or registration candidate panel — same arrow behavior.
4. No duplicate id in DOM (DevTools → search `id="crew-showcase-tab-stats"`).

---

## Acceptance criteria

- [ ] Every `role="tab"` has unique `id`, `aria-controls`, correct `aria-selected`, roving `tabindex`.
- [ ] Every visible `role="tabpanel"` has `aria-labelledby` referencing its tab.
- [ ] Arrow Left/Right change tab focus and selection; activation does not require Enter.
- [ ] Embedded hatch panel ids namespaced when inside showcase.
- [ ] `pnpm check` + unit tests pass.

---

## Follow-up (optional)

- Home/End support (already in helper).
- Vertical tablists — not used in Vibemon today.
