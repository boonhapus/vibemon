# Battle Sprite Animation Plan

Frame-based animation for battle Vibemon so they read as **alive** on the field. Implements the idle breathing intent in `docs/development/DESIGN.md` §6.3 using the limited-animation language of §6 (stepped frames, never smooth interpolation) and the sprite rules of §5.1.

## Problem

Battle mons are currently single static PNGs (`AssetKind.POSE_BATTLE_BACK` / `POSE_BATTLE_OPPONENT`, fallback `REFERENCE`), rendered as a lone `<img>` in `BattleMon.svelte`. DESIGN §6.3 calls for a subliminal idle breathing loop, but faking it with a CSS transform on a one-frame sprite reads as a *stretched picture*, not a living creature — so it was (correctly) left out of the battle scene. To make idle (and later hurt/attack/faint) feel good we need **actual animation frames**, driven the same stepped way as the rest of the battle motion system.

## Goal

Ship frame-based battle sprite animation, starting with the smallest believable unit:

- **M1 (vertical slice):** a **2-frame idle bob** for a single mon, generated → stored → played back stepped, end to end.
- Later milestones extend to the roster and to additional states (hurt / attack / faint) only where frames beat the existing CSS choreography.

The hard part is **not** the frontend playback — it's getting the generation pipeline to produce frame-to-frame–consistent pixel frames on the locked palette. The plan front-loads that risk in M1.

## Relationship to the Emote Animation Plan

`docs/development/plans/emote-animation-plan.md` covers **paid, async image-to-video `.webm` emotes** for the crew/showcase surface. That is a *different medium and pipeline* and does **not** serve the battle idle:

- Battle sprites must stay **crisp pixel art** (`image-rendering: pixelated`, integer scale, locked palette) and snap between poses (`steps()`), per DESIGN §5–6. Interpolated video is smooth and off-aesthetic here.
- Battle animation is **free and deterministic**, baked at generation time — no runtime jobs, credits, or polling.

So this plan introduces a parallel, lighter track: **pixel frame sheets**, not video. The two can coexist; do not try to reuse the emote video worker for battle idle.

## Locked Design Principles (do not re-litigate)

- **Frame-based, not transform-faked.** Real drawn frames; the CSS transform breathing on a single sprite is explicitly rejected for battle.
- **Stepped playback.** Frame advance uses `steps(N)` / discrete swaps per §6.1 — `--anim-cel-fps: 12` is the target cadence. No cross-fade between frames.
- **Locked palette.** Every frame quantizes to the §2 palette; the whole sheet is quantized **together** so frames share exact colors.
- **Single-pass generation for consistency.** All frames of a state are generated as **one image (a horizontal strip)** in a single call, seeded from the style bible (§5.2), so the generator holds character identity/proportion/outline across frames. Generating frames separately drifts and is banned for M1.
- **Feet-anchored.** Frames share one baseline; reuse the existing `SpriteAnchor` (feet anchor + content bbox) so a bobbing sprite stays planted on its ring.
- **Minimum frames for the cozy register.** Idle = 2 frames (down / up bob). Resist adding frames "to be smooth" — limited animation is the look.

## M1 — 2-Frame Idle, One Mon, End to End

A tight slice that proves generation consistency + storage + stepped playback before touching the roster.

### Data model (reuse what exists)

- Reuse `AssetKind.SHEET = "sprite/sheet.png"` (already defined, currently unused) for the battle idle strip. Key path: `…/v1/r{rev}/sprite/sheet.png`.
- Define a small, frozen sheet descriptor in `app/domains/vibemon/assets.py` (sibling to `SpriteAnchor`):

  ```
  class SpriteSheet(pydantic.BaseModel):  # frozen, extra="forbid"
      frame_count: int          # 2 for idle
      frame_w: int              # source px per frame (48–64, §5.1)
      frame_h: int
      fps: int = 12             # cadence; playback may floor to steps
      layout: Literal["horizontal"] = "horizontal"
  ```

  Attach as an optional field on `AssetRef` (alongside `anchor`), so a `SHEET` asset carries its own frame metadata. No new tables, no migration — same approach as `anchor`.
- ponytail: one state (idle) and one layout (horizontal strip) only in M1. No multi-row atlases, no per-frame timing arrays.

### Backend read surface

- `app/http/battle_read.py::_sprite_url` currently returns a single key. Add a parallel resolver that, **when a `SHEET` asset exists**, returns the sheet key + its `SpriteSheet` metadata; otherwise falls back to the existing single-frame pose/reference (so un-animated mons keep working).
- Extend `BattleCombatantRead` with an optional `sprite_sheet` field (`{ url, frame_count, frame_w, frame_h, fps }`). `sprite_url` stays as the static fallback.
- Frontend treats `sprite_sheet` as preferred, `sprite_url` as fallback.

