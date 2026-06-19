# Plan 10 — Sprite alt text, settings affordances, focus polish

**Findings:** A11Y-010, A11Y-011, A11Y-012  
**Severity:** Medium / Low  
**Effort:** S (half day)  
**Primary files:**

- `vibemon/frontend/src/lib/domains/battle/BattleMon.svelte`
- `vibemon/frontend/src/lib/domains/battle/BattleStage.svelte`
- `vibemon/frontend/src/lib/domains/crew/CrewRosterScene.svelte`
- `vibemon/frontend/src/lib/domains/crew/CrewClockFormation.svelte`
- `vibemon/frontend/src/lib/domains/trainer/AdoptCrewModal.svelte`
- `vibemon/frontend/src/lib/domains/trainer/SettingsModal.svelte`
- `vibemon/frontend/src/lib/domains/battle/MoveLearnMenu.svelte`
- `vibemon/frontend/src/lib/ui/ElementBadge.svelte` (optional)

---

## Goal

Close medium-priority visual/accessibility gaps without large refactors.

---

## 1. Battle sprite alt text (A11Y-010)

### Problem

`BattleMon.svelte`:

```svelte
<img class={modelClass} {src} alt="" decoding="async" />
```

Combatant **name** and **level** appear in `BattleHudPlate`, but users who navigate image-by-image or rely on alt when HUD is crowded get no sprite label.

### Fix

Add prop:

```typescript
alt?: string;
```

Default `""` for decorative reuse; battle passes name:

**BattleStage.svelte:**

```svelte
<BattleMon
  spriteSrc={opponent.sprite_url}
  alt={opponent.name}
  …
/>
<BattleMon
  spriteSrc={player.sprite_url}
  alt={player.name}
  …
/>
```

**Img element:**

```svelte
<img class={modelClass} {src} alt={alt ?? ''} decoding="async" />
```

**Duplication note:** HUD already names combatant — alt should be **short**: `{name}` not `{name} level {n}` to reduce redundant announcements when reading whole page. SR users get level from HUD.

### Crew / roster sprites

| File | Current | Recommendation |
| :--- | :--- | :--- |
| `CrewRosterScene.svelte` | `alt=""` | `alt={member.displayName}` on active roster; bench optional |
| `CrewClockFormation.svelte` | `alt=""` | `alt={slot.mon.name}` when mon visible |
| `AdoptCrewModal.svelte` | `alt=""` | `alt={member.name}` on release picker |

Title grass mons (`TitleGrassMon`) — decorative ambient → keep `alt=""`.

Trainer reference sprites — decorative avatar alongside form → keep `alt=""` OR `alt="Trainer avatar preview"`.

---

## 2. Unavailable settings options (A11Y-011)

### Problem

`SettingsModal.svelte`:

```typescript
{ id: 'profile', label: 'Profile', available: false },
```

Disabled buttons skip tab order; sighted users see grey state; screen reader users may not discover unavailable features.

### Fix options

**Option A — Keep disabled, add visible copy (recommended):**

Below options list:

```svelte
<p class="settings-modal__footnote" role="note">
  Profile, Audio, and Controls are coming soon.
</p>
```

**Option B — Enabled but noop with toast:**

`available: true` + click shows `showGameToast('Coming soon', 'amber')` — increases tab stops; worse for clarity.

**Option C — `aria-disabled="true"` with `tabindex="0"`:**

Focusable unavailable items — verbose; not recommended.

Ship **Option A** + ensure disabled buttons retain `aria-label` only (no "dimmed" state needed if footnote documents).

Optional per-button `(coming soon)` in visible label for Profile/Audio/Controls — may clutter UI.

---

## 3. MoveLearnMenu decline focus (A11Y-012)

Add to `MoveLearnMenu.svelte`:

```css
.move-learn-menu__decline-btn:focus-visible {
  outline: 2px solid var(--vm-mustard);
  outline-offset: 2px;
}
```

Ensure Decline is reachable when tabbing from move grid (Plan 04 roving tabindex).

Add `type="button"` explicit (already present).

---

## 4. ElementBadge (optional, A11Y-013)

Current: `<span>{label}</span>` — text content readable when badge is inline.

When badge is **icon-only** in future, add `aria-label={label}`.

No change required today unless audit finds icon-only usage.

---

## 5. Stat hit buttons missing aria-label (HatchCandidatePanel)

Stat row buttons use visible `StatBar` label — OK.

Move buttons — move name visible in pill — OK.

Chart button — has `aria-label="Base stat radar chart"` — OK.

**Audit crew showcase** after Plan 01 — covered there.

---

## Tests

### Manual

1. NVDA image list on battle → opponent and player sprite names appear.
2. Settings modal → footnote readable; disabled items not focusable.
3. Move learn → Tab to Decline → mustard ring.

### axe

Rules: `image-alt` on battle route with seeded battle.

---

## Acceptance criteria

- [ ] `BattleMon` accepts `alt`; battle stage passes combatant names.
- [ ] Crew roster/adopt sprites have meaningful alt where mon identity matters.
- [ ] Settings footnote documents unavailable options.
- [ ] Decline button has `:focus-visible` style.
- [ ] `pnpm check` passes.

---

## Non-goals

- Long `alt` describing sprite appearance (generated mon flavor text).
- Icon-only element badges.
