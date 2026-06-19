# Vibemon UI component inventory

Canonical chrome lives in `vibemon/frontend/src/lib/ui/`. Domain screens compose these under `src/lib/domains/` and `src/routes/`.

## Core chrome (`$lib/ui/`)

| Component | Role | Notes |
| --- | --- | --- |
| `SceneFrame` | Full-screen scene shell | Background image or `BandedBackground`, overlay slot, film grain, bezel, optional settings knob |
| `GamePanel` | 9-slice pixel panel | Tones: `dialog`, `command`, `status` — wood/bevel frame, inset surface |
| `DialogBox` | Narration panel | Wraps `GamePanel`; typewriter, continue ▼, emphasis coloring, UI vs body voice |
| `GameButton` | Primary command control | Tactile pressed state; use in command menus |
| `FreeFormButton` | Secondary / inline action | Lighter chrome than `GameButton` |
| `GameModal` | Blocking overlay | Use sparingly; match panel styling |
| `GameToast` | Transient feedback | Corner/toast placement respects bezel tokens |
| `SegmentedHpBar` | HP display | Segmented blocks, Sage → Amber → Brick thresholds |
| `ElementBadge` | Type pill | Pixel pill with dither; type colors from palette |
| `TrainerNameInput` | Text entry | Trainer setup flows |
| `PixelIcon` | Raster HUD icon slot | For custom game icons, not Lucide |
| `BandedBackground` | Procedural fallback bg | When no `backgroundSrc` image |
| `FilmGrain` | Screen-space grain | Post-process over frame, not per-sprite |
| `StyleguideSpecimen` | Proof grid | Three background chips for optical balance |

## Domain compositions

| Area | Key files |
| --- | --- |
| Battle | `domains/battle/BattleScene.svelte`, `BattleStage.svelte`, `BattleHudPlate.svelte`, `CommandMenu.svelte`, `MoveMenu.svelte`, `MoveLearnMenu.svelte`, `BattleMon.svelte` |
| Encounters | `domains/battle/EncounterSeekScene.svelte`, `routes/encounters/` |
| Crew / trainer | `domains/crew/`, `domains/trainer/SettingsNavButton.svelte` |
| Backgrounds | `domains/game/sceneBackgrounds.ts`, `solarPhase.ts` |
| Styleguide | `routes/styleguide/+page.svelte` |

## Token groups (`tokens.css`)

| Group | Examples | When to touch |
| --- | --- | --- |
| Palette | `--vm-parchment`, `--vm-tobacco`, `--vm-plum` | New semantic color needs ADR + COLORS.md first |
| Typography | `--vm-font-*`, `--vm-text-*`, `--vm-leading-*` | HUD readability tweaks |
| Spacing / radius | `--vm-space-*`, `--vm-radius-*` | Layout rhythm |
| HUD layout | `--vm-hud-*`, `--vm-bezel-w`, `--vm-settings-corner-*` | Battle/footer chrome |
| Animation | `--anim-*` | Shared choreographies |

Add new tokens at `:root` with a comment pointing to the DESIGN.md section that owns the decision.

## Anti-patterns

| Don't | Do instead |
| --- | --- |
| Copy panel CSS into a route | Wrap content in `GamePanel` / `DialogBox` |
| Hard-code `#3D2B1F` in a component | `var(--vm-tobacco)` |
| New button styled from scratch | Extend `GameButton` or `FreeFormButton` |
| Lucide icons in diegetic game HUD | `PixelIcon` or assets under `static/game/icons/` |
| Blur/filter on Vibemon sprites | Palette-based atmospheric perspective |
| Large mustard fills | Soft Mustard for cursor/small accents only |
| Inline `@keyframes` with random durations | `--anim-*` tokens + `steps()` |
| Skip `/styleguide` after chrome changes | Add or update a `StyleguideSpecimen` row |

## Responsive checklist

- Scene pins to top on portrait; UI layer reflows below (DESIGN.md §5.3)
- Touch targets on command layer ≥ 44px
- `env(safe-area-inset-*)` respected on mobile
- Settings knob corner reserve: `--vm-settings-corner-reserve`
- Integer scale for 320×180 scene; bezel fills remainder