### Generation pipeline

- Add/extend the mon sprite generator to emit a **horizontal 2-frame idle strip** in a single generation, then:
  - quantize the whole strip to the locked palette together,
  - slice to confirm frame width, derive the shared `SpriteAnchor` from the alpha bbox,
  - persist as the `SHEET` asset with `SpriteSheet` metadata.
- Add an `asset-prompts/` record (per DESIGN §5.1 provenance rule) for the idle-strip prompt, anchored to `base-style.md`. The prompt must instruct: same character, same scale/baseline, only a subtle breathing pose delta between frames; output as one side-by-side strip on a transparent canvas.
- `vibemon/backend/scripts/generate_morph_webp.py` already globs `sprite/reference.png` — check whether it can be extended or whether a dedicated `generate_idle_sheet.py` script is cleaner (likely a new script; keep `morph_webp` for its current purpose).

### Frontend playback

- Add a small `SpriteSheetView.svelte` (or extend `BattleMon.svelte`) that, given a sheet URL + frame metadata, renders one frame via `background-image` + `background-position` (or `object-position` on a sized window) and steps through frames with a CSS keyframe using `steps(frame_count)` over `frame_count / fps` seconds, infinite. `image-rendering: pixelated` throughout.
  - Single-frame fallback path renders today's `<img>` unchanged.
- Pause/replace idle while an action state animation is active (`is-attacking` / `is-hurt` / fainting) so M1 idle never fights the existing lunge/flash choreography.
- Respect `prefersReducedMotion`: hold frame 0 (no loop).

### M1 acceptance

- One chosen mon shows a gentle, stepped 2-frame breathing loop in `/battle/{id}`, planted on its ring, crisp at integer scale.
- A mon **without** a `SHEET` asset still renders its static sprite with no errors.
- Frames share palette and baseline (visual check on `/styleguide` — add an idle-sheet specimen).
- `pytest` (backend read/asset shape) + `pnpm check` + `pnpm vitest` green.

## Later Milestones (deferred — do not build until M1 lands)

| Milestone | Scope | Notes |
| :--- | :--- | :--- |
| **M2 — Roster idle** | Generate idle sheets for all existing mons; batch script + backfill | Gate behind the same fallback so partial coverage is safe |
| **M3 — Action frames** | Add `hurt` / `attack` / `faint` frame states where drawn frames beat the current CSS transforms | Keep CSS lunge/flash for any state without frames; choose per-state |
| **M4 — Pipeline hardening** | Consistency QA (identity drift check), re-roll-on-fail, anchor auto-derivation tuning | Only if M1/M2 show drift problems worth automating |

Animation profile selection stays frontend-derived from `(category, type)` per ADR 0004 — frame states are an *enrichment*, not a backend `animation_key`.

## Open Questions

- **Frame count ceiling:** is 2 enough for idle long-term, or do we want a 3-frame (down / rest / up) for slightly more life? Decide after seeing M1.
- **Sheet vs separate frames on disk:** single strip PNG (chosen) vs individual frame files. Strip wins for generation consistency and fewer assets; revisit only if slicing is painful.
- **Revision semantics:** does a re-generated idle sheet bump the asset `revision` like other assets, and does the old one stay addressable? Follow existing `AssetRef.revision` convention.
- **Does the existing `generate_morph_webp.py` overlap?** Confirm its purpose before adding a sibling script.

## Out of Scope

- Emote `.webm` video animations (owned by `emote-animation-plan.md`).
- Skeletal/mesh deformation (Spine/Live2D) — off-aesthetic for pixel art.
- Runtime/async generation, credits, or job queues for battle frames (these are baked at generation time).
- Backend `animation_key` on moves (ADR 0004 keeps animation frontend-derived).
- Trainer sprite animation.

## Dependencies & References

- `docs/development/DESIGN.md` §5.1 (sprite resolution / provenance), §6.1–6.3 (limited animation, idle breathe).
- `vibemon/backend/app/domains/vibemon/assets.py` — `AssetKind.SHEET`, `SpriteAnchor`, `AssetRef` (extend here).
- `vibemon/backend/app/http/battle_read.py::_sprite_url` — sprite resolution to extend.
- `vibemon/frontend/src/lib/domains/battle/BattleMon.svelte` — playback integration point.
- `vibemon/frontend/asset-prompts/` + `base-style.md` — prompt provenance and style anchor.
- `docs/development/plans/emote-animation-plan.md` — sibling (video) track; intentionally distinct.
