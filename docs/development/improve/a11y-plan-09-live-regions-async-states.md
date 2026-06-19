# Plan 09 — Live regions and async states

**Findings:** A11Y-009  
**Severity:** Medium  
**Effort:** S (half day)  
**Primary files:**

- `vibemon/frontend/src/lib/domains/battle/BattleScene.svelte`
- `vibemon/frontend/src/lib/domains/trainer/TrainerRegistrationScene.svelte`
- `vibemon/frontend/src/lib/domains/trainer/TrainerLoginScene.svelte`
- `vibemon/frontend/src/lib/domains/trainer/ProviderConfigModal.svelte`
- `vibemon/frontend/src/lib/domains/trainer/AdoptCrewModal.svelte`

---

## Goal

Async and loading UI updates must reach assistive technology without requiring visual scan.

**Already good:**

- `GameToast` — `role="alert"`, `aria-live="assertive"`
- `DialogBox` — `aria-live="polite"` during typewriter
- `TrainerRegistrationScene` / `TrainerLoginScene` — loading `<p aria-live="polite">`
- `ProviderConfigModal` — conditional `aria-live` on fetch state
- `AdoptCrewModal` — `aria-live="polite"` on nickname feedback
- `BattleHudPlate` — `aria-live="polite"` on stat context (Deck Read)

---

## Gaps to fix

### 1. Battle loading

`BattleScene.svelte`:

```svelte
{#if session.phase === 'loading'}
  <p class="battle-scene__loading">Wild vibes stirring...</p>
```

**Fix:**

```svelte
<p class="battle-scene__loading" role="status" aria-live="polite">Wild vibes stirring...</p>
```

When loading completes, node unmounts — next dialog text should live in `DialogBox` (already does).

### 2. Battle phase transitions (optional)

When phase jumps to `defeat` / `fled` / `won`, dialog updates via `DialogBox` — OK if text prop changes trigger live region.

Verify: empty dialog on silent XP beat — ensure HUD XP animation is not the only feedback; Plan 04/05 may add announcements.

### 3. Encounter seek scene

Check `EncounterSeekScene.svelte` for loading/search copy — add `role="status"` if missing.

### 4. Hatch scene bootstrap

`HatchScene.svelte` — audit suspense/loading strings.

### 5. Error surfacing

`BattleScene` uses `showGameToast` for errors — assertive toast OK.

Ensure API errors on registration also toast or live region — grep `session.error`, `loadingText`.

---

## Live region policy

Document in code comment or `improve/README.md`:

| Urgency | Pattern | Example |
| :--- | :--- | :--- |
| Critical / blocking error | `role="alert"` or assertive toast | Network failure, invalid action |
| Progress / waiting | `role="status"` + `aria-live="polite"` | Loading battle, fetching provider |
| Incremental copy | `aria-live="polite"` on dialog | Typewriter dialog |
| Supplementary hint | `aria-live="polite"` + atomic when toggled | Deck Read (Plan 05) |

**Avoid** multiple competing polite regions updating every frame — battle HUD context only when Deck Read active.

---

## Implementation checklist

| File | Change |
| :--- | :--- |
| `BattleScene.svelte` | loading `p` → status live region |
| `EncounterSeekScene.svelte` | audit + fix |
| `HatchScene.svelte` | audit + fix |
| `battleSession.svelte.ts` | no DOM — skip |
| `CrewFormationScene.svelte` | busy/saving states if any text-only |

---

## Tests

### Manual

1. Start battle with throttled network → NVDA announces "Wild vibes stirring..." or subsequent dialog without focus move.
2. Registration slow path → loading line announced (already should work — regression test).

### Automated

Optional component test asserting `aria-live` attribute on loading branch.

---

## Acceptance criteria

- [ ] Battle loading text in polite live region.
- [ ] All route-level loading states grep to `aria-live` or `role="status"`.
- [ ] No new assertive regions for non-critical updates (avoid alert fatigue).
- [ ] `pnpm check` passes.

---

## Non-goals

- Announcing every HP digit change during tween (visual only).
- Server-sent events / websocket copy.
