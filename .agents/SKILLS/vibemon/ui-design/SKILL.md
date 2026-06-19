---
name: ui-design
description: Refines Vibemon frontend UI against the cozy pixel mid-century spec — locked palette, typography voices, scene/HUD layout, and reusable chrome. Use when designing, polishing, or iterating on Svelte screens, HUD, battle UI, styleguide specimens, scene backgrounds, or visual layout in vibemon/frontend.
paths: vibemon/frontend/**, docs/development/DESIGN.md, docs/development/COLORS.md, docs/development/plans/**/*
---

# Vibemon UI Design

Use this skill for **frontend visual work only**. Pair with `development/svelte-code-writer` for Svelte 5 implementation details.

## Before editing

Read these in order (skim sections relevant to the task):

1. `docs/development/DESIGN.md` — vision, palette lock, typography, scene vs UI layers, animation rules
2. `docs/development/COLORS.md` — canonical hex values
3. `vibemon/frontend/src/lib/ui/tokens.css` — runtime tokens (`--vm-*`, `--anim-*`, HUD sizing)
4. `docs/development/CONTEXT.md` — domain vocabulary (Vibemon, trainer, battle, etc.)

Do **not** import shadcn, Tailwind component libraries, or generic SaaS palettes. Extend existing Vibemon primitives.

## Iteration workflow

Copy and track progress:

```
UI iteration:
- [ ] 1. Identify starting point (component, route, mockup, or styleguide specimen)
- [ ] 2. State the refinement goal in one sentence (layout, hierarchy, tone, spacing, state)
- [ ] 3. Reuse or extend existing primitives before inventing new chrome
- [ ] 4. Apply tokens only — no raw hex, px sizes, or font stacks inline unless adding a token
- [ ] 5. Verify on /styleguide and the target route
- [ ] 6. Check responsive bezel, touch targets, and reduced motion
```

### Step 1 — Anchor the work

| Starting point | First files to open |
| --- | --- |
| Battle HUD / menus | `BattleHudPlate.svelte`, `CommandMenu.svelte`, `DialogBox.svelte`, `MoveMenu.svelte` |
| Scene shell | `SceneFrame.svelte`, `sceneBackgrounds.ts`, `solarPhase.ts` |
| Shared chrome | `GamePanel.svelte`, `GameButton.svelte`, `GameModal.svelte`, `SegmentedHpBar.svelte` |
| New screen | Nearest route under `src/routes/`, wrap in `SceneFrame` |
| Static art | Matching `.mdc` in `asset-prompts/game/`, `base-style*.md` anchors |

### Step 2 — Compose from primitives

Prefer these building blocks (see [references/components.md](references/components.md) for full inventory):

- **Scene shell:** `SceneFrame` — background, film grain, bezel, settings knob
- **Panels:** `GamePanel` tones — `dialog`, `command`, `status`
- **Copy / narration:** `DialogBox` — typewriter, continue cursor, emphasis badges
- **Actions:** `GameButton`, `FreeFormButton`
- **Stats:** `SegmentedHpBar`, `ElementBadge`
- **Proof surface:** `StyleguideSpecimen` on `/styleguide`

Extend props/CSS on these components instead of duplicating panel chrome.

### Step 3 — Enforce the visual contract

**Palette:** Only colors from `COLORS.md` / `--vm-*` tokens. Tobacco Brown replaces black. No off-palette improvisation.

**Typography — three voices (DESIGN.md §3.1):**

| Voice | Token | Use |
| --- | --- | --- |
| Title | `--vm-font-title` | Logo, title screens, large display moments |
| UI | `--vm-font-ui` (Press Start 2P) | Labels, buttons, ALL-CAPS chrome, `DialogBox` when in UI voice |
| Body | `--vm-font-body` (Pixelify Sans) | Dialog hints, descriptions, longer copy |

Use the type ramp (`--vm-text-*`, `--vm-leading-*`) and spacing tokens (`--vm-space-*`). Do not invent font sizes inline.

**Layers (DESIGN.md §5.2):**

- **Scene layer:** 320×180 pixel canvas, `image-rendering: pixelated`, integer scale
- **UI layer:** HTML/CSS HUD at display resolution; touch targets ≥ 44px on smallest side
- **Post-process:** vignette + film grain on the frame (`FilmGrain`), not baked into sprites

**Motion:**

- State-driven: `Tween` / `Spring` from `svelte/motion`; respect `prefersReducedMotion`
- Choreographed beats: `@keyframes` + `--anim-*` + `steps()` timing
- Simple mount/unmount: `transition:` from `svelte/transition`
- Never use smooth easing on battle action states

### Step 4 — Refine, don't restart

When iterating from an existing design:

1. **Name what stays** — palette, panel tone, font voice, layout region
2. **Change one axis per pass** — spacing, hierarchy, copy voice, or animation; not all at once
3. **Prefer token tweaks** — adjust `--vm-hud-*` or panel padding before rewriting markup
4. **Compare contexts** — use `StyleguideSpecimen` chips (parchment / scene green / tobacco bezel)
5. **Preserve domain copy tone** — see `VOICE.md` for player-facing text

### Step 5 — Verify

1. Open `/styleguide` for component-level checks
2. Open the target route (e.g. `/battle`, `/encounters`, trainer setup flows)
3. Resize across desktop width, mobile landscape, and mobile portrait (UI layer reflow per DESIGN.md §5.3)
4. Confirm `--vm-settings-corner-reserve` is respected where footer HUD meets the settings knob
5. Optional: screenshot with `development/playwright-cli` for before/after comparison

## Hard rejects

- Pure `#000` / `#fff`, saturated digital primaries, glassmorphism, soft blur on sprites
- New color hex values outside the locked palette
- shadcn, Radix wrappers, or third-party UI kits
- Smooth CSS gradients on HP bars (use segmented blocks)
- Hover-only affordances on touch-critical paths
- Prompt markdown inside `static/` (use `asset-prompts/` per DESIGN.md §5.1)

## Asset prompts

When static art needs to change:

1. Find or create the matching `.mdc` under `vibemon/frontend/asset-prompts/game/`
2. Reference `base-style.md` (sprites), `base-style-background.md` (backgrounds), or `base-style-icon.md` (HUD icons)
3. Keep palette language aligned with `COLORS.md`

## Related skills

- `development/svelte-code-writer` — Svelte 5 syntax, autofixer, docs lookup
- `development/svelte-core-bestpractices` — runes, snippets, reactivity
- `development/playwright-cli` — visual verification screenshots
- `vibemon/audio-production-pipeline` — music/SFX only, not layout

## Additional resources

- Component inventory and anti-patterns: [references/components.md](references/components.md)
